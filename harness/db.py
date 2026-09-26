"""SQLite results store. A run is identified by name, so re-running resumes it."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY, created REAL, config TEXT, environment TEXT);
CREATE TABLE IF NOT EXISTS models (
    run_id TEXT, model TEXT, spec TEXT, provenance TEXT,
    load_s REAL, status TEXT, error TEXT, updated REAL,
    PRIMARY KEY (run_id, model));
CREATE TABLE IF NOT EXISTS datasets (
    name TEXT PRIMARY KEY, meta TEXT);
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY, dataset TEXT, type TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS predictions (
    run_id TEXT, model TEXT, case_id TEXT, mode TEXT, variant TEXT, rep INTEGER,
    prediction TEXT, probabilities TEXT, confidence REAL, top_prob REAL,
    correct INTEGER, abs_error REAL, latency_ms REAL, error TEXT, raw TEXT, created REAL,
    PRIMARY KEY (run_id, model, case_id, mode, variant, rep));
CREATE TABLE IF NOT EXISTS throughput (
    run_id TEXT, model TEXT, concurrency INTEGER, requests INTEGER, errors INTEGER,
    seconds REAL, decisions_per_s REAL,
    PRIMARY KEY (run_id, model, concurrency));
CREATE TABLE IF NOT EXISTS resource_samples (
    run_id TEXT, model TEXT, t REAL, phase TEXT,
    gpu_mem_mb REAL, gpu_util REAL, gpu_power_w REAL,
    sys_mem_mb REAL, cpu_pct REAL, proc_rss_mb REAL);
CREATE TABLE IF NOT EXISTS errors (
    run_id TEXT, model TEXT, case_id TEXT, stage TEXT, message TEXT, t REAL);
"""


def _j(v):
    return None if v is None else json.dumps(v, default=str)


class DB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.lock = threading.Lock()   # resource sampler thread writes too

    def _exec(self, sql, args=()):
        with self.lock:
            self.conn.execute(sql, args)
            self.conn.commit()

    def query(self, sql, args=()):
        with self.lock:
            return self.conn.execute(sql, args).fetchall()

    # ---- writes
    def upsert_run(self, run_id, config, environment):
        self._exec("INSERT INTO runs VALUES (?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET "
                   "config=excluded.config, environment=excluded.environment",
                   (run_id, time.time(), _j(config), _j(environment)))

    def upsert_model(self, run_id, model, spec=None, provenance=None, load_s=None,
                     status=None, error=None):
        self._exec(
            "INSERT INTO models VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(run_id, model) DO UPDATE SET "
            "spec=COALESCE(excluded.spec, spec), provenance=COALESCE(excluded.provenance, provenance), "
            "load_s=COALESCE(excluded.load_s, load_s), status=COALESCE(excluded.status, status), "
            "error=excluded.error, updated=excluded.updated",
            (run_id, model, _j(spec), _j(provenance), load_s, status, error, time.time()))

    def upsert_dataset(self, name, meta):
        self._exec("INSERT OR REPLACE INTO datasets VALUES (?,?)", (name, _j(meta)))

    def upsert_cases(self, cases):
        with self.lock:
            self.conn.executemany("INSERT OR REPLACE INTO cases VALUES (?,?,?,?)",
                                  [(c.id, c.dataset, c.type, _j(c.to_dict())) for c in cases])
            self.conn.commit()

    def save_prediction(self, run_id, mode, variant, rep, result, correct, abs_error):
        self._exec(
            "INSERT OR REPLACE INTO predictions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, result.model, result.case_id, mode, variant, rep,
             _j(result.prediction), _j(result.probabilities), result.confidence, result.top_prob,
             None if correct is None else int(correct), abs_error, result.latency_ms,
             result.error, _j(result.raw), time.time()))

    def save_throughput(self, run_id, model, concurrency, requests, errors, seconds):
        self._exec("INSERT OR REPLACE INTO throughput VALUES (?,?,?,?,?,?,?)",
                   (run_id, model, concurrency, requests, errors, seconds,
                    (requests - errors) / seconds if seconds else None))

    def save_resource(self, run_id, model, phase, s):
        self._exec("INSERT INTO resource_samples VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (run_id, model, time.time(), phase, s.get("gpu_mem_mb"), s.get("gpu_util"),
                    s.get("gpu_power_w"), s.get("sys_mem_mb"), s.get("cpu_pct"), s.get("proc_rss_mb")))

    def log_error(self, run_id, model, case_id, stage, message):
        self._exec("INSERT INTO errors VALUES (?,?,?,?,?,?)",
                   (run_id, model, case_id, stage, str(message)[:4000], time.time()))

    # ---- reads
    def done_keys(self, run_id, model, mode) -> set[tuple]:
        """(case_id, variant, rep) already answered without error -> skipped on resume."""
        rows = self.query("SELECT case_id, variant, rep FROM predictions "
                          "WHERE run_id=? AND model=? AND mode=? AND error IS NULL",
                          (run_id, model, mode))
        return {(r[0], r[1], r[2]) for r in rows}

    def throughput_done(self, run_id, model) -> set[int]:
        return {r[0] for r in self.query(
            "SELECT concurrency FROM throughput WHERE run_id=? AND model=?", (run_id, model))}
