#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"; source "$SCRIPT_DIR/pipeline_config.sh"
echo "ADAR2-SD40 Linker Pipeline V2"
echo "Authoritative construct: 439 aa; linker A394-A403; SD40 A404-A439 (36 aa)"
echo "Grid: spans 11-20 A x 3 RF designs = 30 backbones; 10 MPNN sequences/backbone"
for d in rfdiffusion/final mpnn boltz/outputs boltz/evaluations docking ranker; do
  n=$(find "$OUTPUT_ROOT/$d" -type f 2>/dev/null | wc -l); printf '%-24s %s files\n' "$d" "$n"
done
if [[ -d "$OUTPUT_ROOT/boltz/evaluations" ]]; then
  "$BOLTZ_PYTHON" - "$OUTPUT_ROOT/boltz/evaluations" "$OUTPUT_ROOT/docking" <<'PY'
import json,sys
from pathlib import Path
ev=list(Path(sys.argv[1]).glob('*.json')); rf=sum(json.loads(p.read_text()).get('rf_rmsd_gate',{}).get('candidate_pass') is True for p in ev); baseline=sum(json.loads(p.read_text()).get('candidate_type')=='baseline' for p in ev)
dock=list(Path(sys.argv[2]).glob('*.json')) if Path(sys.argv[2]).exists() else []; vp=sum(json.loads(p.read_text()).get('vina_gate',{}).get('candidate_pass') is True for p in dock)
print(f"Boltz evaluations={len(ev)} RF_2of3_pass={rf} baseline={baseline} Vina_2of3_pass={vp}")
PY
fi
echo "Legacy smoke-test files are under legacy_results/ and are not V2 results."
