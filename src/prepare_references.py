#!/usr/bin/env python3
"""Prepare authoritative V2 reference structures from RCSB and SnapGene inputs."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

AA3={"ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E","GLY":"G","HIS":"H","ILE":"I","LEU":"L","LYS":"K","MET":"M","PHE":"F","PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V"}
ADAR_SEQUENCE="LHLPQVLADAVSRLVLGKFGDLTDNFSSPHARRKVLAGVVMTTGTDVKDAKVISVSTGTKCINGEYMSDRGLALNDCHAEIISRRSLLRFLYTQLELYLNNKDDQKRSIFQKSERGGFRLKENVQFHLYISTSPCGDARIFSPHEPILEEPADRHPNRKARGQLRTKIESGQGTIPVRSNASIQTWDGVLQGERLLTMSCSDKIARWNVVGIQGSLLSIFVEPIYFSSIILGSLYHGDHLSRAMYQRISNIEDLPPLYTLNKPLLSGISNAEARQPGKAPNFSVNWTVGDSAIEVINATTGKDELGRASRLCKHALYCRWMRVHGKVPSHLLRSKITKPNVYHESKLAAKEYQAAKARLFTAFIKAGLGAWVEKPTEQDQFSLT"
NES_SEQUENCE="LPPLERLTL"
SD40_SEQUENCE="LLLFCPICGFTCRQKGNLLRHINLHTGEKLFKYHLY"

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest()

def residues(path,chain,low,high):
    groups=[]; key=None
    for line in Path(path).read_text(errors="replace").splitlines():
        if not line.startswith("ATOM  ") or line[21]!=chain: continue
        rid=int(line[22:26])
        if not low<=rid<=high or line[16] not in " A": continue
        k=(rid,line[26],line[17:20])
        if k!=key: groups.append([k,[]]); key=k
        groups[-1][1].append(line)
    return groups

def sequence(groups): return "".join(AA3.get(k[2],"X") for k,_ in groups)

def write_renumbered(groups,out,start=1):
    serial=1; lines=[]
    for new,(_,atoms) in enumerate(groups,start):
        for line in atoms:
            lines.append(f"{line[:6]}{serial:5d}{line[11:21]}A{new:4d} {line[27:]}"[:80]); serial+=1
    Path(out).write_text("\n".join(lines)+"\nTER\nEND\n",newline="\n")

def snapgene_sequences(path):
    try: from Bio import SeqIO
    except ImportError as e: raise RuntimeError("Biopython is required to read the authoritative SnapGene .dna file") from e
    rec=SeqIO.read(str(path),"snapgene")
    return {"ADAR2DD_E488Q":str(rec.seq[5548:6700].translate()),"NES":str(rec.seq[6718:6745].translate()),"SD40":str(rec.seq[6775:6883].translate())}

def extract_miq(pdb,out):
    lines=Path(pdb).read_text(errors="replace").splitlines(); chosen=[l for l in lines if l.startswith("HETATM") and l[17:20]=="MIQ"]
    if not chosen: raise ValueError("8TNQ contains no MIQ coordinates")
    serials={int(l[6:11]) for l in chosen}; conect=[]
    for l in lines:
        if l.startswith("CONECT"):
            nums=[int(x) for x in l[6:].split()]
            if nums and nums[0] in serials: conect.append(l)
    Path(out).write_text("\n".join(chosen+conect)+"\nEND\n",newline="\n")

def validate_miq_chemistry(raw,experimental_pdb):
    from Bio.PDB.MMCIF2Dict import MMCIF2Dict
    c=MMCIF2Dict(str(Path(raw)/"MIQ.cif")); atom_ids=list(c["_chem_comp_atom.atom_id"]); elements=list(c["_chem_comp_atom.type_symbol"]); stereo=list(c["_chem_comp_atom.pdbx_stereo_config"])
    heavy={a for a,e in zip(atom_ids,elements) if e.upper()!="H"}; exp={l[12:16].strip() for l in Path(experimental_pdb).read_text().splitlines() if l.startswith("HETATM") and l[76:78].strip().upper()!="H"}
    if exp!=heavy: raise ValueError(f"8TNQ MIQ heavy-atom names do not match CCD: missing={heavy-exp}, extra={exp-heavy}")
    bonds=list(zip(c["_chem_comp_bond.atom_id_1"],c["_chem_comp_bond.atom_id_2"],c["_chem_comp_bond.value_order"]))
    if not bonds or not any(x in {"R","S"} for x in stereo): raise ValueError("MIQ CCD lacks bond-order or stereochemistry definition")
    return {"ccd_atoms_total":len(atom_ids),"ccd_heavy_atoms":len(heavy),"experimental_heavy_atoms":len(exp),"ccd_bonds":len(bonds),"stereocenters":[{"atom_id":a,"configuration":s} for a,s in zip(atom_ids,stereo) if s in {"R","S"}],"bond_orders":sorted(set(x[2] for x in bonds))}

def prepare(root):
    root=Path(root); raw=root/"references"/"raw"; out=root/"references"/"prepared"; out.mkdir(parents=True,exist_ok=True)
    dna=next((root/"original_inputs").glob("*.dna")); auth=snapgene_sequences(dna)
    expected={"ADAR2DD_E488Q":ADAR_SEQUENCE,"NES":NES_SEQUENCE,"SD40":SD40_SEQUENCE}
    if auth!=expected: raise ValueError(f"SnapGene sequence mismatch: {auth}")
    adar=residues(raw/"5ED1.pdb","A",317,700)
    if len(adar)!=384 or sequence(adar)!=ADAR_SEQUENCE: raise ValueError("5ED1 A317-700 is not the authoritative 384-aa E488Q sequence")
    sd=residues(raw/"8TNQ.pdb","C",16,50)
    if len(sd)!=35 or sequence(sd)!=SD40_SEQUENCE[1:]: raise ValueError("8TNQ C16-50 is not SD40 positions 2-36")
    write_renumbered(adar,out/"5ED1_ADAR2DD_E488Q_A1-384.pdb",1); write_renumbered(sd,out/"8TNQ_SD40_positions_2-36.pdb",2)
    extract_miq(raw/"8TNQ.pdb",out/"8TNQ_MIQ_experimental.pdb"); miq=validate_miq_chemistry(raw,out/"8TNQ_MIQ_experimental.pdb")
    meta={"sequence_authority":dna.name,"ADAR2DD_E488Q":{"length":384,"sequence":ADAR_SEQUENCE,"source":"5ED1 chain A residues 317-700"},"NES":{"length":9,"sequence":NES_SEQUENCE},"SD40":{"sequence_length":36,"experimental_coordinate_length":35,"unresolved_position":1,"sequence":SD40_SEQUENCE,"resolved_sequence":SD40_SEQUENCE[1:],"source":"8TNQ chain C residues 16-50"},"MIQ":{"experimental_source":"8TNQ","chemical_definition":"RCSB CCD MIQ.cif","validation":miq},"raw_sha256":{p.name:sha256(p) for p in sorted(raw.iterdir()) if p.is_file()}}
    (out/"reference_metadata.json").write_text(json.dumps(meta,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
    return meta

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]); a=ap.parse_args(); prepare(a.root)
    print(json.dumps({"status":"ok","adar_length":384,"sd40_sequence_length":36,"sd40_coordinate_length":35},ensure_ascii=False))
if __name__=="__main__": main()
