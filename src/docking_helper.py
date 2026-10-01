#!/usr/bin/env python3
"""Validate full receptors, build per-model boxes, run Vina, and apply its 2/3 gate."""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys
from pathlib import Path

AA3={"ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E","GLY":"G","HIS":"H","ILE":"I","LEU":"L","LYS":"K","MET":"M","PHE":"F","PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V"}
ADAR_SEQUENCE="LHLPQVLADAVSRLVLGKFGDLTDNFSSPHARRKVLAGVVMTTGTDVKDAKVISVSTGTKCINGEYMSDRGLALNDCHAEIISRRSLLRFLYTQLELYLNNKDDQKRSIFQKSERGGFRLKENVQFHLYISTSPCGDARIFSPHEPILEEPADRHPNRKARGQLRTKIESGQGTIPVRSNASIQTWDGVLQGERLLTMSCSDKIARWNVVGIQGSLLSIFVEPIYFSSIILGSLYHGDHLSRAMYQRISNIEDLPPLYTLNKPLLSGISNAEARQPGKAPNFSVNWTVGDSAIEVINATTGKDELGRASRLCKHALYCRWMRVHGKVPSHLLRSKITKPNVYHESKLAAKEYQAAKARLFTAFIKAGLGAWVEKPTEQDQFSLT"
NES_SEQUENCE="LPPLERLTL"; SD40_SEQUENCE="LLLFCPICGFTCRQKGNLLRHINLHTGEKLFKYHLY"
SD40_START,SD40_END=404,439

def stable_seed(candidate_id,model_index): return int.from_bytes(hashlib.sha256(f"{candidate_id}:{model_index}".encode()).digest()[:4],"big")%2147483646+1

def pdb_sequence(path):
    rows=[]; seen=set()
    for l in Path(path).read_text(errors="replace").splitlines():
        if l.startswith("ATOM  ") and l[21]=="A" and l[16] in " A":
            rid=int(l[22:26]); key=(rid,l[26])
            if key not in seen: rows.append((rid,AA3.get(l[17:20],"X"))); seen.add(key)
    return rows

def validate_full_receptor(path):
    rows=pdb_sequence(path); ids=[x[0] for x in rows]; seq="".join(x[1] for x in rows)
    if ids!=list(range(1,440)): raise ValueError(f"Vina receptor must be the complete chain A1-A439; found {len(ids)} residues")
    if seq[:393]!=ADAR_SEQUENCE+NES_SEQUENCE or seq[403:]!=SD40_SEQUENCE: raise ValueError("Vina receptor fixed sequence/numbering is not the authoritative 439-aa fusion")
    return {"residue_count":439,"linker_range":"A394-A403","sd40_range":"A404-A439"}

def sd40_box(pdb,margin=5.0):
    validate_full_receptor(pdb); xyz=[]; residues=set()
    for l in Path(pdb).read_text(errors="replace").splitlines():
        if l.startswith(("ATOM  ","HETATM")) and l[21]=="A" and SD40_START<=int(l[22:26])<=SD40_END and (l[76:78].strip() or l[12:16].strip()[0]).upper()!="H":
            residues.add(int(l[22:26])); xyz.append(tuple(float(l[s:e]) for s,e in ((30,38),(38,46),(46,54))))
    if residues!=set(range(404,440)): raise ValueError(f"docking box must cover all 36 SD40 residues A404-A439; found {len(residues)}")
    mins=[min(v[i] for v in xyz) for i in range(3)]; maxs=[max(v[i] for v in xyz) for i in range(3)]
    return {"center":[(mins[i]+maxs[i])/2 for i in range(3)],"size":[maxs[i]-mins[i]+2*margin for i in range(3)],"margin_A_per_side":margin,"residue_count":36,"heavy_atom_count":len(xyz)}

def vina_command(receptor,ligand,out,candidate_id,model_index,vina=None,log=None,box=None):
    vina = vina or os.environ.get("VINA_EXE", "vina")
    b=box if box is not None else sd40_box(receptor); c=b["center"]; s=b["size"]
    cmd=[vina,"--receptor",str(receptor),"--ligand",str(ligand),"--out",str(out),"--center_x",f"{c[0]:.3f}","--center_y",f"{c[1]:.3f}","--center_z",f"{c[2]:.3f}","--size_x",f"{s[0]:.3f}","--size_y",f"{s[1]:.3f}","--size_z",f"{s[2]:.3f}","--exhaustiveness","32","--num_modes","9","--energy_range","3","--seed",str(stable_seed(candidate_id,model_index))]
    if log is not None: cmd.extend(["--log",str(log)])
    return cmd

def best_score(text):
    vals=[float(m.group(1)) for m in re.finditer(r"^\s*\d+\s+(-?\d+(?:\.\d+)?)\s+",text,re.M)]
    if not vals: raise ValueError("no Vina mode scores found")
    return min(vals)

VINA_SCORE_CUTOFF=-6.0

def vina_gate(scores):
    if len(scores)!=3: raise ValueError(f"expected exactly 3 Vina scores, found {len(scores)}")
    passed=[x<=VINA_SCORE_CUTOFF for x in scores]
    return {"model_pass":passed,"pass_count":sum(passed),"required":2,"candidate_pass":sum(passed)>=2,"operator":"<=","threshold_kcal_mol":VINA_SCORE_CUTOFF}

def native_path(value):
    s=str(value)
    m=re.match(r"^/mnt/([a-zA-Z])/(.*)$",s)
    return Path(f"{m.group(1).upper()}:\\{m.group(2).replace('/',os.sep)}") if m else Path(s)

def prepare_pdbqt(pdb,pdbqt,kind,python2=None,utilities=None):
    python2 = python2 or os.environ.get("ADT_PYTHON", "pythonsh")
    utilities = utilities or os.environ.get("ADT_UTILITIES")
    if not utilities:
        raise RuntimeError("Set ADT_UTILITIES to the AutoDockTools Utilities24 directory")
    script=Path(utilities)/("prepare_receptor4.py" if kind=="receptor" else "prepare_ligand4.py"); flag="-r" if kind=="receptor" else "-l"
    # AutoDockTools 1.5.x applies os.path.basename() to its input argument;
    # run it from the input directory so the basename remains resolvable.
    subprocess.run([python2,str(script),flag,str(pdb),"-o",str(pdbqt)],check=True,capture_output=True,text=True,cwd=str(Path(pdb).parent))

def run_batch(evaluations_dir,ligand_pdb,output_root,vina=None):
    vina = vina or os.environ.get("VINA_EXE", "vina")
    if os.name!="nt": raise RuntimeError("Vina/MGLTools stage must run with Windows Python, not inside WSL")
    evaluations_dir=Path(evaluations_dir); output_root=Path(output_root); output_root.mkdir(parents=True,exist_ok=True)
    ligand_pdb=native_path(ligand_pdb); ligand_pdbqt=output_root/"MIQ_8TNQ.pdbqt"
    if not ligand_pdbqt.exists(): prepare_pdbqt(ligand_pdb,ligand_pdbqt,"ligand")
    results=[]
    for ep in sorted(evaluations_dir.glob("*.json")):
        ev=json.loads(ep.read_text(encoding="utf-8"))
        if not ev.get("downstream_eligible"): continue
        cid=ev["candidate_id"]; cdir=output_root/cid; cdir.mkdir(parents=True,exist_ok=True); models=[]; scores=[]
        for model in ev["models"]:
            idx=int(model["model_index"]); receptor=native_path(model["prediction_pdb"]); validate_full_receptor(receptor); box=sd40_box(receptor)
            receptor_qt=cdir/f"model_{idx}_receptor.pdbqt"; out=cdir/f"model_{idx}_vina.pdbqt"; log=cdir/f"model_{idx}_vina.log"
            if not receptor_qt.exists(): prepare_pdbqt(receptor,receptor_qt,"receptor")
            cmd=vina_command(receptor_qt,ligand_pdbqt,out,cid,idx,vina,log,box) # box was computed from this model's full PDB.
            # A completed log plus non-empty pose file is the resumable unit.  Parse and
            # reuse it instead of silently spending another Vina run after interruption.
            if log.is_file() and log.stat().st_size and out.is_file() and out.stat().st_size:
                score=best_score(log.read_text(errors="replace"))
            else:
                subprocess.run(cmd,check=True,capture_output=True,text=True)
                score=best_score(log.read_text(errors="replace"))
            scores.append(score)
            models.append({**model,"receptor_pdb":str(receptor),"docking_box":box,"vina_seed":stable_seed(cid,idx),"vina_best_score_kcal_mol":score,"vina_model_pass":score<=VINA_SCORE_CUTOFF,"vina_output":str(out),"vina_log":str(log)})
        gate=vina_gate(scores); result={"candidate_id":cid,"candidate_type":ev["candidate_type"],"rf_rmsd_status":ev["rf_rmsd_status"],"vina_gate":gate,"models":models}
        (cdir/"docking_result.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); (output_root/f"{cid}.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); results.append(result)
    return results

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    c=sub.add_parser("command"); c.add_argument("receptor",type=Path); c.add_argument("ligand",type=Path); c.add_argument("out",type=Path); c.add_argument("candidate_id"); c.add_argument("model_index",type=int)
    b=sub.add_parser("run-batch"); b.add_argument("--evaluations-dir",type=Path,required=True); b.add_argument("--ligand-pdb",type=Path,required=True); b.add_argument("--output-root",type=Path,required=True); b.add_argument("--vina",default=os.environ.get("VINA_EXE", "vina"))
    a=ap.parse_args()
    if a.cmd=="command": print(json.dumps({"receptor":validate_full_receptor(a.receptor),"box":sd40_box(a.receptor),"seed":stable_seed(a.candidate_id,a.model_index),"command":vina_command(a.receptor,a.ligand,a.out,a.candidate_id,a.model_index)},indent=2))
    else: print(json.dumps({"status":"ok","candidates":len(run_batch(a.evaluations_dir,a.ligand_pdb,a.output_root,a.vina))},indent=2))
if __name__=="__main__": main()
