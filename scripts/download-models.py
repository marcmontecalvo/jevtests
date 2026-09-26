"""Download model weights from Hugging Face (never done by setup.sh for large models).

  uv run python scripts/download-models.py --group small
  uv run python scripts/download-models.py --group all
  uv run python scripts/download-models.py --model kev-4b-qwen3.5
  uv run python scripts/download-models.py --group all --check     # existence + size only

Base models named in an adapter repo's card (`base_model`) are fetched too.
Resolved revisions are recorded in cache/models.json for run provenance.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from huggingface_hub import snapshot_download  # noqa: E402

from harness.config import CACHE, load_dotenv, select_models  # noqa: E402
from harness.hub import resolve  # noqa: E402

MANIFEST = CACHE / "models.json"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--group")
    ap.add_argument("--model", action="append", default=[])
    ap.add_argument("--check", action="store_true", help="don't download, just report")
    args = ap.parse_args()
    load_dotenv()

    specs = select_models(args.model, args.group, include_jev=False)
    infos = resolve(list(dict.fromkeys(r for s in specs for r in s.get("hf") or [])))
    for repo, i in infos.items():
        if "error" in i:
            print(f"MISSING  {repo:50s} {i['error']}")
        else:
            print(f"{i['bytes'] / 1e9:7.1f} GB  {repo:50s} sha={i['sha'][:10]}"
                  f"{'  GATED' if i['gated'] else ''}")
    print(f"{sum(i.get('bytes', 0) for i in infos.values()) / 1e9:7.1f} GB  total")
    if args.check:
        return

    CACHE.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    failed = [r for r, i in infos.items() if "error" in i]
    for repo, i in infos.items():
        if "error" in i:
            continue
        try:
            path = snapshot_download(repo, revision=i["sha"])
            manifest[repo] = {"sha": i["sha"], "bytes": i["bytes"], "path": path}
            MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            print(f"ok  {repo}")
        except Exception as e:  # noqa: BLE001 - keep going
            failed.append(repo)
            print(f"FAIL {repo}: {type(e).__name__}: {e}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
