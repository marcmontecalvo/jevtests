"""Model adapter contract shared by every contestant."""
from __future__ import annotations

from harness.schema import Case, Result


class DecisionModel:
    """load -> health -> evaluate* -> unload. `evaluate` never raises: failures
    come back as Result.error so one bad case (or model) can't abort a run."""

    name: str
    load_s: float | None = None          # cold start / load time
    provenance: dict                     # served model id, versions, revisions...

    async def load(self) -> None: ...
    async def evaluate(self, case: Case) -> Result: ...
    async def unload(self) -> None: ...
    async def health(self) -> bool: ...

    def server_pid(self) -> int | None:
        """Pid of a locally launched server, for resource sampling."""
        return None
