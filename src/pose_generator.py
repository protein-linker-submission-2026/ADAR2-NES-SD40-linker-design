#!/usr/bin/env python3
"""Generate the ten 11-20 A, spin=0 RFdiffusion input poses."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path

NES="LPPLERLTL"
AA3={"A":"ALA","C":"CYS","D":"ASP","E":"GLU","F":"PHE","G":"GLY","H":"HIS","I":"ILE","K":"LYS","L":"LEU","M":"MET","N":"ASN","P":"PRO","Q":"GLN","R":"ARG","S":"SER","T":"THR","V":"VAL","W":"TRP","Y":"TYR"}
def add(a,b): return tuple(x+y for x,y in zip(a,b))
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def mul(a,s): return tuple(x*s for x in a)
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a): return math.sqrt(dot(a,a))
def unit(a):
    n=norm(a)
    if n<1e-9: raise ValueError("zero-length direction vector")
    return mul(a,1/n)
def rot(v,axis,angle):
    axis=unit(axis); c=math.cos(angle); s=math.sin(angle)
    return add(add(mul(v,c),mul(cross(axis,v),s)),mul(axis,dot(axis,v)*(1-c)))

def read_atoms(path):
    a=[]
    for l in Path(path).read_text().splitlines():
        if l.startswith("ATOM  "):
            a.append({"name":l[12:16].strip(),"res":l[17:20],"id":int(l[22:26]),"xyz":(float(l[30:38]),float(l[38:46]),float(l[46:54])),"element":l[76:78].strip() or l[12:16].strip()[0]})
    return a
def atom(atoms,r,n): return next(x for x in atoms if x["id"]==r and x["name"]==n)
def center(atoms): return tuple(sum(x["xyz"][i] for x in atoms)/len(atoms) for i in range(3))

def make_nes(adar):
    ca=atom(adar,384,"CA")["xyz"]; c=atom(adar,384,"C")["xyz"]; n=atom(adar,384,"N")["xyz"]
    x=unit(sub(c,ca)); z=unit(cross(x,unit(sub(ca,n)))); y=unit(cross(z,x)); out=[]
    for i,aa in enumerate(NES,1):
        ctr=add(ca,mul(x,3.8*i)); th=math.radians(100*(i-1)); radial=add(mul(y,math.cos(th)),mul(z,math.sin(th))); q=add(ctr,mul(radial,1.6)); rid=384+i
        for name,xyz,el in [("N",sub(q,mul(x,1.3)),"N"),("CA",q,"C"),("C",add(q,mul(x,1.5)),"C"),("O",add(add(q,mul(x,1.5)),mul(radial,1.1)),"O")]: out.append({"name":name,"res":AA3[aa],"id":rid,"xyz":xyz,"element":el})
    return out

def move_sd40(sd,target,adar_center):
    origin=atom(sd,2,"CA")["xyz"]; old_axis=unit(sub(center(sd),origin)); new_axis=unit(sub(target,adar_center)); axis=cross(old_axis,new_axis)
    if norm(axis)<1e-8: axis=(0,0,1)
    angle=math.acos(max(-1,min(1,dot(old_axis,new_axis))))
    out=[]
    for a in sd:
        b=dict(a); b["xyz"]=add(target,rot(sub(a["xyz"],origin),axis,angle)); b["id"]=392+a["id"] # full pos2 -> RF input A394
        out.append(b)
    return out

def line(serial,a):
    x,y,z=a["xyz"]; return f"ATOM  {serial:5d} {a['name']:^4s} {a['res']:>3s} A{a['id']:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00          {a['element']:>2s}"

def generate(root):
    root=Path(root); prep=root/"references"/"prepared"; out=root/"references"/"poses_11-20A_spin0"; out.mkdir(parents=True,exist_ok=True)
    adar=read_atoms(prep/"5ED1_ADAR2DD_E488Q_A1-384.pdb"); sd=read_atoms(prep/"8TNQ_SD40_positions_2-36.pdb"); nes=make_nes(adar)
    if len({a['id'] for a in adar})!=384 or len({a['id'] for a in sd})!=35: raise ValueError("prepared reference residue count invalid")
    last=atom(nes,393,"CA")["xyz"]; outward=unit(sub(last,center(adar))); manifest=[]
    for span in range(11,21):
        moved=move_sd40(sd,add(last,mul(outward,float(span))),center(adar)); atoms=adar+nes+moved
        p=out/f"ADAR2_NES_SD40_pose_span_{span:02d}A_spin0.pdb"; p.write_text(f"REMARK V2 TARGET_SPAN {span}.0 A SPIN 0.0 DEG\n"+"\n".join(line(i,a) for i,a in enumerate(atoms,1))+"\nTER\nEND\n",newline="\n")
        measured=norm(sub(atom(moved,394,"CA")["xyz"],last)); manifest.append({"span_A":span,"spin_deg":0,"path":p.name,"measured_span_A":round(measured,4),"input_residues":428,"rf_designs":3})
    (out/"pose_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",newline="\n"); return manifest

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]); a=ap.parse_args(); m=generate(a.root); print(json.dumps({"status":"ok","poses":len(m),"rf_backbones":sum(x["rf_designs"] for x in m)}))
if __name__=="__main__": main()
