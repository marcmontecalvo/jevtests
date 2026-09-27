"""Financial PhraseBank (Malo et al. 2014) from the original zip in takala/financial_phrasebank.

The Hub repo is script-only, so we read the zip it ships: `Sentences_<agreement>.txt`,
one `sentence@label` per line, Latin-1. Cases are built by the generic HF transform.
"""
from __future__ import annotations

import datetime
import zipfile

from benchmarks.loaders import hf
from harness.schema import Case

ZIP = "data/FinancialPhraseBank-v1.0.zip"


def parse(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        sentence, _, label = line.rpartition("@")
        rows.append({"sentence": sentence.strip(), "label": label.strip()})
    return rows


def load(name: str, cfg: dict) -> tuple[list[Case], dict]:
    from huggingface_hub import HfApi, hf_hub_download

    revision = HfApi().dataset_info(cfg["source"]).sha
    path = hf_hub_download(cfg["source"], ZIP, repo_type="dataset", revision=revision)
    member = f"FinancialPhraseBank-v1.0/Sentences_{cfg['agreement']}.txt"
    with zipfile.ZipFile(path) as z:
        rows = parse(z.read(member).decode("latin-1"))
    cases = [hf.to_case(name, cfg, i, row, None) for i, row in enumerate(rows)]
    meta = {"source": cfg["source"], "file": member, "split": cfg["split"],
            "revision": revision, "license": cfg["license"],
            "download_date": datetime.date.today().isoformat(), "rows": len(cases),
            "transform_version": cfg["transform_version"]}
    return cases, meta
