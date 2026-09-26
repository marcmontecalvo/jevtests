"""Run (or resume) a benchmark and build its report.

  uv run python scripts/run-benchmark.py --run smoke --group small --limit 4 --modes accuracy,latency
  uv run python scripts/run-benchmark.py --run full-2026-09 --group all
  uv run python scripts/run-benchmark.py --run full-2026-09 --report-only
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.loaders import load_cases, load_meta  # noqa: E402
from harness import report  # noqa: E402
from harness.config import DB_PATH, benchmark_config, load_dotenv, select_models  # noqa: E402
from harness.db import DB  # noqa: E402
from harness.runner import ALL_MODES, DEFAULT_MODES, run_benchmark  # noqa: E402
from harness.sysinfo import host  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--run", required=True, help="run name; re-using it resumes")
    ap.add_argument("--models", default="", help="comma-separated model names")
    ap.add_argument("--group", help="tiny | small | medium | large | all")
    ap.add_argument("--no-jev", action="store_true", help="don't auto-include the Jev cloud model")
    ap.add_argument("--datasets", default="", help="comma-separated (default: all in benchmark.yaml)")
    ap.add_argument("--limit", type=int, help="cases per dataset (overrides benchmark.yaml)")
    ap.add_argument("--modes", default=",".join(DEFAULT_MODES), help=f"any of {','.join(ALL_MODES)}")
    ap.add_argument("--parallel", type=int, default=1, help="models run concurrently")
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    db = DB(DB_PATH)
    if not args.report_only:
        bench = benchmark_config()
        modes = [m for m in args.modes.split(",") if m]
        bad = set(modes) - set(ALL_MODES)
        if bad:
            raise SystemExit(f"unknown modes: {bad}")
        specs = select_models([m for m in args.models.split(",") if m], args.group,
                              include_jev=not args.no_jev)
        if not specs:
            raise SystemExit("no models selected (use --models or --group)")
        names = [d for d in args.datasets.split(",") if d] or list(bench["datasets"])
        cases = []
        for name in names:
            limit = args.limit if args.limit is not None else bench["datasets"].get(name)
            ds_cases = load_cases(name, limit)
            db.upsert_dataset(name, load_meta(name))
            db.upsert_cases(ds_cases)
            cases += ds_cases
        db.upsert_run(args.run, {"args": vars(args), "benchmark": bench,
                                 "models": [s["name"] for s in specs], "datasets": names},
                      host())
        logging.info("run %s: %d models x %d cases, modes=%s", args.run, len(specs),
                     len(cases), modes)
        statuses = asyncio.run(run_benchmark(db, args.run, specs, cases, bench, modes,
                                             args.parallel))
        for name, status in statuses.items():
            logging.info("%-40s %s", name, status)
    out = report.build(db, args.run)
    print(f"report: {out / 'summary.md'}")


if __name__ == "__main__":
    main()
