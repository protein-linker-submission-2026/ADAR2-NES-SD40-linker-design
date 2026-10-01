#!/usr/bin/env bash
set -Eeuo pipefail
# Historical production defaults are retained for provenance and can be
# overridden when replaying this stage on another machine.
MPNN_DIR=${PROTEINMPNN_DIR:-/opt/adar2/ProteinMPNN}
MPNN_PY=${PROTEINMPNN_PYTHON:-/opt/adar2/envs/rfdiffusion/bin/python}
DATA_ROOT=${PROJECT_ROOT}/data
for idx in 0 1 2; do
  id="span16A_design_${idx}"
  work="$DATA_ROOT/06_proteinmpnn/$id"
  mkdir -p "$work/input" "$work/output"
  cp -f "$DATA_ROOT/03_rfdiffusion_validated/$id.pdb" "$work/input/$id.pdb"
  cd "$MPNN_DIR"
  "$MPNN_PY" helper_scripts/parse_multiple_chains.py --input_path "$work/input" --output_path "$work/parsed.jsonl"
  "$MPNN_PY" helper_scripts/assign_fixed_chains.py --input_path "$work/parsed.jsonl" --output_path "$work/assigned.jsonl" --chain_list A
  "$MPNN_PY" helper_scripts/make_fixed_positions_dict.py --input_path "$work/parsed.jsonl" --output_path "$work/fixed.jsonl" --chain_list A --position_list "394 395 396 397 398 399 400 401 402 403" --specify_non_fixed
  "$MPNN_PY" protein_mpnn_run.py \
    --jsonl_path "$work/parsed.jsonl" \
    --chain_id_jsonl "$work/assigned.jsonl" \
    --fixed_positions_jsonl "$work/fixed.jsonl" \
    --bias_AA_jsonl "$DATA_ROOT/06_proteinmpnn/linker_bias_AA.jsonl" \
    --out_folder "$work/output" \
    --num_seq_per_target 10 \
    --sampling_temp 0.15 \
    --seed "$((100160 + idx))" \
    --batch_size 1 2>&1 | tee "$DATA_ROOT/04_logs/proteinmpnn_${id}.log"
done
