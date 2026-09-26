"""Fast harness sanity check (no model downloads):
  1. config validation (every model's upstream/env/templates resolve)
  2. prepared datasets present
  3. one live Jev cloud request, if JEV_API_KEY is set

  uv run python scripts/smoke-test.py [--offline]

The 10-20 case contestant smoke benchmark is:
  uv run python scripts/run-benchmark.py --run smoke --group small --limit 4 --modes accuracy,latency
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.loaders import load_cases  # noqa: E402
from harness.config import (UPSTREAM, benchmark_config, datasets_config, load_dotenv,  # noqa: E402
                            model_specs, models_config)
from harness.schema import Case  # noqa: E402

PROBE = Case(id="smoke-noul", dataset="smoke", type="noul",
             state="Help! My payouts have been failing for 3 days.",
             question="Does this convey urgency?", criteria=None, expected=True)


def check_config() -> list[str]:
    problems = []
    cfg = models_config()
    for name, m in model_specs().items():
        if m.get("kind") == "cloud" or not m["enabled"]:
            continue
        if m.get("upstream") not in cfg["upstreams"]:
            problems.append(f"{name}: unknown upstream {m.get('upstream')!r}")
            continue
        if not Path(m["upstream_dir"]).exists():
            problems.append(f"{name}: upstream not cloned ({m['upstream_dir']})")
        if not m.get("serve") and not m.get("base_url"):
            problems.append(f"{name}: needs `serve` or `base_url`")
    bench = benchmark_config()
    specs = model_specs()
    for g, spec in bench["groups"].items():
        for n in spec.get("models", []):
            if n not in specs:
                problems.append(f"group {g}: unknown model {n}")
    for d in bench["datasets"]:
        if d not in datasets_config():
            problems.append(f"benchmark.yaml dataset {d} not in datasets.yaml")
    return problems


async def jev_probe() -> str:
    from adapters.jev_cloud import JevCloud
    spec = {**model_specs()["typesafe-jev-latest"]}
    m = JevCloud(spec)
    await m.load()
    try:
        r = await m.evaluate(PROBE)
    finally:
        await m.unload()
    if r.error:
        return f"FAIL {r.error}"
    return (f"ok  served={m.provenance.get('served_model')} noul={r.probabilities['true']:.3f} "
            f"latency={r.latency_ms:.0f}ms")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    failed = False

    problems = check_config()
    print(f"[config]   {'ok' if not problems else f'{len(problems)} problem(s)'}")
    for p in problems:
        print(f"           - {p}")
    failed |= bool(problems)

    for name in benchmark_config()["datasets"]:
        try:
            print(f"[dataset]  ok    {name}: {len(load_cases(name))} cases")
        except FileNotFoundError:
            print(f"[dataset]  MISSING {name} (run scripts/prepare-datasets.py)")
            failed = True

    if not args.offline:
        if os.environ.get("JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY"):
            try:
                status = asyncio.run(jev_probe())
            except Exception as e:  # noqa: BLE001
                status = f"FAIL {type(e).__name__}: {e}"
            print(f"[jev]      {status}")
            failed |= status.startswith("FAIL")
        else:
            print("[jev]      skipped (JEV_API_KEY not set)")
    print("[upstream] " + ", ".join(sorted(p.name for p in UPSTREAM.iterdir()))
          if UPSTREAM.exists() else "[upstream] none cloned")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
