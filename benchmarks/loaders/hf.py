"""Standard Hugging Face classification datasets -> Cases, driven by config/datasets.yaml.

Labels are kept verbatim; question wording comes from the config (versioned there).
"""
from __future__ import annotations

import math

from harness.schema import Case


def _state(cfg: dict, row: dict):
    """One text field, or `state_fields` {state key: row field} for paired inputs."""
    if cfg.get("state_fields"):
        return {k: row[f] for k, f in cfg["state_fields"].items()}
    return row[cfg["text_field"]]


def score_level(value: float, scale: float) -> int:
    """Continuous label -> ordered level index; halves round up (2.5 -> 3)."""
    return int(math.floor(value * scale + 0.5))


def to_case(name: str, cfg: dict, idx: int, row: dict, label_names: list[str] | None) -> Case:
    label = row[cfg["label_field"]]
    meta = {"source": cfg["source"], "split": cfg["split"], "row": idx,
            "original_label": label, "transform_version": cfg["transform_version"]}
    if cfg["type"] == "noul":
        return Case(id=f"{name}-{idx:05d}", dataset=name, type="noul",
                    state=_state(cfg, row),
                    question=cfg["instructions_template"].format(
                        question=row[cfg["question_field"]].rstrip("?")),
                    criteria=None, expected=label == cfg.get("true_label", 1), metadata=meta)
    if cfg["type"] == "score":
        levels = cfg["levels"]
        expected = score_level(label, cfg.get("score_scale", 1))
        if not 0 <= expected < len(levels):
            raise ValueError(f"{name} row {idx}: label {label} maps outside {len(levels)} levels")
        return Case(id=f"{name}-{idx:05d}", dataset=name, type="score", state=_state(cfg, row),
                    question=cfg["instructions"], criteria=list(levels), expected=expected,
                    metadata=meta)
    names = cfg.get("label_names") or label_names
    expected = label if isinstance(label, str) else names[label]
    descriptions = cfg.get("descriptions") or {}
    criteria = cfg.get("criteria") or {n: descriptions.get(n) for n in names}
    return Case(id=f"{name}-{idx:05d}", dataset=name, type="choice",
                state=_state(cfg, row), question=cfg["instructions"],
                criteria=criteria, expected=expected, metadata=meta)


def load(name: str, cfg: dict) -> tuple[list[Case], dict]:
    import datetime

    import datasets
    from huggingface_hub import HfApi

    # `revision` e.g. refs/convert/parquet for script-only repos (datasets>=4 won't run scripts)
    ds = datasets.load_dataset(cfg["source"], cfg.get("config"), split=cfg["split"],
                               revision=cfg.get("revision"))
    label_names = None
    if cfg["type"] == "choice" and not cfg.get("label_names"):
        if cfg["label_field"].endswith("_text"):
            label_names = sorted(set(ds[cfg["label_field"]]))
        else:
            label_names = ds.features[cfg["label_field"]].names
    cases = [to_case(name, cfg, i, row, label_names) for i, row in enumerate(ds)]
    meta = {"source": cfg["source"], "config": cfg.get("config"), "split": cfg["split"],
            "revision": HfApi().dataset_info(cfg["source"], revision=cfg.get("revision")).sha,
            "license": cfg["license"],
            "download_date": datetime.date.today().isoformat(), "rows": len(cases),
            "transform_version": cfg["transform_version"]}
    return cases, meta
