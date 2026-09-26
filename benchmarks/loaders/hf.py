"""Standard Hugging Face classification datasets -> Cases, driven by config/datasets.yaml.

Labels are kept verbatim; question wording comes from the config (versioned there).
"""
from __future__ import annotations

from harness.schema import Case


def to_case(name: str, cfg: dict, idx: int, row: dict, label_names: list[str] | None) -> Case:
    label = row[cfg["label_field"]]
    meta = {"source": cfg["source"], "split": cfg["split"], "row": idx,
            "original_label": label, "transform_version": cfg["transform_version"]}
    if cfg["type"] == "noul":
        return Case(id=f"{name}-{idx:05d}", dataset=name, type="noul",
                    state=row[cfg["text_field"]],
                    question=cfg["instructions_template"].format(
                        question=row[cfg["question_field"]].rstrip("?")),
                    criteria=None, expected=bool(label), metadata=meta)
    names = cfg.get("label_names") or label_names
    expected = label if isinstance(label, str) else names[label]
    criteria = cfg.get("criteria") or {n: None for n in names}
    return Case(id=f"{name}-{idx:05d}", dataset=name, type="choice",
                state=row[cfg["text_field"]], question=cfg["instructions"],
                criteria=criteria, expected=expected, metadata=meta)


def load(name: str, cfg: dict) -> tuple[list[Case], dict]:
    import datetime

    import datasets
    from huggingface_hub import HfApi

    ds = datasets.load_dataset(cfg["source"], cfg.get("config"), split=cfg["split"])
    label_names = None
    if cfg["type"] == "choice" and not cfg.get("label_names"):
        if cfg["label_field"].endswith("_text"):
            label_names = sorted(set(ds[cfg["label_field"]]))
        else:
            label_names = ds.features[cfg["label_field"]].names
    cases = [to_case(name, cfg, i, row, label_names) for i, row in enumerate(ds)]
    meta = {"source": cfg["source"], "config": cfg.get("config"), "split": cfg["split"],
            "revision": HfApi().dataset_info(cfg["source"]).sha, "license": cfg["license"],
            "download_date": datetime.date.today().isoformat(), "rows": len(cases),
            "transform_version": cfg["transform_version"]}
    return cases, meta
