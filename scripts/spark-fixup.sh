#!/usr/bin/env bash
# Follow-up to the first setup.sh run on the DGX Spark (see commit 3c68be6):
# fixes HF cache ownership, rebuilds the venvs whose torch/MLX builds changed,
# GPU-checks every venv, prepares datasets and refreshes reports/SETUP_STATUS.md.
# Run after `git pull`:   ./scripts/spark-fixup.sh
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"
fail=0
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

step "1. Hugging Face cache ownership"
HF_CACHE="${HF_HOME:-$HOME/.cache/huggingface}"
mkdir -p "$HF_CACHE" 2>/dev/null || true
if [ -n "$(find "$HF_CACHE" ! -user "$USER" -print -quit 2>/dev/null)" ]; then
  echo "  $HF_CACHE has files not owned by $USER; fixing (needs sudo)"
  sudo chown -R "$USER:$USER" "$HF_CACHE" || { echo "  ! chown failed"; fail=1; }
else
  echo "  ok ($HF_CACHE)"
fi

step "2. Rebuild the small-group venvs (uv-managed Python with headers, GPU-correct torch)"
uv run python scripts/setup-envs.py --group small || fail=1

step "3. GPU check of every venv"
uv run python scripts/setup-envs.py --verify || fail=1

step "4. Prepare datasets"
uv run python scripts/prepare-datasets.py || fail=1

step "5. Refresh reports/SETUP_STATUS.md"
uv run python scripts/setup-status.py || fail=1

echo
if [ "$fail" = 0 ]; then
  echo "all good. next:"
  echo "  uv run python scripts/download-models.py --group small"
  echo "  uv run python scripts/run-benchmark.py --run smoke --group small --limit 4 --modes accuracy,latency"
else
  echo "finished with problems - paste the output above (especially step 3)"
fi
exit $fail
