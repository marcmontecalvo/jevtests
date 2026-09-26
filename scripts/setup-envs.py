"""Clone/pin upstreams and build one isolated venv per upstream (envs/<name>).

  uv run python scripts/setup-envs.py --clone             # clone/checkout pinned commits only
  uv run python scripts/setup-envs.py --group small       # venvs needed by a model group
  uv run python scripts/setup-envs.py --upstream kev reflex
  uv run python scripts/setup-envs.py --pin               # record current upstream HEADs
  uv run python scripts/setup-envs.py --verify            # GPU check of every built venv

Every build ends with a GPU check (a real kernel launch in the venv, torch or MLX):
a CPU-only or wrong-architecture build fails here instead of silently running slow.

Pins live in config/upstreams.lock.json (committed).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.config import CONFIG, ENVS, UPSTREAM, models_config, select_models  # noqa: E402
from harness.sysinfo import env_versions  # noqa: E402

LOCK = CONFIG / "upstreams.lock.json"


def git(*a, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)


def clone_all(upstreams: dict) -> None:
    pins = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    UPSTREAM.mkdir(exist_ok=True)
    for name, up in upstreams.items():
        d = UPSTREAM / up["dir"]
        if not d.exists():
            r = git("clone", "--filter=blob:none", up["repo"], str(d))
            if r.returncode:
                print(f"FAIL clone {name}: {r.stderr.strip()[:200]}")
                continue
        pin = pins.get(name)
        if pin:
            git("fetch", "--quiet", "origin", cwd=d)
            r = git("checkout", "--quiet", pin, cwd=d)
            state = "pinned" if r.returncode == 0 else f"PIN FAILED ({r.stderr.strip()[:80]})"
        else:
            state = "unpinned (run --pin)"
        print(f"{name:18s} {git('rev-parse', '--short', 'HEAD', cwd=d).stdout.strip()}  {state}")


def pin_all(upstreams: dict) -> None:
    pins = {name: git("rev-parse", "HEAD", cwd=UPSTREAM / up["dir"]).stdout.strip()
            for name, up in upstreams.items() if (UPSTREAM / up["dir"]).exists()}
    LOCK.write_text(json.dumps(pins, indent=2) + "\n")
    print(f"wrote {LOCK} ({len(pins)} upstreams)")


def build_env(name: str, up: dict) -> bool:
    if not up.get("env_setup"):
        print(f"skip  {name}: no env_setup (not served directly)")
        return True
    env_dir = ENVS / name
    cmd = up["env_setup"].format(env=env_dir)
    env = {**os.environ, "UV_PROJECT_ENVIRONMENT": str(env_dir), "UV_TORCH_BACKEND": "auto"}
    env.pop("VIRTUAL_ENV", None)   # set by `uv run`; would make uv warn about the harness venv
    # uv-managed CPython ships Python.h; distro pythons often don't (python3.x-dev), and
    # Triton JIT-compiles a C launcher at runtime -> "fatal error: Python.h" otherwise.
    env["UV_PYTHON_PREFERENCE"] = "only-managed"
    print(f"build {name}: {cmd}")
    shutil.rmtree(env_dir, ignore_errors=True)   # clean rebuild: never inherit an old interpreter
    r = subprocess.run(cmd, shell=True, cwd=UPSTREAM / up["dir"], env=env)
    if r.returncode:
        print(f"FAIL  {name} (build)")
        return False
    return verify_env(name)


def verify_env(name: str) -> bool:
    v = env_versions(str(ENVS / name))
    if "torch" in v:
        lib = f"torch {v['torch']} (cuda {v.get('torch_cuda')})"
    elif "mlx_device" in v:
        lib = f"mlx {v.get('mlx', '?')} on {v['mlx_device']}"
    else:
        lib = "no torch/mlx"
    if v.get("python_headers") is False:
        print(f"FAIL  {name}: venv Python has no headers (Python.h); Triton kernels will fail to build."
              f" Rebuild: uv run python scripts/setup-envs.py --upstream {name}")
        return False
    if v.get("gpu_ok"):
        print(f"ok    {name}: {lib}, GPU kernel ok {v.get('capability', '')}")
        return True
    why = v.get("gpu_error") or ("CPU-only build" if v.get("cuda_available") is False else v.get("error", "no GPU library"))
    print(f"FAIL  {name}: {lib}: {why}")
    if v.get("arch_list"):
        print(f"      built for {v['arch_list']}, device is {v.get('capability')}")
    return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--clone", action="store_true")
    ap.add_argument("--pin", action="store_true")
    ap.add_argument("--group")
    ap.add_argument("--upstream", nargs="*", default=[])
    ap.add_argument("--verify", action="store_true", help="GPU-check existing venvs, no builds")
    args = ap.parse_args()
    upstreams = models_config()["upstreams"]

    if args.clone:
        clone_all(upstreams)
    if args.pin:
        pin_all(upstreams)
    wanted = list(args.upstream)
    if args.group:
        wanted += [s["upstream"] for s in select_models(group=args.group, include_jev=False)
                   if s.get("upstream")]
    if args.verify:
        built = [n for n in upstreams if (ENVS / n).exists()]
        sys.exit(0 if all([verify_env(n) for n in built]) else 1)
    ENVS.mkdir(exist_ok=True)
    failed = [n for n in dict.fromkeys(wanted) if not build_env(n, upstreams[n])]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
