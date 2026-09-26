#!/usr/bin/env bash
# One-shot setup (target: DGX Spark / Linux). Safe to re-run.
#   ./scripts/setup.sh              # everything except model weights
#   ENV_GROUP=all ./scripts/setup.sh  # build venvs for every upstream (default: small)
# Model weights are NOT downloaded here; use scripts/download-models.py.
set -uo pipefail
cd "$(dirname "$0")/.."
ENV_GROUP="${ENV_GROUP:-small}"
fail=0
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
warn() { printf '  ! %s\n' "$*"; fail=1; }

step "1. Verify OS, Python, uv, git, CUDA / NVIDIA tooling"
uname -a
# uv's installer drops the binary here but only fixes PATH for new shells
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
command -v uv  >/dev/null && uv --version  || { echo "uv missing: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
command -v git >/dev/null && git --version || { echo "git missing"; exit 1; }
if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
  nvidia-smi | grep -o 'CUDA Version: [0-9.]*' || true
else
  warn "nvidia-smi not found (no NVIDIA GPU?) - only the Jev cloud contestant will run"
fi
command -v nvcc >/dev/null && nvcc --version | tail -1 || echo "  (nvcc not on PATH; fine unless an upstream builds CUDA kernels)"
command -v docker >/dev/null && docker --version || echo "  (docker not found; needed only for openjev-diffusiongemma)"

step "2-3. Harness environment + dependencies"
uv sync || { echo "uv sync failed"; exit 1; }

step "4. Clone / update upstream repositories (pinned by config/upstreams.lock.json)"
uv run python scripts/setup-envs.py --clone || warn "some upstreams failed to clone"
echo "  building per-upstream venvs for group '$ENV_GROUP'"
uv run python scripts/setup-envs.py --group "$ENV_GROUP" || warn "some upstream venvs failed (see above)"

step "5. Prepare dataset caches"
uv run python scripts/prepare-datasets.py || warn "some datasets failed"

step "6. Local directories"
mkdir -p data cache logs results reports envs
[ -f .env ] || { cp .env.example .env; warn ".env created from template - fill in OPENROUTER_API_KEY (or JEV_API_KEY) / HF_TOKEN"; }

step "7. Validate configuration  +  8. Smoke tests"
uv run pytest -q || warn "unit tests failed"
uv run python scripts/smoke-test.py || warn "smoke test reported problems"

step "Status report"
uv run python scripts/setup-status.py || warn "status report failed"

echo
if [ "$fail" = 0 ]; then echo "setup OK"; else echo "setup finished with warnings (see above)"; fi
echo "next: uv run python scripts/download-models.py --group small"
echo "      uv run python scripts/run-benchmark.py --run smoke --group small --limit 4 --modes accuracy,latency"
exit $fail
