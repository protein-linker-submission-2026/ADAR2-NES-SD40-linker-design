#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/pipeline_config.sh"
HELPER="$SCRIPT_DIR/pipeline_helper.py"
REPORTER="$SCRIPT_DIR/span_report.py"
SPAN=""; OUTPUT=""; MSA_MODE="online"; STAGE="all"; DRY_RUN=false

usage(){ echo "Usage: $0 --span {11..20} --output-root ${PROJECT_ROOT}/<span> --msa-mode online [--stage rf|mpnn|qc|boltz|ranker|finalize|all] [--dry-run]"; }
while (($#)); do
  case "$1" in
    --span) SPAN="$2"; shift 2;;
    --output-root) OUTPUT="$2"; shift 2;;
    --msa-mode) MSA_MODE="$2"; shift 2;;
    --stage) STAGE="$2"; shift 2;;
    --dry-run) DRY_RUN=true; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2;;
  esac
done

[[ "$SPAN" =~ ^(11|12|13|14|15|16|17|18|19|20)$ ]] || { echo "span must be one of 11-20" >&2; exit 2; }
[[ "$OUTPUT" == "${PROJECT_ROOT}/$SPAN" ]] || { echo "output-root must be exactly ${PROJECT_ROOT}/$SPAN" >&2; exit 2; }
[[ "$MSA_MODE" == online ]] || { echo "this remaining-span run requires --msa-mode online" >&2; exit 2; }
[[ "$STAGE" =~ ^(rf|mpnn|qc|boltz|ranker|finalize|all)$ ]] || { echo "invalid stage: $STAGE" >&2; exit 2; }

POSE="$PACKAGE_ROOT/references/poses_11-20A_spin0/ADAR2_NES_SD40_pose_span_$(printf '%02d' "$SPAN")A_spin0.pdb"
SHARED=${PROJECT_ROOT}/_shared/baseline_online
mkdir_layout(){ mkdir -p "$OUTPUT"/{01_input,02_rfdiffusion_raw,03_rfdiffusion_validated,04_logs/{rfdiffusion,proteinmpnn,boltz2},05_reports,06_proteinmpnn,07_sequence_qc,08_msa_online,08_boltz2_local/{inputs,outputs},09_rmsd_gate_local,10_docking,11_ranker,state}; }

preflight(){
  [[ -s "$POSE" ]] || { echo "missing pose: $POSE" >&2; exit 1; }
  [[ -x "$RFDIFFUSION_PYTHON" && -x "$PROTEIN_MPNN_PYTHON" && -x "$BOLTZ_PYTHON" ]] || { echo "one or more Python environments are missing" >&2; exit 1; }
  [[ -x /opt/adar2/envs/boltz/bin/boltz ]] || { echo "Boltz executable missing" >&2; exit 1; }
  local free_kb; free_kb=$(df -Pk /mnt/d | awk 'NR==2{print $4}')
  (( free_kb >= 68*1024*1024 )) || { echo "D drive has less than the required 68 GiB free" >&2; exit 1; }
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
  "$BOLTZ_PYTHON" "$HELPER" check-only --root "$PACKAGE_ROOT" >/dev/null
}

if $DRY_RUN; then
  preflight
  printf '{"status":"ok","dry_run":true,"span_A":%s,"output_root":"%s","msa_mode":"online","rf_backbones":3,"mpnn_requested":30,"historical_span_16_preserved":true}\n' "$SPAN" "$OUTPUT"
  exit 0
fi

mkdir_layout; preflight
cp -f "$POSE" "$OUTPUT/01_input/"
cat > "$OUTPUT/01_input/run_parameters.txt" <<EOF
span_A=$SPAN
spin_deg=0
rf_designs=3
mpnn_sequences_per_backbone=10
msa_mode=online
msa_server=https://api.colabfold.com
boltz_model=boltz2
boltz_sampling_steps=200
boltz_recycling_steps=3
boltz_diffusion_samples=3
vina_exhaustiveness=32
vina_num_modes=9
vina_energy_range=3
vina_score_cutoff=-6.0
ranker_weights=0.3,0.3,0.4
EOF

run_rf(){
  for idx in 0 1 2; do
    raw="$OUTPUT/02_rfdiffusion_raw/design_${idx}.pdb"; final="$OUTPUT/03_rfdiffusion_validated/span${SPAN}A_design_${idx}.pdb"
    if [[ ! -s "$raw" ]]; then
      prefix="$OUTPUT/02_rfdiffusion_raw/design"
      (cd "$RFDIFFUSION_DIR" && "$RFDIFFUSION_PYTHON" scripts/run_inference.py \
        "inference.input_pdb=$POSE" "inference.output_prefix=$prefix" inference.num_designs=1 \
        "inference.design_startnum=$idx" inference.deterministic=True \
        "inference.model_directory_path=$RFDIFFUSION_DIR/models" "contigmap.contigs=$RF_CONTIG") \
        2>&1 | tee "$OUTPUT/04_logs/rfdiffusion/design_${idx}.log"
    fi
    [[ -s "$raw" ]] || { echo "RF output missing: $raw" >&2; exit 1; }
    if [[ ! -s "$final" ]]; then "$BOLTZ_PYTHON" "$HELPER" postprocess-rf "$raw" "$final"; fi
    tmp="$OUTPUT/state/validate_design_${idx}.pdb"
    "$BOLTZ_PYTHON" "$HELPER" postprocess-rf "$final" "$tmp" >/dev/null
    cmp -s "$final" "$tmp" || { echo "validated RF file changed under repeat validation: $final" >&2; exit 1; }
    rm -f "$tmp"
  done
  : > "$OUTPUT/03_rfdiffusion_validated/backbone_manifest.jsonl"
  for idx in 0 1 2; do
    final="$OUTPUT/03_rfdiffusion_validated/span${SPAN}A_design_${idx}.pdb"
    printf '{"target_span_A":%d,"rf_design_index":%d,"rf_seed":%d,"rf_backbone_id":"span%dA_design_%d","rf_pdb_path":"%s"}\n' "$SPAN" "$idx" "$idx" "$SPAN" "$idx" "$final" >> "$OUTPUT/03_rfdiffusion_validated/backbone_manifest.jsonl"
  done
  touch "$OUTPUT/state/rf.complete"
}

run_mpnn(){
  printf '%s\n' '{"C":-0.30,"K":-0.10,"R":-0.10}' > "$OUTPUT/06_proteinmpnn/linker_bias_AA.jsonl"
  for idx in 0 1 2; do
    id="span${SPAN}A_design_${idx}"; pdb="$OUTPUT/03_rfdiffusion_validated/$id.pdb"; work="$OUTPUT/06_proteinmpnn/$id"; fa="$work/output/seqs/$id.fa"
    [[ -s "$pdb" ]] || { echo "missing validated RF backbone: $pdb" >&2; exit 1; }
    mkdir -p "$work/input" "$work/output"; cp -f "$pdb" "$work/input/$id.pdb"
    (cd "$PROTEIN_MPNN_DIR"
      "$PROTEIN_MPNN_PYTHON" helper_scripts/parse_multiple_chains.py --input_path "$work/input" --output_path "$work/parsed.jsonl"
      "$PROTEIN_MPNN_PYTHON" helper_scripts/assign_fixed_chains.py --input_path "$work/parsed.jsonl" --output_path "$work/assigned.jsonl" --chain_list A
      "$PROTEIN_MPNN_PYTHON" helper_scripts/make_fixed_positions_dict.py --input_path "$work/parsed.jsonl" --output_path "$work/fixed.jsonl" --chain_list A --position_list "394 395 396 397 398 399 400 401 402 403" --specify_non_fixed)
    count=$(grep -c '^>' "$fa" 2>/dev/null || true)
    if (( count < 11 )); then
      if [[ -d "$work/output" && -n "$(find "$work/output" -type f -print -quit 2>/dev/null)" ]]; then mv "$work/output" "$work/output.incomplete.$(date +%Y%m%d_%H%M%S)"; mkdir -p "$work/output"; fi
      (cd "$PROTEIN_MPNN_DIR" && "$PROTEIN_MPNN_PYTHON" protein_mpnn_run.py --jsonl_path "$work/parsed.jsonl" --chain_id_jsonl "$work/assigned.jsonl" --fixed_positions_jsonl "$work/fixed.jsonl" --bias_AA_jsonl "$OUTPUT/06_proteinmpnn/linker_bias_AA.jsonl" --out_folder "$work/output" --num_seq_per_target 10 --sampling_temp 0.15 --seed "$((100000+SPAN*10+idx))" --batch_size 1) 2>&1 | tee "$OUTPUT/04_logs/proteinmpnn/$id.log"
    fi
    [[ $(grep -c '^>' "$fa") -ge 11 ]] || { echo "ProteinMPNN returned fewer than 10 samples for $id" >&2; exit 1; }
    "$BOLTZ_PYTHON" "$HELPER" collect-mpnn "$fa" "$id" "$work/candidates.jsonl" --limit 10 --rf-pdb-path "$pdb" --target-span "$SPAN" --rf-design-index "$idx" --rf-seed "$idx" >/dev/null
  done
  touch "$OUTPUT/state/mpnn.complete"
}

run_qc(){
  "$BOLTZ_PYTHON" "$REPORTER" prepare-qc --root "$OUTPUT" --span "$SPAN"
  "$BOLTZ_PYTHON" "$REPORTER" prepare-boltz-list --root "$OUTPUT"
  touch "$OUTPUT/state/qc.complete"
}

run_boltz(){
  list="$OUTPUT/08_boltz2_local/candidates_to_predict.jsonl"; [[ -s "$list" ]] || run_qc
  total=$(grep -c . "$list"); n=0
  while IFS= read -r row; do
    [[ -n "$row" ]] || continue; n=$((n+1))
    cid=$(printf '%s' "$row" | "$BOLTZ_PYTHON" -c 'import json,sys; print(json.load(sys.stdin)["candidate_id"])')
    seq=$(printf '%s' "$row" | "$BOLTZ_PYTHON" -c 'import json,sys; print(json.load(sys.stdin)["full_sequence"])')
    yaml="$OUTPUT/08_boltz2_local/inputs/$cid.yaml"; out="$OUTPUT/08_boltz2_local/outputs/$cid"; eval="$OUTPUT/09_rmsd_gate_local/$cid.json"; msadir="$OUTPUT/08_msa_online/$cid"; log="$OUTPUT/04_logs/boltz2/$cid.log"
    mkdir -p "$out" "$msadir" "$OUTPUT/state/candidates"
    "$BOLTZ_PYTHON" "$HELPER" make-yaml "$seq" "$yaml" "$cid" --msa-mode online --query-fasta "$msadir/query.fasta" >/dev/null
    printf '%s\n' "$row" > "$OUTPUT/state/candidates/$cid.jsonl"
    if [[ "$cid" == baseline_GGGGSGGGGS && $(find "$SHARED/outputs/$cid" -type f -name '*_model_*.pdb' 2>/dev/null | wc -l) -ge 3 && $(find "$out" -type f -name '*_model_*.pdb' 2>/dev/null | wc -l) -lt 3 ]]; then
      cp -a "$SHARED/outputs/$cid/." "$out/"
      [[ ! -d "$SHARED/msa/$cid" ]] || cp -a "$SHARED/msa/$cid/." "$msadir/"
      echo "Reused shared online-MSA baseline" >> "$log"
    fi
    found=$(find "$out" -type f -name '*_model_*.pdb' 2>/dev/null | wc -l)
    if (( found < 3 )); then
      success=false
      for attempt in 1 2 3; do
        echo "[$n/$total] Boltz-2 + online MSA $cid attempt=$attempt" | tee -a "$log"
        if /opt/adar2/envs/boltz/bin/boltz predict "$yaml" --out_dir "$out" --cache "$BOLTZ_CACHE" --model boltz2 --accelerator gpu --devices 1 --recycling_steps 3 --sampling_steps 200 --diffusion_samples 3 --max_parallel_samples 1 --output_format pdb --write_full_pae --use_potentials --no_kernels --seed "$(printf '%s' "$cid" | "$BOLTZ_PYTHON" -c 'import hashlib,sys; s=sys.stdin.read(); print(int.from_bytes(hashlib.sha256(s.encode()).digest()[:4],"big")%2147483646+1)')" --use_msa_server --msa_server_url https://api.colabfold.com --msa_pairing_strategy greedy 2>&1 | tee -a "$log"; then
          found=$(find "$out" -type f -name '*_model_*.pdb' | wc -l); if (( found >= 3 )); then success=true; break; fi
        fi
        sleep $((attempt*30))
      done
      $success || { printf '{"status":"failed","candidate_id":"%s","reason":"online MSA or Boltz failed after 3 attempts"}\n' "$cid" > "$msadir/status.json"; exit 1; }
    fi
    find "$out" -type f \( -name '*.a3m' -o -name '*.csv' -o -name '*.m8' -o -name '*.tar.gz' \) -exec cp -f {} "$msadir/" \; 2>/dev/null || true
    printf '{"status":"complete","candidate_id":"%s","msa_mode":"online","server":"https://api.colabfold.com","models":3}\n' "$cid" > "$msadir/status.json"
    "$BOLTZ_PYTHON" "$HELPER" evaluate-boltz "$OUTPUT/state/candidates/$cid.jsonl" "$cid" "$out" "$eval" >/dev/null
    if [[ "$cid" == baseline_GGGGSGGGGS && $(find "$SHARED/outputs/$cid" -type f -name '*_model_*.pdb' 2>/dev/null | wc -l) -lt 3 ]]; then
      mkdir -p "$SHARED/outputs/$cid" "$SHARED/msa/$cid"; cp -a "$out/." "$SHARED/outputs/$cid/"; cp -a "$msadir/." "$SHARED/msa/$cid/"
    fi
  done < "$list"
  touch "$OUTPUT/state/boltz.complete"
}

run_ranker(){
  "$BOLTZ_PYTHON" "$REPORTER" prepare-ranker --root "$OUTPUT"
  mkdir -p "$OUTPUT/11_ranker"
  (cd "$PACKAGE_ROOT/ranker/sd40_linker_ranker_v0_1" && PYTHONPATH="$PWD/src" "$BOLTZ_PYTHON" -m sd40_linker_ranker.cli rank --config config.yaml --candidates "$OUTPUT/11_ranker/candidates" --output "$OUTPUT/11_ranker/ranking.csv")
  touch "$OUTPUT/state/ranker.complete"
}

run_finalize(){ "$BOLTZ_PYTHON" "$REPORTER" finalize --root "$OUTPUT" --span "$SPAN"; touch "$OUTPUT/state/finalize.complete"; }

case "$STAGE" in
  rf) run_rf;; mpnn) run_mpnn;; qc) run_qc;; boltz) run_boltz;; ranker) run_ranker;; finalize) run_finalize;;
  all) run_rf; run_mpnn; run_qc; run_boltz;;
esac
