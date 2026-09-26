"""Hugging Face Hub lookups: existence, revision, size, gating, and required base models."""
from __future__ import annotations

import re

from huggingface_hub import HfApi

# Full HF weights: model.safetensors, model-00001-of-00004.safetensors,
# model.safetensors-00001-of-00001.safetensors (Qwen3.5), pytorch_model.bin.
# Adapter weights (adapter_model.safetensors, adapters.safetensors) don't count.
_FULL_WEIGHTS = re.compile(r"(^|/)(model|pytorch_model)[^/]*\.(safetensors|bin)$")


def needs_base(files: list[str]) -> bool:
    """A repo needs its card's base_model only if it ships no full weights of its own
    (LoRA adapters like Kev/Open-Jev, or head-only checkpoints like CLM's .pt)."""
    return not any(_FULL_WEIGHTS.search(f) and "adapter" not in f for f in files)


def repo_info(api: HfApi, repo: str) -> dict:
    info = api.model_info(repo, files_metadata=True)
    files = [s.rfilename for s in info.siblings or []]
    base = info.card_data.get("base_model") if info.card_data else None
    if isinstance(base, list):
        base = base[0] if base else None
    return {"sha": info.sha, "bytes": sum(s.size or 0 for s in info.siblings or []),
            "gated": bool(info.gated),
            "base_model": base if base and needs_base(files) else None}


def resolve(repos: list[str], api: HfApi | None = None) -> dict[str, dict]:
    """Repo -> info (or {"error"}), adding required base models transitively."""
    api = api or HfApi()
    out, queue = {}, list(repos)
    while queue:
        repo = queue.pop(0)
        if repo in out:
            continue
        try:
            out[repo] = repo_info(api, repo)
        except Exception as e:  # noqa: BLE001
            out[repo] = {"error": f"{type(e).__name__}: {e}"[:200]}
            continue
        if out[repo]["base_model"]:
            queue.append(out[repo]["base_model"])
    return out
