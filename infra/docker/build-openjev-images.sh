#!/usr/bin/env bash
# Build razorback16/openjev's docker images from the pinned upstream checkout:
# the shared base, then the vLLM images used by clm-qwen3-8b, jevk5-qwen3.5-4b and
# openjev-diffusiongemma-26b-a4b (see config/models.yaml). Laya/Verdict don't need
# docker; they run from envs/openjev.
#   ./infra/docker/build-openjev-images.sh            # all three
#   ./infra/docker/build-openjev-images.sh jevk5 clm  # a subset: base + these
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/upstream/razorback16_openjev"
[ -d "$SRC" ] || { echo "missing $SRC; run scripts/setup.sh first"; exit 1; }
# must exist and be yours before docker bind-mounts it (else docker creates it as root)
mkdir -p "$ROOT/cache/docker"

if [ $# -eq 0 ]; then targets=(diffusiongemma jevk5 clm); else targets=("$@"); fi
cd "$SRC"

build() { echo; echo "== docker build $2"; docker build -f "$1" -t "$2" .; }

build docker/Dockerfile.base razorback16/openjev-base:cu130-torch2.13
fail=0
for t in "${targets[@]}"; do
  case "$t" in
    diffusiongemma) build docker/Dockerfile       razorback16/openjev:0.5.0       || fail=1 ;;
    jevk5)          build docker/Dockerfile.jevk5 razorback16/openjev-jevk5:0.5.0 || fail=1 ;;
    clm)            build docker/Dockerfile.clm   razorback16/openjev-clm:0.5.0   || fail=1 ;;
    *) echo "unknown target $t (diffusiongemma | jevk5 | clm)"; fail=1 ;;
  esac
done
echo
docker images 'razorback16/openjev*' --format '{{.Repository}}:{{.Tag}}  {{.Size}}'
exit $fail
