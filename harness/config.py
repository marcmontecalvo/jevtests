"""Config loading (config/*.yaml, .env) and model selection."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
UPSTREAM = ROOT / "upstream"
ENVS = ROOT / "envs"
DATA = ROOT / "data"
CASES = DATA / "cases"
RESULTS = ROOT / "results"
REPORTS = ROOT / "reports"
LOGS = ROOT / "logs"
CACHE = ROOT / "cache"
DB_PATH = RESULTS / "benchmark.sqlite"


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env reader; real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        if v:
            os.environ.setdefault(k.strip(), v)


class _Loader(yaml.SafeLoader):
    """SafeLoader with YAML 1.2 floats: PyYAML (1.1) reads `1.0e9` as a string."""


_Loader.add_implicit_resolver(
    "tag:yaml.org,2002:float",
    re.compile(r"^[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?$|^[-+]?\d+[eE][-+]?\d+$"),
    list("-+0123456789."))


def _yaml(name: str) -> dict:
    return yaml.load((CONFIG / name).read_text(encoding="utf-8"), Loader=_Loader) or {}


def models_config() -> dict:
    return _yaml("models.yaml")


def datasets_config() -> dict:
    return _yaml("datasets.yaml")


def benchmark_config() -> dict:
    return _yaml("benchmark.yaml")


def model_specs() -> dict[str, dict]:
    """All models with defaults applied and `name` filled in."""
    cfg = models_config()
    defaults = cfg.get("defaults", {})
    out = {}
    for name, spec in cfg["models"].items():
        m = {**defaults, **spec, "name": name}
        m.setdefault("kind", "http")
        m.setdefault("enabled", True)
        if m.get("upstream"):
            up = cfg["upstreams"][m["upstream"]]
            m["upstream_dir"] = str(UPSTREAM / up["dir"])
            m["env_dir"] = str(ENVS / m["upstream"])
        out[name] = m
    return out


def select_models(names: list[str] | None = None, group: str | None = None,
                  include_jev: bool = True) -> list[dict]:
    specs = model_specs()
    bench = benchmark_config()
    chosen: list[str] = []
    if group:
        if group == "all":
            chosen += list(specs)
        else:
            g = bench["groups"][group]
            chosen += g.get("models", [])
            if "max_parameters" in g:
                chosen += [n for n, m in specs.items()
                           if m.get("params") and m["params"] <= g["max_parameters"]]
    chosen += names or []
    if include_jev:
        chosen += bench.get("always_include", [])
    unknown = [n for n in chosen if n not in specs]
    if unknown:
        raise SystemExit(f"unknown model(s): {', '.join(unknown)}")
    seen, result = set(), []
    for n in chosen:
        if n not in seen and specs[n]["enabled"]:
            seen.add(n)
            result.append(specs[n])
    return result


def env_bin(env_dir: str | Path) -> Path:
    return Path(env_dir) / ("Scripts" if sys.platform == "win32" else "bin")


def env_python(env_dir: str | Path) -> Path:
    return env_bin(env_dir) / ("python.exe" if sys.platform == "win32" else "python")


_HF_RE = re.compile(r"\{hf:([^}]+)\}")


def expand(template: str, spec: dict, port: int | None = None) -> str:
    """Fill {python} {bin} {port} {root} {dir} {env} {name} {hf:REPO} in a command template.
    Literal shell braces must be doubled: ${{HF_HOME}}."""
    s = _HF_RE.sub(lambda m: hf_snapshot(m.group(1)), template)
    env_dir = spec.get("env_dir", "")
    return s.format(
        python=env_python(env_dir) if env_dir else sys.executable,
        bin=env_bin(env_dir) if env_dir else "",
        port=port if port is not None else "",
        root=ROOT, dir=spec.get("upstream_dir", ""), env=env_dir, name=spec.get("name", ""),
    )


def hf_snapshot(repo: str) -> str:
    """Local dir of a repo at the revision download-models.py pinned (cache/models.json).
    download-models fetches by commit sha, which never writes refs/main, so a plain
    local_files_only lookup of `main` fails even when the files are there."""
    import json

    from huggingface_hub import snapshot_download
    manifest = CACHE / "models.json"
    revs = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    sha = revs.get(repo, {}).get("sha")
    # pinned sha + cached -> no network; otherwise fetch (same as models that download at load)
    return snapshot_download(repo, revision=sha)
