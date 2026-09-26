"""Hugging Face Hub lookups: existence, revision, size, gating, adapter base models."""
from __future__ import annotations

from huggingface_hub import HfApi

ADAPTER_MAX_BYTES = 3e9   # repos smaller than this that name a base_model need the base too
# Repos whose card names a base that is already fused in (don't fetch the base).
FUSED = {"mpuig/system-one-minicpm5-2b-q8"}


def repo_info(api: HfApi, repo: str) -> dict:
    info = api.model_info(repo, files_metadata=True)
    base = info.card_data.get("base_model") if info.card_data else None
    if isinstance(base, list):
        base = base[0] if base else None
    return {"sha": info.sha, "bytes": sum(s.size or 0 for s in info.siblings or []),
            "gated": bool(info.gated), "base_model": base}


def resolve(repos: list[str], api: HfApi | None = None) -> dict[str, dict]:
    """Repo -> info (or {"error"}), following base_model for small adapter repos."""
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
        base = out[repo]["base_model"]
        if base and out[repo]["bytes"] < ADAPTER_MAX_BYTES and repo not in FUSED:
            queue.append(base)
    return out
