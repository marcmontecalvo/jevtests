"""Background resource sampler: GPU (nvidia-smi), system memory/CPU and the
server process tree's RSS. On unified-memory systems (GB10) nvidia-smi may report
memory as N/A; proc_rss_mb is then the useful number."""
from __future__ import annotations

import shutil
import subprocess
import threading

import psutil

_SMI = shutil.which("nvidia-smi")


def _num(s: str) -> float | None:
    try:
        return float(s)
    except ValueError:
        return None   # "[N/A]", "[Not Supported]"


def gpu_sample() -> dict:
    if not _SMI:
        return {}
    try:
        out = subprocess.run(
            [_SMI, "--query-gpu=memory.used,utilization.gpu,power.draw",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5).stdout
    except (subprocess.SubprocessError, OSError):
        return {}
    rows = [[_num(x.strip()) for x in line.split(",")] for line in out.strip().splitlines()]
    if not rows:
        return {}

    def total(i):
        vals = [r[i] for r in rows if len(r) > i and r[i] is not None]
        return sum(vals) if vals else None
    return {"gpu_mem_mb": total(0), "gpu_util": total(1), "gpu_power_w": total(2)}


def tree_rss_mb(pid: int | None) -> float | None:
    if not pid:
        return None
    try:
        p = psutil.Process(pid)
        procs = [p, *p.children(recursive=True)]
    except psutil.Error:
        return None
    total = 0
    for q in procs:
        try:
            total += q.memory_info().rss
        except psutil.Error:
            pass
    return total / 2**20


def sample(pid: int | None = None) -> dict:
    vm = psutil.virtual_memory()
    return {**gpu_sample(), "sys_mem_mb": (vm.total - vm.available) / 2**20,
            "cpu_pct": psutil.cpu_percent(interval=None), "proc_rss_mb": tree_rss_mb(pid)}


class Sampler:
    """Samples every `interval` seconds into the DB while a model is under test."""

    def __init__(self, db, run_id: str, model: str, pid_fn, interval: float = 1.0):
        self.db, self.run_id, self.model = db, run_id, model
        self.pid_fn, self.interval = pid_fn, interval
        self.phase = "idle"
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        while not self._stop.wait(self.interval):
            self.db.save_resource(self.run_id, self.model, self.phase, sample(self.pid_fn()))

    def __enter__(self):
        self.db.save_resource(self.run_id, self.model, "baseline", sample(None))
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join(timeout=5)
