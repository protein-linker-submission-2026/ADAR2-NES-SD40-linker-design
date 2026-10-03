#!/usr/bin/env python3
"""Create per-span machine-readable QC, audit rows, summaries and README files."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
from pathlib import Path

from pipeline_helper import baseline_row, sequence_qc


def native_path(value: str | Path) -> Path:
    s = str(value)
    if os.name == "nt" and s.startswith("/mnt/") and len(s) > 6:
        drive, rest = s[5], s[7:]
        windows_rest = rest.replace("/", "\\")
        return Path(f"{drive.upper()}:\\{windows_rest}")
    return Path(s)


def read_jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8", newline="\n")


def fasta_records(path: Path):
    records=[]; name=None; parts=[]
    for raw in path.read_text(encoding="utf-8").splitlines()+[">"]:
        if raw.startswith(">"):
            if name is not None: records.append((name,"".join(parts)))
            name=raw[1:].strip(); parts=[]
        else: parts.append(raw.strip())
    return records


def prepare_qc(root: Path, span: int, rf_count: int = 3):
    qcdir=root/"07_sequence_qc"; qcdir.mkdir(parents=True,exist_ok=True)
    rows=[]
    for idx in range(rf_count):
        p=root/"06_proteinmpnn"/f"span{span}A_design_{idx}"/"candidates.jsonl"
        part=read_jsonl(p)
        rows.extend(part)
        write_jsonl(qcdir/f"span{span}A_design_{idx}_candidates.jsonl",part)
    write_jsonl(qcdir/"all_candidates.jsonl",rows)
    write_jsonl(qcdir/"baseline_candidate.jsonl",[baseline_row()])
    fields=["candidate_id","rf_backbone_id","target_span_A","rf_design_index","rf_seed","sample_index","linker_sequence","qc_pass","reasons","kr_fraction","hydrophobic_fraction","net_charge"]
    with (qcdir/"sequence_qc.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for x in rows:
            q=x["qc"]
            w.writerow({"candidate_id":x["candidate_id"],"rf_backbone_id":x["rf_backbone_id"],"target_span_A":x["target_span_A"],"rf_design_index":x["rf_design_index"],"rf_seed":x["rf_seed"],"sample_index":x["sample_index"],"linker_sequence":x["linker_sequence"],"qc_pass":q["pass"],"reasons":";".join(q["reasons"]),"kr_fraction":q["kr_fraction"],"hydrophobic_fraction":q["hydrophobic_fraction"],"net_charge":q["net_charge"]})
    return {"requested":sum(max(0,len(fasta_records(root/"06_proteinmpnn"/f"span{span}A_design_{i}"/"output"/"seqs"/f"span{span}A_design_{i}.fa"))-1) for i in range(rf_count)),"unique":len(rows),"qc_pass":sum(x["qc"]["pass"] for x in rows)}


def prepare_boltz_list(root: Path, design_limit: int | None = None):
    rows=[x for x in read_jsonl(root/"07_sequence_qc"/"all_candidates.jsonl") if x["qc"]["pass"]]
    if design_limit is not None:
        if design_limit < 1 or not rows:
            raise ValueError('Smoke test requires at least one QC-passing design; do not count baseline alone as a full design test')
        rows=rows[:design_limit]
    rows+=read_jsonl(root/"07_sequence_qc"/"baseline_candidate.jsonl")
    write_jsonl(root/"08_boltz2_local"/"candidates_to_predict.jsonl",rows)
    return {"candidates":len(rows),"design":sum(x.get("candidate_type")=="design" for x in rows),"baseline":sum(x.get("candidate_type")=="baseline" for x in rows)}


def prepare_ranker(root: Path, docking_dir: Path | None = None, ranker_dir: Path | None = None):
    docking=docking_dir or (root/"10_docking"); ranker_dir=ranker_dir or (root/"11_ranker"); target=ranker_dir/"candidates"
    new=target.with_name("candidates.new")
    if new.exists(): shutil.rmtree(new)
    new.mkdir(parents=True)
    included=[]
    for p in sorted(docking.glob("*.json")):
        r=json.loads(p.read_text(encoding="utf-8"))
        if not r.get("vina_gate",{}).get("candidate_pass") and r.get("candidate_type")!="baseline": continue
        for m in r.get("models",[]):
            src=native_path(m["prediction_pdb"])
            if not src.exists():
                # WSL path in a report executed from Windows is not expected here,
                # but preserve an explicit error instead of dropping a model.
                raise FileNotFoundError(src)
            dst=new/f"{r['candidate_id']}_model{m['model_index']}.pdb"
            shutil.copy2(src,dst); included.append(dst.name)
    old=target.with_name("candidates.previous")
    if old.exists(): shutil.rmtree(old)
    if target.exists(): target.rename(old)
    new.rename(target)
    return {"models":len(included),"files":included}


def _load_map(directory: Path):
    out={}
    for p in directory.glob("*.json") if directory.exists() else []:
        try:
            r=json.loads(p.read_text(encoding="utf-8")); out[r["candidate_id"]]=r
        except (KeyError,json.JSONDecodeError):
            continue
    return out


def _ranking(root: Path):
    p=root/"ranking.csv"
    if not p.exists(): return {}
    with p.open(encoding="utf-8-sig",newline="") as f:
        return {r["candidate"]:r for r in csv.DictReader(f)}


def finalize(root: Path, span: int, docking_dir: Path | None = None, ranker_dir: Path | None = None, rf_count: int = 3):
    reports=root/"05_reports"; reports.mkdir(parents=True,exist_ok=True)
    smoke = rf_count == 1
    selected = {r["candidate_id"] for r in read_jsonl(root/"08_boltz2_local"/"candidates_to_predict.jsonl")}
    unique=read_jsonl(root/"07_sequence_qc"/"all_candidates.jsonl")
    by_slot={(int(x["rf_design_index"]),int(x["sample_index"])):x for x in unique}
    docking_dir=docking_dir or (root/"10_docking"); ranker_dir=ranker_dir or (root/"11_ranker")
    evals=_load_map(root/"09_rmsd_gate_local"); docks=_load_map(docking_dir); ranking=_ranking(ranker_dir)
    model_rows=[]; seen_linkers={}
    for idx in range(rf_count):
        fid=f"span{span}A_design_{idx}"; fa=root/"06_proteinmpnn"/fid/"output"/"seqs"/f"{fid}.fa"
        samples=fasta_records(fa)[1:11]
        for sample_idx in range(1,11):
            if sample_idx<=len(samples):
                seq=samples[sample_idx-1][1]; linker=seq[393:403]
            else:
                seq=""; linker=""
            candidate=by_slot.get((idx,sample_idx)); duplicate_of=""
            if not candidate and linker:
                key=(idx,linker)
                duplicate_of=seen_linkers.get(key,"")
            if linker: seen_linkers.setdefault((idx,linker),f"{fid} 第{sample_idx}条")
            cid=candidate["candidate_id"] if candidate else ""
            ev=evals.get(cid,{}); dock=docks.get(cid,{}); ev_models={int(m["model_index"]):m for m in ev.get("models",[])}; dock_models={int(m["model_index"]):m for m in dock.get("models",[])}
            for mi in range(3):
                em=ev_models.get(mi,{}); dm=dock_models.get(mi,{}); rr=ranking.get(f"{cid}_model{mi}",{}) if cid else {}
                if not seq: dedup="未进入"; qc_status="未进入"; reason="ProteinMPNN未生成该序号"
                elif not candidate: dedup="未通过"; qc_status="未进入"; reason=f"同一RF骨架内linker重复；首次出现：{duplicate_of}"
                else:
                    dedup="通过"; qc_status="通过" if candidate["qc"]["pass"] else "未通过"; reason="；".join(candidate["qc"]["reasons"]) or "无"
                rmsd_gate=ev.get("rf_rmsd_gate",{}); vina_gate=dock.get("vina_gate",{})
                pending = "未抽取（小样本测试）" if smoke and cid and cid not in selected else "未完成"
                final="正式进入Ranker" if rr else ("仅作对照" if candidate and candidate.get("candidate_type")=="baseline" else "未进入Ranker")
                model_rows.append({
                    "距离_A":span,"RF骨架":fid,"MPNN序号":sample_idx,"Linker序列":linker,"ProteinMPNN":"通过" if seq else "未生成","判重":dedup,"Sequence_QC":qc_status,"QC或判重原因":reason,"Boltz模型":mi+1,
                    "在线MSA":"通过" if em else ("未进入" if qc_status!="通过" else pending),"Boltz预测":"通过" if em else ("未进入" if qc_status!="通过" else pending),"Linker_RMSD_A":em.get("linker_ca_rmsd_A"),"RMSD单模型":"通过" if em.get("rf_rmsd_pass") is True else ("未通过" if em.get("rf_rmsd_pass") is False else "未进入"),"RMSD序列门槛":"通过" if rmsd_gate.get("candidate_pass") else ("未通过" if ev else "未进入"),
                    "Vina最佳分_kcal_mol":dm.get("vina_best_score_kcal_mol"),"Vina单模型":"通过" if dm.get("vina_model_pass") is True else ("未通过" if dm.get("vina_model_pass") is False else "未进入"),"Vina序列门槛":"通过" if vina_gate.get("candidate_pass") else ("未通过" if dock else "未进入"),"S_RMSD":float(rr["rmsd_score"]) if rr else None,"S_contact":float(rr["contact_score"]) if rr else None,"S_clash":float(rr["clash_score"]) if rr else None,"方案B总分":float(rr["total_score"]) if rr else None,"最终状态":final,"候选ID":cid,
                })
    baseline=evals.get("baseline_GGGGSGGGGS",{}); baseline_dock=docks.get("baseline_GGGGSGGGGS",{}); seq_groups=[]
    ids=["baseline_GGGGSGGGGS"]+[x["candidate_id"] for x in unique]
    linkers={"baseline_GGGGSGGGGS":"GGGGSGGGGS",**{x["candidate_id"]:x["linker_sequence"] for x in unique}}
    for cid in ids:
        vals=[]
        for mi in range(3):
            rr=ranking.get(f"{cid}_model{mi}"); vals.append(float(rr["total_score"]) if rr else None)
        numeric=[x for x in vals if x is not None]
        med=sorted(numeric)[len(numeric)//2] if len(numeric)==3 else None
        d=docks.get(cid,baseline_dock if cid.startswith("baseline") else {})
        e=evals.get(cid,baseline if cid.startswith("baseline") else {})
        status="仅作对照" if cid.startswith("baseline") else ("正式候选" if d.get("vina_gate",{}).get("candidate_pass") else "未进入最终排名")
        seq_groups.append({"类别":"基准对照" if cid.startswith("baseline") else "设计序列","Linker序列":linkers[cid],"候选ID":cid,"模型1总分":vals[0],"模型2总分":vals[1],"模型3总分":vals[2],"方案B中位数":med,"最终状态":status,"RMSD通过模型数":e.get("rf_rmsd_gate",{}).get("pass_count"),"Vina通过模型数":d.get("vina_gate",{}).get("pass_count")})
    summary={"span_A":span,"rf_backbones":len(list((root/"03_rfdiffusion_validated").glob("*.pdb"))),"mpnn_requested":sum(1 for r in model_rows if r["Boltz模型"]==1 and r["ProteinMPNN"]=="通过"),"mpnn_unique":len(unique),"qc_pass_design":sum(x["qc"]["pass"] for x in unique),"boltz_candidates":len(evals),"boltz_models":sum(len(x.get("models",[])) for x in evals.values()),"rmsd_pass_design":sum(x.get("candidate_type")=="design" and x.get("rf_rmsd_gate",{}).get("candidate_pass") for x in evals.values()),"vina_candidates":len(docks),"vina_models":sum(len(x.get("models",[])) for x in docks.values()),"vina_pass_design":sum(x.get("candidate_type")=="design" and x.get("vina_gate",{}).get("candidate_pass") for x in docks.values()),"ranker_models":len(ranking),"network_used_for_MSA":True,"msa_server":"https://api.colabfold.com","boltz_inference":"local GPU","scoring_weights":{"S_RMSD":0.3,"S_contact":0.3,"S_clash":0.4}}
    summary["run_mode"] = "smoke_test" if smoke else "full"
    summary["network_used_for_MSA"] = bool(evals)
    (reports/f"span{span}A_summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (reports/"model_rows.json").write_text(json.dumps(model_rows,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (reports/"sequence_rows.json").write_text(json.dumps(seq_groups,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    with (reports/"model_rows.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(model_rows[0])); w.writeheader(); w.writerows(model_rows)
    readme=f"""# ADAR2–SD40 {span} Å结果说明\n\n本目录保存{span} Å、spin=0°条件的完整V2计算结果。RFdiffusion、ProteinMPNN、Boltz-2推理、RMSD、Vina和Ranker均在本机执行；仅MSA查询访问 `https://api.colabfold.com`。\n\n## 实际数量\n\n- RFdiffusion骨架：{summary['rf_backbones']}\n- ProteinMPNN请求：{summary['mpnn_requested']}\n- 去重后设计序列：{summary['mpnn_unique']}\n- Sequence QC通过：{summary['qc_pass_design']}\n- Boltz-2候选/模型：{summary['boltz_candidates']} / {summary['boltz_models']}\n- RMSD通过设计序列：{summary['rmsd_pass_design']}\n- Vina候选/模型：{summary['vina_candidates']} / {summary['vina_models']}\n- Vina通过设计序列：{summary['vina_pass_design']}\n- Ranker模型：{summary['ranker_models']}\n\n## 目录\n\n`01_input`输入与参数；`02_rfdiffusion_raw`原始RF输出；`03_rfdiffusion_validated`校验后439-aa骨架；`04_logs`日志；`05_reports`中文表及CSV/JSON；`06_proteinmpnn`序列设计；`07_sequence_qc`QC；`08_msa_online`在线MSA记录；`08_boltz2_local`本地Boltz-2结果；`09_rmsd_gate_local`RMSD；`10_docking`Vina；`11_ranker`方案B评分。\n\n## 方法限制\n\n16 Å旧批次使用本地单序列A3M；本批次使用在线MSA，因此跨距离差异不能全部解释为span效应。`GGGGSGGGGS`是人工baseline，不属于30条ProteinMPNN请求，也不伪造RF RMSD。\n"""
    readme = readme.replace("## 方法限制\\n\\n16 Å旧批次使用本地单序列A3M；", "## 方法限制\\n\\nVina门控：每个候选的3个模型中至少2个best score ≤−6.0 kcal/mol，才进入后续Ranker。16 Å旧批次使用本地单序列A3M且原始Vina记录仍按−7.0门槛解释；")
    readme = readme.replace("完整V2计算结果", "计算阶段输出（实际完成数量见下表）")
    readme = readme.replace("RFdiffusion、ProteinMPNN、Boltz-2推理、RMSD、Vina和Ranker均在本机执行；仅MSA查询访问", "流程配置为本地运行RFdiffusion、ProteinMPNN、Boltz-2、RMSD、Vina和Ranker；MSA配置的服务地址为")
    if smoke:
        readme = "> 小样本测试：1个RF骨架、10条MPNN请求，最多1条QC通过设计加baseline进入Boltz；不是正式完整批次。\n\n" + readme
        readme = readme.replace("30条ProteinMPNN请求", "10条ProteinMPNN请求")
    (root/"README.md").write_text(readme,encoding="utf-8",newline="\n")
    return summary


def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="command",required=True)
    q=sub.add_parser("prepare-qc"); q.add_argument("--root",type=Path,required=True); q.add_argument("--span",type=int,required=True)
    q.add_argument("--rf-count",type=int,choices=(1,3),default=3)
    b=sub.add_parser("prepare-boltz-list"); b.add_argument("--root",type=Path,required=True)
    b.add_argument("--design-limit",type=int)
    r=sub.add_parser("prepare-ranker"); r.add_argument("--root",type=Path,required=True); r.add_argument("--docking-dir",type=Path); r.add_argument("--ranker-dir",type=Path)
    f=sub.add_parser("finalize"); f.add_argument("--root",type=Path,required=True); f.add_argument("--span",type=int,required=True); f.add_argument("--docking-dir",type=Path); f.add_argument("--ranker-dir",type=Path)
    f.add_argument("--rf-count",type=int,choices=(1,3),default=3)
    a=ap.parse_args()
    if a.command=="prepare-qc": result=prepare_qc(a.root,a.span,a.rf_count)
    elif a.command=="prepare-boltz-list": result=prepare_boltz_list(a.root,a.design_limit)
    elif a.command=="prepare-ranker": result=prepare_ranker(a.root, a.docking_dir, a.ranker_dir)
    else: result=finalize(a.root,a.span, a.docking_dir, a.ranker_dir,a.rf_count)
    print(json.dumps({"status":"ok",**result},ensure_ascii=False,indent=2))


if __name__=="__main__": main()
