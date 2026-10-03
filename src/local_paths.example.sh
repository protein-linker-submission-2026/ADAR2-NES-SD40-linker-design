#!/usr/bin/env bash
# Copy this file to src/local_paths.sh and edit only the paths for this machine.
# The copied file is ignored by Git.

RFDIFFUSION_DIR="$PACKAGE_ROOT/external/RFdiffusion"
RFDIFFUSION_PYTHON="$HOME/miniconda3/envs/rfdiffusion/bin/python"

PROTEIN_MPNN_DIR="$PACKAGE_ROOT/external/ProteinMPNN"
# The recorded production run used the verified RFdiffusion PyTorch environment.
PROTEIN_MPNN_PYTHON="$RFDIFFUSION_PYTHON"

BOLTZ_PYTHON="$HOME/miniconda3/envs/boltz/bin/python"
BOLTZ_EXE="$HOME/miniconda3/envs/boltz/bin/boltz"
BOLTZ_CACHE="$PACKAGE_ROOT/cache/boltz"

# Output storage should have at least 68 GiB free for a complete 11-20 A run.
RUN_ROOT="${RUN_ROOT:-$PACKAGE_ROOT/reproduction_runs}"
MIN_FREE_GB=68
MSA_SERVER_URL="https://api.colabfold.com"
