"""Benchmark runner. Every mode is resumable (answered predictions are skipped) and
failure-isolated (a model that fails to load or crashes is logged; the run continues).

Modes:
  accuracy    every case once (variant orig, rep 0) at a fixed shared concurrency
  order       choice cases in reversed + seeded orders (orig comes from accuracy)
  repeat      identical re-requests of a subset (rep 0 comes from accuracy)
  latency     cold first request, then sequential warm requests
  throughput  decisions/sec at several concurrency levels (aggregates only)
"""
from __future__ import annotations

import asyncio
import logging
import random
import time

from adapters import build_adapter
from benchmarks.transforms.permute import variants
from harness.db import DB
from harness.resources import Sampler
from harness.schema import Case, is_correct
from harness.sysinfo import model_provenance

log = logging.getLogger("runner")
ALL_MODES = ("accuracy", "order", "repeat", "latency", "throughput")
DEFAULT_MODES = ("accuracy", "order", "repeat", "latency")


async def gather_limited(coros, limit: int):
    sem = asyncio.Semaphore(limit)

    async def guarded(c):
        async with sem:
            return await c
    return await asyncio.gather(*(guarded(c) for c in coros))


def subset(cases: list[Case], n: int, seed: int) -> list[Case]:
    if n >= len(cases):
        return list(cases)
    return sorted(random.Random(seed).sample(cases, n), key=lambda c: c.id)


class ModelRun:
    def __init__(self, db: DB, run_id: str, spec: dict, cases: list[Case], bench: dict):
        self.db, self.run_id, self.spec, self.cases, self.bench = db, run_id, spec, cases, bench
        self.name = spec["name"]
        self.adapter = None   # built in run() so a bad spec/missing key is a logged failure
        self.mcfg = bench["modes"]
        self.seed = bench["seed"]

    async def evaluate(self, mode: str, variant: str, rep: int, case: Case):
        r = await self.adapter.evaluate(case)
        correct = abs_err = None
        if r.error is None:
            correct = is_correct(case, r.prediction, r.probabilities)
            if case.type == "score":
                abs_err = abs(float(r.prediction) - case.expected)
        else:
            self.db.log_error(self.run_id, self.name, case.id, mode, r.error)
        self.db.save_prediction(self.run_id, mode, variant, rep, r, correct, abs_err)
        return r

    def todo(self, mode: str, jobs: list[tuple[str, int, Case]]):
        done = self.db.done_keys(self.run_id, self.name, mode)
        return [(v, rep, c) for v, rep, c in jobs if (c.id, v, rep) not in done]

    async def run_jobs(self, mode: str, jobs, concurrency: int):
        jobs = self.todo(mode, jobs)
        log.info("%s %s: %d requests", self.name, mode, len(jobs))
        await gather_limited([self.evaluate(mode, v, rep, c) for v, rep, c in jobs], concurrency)

    # ---------------------------------------------------------------- modes
    async def mode_accuracy(self):
        await self.run_jobs("accuracy", [("orig", 0, c) for c in self.cases],
                            self.mcfg["accuracy"]["concurrency"])

    async def mode_order(self):
        cfg = self.mcfg["order"]
        choice = subset([c for c in self.cases if c.type == "choice"], cfg["max_cases"], self.seed)
        jobs = [(name, 0, v) for c in choice
                for name, v in variants(c, cfg["seeds"]).items() if name != "orig"]
        await self.run_jobs("order", jobs, self.mcfg["accuracy"]["concurrency"])

    async def mode_repeat(self):
        cfg = self.mcfg["repeat"]
        jobs = [("orig", rep, c) for c in subset(self.cases, cfg["max_cases"], self.seed)
                for rep in range(1, cfg["repeats"])]
        await self.run_jobs("repeat", jobs, self.mcfg["accuracy"]["concurrency"])

    async def mode_latency(self):
        n = self.mcfg["latency"]["warm_requests"]
        pool = subset(self.cases, len(self.cases), self.seed)
        # rep 0 of "first" is the cold first inference right after load
        await self.run_jobs("first", [("orig", 0, pool[0])], 1)
        await self.run_jobs("latency", [("orig", i, pool[i % len(pool)]) for i in range(n)], 1)

    async def mode_throughput(self):
        cfg = self.mcfg["throughput"]
        done = self.db.throughput_done(self.run_id, self.name)
        pool = subset(self.cases, len(self.cases), self.seed)
        for conc in cfg["concurrency"]:
            if conc in done:
                continue
            n = cfg["requests_per_level"]
            t0 = time.perf_counter()
            results = await gather_limited(
                [self.adapter.evaluate(pool[i % len(pool)]) for i in range(n)], conc)
            secs = time.perf_counter() - t0
            errors = sum(r.error is not None for r in results)
            self.db.save_throughput(self.run_id, self.name, conc, n, errors, secs)
            log.info("%s throughput c=%d: %.2f/s (%d errors)", self.name, conc,
                     (n - errors) / secs, errors)

    # ---------------------------------------------------------------- lifecycle
    async def run(self, modes) -> str:
        prov = model_provenance(self.spec)
        self.db.upsert_model(self.run_id, self.name, spec=self.spec, provenance=prov,
                             status="loading")
        interval = self.mcfg.get("resources", {}).get("interval_s", 1.0)
        pid = lambda: self.adapter.server_pid() if self.adapter else None  # noqa: E731
        with Sampler(self.db, self.run_id, self.name, pid, interval) as smp:
            try:
                smp.phase = "load"
                self.adapter = build_adapter(self.spec)
                await self.adapter.load()
                self.db.upsert_model(self.run_id, self.name, load_s=self.adapter.load_s,
                                     status="running")
                log.info("%s loaded in %.1fs", self.name, self.adapter.load_s)
            except Exception as e:  # noqa: BLE001
                msg = f"{type(e).__name__}: {e}"
                log.error("%s failed to load: %s", self.name, msg)
                self.db.log_error(self.run_id, self.name, None, "load", msg)
                self.db.upsert_model(self.run_id, self.name, status="load_failed", error=msg)
                if self.adapter:
                    await self.adapter.unload()
                return "load_failed"
            status = "done"
            try:
                for mode in modes:
                    smp.phase = mode
                    try:
                        await getattr(self, f"mode_{mode}")()
                    except Exception as e:  # noqa: BLE001
                        status = "partial"
                        log.exception("%s mode %s crashed", self.name, mode)
                        self.db.log_error(self.run_id, self.name, None, mode,
                                          f"{type(e).__name__}: {e}")
            finally:
                await self.adapter.unload()
            answered, total = self.db.query(
                "SELECT COUNT(*) FILTER (WHERE error IS NULL), COUNT(*) FROM predictions "
                "WHERE run_id=? AND model=? AND mode='accuracy'", (self.run_id, self.name))[0]
            if total and not answered:
                status = "no_answers"   # served, but every request errored (see errors.csv)
            self.db.upsert_model(self.run_id, self.name,
                                 provenance={**prov, **self.adapter.provenance}, status=status)
            return status


async def run_benchmark(db: DB, run_id: str, specs: list[dict], cases: list[Case],
                        bench: dict, modes=DEFAULT_MODES, parallel: int = 1) -> dict[str, str]:
    """Run models (sequentially by default; `parallel` > 1 co-hosts small models)."""
    async def one(spec):
        return spec["name"], await ModelRun(db, run_id, spec, cases, bench).run(modes)

    results = await gather_limited([one(s) for s in specs], max(1, parallel))
    return dict(results)
