"""Generic adapter for any server speaking the Jev wire format (POST /v1/systemone).

If the model spec has `serve`, the upstream server is launched in its own venv on a
free port and torn down on unload; otherwise `base_url` points at a running server.
"""
from __future__ import annotations

import asyncio
import os
import signal
import socket
import subprocess
import sys
import time

import httpx

from adapters.base import DecisionModel
from harness.config import LOGS, expand
from harness.schema import Case, Result, normalize_answer

QID = "q"   # question key; keys are not sent to the model per the Jev spec


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class HttpSystemOne(DecisionModel):
    retry_statuses = (429, 529, 502, 503)
    max_retries = 5

    def __init__(self, spec: dict):
        self.spec = spec
        self.name = spec["name"]
        self.base_url = (spec.get("base_url") or "").rstrip("/")
        self.request_model = spec.get("request_model", "jev-latest")
        self.timeout = float(spec.get("request_timeout_s", 180))
        self.proc: subprocess.Popen | None = None
        self.client: httpx.AsyncClient | None = None
        self.provenance: dict = {}
        self.load_s = None

    def headers(self) -> dict:
        return {"Content-Type": "application/json"}

    # ------------------------------------------------------------------ lifecycle
    async def load(self) -> None:
        t0 = time.perf_counter()
        if self.spec.get("serve"):
            self._launch()
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers(),
                                        timeout=self.timeout)
        await self._wait_ready(float(self.spec.get("startup_timeout_s", 1200)))
        self.load_s = time.perf_counter() - t0

    def _launch(self) -> None:
        if self.spec.get("stop"):   # clear a leftover (e.g. container) from a crashed run
            subprocess.run(expand(self.spec["stop"], self.spec), shell=True, capture_output=True)
        port = free_port()
        self.base_url = f"http://127.0.0.1:{port}"
        cmd = expand(self.spec["serve"], self.spec, port)
        env = {**os.environ, **{k: expand(str(v), self.spec, port)
                                for k, v in (self.spec.get("env") or {}).items()}}
        LOGS.mkdir(parents=True, exist_ok=True)
        log = open(LOGS / f"{self.name}.log", "ab")
        log.write(f"\n==== {time.ctime()} $ {cmd}\n".encode())
        log.flush()
        kw = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform == "win32"
              else {"start_new_session": True})
        self.proc = subprocess.Popen(cmd, shell=True, cwd=self.spec.get("upstream_dir"),
                                     env=env, stdout=log, stderr=subprocess.STDOUT, **kw)
        self.provenance["command"] = cmd

    async def _wait_ready(self, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.proc and self.proc.poll() is not None:
                raise RuntimeError(f"server exited with code {self.proc.returncode}; "
                                   f"see logs/{self.name}.log")
            if await self.health():
                return
            await asyncio.sleep(2)
        raise TimeoutError(f"server not ready after {timeout:.0f}s; see logs/{self.name}.log")

    async def health(self) -> bool:
        try:
            r = await self.client.get(self.spec.get("health_path", "/health"), timeout=5)
            return r.status_code < 500
        except httpx.HTTPError:
            return False

    async def unload(self) -> None:
        if self.client:
            await self.client.aclose()
        if self.proc and self.proc.poll() is None:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)],
                               capture_output=True)
            else:
                try:
                    os.killpg(self.proc.pid, signal.SIGTERM)
                    self.proc.wait(timeout=30)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    try:
                        os.killpg(self.proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        if self.spec.get("stop"):
            # e.g. `docker rm -f ...`: killing the docker CLI doesn't always stop the container
            subprocess.run(expand(self.spec["stop"], self.spec), shell=True, capture_output=True)

    def server_pid(self) -> int | None:
        return self.proc.pid if self.proc else None

    # ------------------------------------------------------------------ inference
    def build_request(self, case: Case) -> dict:
        return {"state": case.state, "model": self.request_model,
                "questions": {QID: case.jev_question()}}

    async def _post(self, body: dict) -> httpx.Response:
        delay = 1.0
        for attempt in range(self.max_retries + 1):
            r = await self.client.post("/v1/systemone", json=body)
            if r.status_code not in self.retry_statuses or attempt == self.max_retries:
                return r
            await asyncio.sleep(float(r.headers.get("retry-after", delay)))
            delay *= 2
        return r

    async def evaluate(self, case: Case) -> Result:
        res = Result(model=self.name, case_id=case.id)
        t0 = time.perf_counter()
        try:
            r = await self._post(self.build_request(case))
            res.latency_ms = (time.perf_counter() - t0) * 1000
            try:
                res.raw = r.json()
            except ValueError:
                res.raw = r.text[:2000]
            if r.status_code != 200:
                res.error = f"HTTP {r.status_code}: {str(res.raw)[:500]}"
                return res
            served = res.raw.get("model")
            if served:
                self.provenance["served_model"] = served
            res.prediction, res.probabilities, res.confidence, res.top_prob = \
                normalize_answer(case, res.raw["answers"][QID])
        except Exception as e:  # noqa: BLE001 - log and continue, never abort the run
            res.latency_ms = res.latency_ms or (time.perf_counter() - t0) * 1000
            res.error = f"{type(e).__name__}: {e}"[:1000]
        return res
