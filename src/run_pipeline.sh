#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${PIPELINE_CONFIG:-$SCRIPT_DIR/pipeline_config.sh}"
HELPER="$SCRIPT_DIR/pipeline_helper.py"
POSES="$REFERENCE_ROOT/poses_11-20A_spin0"
STAGE=check
[[ "${1:-}" == "--check-only" ]] && STAGE=check
if [[ "${1:-}" == "--run-expensive" ]]; then STAGE="${2:-all}"; fi

prepare_and_check() {
  "$BOLTZ_PYTHON" "$SCRIPT_DIR/prepare_references.py" --root "$PACKAGE_ROOT"
  "$BOLTZ_PYTHON" "$SCRIPT_DIR/pose_generator.py" --root "$PACKAGE_ROOT"
  "$BOLTZ_PYTHON" "$HELPER" check-only --root "$PACKAGE_ROOT"
}

write_bias() {
  mkdir -p "$OUTPUT_ROOT/state"
  printf '%s\n' '{"C":-0.30,"K":-0.10,"R":-0.10}' > "$OUTPUT_ROOT/state/linker_bias_AA.jsonl"
}

run_rf() {
  mkdir -p "$OUTPUT_ROOT/rfdiffusion/raw" "$OUTPUT_ROOT/rfdiffusion/final" "$OUTPUT_ROOT/logs/rfdiffusion"
  : > "$OUTPUT_ROOT/rfdiffusion/backbone_manifest.jsonl"
  for span in $(seq 11 20); do
    pose="$POSES/ADAR2_NES_SD40_pose_span_$(printf '%02d' "$span")A_spin0.pdb"
    prefix="$OUTPUT_ROOT/rfdiffusion/raw/span_$(printf '%02d' "$span")A/design"
    mkdir -p "$(dirname "$prefix")"
    if [[ ! -s "${prefix}_2.pdb" ]]; then
      (cd "$RFDIFFUSION_DIR" && "$RFDIFFUSION_PYTHON" scripts/run_inference.py \
        "inference.input_pdb=$pose" "inference.output_prefix=$prefix" \
        inference.num_designs=3 inference.design_startnum=0 inference.deterministic=True \
        "inference.model_directory_path=$RFDIFFUSION_DIR/models" \
        "contigmap.contigs=$RF_CONTIG") 2>&1 | tee "$OUTPUT_ROOT/logs/rfdiffusion/span_${span}A.log"
    fi
    for idx in 0 1 2; do
      raw="${prefix}_${idx}.pdb"; final="$OUTPUT_ROOT/rfdiffusion/final/span_$(printf '%02d' "$span")A_design_${idx}.pdb"
      [[ -s "$raw" ]] || { echo "Missing RF design: $raw" >&2; exit 1; }
      "$BOLTZ_PYTHON" "$HELPER" postprocess-rf "$raw" "$final"
      printf '{"target_span_A":%d,"rf_design_index":%d,"rf_seed":%d,"rf_backbone_id":"span_%02dA_design_%d","rf_pdb_path":"%s"}\n' "$span" "$idx" "$idx" "$span" "$idx" "$final" >> "$OUTPUT_ROOT/rfdiffusion/backbone_manifest.jsonl"
    done
  done
}

run_mpnn() {
  write_bias; mkdir -p "$OUTPUT_ROOT/mpnn" "$OUTPUT_ROOT/logs/mpnn"
  for span in $(seq 11 20); do for idx in 0 1 2; do
    id="span_$(printf '%02d' "$span")A_design_${idx}"; pdb="$OUTPUT_ROOT/rfdiffusion/final/$id.pdb"; work="$OUTPUT_ROOT/mpnn/$id"; mkdir -p "$work/input" "$work/output"
    cp -f "$pdb" "$work/input/$id.pdb"
    (cd "$PROTEIN_MPNN_DIR"
      "$PROTEIN_MPNN_PYTHON" helper_scripts/parse_multiple_chains.py --input_path "$work/input" --output_path "$work/parsed.jsonl"
      "$PROTEIN_MPNN_PYTHON" helper_scripts/assign_fixed_chains.py --input_path "$work/parsed.jsonl" --output_path "$work/assigned.jsonl" --chain_list A
      "$PROTEIN_MPNN_PYTHON" helper_scripts/make_fixed_positions_dict.py --input_path "$work/parsed.jsonl" --output_path "$work/fixed.jsonl" --chain_list A --position_list "394 395 396 397 398 399 400 401 402 403" --specify_non_fixed
      "$PROTEIN_MPNN_PYTHON" protein_mpnn_run.py --jsonl_path "$work/parsed.jsonl" --chain_id_jsonl "$work/assigned.jsonl" --fixed_positions_jsonl "$work/fixed.jsonl" --bias_AA_jsonl "$OUTPUT_ROOT/state/linker_bias_AA.jsonl" --out_folder "$work/output" --num_seq_per_target 10 --sampling_temp 0.15 --seed "$((100000+span*10+idx))" --batch_size 1
    ) 2>&1 | tee "$OUTPUT_ROOT/logs/mpnn/$id.log"
    "$BOLTZ_PYTHON" "$HELPER" collect-mpnn "$work/output/seqs/$id.fa" "$id" "$work/candidates.jsonl" --limit 10 --rf-pdb-path "$pdb" --target-span "$span" --rf-design-index "$idx" --rf-seed "$idx"
  done; done
  mkdir -p "$OUTPUT_ROOT/mpnn/baseline"
  "$BOLTZ_PYTHON" "$HELPER" write-baseline "$OUTPUT_ROOT/mpnn/baseline/candidates.jsonl"
}

run_boltz() {
  mkdir -p "$OUTPUT_ROOT/boltz/inputs" "$OUTPUT_ROOT/boltz/outputs" "$OUTPUT_ROOT/logs/boltz"
  mkdir -p "$OUTPUT_ROOT/mpnn/baseline" "$OUTPUT_ROOT/boltz/evaluations"
  "$BOLTZ_PYTHON" "$HELPER" write-baseline "$OUTPUT_ROOT/mpnn/baseline/candidates.jsonl" >/dev/null
  find "$OUTPUT_ROOT/mpnn" -name candidates.jsonl -print0 | while IFS= read -r -d '' f; do
  "$BOLTZ_PYTHON" - "$f" "$HELPER" "$OUTPUT_ROOT" "$BOLTZ_EXE" "$BOLTZ_CACHE" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
f,helper,root,boltz_exe,boltz_cache=Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3]),sys.argv[4],sys.argv[5]
for row in map(json.loads,f.read_text().splitlines()):
 if not row['qc']['pass']: continue
 cid=row['candidate_id']; y=root/'boltz/inputs'/f'{cid}.yaml'; out=root/'boltz/outputs'/cid
 subprocess.run([sys.executable,helper,'make-yaml',row['full_sequence'],str(y),cid],check=True)
 seed=int.from_bytes(hashlib.sha256(cid.encode()).digest()[:4],'big')%2147483646+1
 cmd=[boltz_exe,'predict',str(y),'--out_dir',str(out),'--cache',boltz_cache,'--model','boltz2','--accelerator','gpu','--devices','1','--recycling_steps','3','--sampling_steps','200','--diffusion_samples','3','--max_parallel_samples','1','--output_format','pdb','--no_kernels','--seed',str(seed)]
 if len(list(out.rglob('*_model_*.pdb'))) < 3: subprocess.run(cmd,check=True)
 evaluation=root/'boltz/evaluations'/f'{cid}.json'
 subprocess.run([sys.executable,helper,'evaluate-boltz',str(f),cid,str(out),str(evaluation)],check=True)
PY
  done
}

run_ranker() {
  run_id="$(date +%Y%m%d_%H%M%S)"; docking="$OUTPUT_ROOT/docking"; candidates="$OUTPUT_ROOT/ranker/runs/$run_id/candidates"; ranking="$OUTPUT_ROOT/ranker/runs/$run_id/ranking.csv"; mkdir -p "$candidates"
  "$BOLTZ_PYTHON" - "$docking" "$candidates" <<'PY'
import json,shutil,sys
from pathlib import Path
src,dst=Path(sys.argv[1]),Path(sys.argv[2])
for p in src.glob('*.json'):
 r=json.loads(p.read_text())
 # 正式设计候选必须通过Vina 2/3门控；人工baseline即使未通过也保留作对照。
 if not r.get('vina_gate',{}).get('candidate_pass') and r.get('candidate_type') != 'baseline': continue
 for m in r['models']:
  q=Path(m['prediction_pdb']); shutil.copy2(q,dst/f"{r['candidate_id']}_model_{m['model_index']}.pdb")
PY
  PYTHONPATH="$PACKAGE_ROOT/ranker/sd40_linker_ranker_v0_1/src" "$BOLTZ_PYTHON" -m sd40_linker_ranker.cli rank --config "$PACKAGE_ROOT/ranker/sd40_linker_ranker_v0_1/config.yaml" --candidates "$candidates" --output "$ranking"
}

prepare_and_check
case "$STAGE" in
  check) echo "CHECK-ONLY complete; no RFdiffusion, ProteinMPNN, Boltz-2 or Vina calculation was started.";;
  rf) run_rf;;
  mpnn) run_mpnn;;
  boltz) run_boltz;;
  ranker) run_ranker;;
  all) run_rf; run_mpnn; run_boltz; echo "Docking is intentionally a separately reviewed stage; use docking_helper.py after PDBQT preparation.";;
  *) echo "Usage: $0 --check-only | --run-expensive {rf|mpnn|boltz|ranker|all}" >&2; exit 2;;
esac
