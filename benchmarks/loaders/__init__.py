"""Dataset registry: build, cache and read normalized cases (data/cases/<name>.jsonl)."""
from __future__ import annotations

import json
import random

from harness.config import CASES, benchmark_config, datasets_config
from harness.schema import Case


def prepare(name: str) -> dict:
    """Download + normalize one dataset into data/cases. Returns its metadata."""
    cfg = datasets_config()[name]
    if cfg["loader"] == "jevbench":
        from benchmarks.loaders import jevbench
        cases, meta = jevbench.load(cfg)
    elif cfg["loader"] == "financial_phrasebank":
        from benchmarks.loaders import financial_phrasebank
        cases, meta = financial_phrasebank.load(name, cfg)
    else:
        from benchmarks.loaders import hf
        cases, meta = hf.load(name, cfg)
    CASES.mkdir(parents=True, exist_ok=True)
    with open(CASES / f"{name}.jsonl", "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
    meta = {**meta, "dataset": name, "cases": len(cases)}
    (CASES / f"{name}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def load_meta(name: str) -> dict | None:
    p = CASES / f"{name}.meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_cases(name: str, limit: int | None = None, seed: int | None = None) -> list[Case]:
    """Prepared cases; a seeded, deterministic sample when `limit` is set."""
    path = CASES / f"{name}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run scripts/prepare-datasets.py {name}")
    cases = [Case.from_dict(json.loads(l)) for l in path.read_text(encoding="utf-8").splitlines()]
    if limit is not None and limit < len(cases):
        seed = benchmark_config()["seed"] if seed is None else seed
        cases = random.Random(f"{seed}:{name}").sample(cases, limit)
        cases.sort(key=lambda c: c.id)
    return cases
