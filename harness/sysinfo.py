"""Reproducibility metadata: host, GPU, CUDA, git commits, per-venv library versions."""
from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

import psutil

from harness.config import ROOT, env_python


def _run(cmd, cwd=None, timeout=30) -> str:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def git_commit(path: Path = ROOT) -> str | None:
    return _run(["git", "-C", str(path), "rev-parse", "HEAD"]) or None


def git_dirty(path: Path = ROOT) -> bool:
    return bool(_run(["git", "-C", str(path), "status", "--porcelain"]))


def gpus() -> list[dict]:
    if not shutil.which("nvidia-smi"):
        return []
    out = _run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader"])
    return [dict(zip(("name", "memory", "driver"), (x.strip() for x in line.split(","))))
            for line in out.splitlines() if line.strip()]


def cuda_version() -> str | None:
    # "CUDA Version: 13.0" (older drivers) or "CUDA UMD Version: 13.3" (newer)
    m = re.search(r"CUDA (?:UMD )?Version:\s*([\d.]+)", _run(["nvidia-smi"]))
    return m.group(1) if m else None


def host() -> dict:
    return {
        "os": platform.platform(), "machine": platform.machine(),
        "python": sys.version.split()[0], "cpu_count": psutil.cpu_count(),
        "ram_gb": round(psutil.virtual_memory().total / 2**30, 1),
        "gpus": gpus(), "cuda_driver_version": cuda_version(),
        "repo_commit": git_commit(), "repo_dirty": git_dirty(),
    }


_VERSIONS = r"""
import json, os, sysconfig, importlib.metadata as m
out = {"python_headers": os.path.exists(os.path.join(sysconfig.get_paths()["include"], "Python.h"))}
for p in ("torch", "transformers", "peft", "sglang", "vllm", "mlx", "mlx-lm", "accelerate"):
    try: out[p] = m.version(p)
    except Exception: pass
try:
    import torch
    out["torch_cuda"] = torch.version.cuda
    out["cuda_available"] = torch.cuda.is_available()
    if out["cuda_available"]:
        out["capability"] = "sm_%d%d" % torch.cuda.get_device_capability(0)
        out["arch_list"] = torch.cuda.get_arch_list()
        # is_available() is not enough: a build without kernels for this GPU only fails here
        x = torch.randn(512, 512, device="cuda", dtype=torch.bfloat16)
        torch.nn.functional.softmax(x @ x, dim=-1).sum().item()
        out["gpu_ok"] = True
    else:
        out["gpu_ok"] = False
except ImportError: pass
except Exception as e:
    out["gpu_ok"] = False
    out["gpu_error"] = f"{type(e).__name__}: {e}"[:300]
if "torch" not in out:
    try:
        import mlx.core as mx
        out["mlx_device"] = str(mx.default_device())
        mx.eval(mx.softmax(mx.random.normal((512, 512)) @ mx.random.normal((512, 512)), axis=-1))
        out["gpu_ok"] = "gpu" in out["mlx_device"]
    except ImportError: pass
    except Exception as e:
        out["gpu_ok"] = False
        out["gpu_error"] = f"{type(e).__name__}: {e}"[:300]
print(json.dumps(out))
"""


def env_versions(env_dir: str | None) -> dict:
    """Library versions inside a model's venv (each upstream pins its own)."""
    if not env_dir:
        return {}
    py = env_python(env_dir)
    if not py.exists():
        return {"error": f"venv missing: {env_dir}"}
    try:
        return json.loads(_run([str(py), "-c", _VERSIONS], timeout=120) or "{}")
    except json.JSONDecodeError:
        return {}


def model_provenance(spec: dict) -> dict:
    """Everything needed to say exactly which model/code produced a prediction."""
    prov = {"upstream": spec.get("upstream"), "params": spec.get("params"),
            "active_params": spec.get("active_params"),
            "quantization": spec.get("quantization"), "hf": spec.get("hf"),
            "env": spec.get("env")}
    if spec.get("upstream_dir"):
        prov["upstream_commit"] = git_commit(Path(spec["upstream_dir"]))
        prov["versions"] = env_versions(spec.get("env_dir"))
    manifest = ROOT / "cache" / "models.json"
    if manifest.exists():
        revs = json.loads(manifest.read_text(encoding="utf-8"))
        prov["hf_revisions"] = {r: revs.get(r, {}).get("sha") for r in spec.get("hf") or []}
    return prov
