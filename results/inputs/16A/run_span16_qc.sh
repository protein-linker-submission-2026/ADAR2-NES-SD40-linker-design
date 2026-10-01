#!/usr/bin/env bash
set -Eeuo pipefail
# Historical production defaults are retained for provenance and can be
# overridden when replaying this stage on another machine.
HELPER=${PIPELINE_HELPER:-${PACKAGE_ROOT}/02_原始记录/方法脚本与公共参考/src/pipeline_helper.py}
PY=${BOLTZ_PYTHON:-/opt/adar2/envs/boltz/bin/python}
DATA_ROOT=${PROJECT_ROOT}/data
: > "$DATA_ROOT/07_sequence_qc/all_candidates.jsonl"
for idx in 0 1 2; do
  id="span16A_design_${idx}"
  fasta="$DATA_ROOT/06_proteinmpnn/$id/output/seqs/$id.fa"
  out="$DATA_ROOT/07_sequence_qc/${id}_candidates.jsonl"
  "$PY" "$HELPER" collect-mpnn "$fasta" "$id" "$out" --limit 10 \
    --rf-pdb-path "$DATA_ROOT/03_rfdiffusion_validated/$id.pdb" \
    --target-span 16 --rf-design-index "$idx" --rf-seed "$idx"
  cat "$out" >> "$DATA_ROOT/07_sequence_qc/all_candidates.jsonl"
done
"$PY" "$HELPER" write-baseline "$DATA_ROOT/07_sequence_qc/baseline_candidate.jsonl"
"$PY" - <<'PY'
import csv,json
from pathlib import Path
root=Path('${PROJECT_ROOT}/data/07_sequence_qc')
rows=[json.loads(x) for x in (root/'all_candidates.jsonl').read_text().splitlines()]
fields=['candidate_id','rf_backbone_id','target_span_A','rf_design_index','rf_seed','sample_index','linker_sequence','qc_pass','reasons','kr_fraction','hydrophobic_fraction','net_charge']
with (root/'sequence_qc.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for x in rows:
        q=x['qc']; w.writerow({'candidate_id':x['candidate_id'],'rf_backbone_id':x['rf_backbone_id'],'target_span_A':x['target_span_A'],'rf_design_index':x['rf_design_index'],'rf_seed':x['rf_seed'],'sample_index':x['sample_index'],'linker_sequence':x['linker_sequence'],'qc_pass':q['pass'],'reasons':';'.join(q['reasons']),'kr_fraction':q['kr_fraction'],'hydrophobic_fraction':q['hydrophobic_fraction'],'net_charge':q['net_charge']})
print('total',len(rows),'pass',sum(x['qc']['pass'] for x in rows),'fail',sum(not x['qc']['pass'] for x in rows))
for x in rows: print(x['rf_backbone_id'],x['sample_index'],x['linker_sequence'],'PASS' if x['qc']['pass'] else ','.join(x['qc']['reasons']))
PY
