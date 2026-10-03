#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXTERNAL_ROOT="${EXTERNAL_ROOT:-$PACKAGE_ROOT/external}"
RF_COMMIT="86507b6538f51fce57b5a72477165f03999ed7ae"
MPNN_COMMIT="8907e6671bfbfc92303b5f79c4b5e6ce47cdef57"
RF_MODEL_SHA256="0fcf7d7c32b4848030aca3a051e6768de194616f96ba6c38186351a33bfc6eca"
MPNN_MODEL_SHA256="c9cb4a671d79604111231f8dbfc7c590e06f1197453b7a6854ac6661a642f5bd"

command -v git >/dev/null 2>&1 || { echo "git is required" >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "curl is required" >&2; exit 1; }
mkdir -p "$EXTERNAL_ROOT"

checkout_exact() {
  local url="$1" commit="$2" destination="$3"
  if [[ ! -d "$destination/.git" ]]; then
    git clone "$url" "$destination"
  fi
  git -C "$destination" fetch --tags --prune origin
  git -C "$destination" checkout --detach "$commit"
  [[ "$(git -C "$destination" rev-parse HEAD)" == "$commit" ]] || {
    echo "commit verification failed for $destination" >&2
    exit 1
  }
}

checkout_exact https://github.com/RosettaCommons/RFdiffusion.git "$RF_COMMIT" "$EXTERNAL_ROOT/RFdiffusion"
checkout_exact https://github.com/dauparas/ProteinMPNN.git "$MPNN_COMMIT" "$EXTERNAL_ROOT/ProteinMPNN"

mkdir -p "$EXTERNAL_ROOT/RFdiffusion/models"
RF_MODEL="$EXTERNAL_ROOT/RFdiffusion/models/Base_ckpt.pt"
if [[ -s "$RF_MODEL" ]] && ! printf '%s  %s\n' "$RF_MODEL_SHA256" "$RF_MODEL" | sha256sum --check --status; then
  echo "Preserving incomplete or mismatched RFdiffusion checkpoint" >&2
  mv "$RF_MODEL" "${RF_MODEL}.unverified.$(date +%Y%m%d_%H%M%S).$$"
fi
if [[ ! -s "$RF_MODEL" ]]; then
  curl -fL --retry 20 --retry-all-errors --continue-at - \
    -o "${RF_MODEL}.part" \
    http://files.ipd.uw.edu/pub/RFdiffusion/6f5902ac237024bdd0c176cb93063dc4/Base_ckpt.pt
  printf '%s  %s\n' "$RF_MODEL_SHA256" "${RF_MODEL}.part" | sha256sum --check --status || {
    echo "Downloaded checkpoint checksum mismatch; .part file retained for inspection" >&2
    exit 1
  }
  mv "${RF_MODEL}.part" "$RF_MODEL"
fi
printf '%s  %s\n' "$RF_MODEL_SHA256" "$RF_MODEL" | sha256sum --check --status || {
  echo "RFdiffusion Base_ckpt.pt checksum mismatch" >&2
  exit 1
}

MPNN_MODEL="$EXTERNAL_ROOT/ProteinMPNN/vanilla_model_weights/v_48_020.pt"
[[ -s "$MPNN_MODEL" ]] || {
  echo "ProteinMPNN v_48_020 weight is missing after checkout" >&2
  exit 1
}
printf '%s  %s\n' "$MPNN_MODEL_SHA256" "$MPNN_MODEL" | sha256sum --check --status || {
  echo "ProteinMPNN v_48_020.pt checksum mismatch" >&2
  exit 1
}

cat <<EOF
External source checkout complete.
RFdiffusion: $EXTERNAL_ROOT/RFdiffusion ($RF_COMMIT)
ProteinMPNN:  $EXTERNAL_ROOT/ProteinMPNN ($MPNN_COMMIT)

This script intentionally does not modify Conda environments. Continue with
REPRODUCE_FROM_ZERO.md, then copy src/local_paths.example.sh to
src/local_paths.sh and set the environment executable paths.
EOF
