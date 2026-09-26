"""Write reports/SETUP_STATUS.md: hardware, deps, upstreams, checkpoints, disk estimates,
smoke results, datasets, Jev API status and blockers.

  uv run python scripts/setup-status.py [--smoke-run smoke] [--offline]
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import importlib.metadata as md
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.loaders import load_meta  # noqa: E402
from harness.config import (DB_PATH, ENVS, REPORTS, benchmark_config, datasets_config,  # noqa: E402
                            load_dotenv, model_specs, models_config, select_models, UPSTREAM)
from harness.hub import resolve  # noqa: E402
from harness.sysinfo import env_versions, git_commit, host  # noqa: E402


def tool_version(cmd: list[str]) -> str:
    if not shutil.which(cmd[0]):
        return "not found"
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return (out.stdout or out.stderr).strip().splitlines()[0][:100]
    except (OSError, subprocess.SubprocessError, IndexError):
        return "error"


def gb(b):
    return f"{b / 1e9:.1f}"


def smoke_rows(run_id: str) -> list[dict]:
    if not DB_PATH.exists():
        return []
    from harness.db import DB
    from harness.report import RunData, model_summary
    db = DB(DB_PATH)
    d = RunData(db, run_id)
    return [model_summary(d, m) for m in sorted(d.models)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke-run", default="smoke")
    ap.add_argument("--offline", action="store_true", help="skip HF + Jev network checks")
    args = ap.parse_args()
    load_dotenv()
    specs = model_specs()
    cfg = models_config()
    L = ["# Setup status", "", f"Generated {datetime.datetime.now():%Y-%m-%d %H:%M} by "
         "`scripts/setup-status.py`.", ""]

    # ---- hardware
    h = host()
    L += ["## Detected hardware", "",
          f"- OS: {h['os']} ({h['machine']}), Python {h['python']}",
          f"- CPU cores: {h['cpu_count']}, RAM: {h['ram_gb']} GB",
          f"- GPUs: " + ("; ".join(f"{g['name']} ({g['memory']}, driver {g['driver']})"
                                   for g in h["gpus"]) or "none detected"),
          f"- CUDA (driver): {h['cuda_driver_version'] or 'n/a'}",
          f"- Repo commit: {h['repo_commit'] or 'uncommitted'}{' (dirty)' if h['repo_dirty'] else ''}", ""]

    # ---- deps
    L += ["## Installed dependencies", "", "| Component | Version |", "|---|---|"]
    for t in (["uv", "--version"], ["git", "--version"], ["docker", "--version"],
              ["nvidia-smi", "--version"]):
        L.append(f"| {t[0]} | {tool_version(t)} |")
    for p in ("httpx", "datasets", "huggingface_hub", "pyyaml", "psutil"):
        try:
            L.append(f"| {p} (harness) | {md.version(p)} |")
        except md.PackageNotFoundError:
            L.append(f"| {p} (harness) | missing |")
    L += ["", "Per-upstream venvs (`envs/`):", "", "| Upstream | torch | CUDA | transformers | other |",
          "|---|---|---|---|---|"]
    for name in cfg["upstreams"]:
        v = env_versions(str(ENVS / name)) if (ENVS / name).exists() else None
        if v is None:
            L.append(f"| {name} | not built | | | |")
            continue
        other = ", ".join(f"{k} {v[k]}" for k in ("sglang", "vllm", "mlx", "peft") if k in v)
        L.append(f"| {name} | {v.get('torch', '–')} | {v.get('torch_cuda', '–')} "
                 f"(avail={v.get('cuda_available')}) | {v.get('transformers', '–')} | {other} |")
    L.append("")

    # ---- upstreams
    L += ["## Upstream repositories", "", "| Upstream | Repo | Commit |", "|---|---|---|"]
    for name, up in cfg["upstreams"].items():
        d = UPSTREAM / up["dir"]
        L.append(f"| {name} | {up['repo']} | `{git_commit(d) or 'not cloned'}` |")
    L.append("")

    # ---- checkpoints + disk
    blockers = [f"`{n}`: {m['blocker']}" for n, m in specs.items() if not m["enabled"]]
    infos = {} if args.offline else resolve(
        list(dict.fromkeys(r for m in specs.values() for r in m.get("hf") or [])))
    for repo, i in infos.items():
        if "error" in i:
            blockers.append(f"HF repo `{repo}` not reachable: {i['error']}")
    L += ["## Discovered checkpoints", "",
          "| Model | Upstream | Params | HF repos (+ bases) | GB | Enabled |", "|---|---|---:|---|---:|---|"]

    def closure(repos):
        out, q = [], list(repos)
        while q:
            r = q.pop(0)
            if r in out:
                continue
            out.append(r)
            b = infos.get(r, {}).get("base_model")
            if b and b in infos:
                q.append(b)
        return out

    for n, m in specs.items():
        repos = closure(m.get("hf") or [])
        size = sum(infos.get(r, {}).get("bytes", 0) for r in repos)
        p = m.get("params")
        L.append(f"| {n} | {m.get('upstream') or 'cloud'} | "
                 f"{'–' if not p else (f'{p/1e9:.1f}B' if p >= 1e9 else f'{p/1e6:.0f}M')} | "
                 f"{', '.join(repos) or '–'} | {gb(size) if size else '–'} | "
                 f"{'yes' if m['enabled'] else 'no'} |")
    L += ["", "## Estimated disk requirements", "", "| Group | Models | Unique repos | GB |",
          "|---|---:|---:|---:|"]
    for g in [*benchmark_config()["groups"], "all"]:
        ms = select_models(group=g, include_jev=False)
        repos = set(r for m in ms for r in closure(m.get("hf") or []))
        L.append(f"| {g} | {len(ms)} | {len(repos)} | "
                 f"{gb(sum(infos.get(r, {}).get('bytes', 0) for r in repos))} |")
    L += ["", "Sizes are current-revision file totals on the Hub; local-jev fetches its own "
          "models (not counted). Groups overlap.", ""]

    # ---- smoke
    rows = smoke_rows(args.smoke_run)
    L += [f"## Smoke test (run `{args.smoke_run}`)", ""]
    if rows:
        L += ["| Model | Status | Answered | Errors | Accuracy | p50 ms | Load s |",
              "|---|---|---:|---:|---:|---:|---:|"]
        for r in rows:
            acc = "–" if r["accuracy"] is None else f"{r['accuracy']:.3f}"
            p50 = "–" if r["p50_ms"] is None else f"{r['p50_ms']:.0f}"
            ls = "–" if r["load_s"] is None else f"{r['load_s']:.1f}"
            L.append(f"| {r['model']} | {r['status']} | {r['answered']} | {r['errors']} | "
                     f"{acc} | {p50} | {ls} |")
            if r["status"] == "load_failed":
                blockers.append(f"`{r['model']}` failed to load in smoke run (see logs/{r['model']}.log)")
    else:
        L.append("Not run yet.")
    L.append("")

    # ---- special handling
    L += ["## Models requiring special handling", ""]
    L += [f"- `{n}`: {m['notes']}" for n, m in specs.items() if m.get("notes") and m["enabled"]]
    L += ["- `jevlike` (vinnylarouge): inspected only — a training toolkit whose checkpoints are "
          "game-specific (doom/chess), not a general Choice/Score/Noul contestant.",
          "- `jev-local` (us): deterministic stub scorer excluded; only its HF logprob scorer is benchmarked.",
          "- `simple-jev`, `local-jev`, `jevbench`: evaluation code inspected; JevBench public "
          "tasks are used verbatim as our primary dataset.", ""]

    # ---- datasets
    L += ["## Datasets", "", "| Dataset | Cases | Source | Split | Revision | License | Downloaded |",
          "|---|---:|---|---|---|---|---|"]
    for name in datasets_config():
        meta = load_meta(name)
        if meta:
            L.append(f"| {name} | {meta['cases']} | {meta['source']} | {meta.get('split')} | "
                     f"`{str(meta.get('revision'))[:12]}` | {meta.get('license')} | "
                     f"{meta.get('download_date', '–')} |")
        else:
            L.append(f"| {name} | not prepared | | | | | |")
            blockers.append(f"dataset `{name}` not prepared")
    L.append("")

    # ---- jev
    L += ["## Jev API status", ""]
    if args.offline:
        L.append("Skipped (--offline).")
    elif not (os.environ.get("JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY")):
        L.append("JEV_API_KEY not set.")
        blockers.append("JEV_API_KEY not set")
    else:
        sys.path.insert(0, str(Path(__file__).parent))
        smoke = __import__("smoke-test")
        try:
            status = asyncio.run(smoke.jev_probe())
        except Exception as e:  # noqa: BLE001
            status = f"FAIL {type(e).__name__}: {e}"
        L.append(status)
        if status.startswith("FAIL"):
            blockers.append(f"Jev API: {status}")
    L.append("")

    L += ["## Blockers / incompatibilities", ""] + [f"- {b}" for b in blockers] + [""]
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / "SETUP_STATUS.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
