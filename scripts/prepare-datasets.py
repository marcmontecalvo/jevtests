"""Download + normalize benchmark datasets into data/cases/.

  uv run python scripts/prepare-datasets.py            # all in config/datasets.yaml
  uv run python scripts/prepare-datasets.py jevbench banking77
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.loaders import prepare  # noqa: E402
from harness.config import datasets_config, load_dotenv  # noqa: E402


def main() -> None:
    load_dotenv()
    names = sys.argv[1:] or list(datasets_config())
    failed = []
    for name in names:
        try:
            meta = prepare(name)
            print(f"ok    {name:12s} {meta['cases']:6d} cases  rev={str(meta.get('revision'))[:12]}")
        except Exception as e:  # noqa: BLE001 - one bad dataset must not stop the others
            failed.append(name)
            print(f"FAIL  {name:12s} {type(e).__name__}: {e}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
