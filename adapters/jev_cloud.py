"""TypeSafe Jev cloud: the same /v1/systemone contract, plus bearer auth.

Env: JEV_API_KEY (or TYPESAFE_API_KEY), JEV_BASE_URL (default https://api.typesafe.ai).
"""
from __future__ import annotations

import os

from adapters.http_systemone import HttpSystemOne

DEFAULT_BASE_URL = "https://api.typesafe.ai"


class JevCloud(HttpSystemOne):
    def __init__(self, spec: dict):
        spec = {**spec, "serve": None,
                "base_url": os.environ.get("JEV_BASE_URL") or DEFAULT_BASE_URL,
                "startup_timeout_s": 30}
        super().__init__(spec)
        self.api_key = os.environ.get("JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
        if not self.api_key:
            raise RuntimeError("JEV_API_KEY is not set (put it in .env)")

    def headers(self) -> dict:
        return {**super().headers(), "Authorization": f"Bearer {self.api_key}"}

    async def health(self) -> bool:
        # No health route is documented; any non-5xx answer from the host means reachable.
        try:
            r = await self.client.get("/v1/systemone", timeout=10)
            return r.status_code < 500
        except Exception:  # noqa: BLE001
            return False
