"""Hosted Jev: the same /v1/systemone contract, plus bearer auth, via a provider.

Providers (model spec `provider:`):
  typesafe    https://api.typesafe.ai   key JEV_API_KEY (or TYPESAFE_API_KEY), url JEV_BASE_URL
  openrouter  https://openrouter.ai/api key OPENROUTER_API_KEY,               url OPENROUTER_BASE_URL
OpenRouter passes the TypeSafe wire format through unchanged (it adds `id`,
`provider` and `usage.cost` to responses, which land in the raw record).
"""
from __future__ import annotations

import os

from adapters.http_systemone import HttpSystemOne

PROVIDERS = {
    "typesafe": {"base_url": "https://api.typesafe.ai", "url_env": "JEV_BASE_URL",
                 "key_envs": ("JEV_API_KEY", "TYPESAFE_API_KEY")},
    "openrouter": {"base_url": "https://openrouter.ai/api", "url_env": "OPENROUTER_BASE_URL",
                   "key_envs": ("OPENROUTER_API_KEY",)},
}


def provider_of(spec: dict) -> dict:
    name = spec.get("provider", "typesafe")
    if name not in PROVIDERS:
        raise ValueError(f"{spec['name']}: unknown provider {name!r} (known: {', '.join(PROVIDERS)})")
    return PROVIDERS[name]


def api_key(spec: dict) -> str | None:
    return next((os.environ[k] for k in provider_of(spec)["key_envs"] if os.environ.get(k)), None)


class JevCloud(HttpSystemOne):
    def __init__(self, spec: dict):
        p = provider_of(spec)
        spec = {**spec, "serve": None,
                "base_url": os.environ.get(p["url_env"]) or p["base_url"],
                "startup_timeout_s": 30}
        super().__init__(spec)
        self.api_key = api_key(spec)
        if not self.api_key:
            raise RuntimeError(f"{' / '.join(p['key_envs'])} is not set (put it in .env)")
        self.provenance["provider"] = spec.get("provider", "typesafe")

    def headers(self) -> dict:
        return {**super().headers(), "Authorization": f"Bearer {self.api_key}"}

    async def health(self) -> bool:
        # No health route is documented; any non-5xx answer from the host means reachable.
        try:
            r = await self.client.get("/v1/systemone", timeout=10)
            return r.status_code < 500
        except Exception:  # noqa: BLE001
            return False
