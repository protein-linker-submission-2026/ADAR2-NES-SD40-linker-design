#!/usr/bin/env bash
# Rebuild the test environment; do not replace a historical production environment.
set -Eeuo pipefail
PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:?Usage: install_gpu_environment.sh rfdiffusion|boltz /absolute/environment-root}"
ROOT="${2:?Provide an absolute environment root on a disk with sufficient space}"
[[ "$ROOT" == /* && "$ROOT" != / ]] || { echo 'Use an absolute, non-root directory' >&2; exit 2; }
case "$MODE" in
  rfdiffusion) PYTHON_VERSION=3.9.23;;
  boltz) PYTHON_VERSION=3.11.16;;
  *) echo 'Choose rfdiffusion or boltz' >&2; exit 2;;
esac
CONDA="${CONDA_EXE:-conda}"
ENV="$ROOT/$MODE"
[[ ! -e "$ENV" ]] || { echo "Refusing to alter existing environment: $ENV" >&2; exit 1; }
mkdir -p "$ROOT"/{tmp,pip-cache,conda-cache,logs}
export TMPDIR="$ROOT/tmp" PIP_CACHE_DIR="$ROOT/pip-cache" CONDA_PKGS_DIRS="$ROOT/conda-cache"
exec > >(tee "$ROOT/logs/install_${MODE}_$(date +%Y%m%d_%H%M%S).log") 2>&1
if [[ -n "${BOOTSTRAP_PYTHON:-}" ]]; then
  [[ "$("$BOOTSTRAP_PYTHON" -c 'import platform; print(platform.python_version())')" == "$PYTHON_VERSION" ]] || { echo 'Bootstrap Python version mismatch' >&2; exit 1; }
  "$BOOTSTRAP_PYTHON" -m venv "$ENV"
else
  "$CONDA" create --prefix "$ENV" --override-channels -c conda-forge "python=$PYTHON_VERSION" pip=25.2 -y
fi
REQ="$PACKAGE_ROOT/environments/${MODE}-test-pins.txt"
if [[ -n "${WHEELHOUSE:-}" ]]; then
  [[ -d "$WHEELHOUSE" ]] || { echo 'Wheelhouse directory does not exist' >&2; exit 1; }
  LOCAL_REQ="$ROOT/logs/${MODE}-offline-requirements.txt"
  "$ENV/bin/python" "$PACKAGE_ROOT/src/prepare_offline_requirements.py" "$REQ" "$LOCAL_REQ" --wheelhouse "$WHEELHOUSE"
  "$ENV/bin/python" -m pip install --no-index --find-links "$WHEELHOUSE" wheel==0.45.1
  "$ENV/bin/python" -m pip install --no-index --find-links "$WHEELHOUSE" -r "$LOCAL_REQ"
else
  "$ENV/bin/python" -m pip install setuptools==80.9.0 wheel==0.45.1
  "$ENV/bin/python" -m pip install --timeout 60 --retries 5 -r "$REQ"
fi
if [[ "$MODE" == rfdiffusion ]]; then
  EXTERNAL="${EXTERNAL_ROOT:-$PACKAGE_ROOT/external}"
  RF="$EXTERNAL/RFdiffusion"
  [[ "$(git -C "$RF" rev-parse HEAD)" == 86507b6538f51fce57b5a72477165f03999ed7ae ]] || { echo 'Run setup_external_sources.sh first' >&2; exit 1; }
  [[ -z "$(git -C "$RF" status --porcelain --untracked-files=no)" ]] || { echo 'RF tracked source modified; review before install' >&2; exit 1; }
  SE3="$EXTERNAL/DeepLearningExamples"
  if [[ ! -e "$SE3" ]]; then
    git clone --filter=blob:none --no-checkout https://github.com/NVIDIA/DeepLearningExamples.git "$SE3"
    git -C "$SE3" sparse-checkout init --cone
    git -C "$SE3" sparse-checkout set DGLPyTorch/DrugDiscovery/SE3Transformer
    git -C "$SE3" checkout --detach 729963dd47e7c8bd462ad10bfac7a7b0b604e6dd
  fi
  [[ "$(git -C "$SE3" rev-parse HEAD)" == 729963dd47e7c8bd462ad10bfac7a7b0b604e6dd ]] || { echo 'SE3 source revision mismatch' >&2; exit 1; }
  [[ -z "$(git -C "$SE3" status --porcelain --untracked-files=no)" ]] || { echo 'SE3 tracked source modified; review before install' >&2; exit 1; }
  "$ENV/bin/python" -m pip install --no-build-isolation --no-deps "$SE3/DGLPyTorch/DrugDiscovery/SE3Transformer" "$RF"
fi
"$ENV/bin/python" -m pip check
"$ENV/bin/python" -c 'import torch; print(torch.__version__, torch.version.cuda); assert torch.cuda.is_available(); print(torch.ones(16,device="cuda").sum().item())'
if [[ "$MODE" == rfdiffusion ]]; then
  "$ENV/bin/python" -c 'import dgl,se3_transformer,rfdiffusion; print(dgl.__version__)'
else
  "$ENV/bin/boltz" predict --help
fi
"$ENV/bin/python" "$PACKAGE_ROOT/src/capture_runtime.py" --label "$MODE" --output "$ROOT/logs/runtime_${MODE}.json"
"$ENV/bin/python" "$PACKAGE_ROOT/src/check_environment_isolation.py" --mode "$MODE" --output "$ROOT/logs/isolation_${MODE}.json"
echo 'Installation and import checks passed. Run the separate SmokeTest before claiming inference passed.'
