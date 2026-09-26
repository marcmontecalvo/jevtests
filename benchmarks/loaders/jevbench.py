"""JevBench public subset (fstandhartinger/jevbench) -> Cases. Questions used verbatim."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from harness.config import UPSTREAM
from harness.schema import Case

REPO_DIR = UPSTREAM / "fstandhartinger_jevbench"


def to_case(row: dict, tier: str) -> Case:
    q = row["question"]
    expected = row["expected"]
    if q["type"] == "noul":
        if expected not in ("yes", "no"):
            raise ValueError(f"{row['id']}: noul expected must be yes/no, got {expected!r}")
        expected = expected == "yes"
    elif q["type"] == "score":
        expected = int(expected)
    return Case(
        id=f"jevbench-{row['id']}",
        dataset="jevbench",
        type=q["type"],
        state=row["state"],
        question=q["instructions"],
        criteria=q.get("criteria"),
        expected=expected,
        metadata={"original_id": row["id"], "tier": tier, "family": row.get("family"),
                  "group": row.get("group"), "split": row.get("split"),
                  "labels": row.get("labels"), "provenance": row.get("provenance")},
    )


def load(cfg: dict) -> tuple[list[Case], dict]:
    if not REPO_DIR.exists():
        raise FileNotFoundError(f"{REPO_DIR} missing; run scripts/setup.sh (clones upstreams)")
    cases = []
    for rel in cfg["files"]:
        path = REPO_DIR / rel
        tier = Path(rel).stem
        cases += [to_case(json.loads(line), tier)
                  for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    commit = subprocess.run(["git", "-C", str(REPO_DIR), "rev-parse", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    meta = {"source": cfg["source"], "revision": commit, "split": "public",
            "files": cfg["files"], "license": cfg["license"]}
    return cases, meta
