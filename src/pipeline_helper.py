#!/usr/bin/env python3
"""V2 validation, sequence QC, RF post-processing and Boltz input helpers."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
import numpy as np
from prepare_references import ADAR_SEQUENCE,NES_SEQUENCE,SD40_SEQUENCE,AA3

ADAR_END=384; NES_START=385; NES_END=393; LINKER_START=394; LINKER_END=403; SD40_START=404; SD40_END=439; FUSION_LENGTH=439
CANONICAL=set("ACDEFGHIKLMNPQRSTVWY"); HYDRO=set("ILVMFWY")

def pdb_residues(path,chain="A"):
    out=[]; seen=set()
    for l in Path(path).read_text(errors="replace").splitlines():
        if l.startswith("ATOM  ") and l[21]==chain and l[16] in " A":
            key=(int(l[22:26]),l[26]);
            if key not in seen: out.append((key[0],AA3.get(l[17:20],"X"))); seen.add(key)
    return out

def validate_fusion_pdb(path,require_fixed_sequence=True):
    rs=pdb_residues(path); ids=[r for r,_ in rs]; seq="".join(a for _,a in rs)
    errors=[]
    if ids!=list(range(1,440)): errors.append(f"expected A1-A439, found {len(ids)} residues")
    if len(seq)!=439: errors.append(f"expected 439 aa, found {len(seq)}")
    if require_fixed_sequence and len(seq)==439:
        if seq[:384]!=ADAR_SEQUENCE: errors.append("ADAR2DD A1-A384 mismatch")
        if seq[384:393]!=NES_SEQUENCE: errors.append("NES A385-A393 mismatch")
        if seq[403:439]!=SD40_SEQUENCE: errors.append("SD40 A404-A439 is not the authoritative 36-aa sequence")
    if errors: raise ValueError("; ".join(errors))
    return {"length":439,"linker":seq[393:403],"sd40":seq[403:439],"sd40_count":36}

def postprocess_rf(input_pdb,output_pdb):
    lines=Path(input_pdb).read_text(errors="replace").splitlines(); out=[]
    for l in lines:
        if l.startswith("ATOM  ") and l[21]=="A" and int(l[22:26])==404: l=l[:17]+"LEU"+l[20:]
        out.append(l)
    Path(output_pdb).parent.mkdir(parents=True,exist_ok=True); Path(output_pdb).write_text("\n".join(out)+"\n",newline="\n")
    return validate_fusion_pdb(output_pdb)

def sequence_qc(linker):
    reasons=[]
    if len(linker)!=10: reasons.append("linker_length_not_10")
    if any(a not in CANONICAL for a in linker): reasons.append("non_standard_amino_acid")
    if linker.count("C")>=2: reasons.append("cys_count_ge_2")
    if any(sum(a in "KR" for a in linker[i:i+5])>=4 for i in range(max(0,len(linker)-4))): reasons.append("five_residue_window_KR_ge_4")
    if any(sum(a in HYDRO for a in linker[i:i+5])>=4 for i in range(max(0,len(linker)-4))): reasons.append("five_residue_window_hydrophobic_ge_4")
    if re.search(r"(.)\1{4,}",linker): reasons.append("homopolymer_ge_5")
    return {"pass":not reasons,"reasons":reasons,"kr_fraction":sum(a in "KR" for a in linker)/len(linker) if linker else 0.0,"hydrophobic_fraction":sum(a in HYDRO for a in linker)/len(linker) if linker else 0.0,"net_charge":sum(a in "KR" for a in linker)-sum(a in "DE" for a in linker)}

def dedup_key(rf_backbone_id,linker_sequence): return (str(rf_backbone_id),str(linker_sequence))

def ca_coords(path,start=LINKER_START,end=LINKER_END):
    d={}
    for l in Path(path).read_text(errors="replace").splitlines():
        if l.startswith("ATOM  ") and l[21]=="A" and l[12:16].strip()=="CA":
            r=int(l[22:26]);
            if start<=r<=end: d[r]=[float(l[30:38]),float(l[38:46]),float(l[46:54])]
    if set(d)!=set(range(start,end+1)): raise ValueError(f"expected CA atoms A{start}-A{end}")
    return np.array([d[i] for i in range(start,end+1)],dtype=float)

def kabsch_rmsd(reference,mobile):
    p=np.asarray(reference,float); q=np.asarray(mobile,float)
    if p.shape!=q.shape or p.ndim!=2 or p.shape[1]!=3: raise ValueError("coordinate arrays must match Nx3")
    pc=p-p.mean(0); qc=q-q.mean(0); u,_,vt=np.linalg.svd(qc.T@pc); d=np.linalg.det(u@vt); rot=u@np.diag([1,1,d])@vt; fitted=qc@rot
    return float(np.sqrt(np.mean(np.sum((fitted-pc)**2,axis=1))))

def linker_rmsd(reference_pdb,prediction_pdb): return kabsch_rmsd(ca_coords(reference_pdb),ca_coords(prediction_pdb))

def consensus_gate(values,threshold=2.0,required=2,operator="lt"):
    if len(values)!=3: raise ValueError(f"expected exactly 3 model values, found {len(values)}")
    passed=[v<threshold if operator=="lt" else v<=threshold for v in values]
    return {"model_pass":passed,"pass_count":sum(passed),"required":required,"candidate_pass":sum(passed)>=required,"operator":"<" if operator=="lt" else "<=","threshold":threshold}

def make_boltz_yaml(full_sequence,out_path,candidate_id,msa_mode="local",query_fasta=None):
    if len(full_sequence)!=439 or full_sequence[:393]!=ADAR_SEQUENCE+NES_SEQUENCE or full_sequence[403:]!=SD40_SEQUENCE: raise ValueError("Boltz sequence must be the authoritative 439-aa V2 fusion")
    if msa_mode not in {"local","online"}: raise ValueError("msa_mode must be local or online")
    text=f"version: 1\nsequences:\n  - protein:\n      id: A\n      sequence: {full_sequence}\n"
    if msa_mode=="local":
        msa_path=Path(out_path).with_suffix('.a3m').resolve()
        msa_path.write_text(f">{candidate_id}\n{full_sequence}\n",encoding="utf-8",newline="\n")
        text+=f"      msa: {msa_path.as_posix()}\n"
    else:
        q=Path(query_fasta) if query_fasta else Path(out_path).with_suffix('.query.fasta')
        q.parent.mkdir(parents=True,exist_ok=True)
        q.write_text(f">{candidate_id}\n{full_sequence}\n",encoding="utf-8",newline="\n")
    text+=f"# candidate_id: {candidate_id}\n# msa_mode: {msa_mode}\n"
    Path(out_path).parent.mkdir(parents=True,exist_ok=True); Path(out_path).write_text(text,newline="\n")

def collect_mpnn_fasta(fasta,rf_backbone_id,out_jsonl,limit=10,rf_pdb_path=None,target_span=None,rf_design_index=None,rf_seed=None):
    records=[]; name=None; parts=[]
    for raw in Path(fasta).read_text().splitlines()+[">"]:
        if raw.startswith(">"):
            if name is not None: records.append((name,"".join(parts).strip()))
            name=raw[1:].strip(); parts=[]
        else: parts.append(raw.strip())
    generated=records[1:1+limit] # ProteinMPNN writes the input/native record first.
    seen=set(); rows=[]
    for i,(header,seq) in enumerate(generated,1):
        if len(seq)!=439: raise ValueError(f"{rf_backbone_id} sample {i}: expected 439 aa, found {len(seq)}")
        if seq[:393]!=ADAR_SEQUENCE+NES_SEQUENCE or seq[403:]!=SD40_SEQUENCE: raise ValueError(f"{rf_backbone_id} sample {i}: ProteinMPNN modified a fixed position")
        linker=seq[393:403]; key=dedup_key(rf_backbone_id,linker)
        if key in seen: continue
        seen.add(key); qc=sequence_qc(linker); rows.append({"candidate_id":f"{rf_backbone_id}_s{i:02d}_{linker}","candidate_type":"design","rf_gate_applicable":True,"rf_backbone_id":rf_backbone_id,"rf_pdb_path":str(rf_pdb_path) if rf_pdb_path else None,"target_span_A":target_span,"rf_design_index":rf_design_index,"rf_seed":rf_seed,"sample_index":i,"linker_sequence":linker,"full_sequence":seq,"qc":qc,"mpnn_header":header})
    Path(out_jsonl).parent.mkdir(parents=True,exist_ok=True); Path(out_jsonl).write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows),encoding="utf-8",newline="\n")
    return rows

def baseline_row():
    linker="GGGGSGGGGS"; return {"candidate_id":"baseline_GGGGSGGGGS","candidate_type":"baseline","rf_gate_applicable":False,"rf_backbone_id":None,"rf_pdb_path":None,"target_span_A":None,"rf_design_index":None,"rf_seed":None,"sample_index":0,"linker_sequence":linker,"full_sequence":ADAR_SEQUENCE+NES_SEQUENCE+linker+SD40_SEQUENCE,"qc":sequence_qc(linker),"rf_rmsd_status":"not_applicable"}

def find_model_pdbs(output_dir):
    found=[]
    for p in sorted(Path(output_dir).rglob("*.pdb")):
        m=re.search(r"_model_(\d+)\.pdb$",p.name)
        if m: found.append((int(m.group(1)),p))
    unique={i:p for i,p in found}
    return sorted(unique.items())

def evaluate_boltz_candidate(candidate,output_dir,evaluation_path):
    models=find_model_pdbs(output_dir)
    if len(models)!=3: raise ValueError(f"{candidate['candidate_id']}: expected exactly 3 Boltz PDB models, found {len(models)}")
    rows=[]; rmsds=[]
    for idx,pdb in models:
        validate_fusion_pdb(pdb)
        value=None
        if candidate.get("rf_gate_applicable",True):
            rf=Path(candidate.get("rf_pdb_path") or "")
            if not rf.is_file(): raise ValueError(f"{candidate['candidate_id']}: its own rf_pdb_path is missing: {rf}")
            value=linker_rmsd(rf,pdb); rmsds.append(value)
        rows.append({"model_index":idx,"prediction_pdb":str(pdb.resolve()),"linker_ca_atoms":10,"linker_ca_rmsd_A":value})
    if candidate.get("rf_gate_applicable",True):
        gate=consensus_gate(rmsds,2.0,2,"lt"); status="evaluated"
    else:
        gate={"model_pass":[None,None,None],"pass_count":None,"required":None,"candidate_pass":None,"operator":"not_applicable","threshold":None}; status="not_applicable_baseline"
    for row,passed in zip(rows,gate["model_pass"]): row["rf_rmsd_pass"]=passed
    result={"candidate_id":candidate["candidate_id"],"candidate_type":candidate.get("candidate_type","design"),"rf_backbone_id":candidate.get("rf_backbone_id"),"rf_pdb_path":candidate.get("rf_pdb_path"),"rf_rmsd_status":status,"rf_rmsd_gate":gate,"downstream_eligible":True if not candidate.get("rf_gate_applicable",True) else gate["candidate_pass"],"models":rows}
    Path(evaluation_path).parent.mkdir(parents=True,exist_ok=True); Path(evaluation_path).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n"); return result

def load_candidate(jsonl,candidate_id):
    for line in Path(jsonl).read_text(encoding="utf-8").splitlines():
        row=json.loads(line)
        if row["candidate_id"]==candidate_id: return row
    raise KeyError(candidate_id)

def parse_shell_config(path):
    vals={}
    for l in Path(path).read_text().splitlines():
        m=re.match(r"^([A-Z][A-Z0-9_]*)=(?:'([^']*)'|\"([^\"]*)\"|([^#\s]+))",l)
        if m: vals[m.group(1)]=next(x for x in m.groups()[1:] if x is not None)
    return vals

def check_only(root):
    root=Path(root); cfg=parse_shell_config(root/"src"/"pipeline_config.sh"); errors=[]
    expected={"SD40_SEQUENCE_LENGTH":"36","SD40_EXPERIMENTAL_COORDINATE_LENGTH":"35","SD40_UNRESOLVED_POSITION":"1","FUSION_LENGTH":"439","LINKER_START":"394","LINKER_END":"403","SD40_START":"404","SD40_END":"439","RF_GENERATED_POSITIONS":"11","RF_CONTIG":"[A1-393/11/A394-428]","RF_DESIGNS_PER_SPAN":"3","MPNN_SEQUENCES_PER_BACKBONE":"10","VINA_EXHAUSTIVENESS":"32"}
    for k,v in expected.items():
        if cfg.get(k)!=v: errors.append(f"config {k}: expected {v}, got {cfg.get(k)}")
    if "TARGET_PASS" in cfg: errors.append("TARGET_PASS must not exist")
    biases={k:v for k,v in cfg.items() if k.startswith("MPNN_BIAS_")}
    if biases!={"MPNN_BIAS_C":"-0.30","MPNN_BIAS_K":"-0.10","MPNN_BIAS_R":"-0.10"}: errors.append(f"bias values must be exactly C=-0.30,K=-0.10,R=-0.10; got {biases}")
    meta=json.loads((root/"references"/"prepared"/"reference_metadata.json").read_text(encoding="utf-8"))
    if meta["SD40"]["sequence"]!=SD40_SEQUENCE or meta["SD40"]["sequence_length"]!=36 or meta["SD40"]["experimental_coordinate_length"]!=35: errors.append("SD40 reference metadata invalid")
    if meta.get("MIQ",{}).get("validation",{}).get("experimental_heavy_atoms")!=25 or not meta["MIQ"]["validation"].get("stereocenters"): errors.append("MIQ CCD bond/stereochemistry validation invalid")
    if len(pdb_residues(root/"references"/"prepared"/"5ED1_ADAR2DD_E488Q_A1-384.pdb"))!=384: errors.append("5ED1 prepared reference invalid")
    poses=json.loads((root/"references"/"poses_11-20A_spin0"/"pose_manifest.json").read_text())
    if [x["span_A"] for x in poses]!=list(range(11,21)) or sum(x["rf_designs"] for x in poses)!=30: errors.append("pose grid is not 10 spans x 3 designs")
    for x in poses:
        rs=pdb_residues(root/"references"/"poses_11-20A_spin0"/x["path"])
        if [r for r,_ in rs]!=list(range(1,429)): errors.append(f"invalid RF input pose {x['path']}")
        coords={}
        for l in (root/"references"/"poses_11-20A_spin0"/x["path"]).read_text().splitlines():
            if l.startswith("ATOM  ") and l[12:16].strip()=="CA" and int(l[22:26]) in (393,394): coords[int(l[22:26])]=np.array([float(l[30:38]),float(l[38:46]),float(l[46:54])])
        if set(coords)!={393,394} or abs(float(np.linalg.norm(coords[393]-coords[394]))-x["span_A"])>0.002: errors.append(f"pose anchor distance mismatch: {x['path']}")
    run=(root/"src"/"run_pipeline.sh").read_text()
    for token in ["inference.num_designs=3","inference.design_startnum=0","inference.deterministic=True","rf_seed","--num_seq_per_target 10","394 395 396 397 398 399 400 401 402 403","--rf-pdb-path","write-baseline","evaluate-boltz","'--diffusion_samples','3'","'--sampling_steps','200'","'--recycling_steps','3'"]:
        if token not in run: errors.append(f"run script missing: {token}")
    dock=(root/"src"/"docking_helper.py").read_text()
    for token in ['validate_full_receptor','vina_gate','VINA_SCORE_CUTOFF=-6.0','"--exhaustiveness","32"','margin_A_per_side']:
        if token not in dock: errors.append(f"docking implementation missing: {token}")
    result={"status":"ok" if not errors else "failed","errors":errors,"authoritative_fusion_length":439,"linker_range":"A394-A403","sd40_range":"A404-A439","sd40_sequence_length":36,"sd40_experimental_coordinate_length":35,"poses":10,"rf_backbones_planned":30,"mpnn_sequences_per_backbone":10,"mpnn_max_sequences":300,"large_computations_started":False}
    if errors: raise ValueError(json.dumps(result,ensure_ascii=False))
    return result

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    c=sub.add_parser("check-only"); c.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    q=sub.add_parser("qc"); q.add_argument("linker")
    p=sub.add_parser("postprocess-rf"); p.add_argument("input",type=Path); p.add_argument("output",type=Path)
    y=sub.add_parser("make-yaml"); y.add_argument("sequence"); y.add_argument("output",type=Path); y.add_argument("candidate_id"); y.add_argument("--msa-mode",choices=("local","online"),default="local"); y.add_argument("--query-fasta",type=Path)
    f=sub.add_parser("collect-mpnn"); f.add_argument("fasta",type=Path); f.add_argument("rf_backbone_id"); f.add_argument("output",type=Path); f.add_argument("--limit",type=int,default=10); f.add_argument("--rf-pdb-path",type=Path,required=True); f.add_argument("--target-span",type=int,required=True); f.add_argument("--rf-design-index",type=int,required=True); f.add_argument("--rf-seed",type=int,required=True)
    b=sub.add_parser("write-baseline"); b.add_argument("output",type=Path)
    e=sub.add_parser("evaluate-boltz"); e.add_argument("candidate_jsonl",type=Path); e.add_argument("candidate_id"); e.add_argument("boltz_output",type=Path); e.add_argument("evaluation",type=Path)
    r=sub.add_parser("rmsd"); r.add_argument("reference",type=Path); r.add_argument("prediction",type=Path)
    a=ap.parse_args()
    if a.cmd=="check-only": result=check_only(a.root)
    elif a.cmd=="qc": result=sequence_qc(a.linker)
    elif a.cmd=="postprocess-rf": result=postprocess_rf(a.input,a.output)
    elif a.cmd=="make-yaml": make_boltz_yaml(a.sequence,a.output,a.candidate_id,a.msa_mode,a.query_fasta); result={"status":"ok","output":str(a.output),"msa_mode":a.msa_mode}
    elif a.cmd=="collect-mpnn": result={"status":"ok","candidates":len(collect_mpnn_fasta(a.fasta,a.rf_backbone_id,a.output,a.limit,a.rf_pdb_path,a.target_span,a.rf_design_index,a.rf_seed)),"output":str(a.output)}
    elif a.cmd=="write-baseline": a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(baseline_row(),ensure_ascii=False)+"\n",encoding="utf-8",newline="\n"); result={"status":"ok","candidate_id":"baseline_GGGGSGGGGS","rf_rmsd_status":"not_applicable"}
    elif a.cmd=="evaluate-boltz": result=evaluate_boltz_candidate(load_candidate(a.candidate_jsonl,a.candidate_id),a.boltz_output,a.evaluation)
    else: result={"linker_ca_kabsch_rmsd_A":linker_rmsd(a.reference,a.prediction),"strict_pass":linker_rmsd(a.reference,a.prediction)<2.0}
    print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
