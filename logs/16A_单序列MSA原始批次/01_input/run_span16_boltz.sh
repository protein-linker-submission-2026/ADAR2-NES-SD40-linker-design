#!/usr/bin/env bash
set -Eeuo pipefail
DATA_ROOT=${PROJECT_ROOT}/data
HELPER=${PACKAGE_ROOT}/02_原始记录/方法脚本与公共参考/src/pipeline_helper.py
PY=/opt/adar2/envs/boltz/bin/python
BOLTZ=/opt/adar2/envs/boltz/bin/boltz
CACHE=/mnt/d/WSL/Models/Boltz
mkdir -p "$DATA_ROOT/08_boltz2_local/inputs" "$DATA_ROOT/08_boltz2_local/outputs" "$DATA_ROOT/09_rmsd_gate_local" "$DATA_ROOT/04_logs/boltz2_local"

"$PY" - <<'PY'
import json
from pathlib import Path
r=Path('${PROJECT_ROOT}/data/07_sequence_qc')
rows=[json.loads(x) for x in (r/'all_candidates.jsonl').read_text().splitlines()]
passed=[x for x in rows if x['qc']['pass']]
passed.append(json.loads((r/'baseline_candidate.jsonl').read_text()))
Path('${PROJECT_ROOT}/data/08_boltz2_local/candidates_to_predict.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in passed))
print(f'Boltz candidates: {len(passed)}')
PY

total=$(wc -l < "$DATA_ROOT/08_boltz2_local/candidates_to_predict.jsonl")
n=0
while IFS= read -r row; do
  n=$((n+1))
  cid=$(printf '%s' "$row" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["candidate_id"])')
  seq=$(printf '%s' "$row" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["full_sequence"])')
  yaml="$DATA_ROOT/08_boltz2_local/inputs/$cid.yaml"
  out="$DATA_ROOT/08_boltz2_local/outputs/$cid"
  eval="$DATA_ROOT/09_rmsd_gate_local/$cid.json"
  log="$DATA_ROOT/04_logs/boltz2_local/$cid.log"
  "$PY" "$HELPER" make-yaml "$seq" "$yaml" "$cid" >/dev/null
  mkdir -p "$out"
  seed=$(printf '%s' "$cid" | "$PY" -c 'import hashlib,sys; s=sys.stdin.read(); print(int.from_bytes(hashlib.sha256(s.encode()).digest()[:4],"big")%2147483646+1)')
  found=$(find "$out" -type f -name '*_model_*.pdb' 2>/dev/null | wc -l)
  if (( found < 3 )); then
    echo "[$n/$total] Boltz-2 $cid seed=$seed"
    "$BOLTZ" predict "$yaml" --out_dir "$out" --cache "$CACHE" --model boltz2 \
      --accelerator gpu --devices 1 --recycling_steps 3 --sampling_steps 200 \
      --diffusion_samples 3 --max_parallel_samples 1 --output_format pdb \
      --write_full_pae --use_potentials --no_kernels --seed "$seed" --override 2>&1 | tee "$log"
  else
    echo "[$n/$total] Reusing 3 existing Boltz models for $cid"
  fi
  tmp="$DATA_ROOT/08_boltz2_local/current_candidate.jsonl"
  printf '%s\n' "$row" > "$tmp"
  "$PY" "$HELPER" evaluate-boltz "$tmp" "$cid" "$out" "$eval"
done < "$DATA_ROOT/08_boltz2_local/candidates_to_predict.jsonl"
