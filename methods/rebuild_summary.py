from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
import openpyxl


SOURCE_ROOT = Path(os.environ.get("ADAR2_SD40_SOURCE_ROOT", Path.cwd()))
PACKAGE_ROOT = SOURCE_ROOT / "ADAR2_SD40_中期提交材料_匿名版_解压" / "ADAR2_SD40_中期提交材料_匿名版"
ONLINE_ROOT = PACKAGE_ROOT / "02_原始记录" / "11-20A_在线MSA批次"
EARLY16_ROOT = PACKAGE_ROOT / "02_原始记录" / "16A_单序列MSA原始批次"
OUTPUT_ROOT = Path(os.environ.get("ADAR2_SD40_OUTPUT_ROOT", str(SOURCE_ROOT / "ADAR2_SD40_文献式整理_全量")))

BASELINE_SEQUENCE = "GGGGSGGGGS"
BASELINE_SCORE_ONLINE = 24.1035
RMSD_THRESHOLD = 2.0
VINA_THRESHOLD_ONLINE = -6.0

PAPERS = [
    "AI-redesigned starting points and outcomes enhance protein evolution",
    "Design, construction and characterization of a set",
    "PottsMPNN",
]


def safe_float(value):
    if value in (None, "", "NA", "N/A"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value):
    val = safe_float(value)
    return None if val is None else int(val)


def median(values):
    vals = [float(x) for x in values if x is not None and not pd.isna(x)]
    return statistics.median(vals) if vals else None


def long_path(path: Path | str):
    text = str(path)
    if os.name == "nt" and not text.startswith("\\\\?\\"):
        return "\\\\?\\" + os.path.abspath(text)
    return text


def read_json(path: Path):
    with open(long_path(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv_dicts(path: Path):
    with open(long_path(path), "r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def classify_source(relpath: str):
    p = relpath.replace("\\", "/")
    ext = Path(p).suffix.lower() or "[none]"
    if "/04_rfdiffusion/" in p or "/03_rf" in p or p.endswith(".trb"):
        stage = "RFdiffusion"
    elif "/06_mpnn/" in p or "proteinmpnn" in p.lower() or "/04_mpnn" in p:
        stage = "ProteinMPNN"
    elif "/08_boltz2" in p or "/06_boltz" in p or ext in {".a3m", ".npz"}:
        stage = "Boltz-2/MSA"
    elif "/09_rmsd" in p or "rmsd" in p.lower():
        stage = "RMSD门控"
    elif "/10_docking" in p or ext == ".pdbqt" or "vina" in p.lower():
        stage = "Vina对接"
    elif "/11_ranker" in p or "ranking" in p.lower():
        stage = "SD40 Ranker"
    elif "/07_sequence_qc" in p or "sequence_qc" in p.lower():
        stage = "序列QC"
    elif p.startswith("01_中期结果/") or "/05_reports/" in p:
        stage = "汇总结果"
    elif p.startswith("03_运行日志/") or ext == ".log":
        stage = "运行日志"
    elif p.endswith("README_提交说明.md") or "VALIDATION" in p or "匿名化" in p or "SHA256" in p or "文件清单" in p:
        stage = "完整性与复现"
    else:
        stage = "其他原始产物"

    if ext in {".json", ".csv", ".xlsx"}:
        usage = "直接解析或交叉核验"
    elif ext in {".pdb", ".pdbqt", ".a3m", ".npz", ".gz", ".trb", ".log", ".sh", ".yaml", ".jsonl"}:
        usage = "全量索引并保留阶段追溯"
    else:
        usage = "全量索引"
    return stage, ext, usage


def parse_ranker(path: Path):
    ranker = {}
    if not path.exists():
        return ranker
    for row in read_csv_dicts(path):
        name = row.get("candidate", "")
        match = re.match(r"(.+)_model(\d+)$", name)
        if not match:
            continue
        cid, idx = match.group(1), int(match.group(2))
        ranker[(cid, idx)] = {
            "ranker_rank": safe_int(row.get("rank")),
            "total_score": safe_float(row.get("total_score")),
            "sd40_rmsd_A": safe_float(row.get("sd40_rmsd")),
            "contact_recovery": safe_float(row.get("contact_recovery")),
            "recovered_contacts": safe_int(row.get("recovered_contacts")),
            "reference_contacts": safe_int(row.get("reference_contacts")),
            "clashing_atoms": safe_int(row.get("clashing_atoms")),
            "rmsd_score": safe_float(row.get("rmsd_score")),
            "contact_score": safe_float(row.get("contact_score")),
            "clash_score": safe_float(row.get("clash_score")),
            "sd40_chain": row.get("sd40_chain"),
            "sd40_coverage": safe_float(row.get("sd40_coverage")),
        }
    return ranker


def confidence_for(span_dir: Path, cid: str, model_idx: int):
    pattern = f"confidence_{cid}_model_{model_idx}.json"
    matches = list((span_dir / "08_boltz2_local" / "outputs").glob(f"{cid}/**/{pattern}"))
    if not matches:
        return {}
    data = read_json(matches[0])
    return {
        "confidence_score": safe_float(data.get("confidence_score")),
        "ptm": safe_float(data.get("ptm")),
        "complex_plddt": safe_float(data.get("complex_plddt")),
        "complex_pde": safe_float(data.get("complex_pde")),
    }


def parse_online_batch(span: int):
    span_dir = ONLINE_ROOT / f"{span}A"
    summary = read_json(span_dir / "05_reports" / f"span{span}A_summary.json")
    sequence_rows = read_json(span_dir / "05_reports" / "sequence_rows.json")
    qc_rows = {row["candidate_id"]: row for row in read_csv_dicts(span_dir / "07_sequence_qc" / "sequence_qc.csv")}
    ranker = parse_ranker(span_dir / "11_ranker" / "ranking.csv")

    rmsd_jsons = {p.stem: read_json(p) for p in (span_dir / "09_rmsd_gate_local").glob("*.json")}
    dock_jsons = {p.stem: read_json(p) for p in (span_dir / "10_docking").glob("*.json")}

    candidate_rows = []
    model_rows = []

    for seq in sequence_rows:
        cid = seq.get("候选ID")
        qc = qc_rows.get(cid, {})
        rmsd = rmsd_jsons.get(cid, {})
        dock = dock_jsons.get(cid, {})
        rmsd_models = {m.get("model_index"): m for m in rmsd.get("models", [])}
        dock_models = {m.get("model_index"): m for m in dock.get("models", [])}
        model_scores = [safe_float(seq.get(f"模型{i}总分")) for i in range(1, 4)]

        for idx in sorted(set(rmsd_models) | set(dock_models) | {k[1] for k in ranker if k[0] == cid}):
            rm = rmsd_models.get(idx, {})
            dm = dock_models.get(idx, {})
            rr = ranker.get((cid, idx), {})
            conf = confidence_for(span_dir, cid, idx)
            model_rows.append({
                "batch": "online_mmseqs2",
                "target_span_A": span,
                "candidate_id": cid,
                "candidate_type": "baseline" if cid == "baseline_GGGGSGGGGS" else "design",
                "linker_sequence": seq.get("Linker序列"),
                "model_index": idx + 1,
                "linker_ca_rmsd_A": safe_float(rm.get("linker_ca_rmsd_A")),
                "rmsd_model_pass": rm.get("rf_rmsd_pass"),
                "vina_best_score_kcal_mol": safe_float(dm.get("vina_best_score_kcal_mol")),
                "vina_model_pass": dm.get("vina_model_pass"),
                **rr,
                **conf,
            })

        model_subset = [r for r in model_rows if r["target_span_A"] == span and r["candidate_id"] == cid]
        candidate_rows.append({
            "batch": "online_mmseqs2",
            "target_span_A": span,
            "candidate_id": cid,
            "candidate_type": "baseline" if cid == "baseline_GGGGSGGGGS" else "design",
            "linker_sequence": seq.get("Linker序列"),
            "final_status": seq.get("最终状态"),
            "model1_score": model_scores[0],
            "model2_score": model_scores[1],
            "model3_score": model_scores[2],
            "final_score_median": safe_float(seq.get("方案B中位数")),
            "score_minus_baseline": None if safe_float(seq.get("方案B中位数")) is None else safe_float(seq.get("方案B中位数")) - BASELINE_SCORE_ONLINE,
            "qc_pass": str(qc.get("qc_pass", "")).lower() == "true" if qc else None,
            "qc_reasons": qc.get("reasons"),
            "kr_fraction": safe_float(qc.get("kr_fraction")),
            "hydrophobic_fraction": safe_float(qc.get("hydrophobic_fraction")),
            "net_charge": safe_float(qc.get("net_charge")),
            "rmsd_pass_count": rmsd.get("rf_rmsd_gate", {}).get("pass_count"),
            "rmsd_candidate_pass": rmsd.get("rf_rmsd_gate", {}).get("candidate_pass"),
            "linker_rmsd_median_A": median([r.get("linker_ca_rmsd_A") for r in model_subset]),
            "vina_pass_count": dock.get("vina_gate", {}).get("pass_count"),
            "vina_candidate_pass": dock.get("vina_gate", {}).get("candidate_pass"),
            "vina_median_kcal_mol": median([r.get("vina_best_score_kcal_mol") for r in model_subset]),
            "sd40_rmsd_median_A": median([r.get("sd40_rmsd_A") for r in model_subset]),
            "contact_recovery_median": median([r.get("contact_recovery") for r in model_subset]),
            "clashing_atoms_median": median([r.get("clashing_atoms") for r in model_subset]),
            "confidence_median": median([r.get("confidence_score") for r in model_subset]),
            "ptm_median": median([r.get("ptm") for r in model_subset]),
        })

    summary_row = {
        "batch": "online_mmseqs2",
        "target_span_A": span,
        **summary,
        "rmsd_threshold_A": RMSD_THRESHOLD,
        "rmsd_required_models": 2,
        "vina_threshold_kcal_mol": VINA_THRESHOLD_ONLINE,
        "vina_required_models": 2,
        "baseline_sequence": BASELINE_SEQUENCE,
        "baseline_score": BASELINE_SCORE_ONLINE,
    }
    return summary_row, candidate_rows, model_rows


def parse_early16():
    workbook_path = SOURCE_ROOT / "ADAR2_SD40_16A_中文结果表.xlsx"
    wb = openpyxl.load_workbook(workbook_path, data_only=True)
    ws = wb["序列最终得分"]
    rows = []
    for values in ws.iter_rows(min_row=5, values_only=True):
        source, sequence, s1, s2, s3, final, conclusion = values[:7]
        if not source or not sequence:
            continue
        rows.append({
            "batch": "early_single_sequence_msa",
            "target_span_A": 16,
            "source": source,
            "linker_sequence": sequence,
            "model1_score": safe_float(s1),
            "model2_score": safe_float(s2),
            "model3_score": safe_float(s3),
            "final_score_median": safe_float(final),
            "conclusion": conclusion,
            "candidate_type": "baseline" if sequence == BASELINE_SEQUENCE else "design",
        })
    summary = read_json(EARLY16_ROOT / "05_reports" / "span16A_summary.json")
    scored_designs = sum(1 for row in rows if row["candidate_type"] == "design" and row["final_score_median"] is not None)
    if summary.get("vina_pass_design") is None:
        summary["vina_pass_design"] = scored_designs
    if summary.get("ranker_models") is None:
        summary["ranker_models"] = scored_designs * 3
    summary_row = {
        "batch": "early_single_sequence_msa",
        "target_span_A": 16,
        **summary,
        "rmsd_threshold_A": 2.0,
        "rmsd_required_models": 2,
        "vina_threshold_kcal_mol": -7.0,
        "vina_required_models": 2,
        "baseline_sequence": BASELINE_SEQUENCE,
        "baseline_score": next((r["final_score_median"] for r in rows if r["candidate_type"] == "baseline"), 17.0274),
    }
    return summary_row, rows


def build_source_inventory():
    manifest_path = PACKAGE_ROOT / "文件清单.csv"
    inventory = []
    for row in read_csv_dicts(manifest_path):
        rel = row["相对路径"]
        stage, ext, usage = classify_source(rel)
        inventory.append({
            "scope": "匿名包解压内容",
            "relative_path": rel,
            "size_bytes": safe_int(row.get("字节数")),
            "sha256": row.get("SHA256"),
            "modified_time": row.get("修改时间"),
            "stage": stage,
            "extension": ext,
            "usage_in_organization": usage,
        })

    manifest_abs = str(manifest_path.resolve()).lower()
    for path in SOURCE_ROOT.iterdir():
        if path == OUTPUT_ROOT or path.name == "ADAR2_SD40_中期提交材料_匿名版_解压":
            continue
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        stage, ext, usage = classify_source(path.name)
        inventory.append({
            "scope": "匿名归档补充结果文件",
            "relative_path": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": digest.hexdigest(),
            "modified_time": pd.Timestamp(path.stat().st_mtime, unit="s").isoformat(),
            "stage": stage,
            "extension": ext,
            "usage_in_organization": usage,
        })
    return inventory


def ensure_dirs():
    dirs = [
        OUTPUT_ROOT / "00_阅读说明",
        OUTPUT_ROOT / "01_主结果报告",
        OUTPUT_ROOT / "02_核心数据表",
        OUTPUT_ROOT / "03_主图",
        OUTPUT_ROOT / "04_补充表与补充图",
        OUTPUT_ROOT / "05_方法与参数",
        OUTPUT_ROOT / "06_全量来源索引",
        OUTPUT_ROOT / "07_GitHub_ready" / "data",
        OUTPUT_ROOT / "07_GitHub_ready" / "figures",
        OUTPUT_ROOT / "07_GitHub_ready" / "methods",
    ]
    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)


def get_font(size, bold=False):
    candidates = [
        Path(r"C:\Windows\Fonts\msyhbd.ttc") if bold else Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


NAVY = "#202020"
BLUE = "#555555"
TEAL = "#858585"
GOLD = "#B8B8B8"
RED = "#000000"
GRAY = "#6B6B6B"
LIGHT = "#F2F2F2"


def canvas(title, subtitle="", width=1800, height=1080):
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, 118], fill=NAVY)
    draw.text((70, 24), title, fill="white", font=get_font(42, True))
    if subtitle:
        draw.text((72, 78), subtitle, fill="#E0E0E0", font=get_font(22))
    return img, draw


def draw_axes(draw, box, xlabels, y_max, y_label=""):
    x0, y0, x1, y1 = box
    draw.line([x0, y1, x1, y1], fill="#555555", width=3)
    draw.line([x0, y0, x0, y1], fill="#555555", width=3)
    for i in range(6):
        value = y_max * i / 5
        y = y1 - (y1 - y0) * i / 5
        draw.line([x0, y, x1, y], fill="#E5E7EB", width=1)
        draw.text((x0 - 75, y - 12), f"{value:.0f}", fill="#444444", font=get_font(20))
    for i, label in enumerate(xlabels):
        x = x0 + (i + 0.5) * (x1 - x0) / len(xlabels)
        draw.text((x - 18, y1 + 15), str(label), fill="#333333", font=get_font(20))
    if y_label:
        # Keep the axis title above the plot so it cannot collide with the
        # highest y-axis tick label at the left edge.
        draw.text((x0, y0 - 44), y_label, fill="#333333", font=get_font(20, True))


def save_figure(img, name):
    path = OUTPUT_ROOT / "03_主图" / name
    img.save(path, quality=95)
    shutil.copy2(path, OUTPUT_ROOT / "07_GitHub_ready" / "figures" / name)
    return path


def fig_funnel(span_df):
    img, draw = canvas("图 1  各目标距离的筛选漏斗", "RFdiffusion → ProteinMPNN → 序列QC → Boltz-2 → RMSD → Vina → Ranker")
    box = (150, 190, 1710, 900)
    spans = span_df["target_span_A"].astype(int).tolist()
    draw_axes(draw, box, spans, 32, "候选数")
    series = [
        ("MPNN去重", "mpnn_unique", BLUE),
        ("QC通过", "qc_pass_design", TEAL),
        ("RMSD通过", "rmsd_pass_design", GOLD),
        ("Vina通过", "vina_pass_design", RED),
    ]
    x0, y0, x1, y1 = box
    slot = (x1 - x0) / len(spans)
    bw = slot / 5.5
    for j, (label, col, color) in enumerate(series):
        for i, value in enumerate(span_df[col]):
            x = x0 + i * slot + slot * 0.12 + j * bw
            h = (y1 - y0) * float(value) / 32
            draw.rectangle([x, y1 - h, x + bw - 4, y1], fill=color)
        lx = 240 + j * 330
        draw.rectangle([lx, 960, lx + 32, 992], fill=color)
        draw.text((lx + 44, 960), label, fill="#222222", font=get_font(22))
    return save_figure(img, "图1_距离筛选漏斗.png")


def fig_scores(candidate_df):
    designs = candidate_df[(candidate_df.candidate_type == "design") & candidate_df.final_score_median.notna()].copy()
    img, draw = canvas("图 2  候选最终分与基线比较", "每个点为一个正式评分候选；红线为 GGGGSGGGGS 基线 24.1035")
    box = (150, 180, 1710, 900)
    spans = list(range(11, 21))
    ymax = max(70, math.ceil(designs.final_score_median.max() / 10) * 10)
    draw_axes(draw, box, spans, ymax, "Ranker最终分")
    x0, y0, x1, y1 = box
    yb = y1 - (y1 - y0) * BASELINE_SCORE_ONLINE / ymax
    draw.line([x0, yb, x1, yb], fill=RED, width=5)
    for _, row in designs.iterrows():
        i = int(row.target_span_A) - 11
        seed = sum(ord(c) for c in row.candidate_id) % 41 - 20
        x = x0 + (i + 0.5) * (x1 - x0) / len(spans) + seed
        y = y1 - (y1 - y0) * row.final_score_median / ymax
        color = TEAL if row.final_score_median > BASELINE_SCORE_ONLINE else GRAY
        draw.ellipse([x - 7, y - 7, x + 7, y + 7], fill=color, outline="white", width=2)
    draw.text((1240, yb - 34), "基线 24.1035", fill=RED, font=get_font(22, True))
    return save_figure(img, "图2_候选分数与基线.png")


def fig_top_candidates(top_df):
    top = top_df.head(12).sort_values("final_score_median")
    img, draw = canvas("图 3  优于基线的头部候选", "最终分为三个 Boltz-2 模型 Ranker 总分的中位数")
    x0, y0, x1, y1 = 560, 180, 1680, 960
    maxv = max(65, float(top.final_score_median.max()) + 3)
    for i, (_, row) in enumerate(top.iterrows()):
        y = y1 - (i + 1) * 58
        label = f"{int(row.target_span_A)} Å  {row.linker_sequence}"
        draw.text((70, y - 13), label, fill="#222222", font=get_font(22, True))
        w = (x1 - x0) * row.final_score_median / maxv
        draw.rectangle([x0, y - 16, x0 + w, y + 18], fill=TEAL)
        draw.text((x0 + w + 14, y - 14), f"{row.final_score_median:.2f}", fill=NAVY, font=get_font(22, True))
    bx = x0 + (x1 - x0) * BASELINE_SCORE_ONLINE / maxv
    draw.line([bx, y0, bx, y1], fill=RED, width=4)
    draw.text((bx + 8, y0), "基线", fill=RED, font=get_font(20, True))
    return save_figure(img, "图3_头部候选排序.png")


def fig_pass_rates(span_df):
    img, draw = canvas("图 4  RMSD 与 Vina 候选通过率", "候选门控均要求至少 2/3 个模型通过")
    box = (150, 190, 1710, 900)
    spans = span_df.target_span_A.astype(int).tolist()
    draw_axes(draw, box, spans, 100, "通过率 %")
    x0, y0, x1, y1 = box
    slot = (x1 - x0) / len(spans)
    for i, row in span_df.reset_index(drop=True).iterrows():
        denom = max(float(row.boltz_candidates) - 1, 1)
        rmsd = 100 * float(row.rmsd_pass_design) / denom
        vina = 100 * float(row.vina_pass_design) / denom
        for j, (value, color) in enumerate([(rmsd, BLUE), (vina, GOLD)]):
            x = x0 + i * slot + slot * (0.22 + j * 0.30)
            h = (y1 - y0) * value / 100
            draw.rectangle([x, y1 - h, x + slot * 0.24, y1], fill=color)
    draw.rectangle([500, 970, 532, 1002], fill=BLUE)
    draw.text((545, 969), "Linker RMSD < 2.0 Å", fill="#222", font=get_font(22))
    draw.rectangle([980, 970, 1012, 1002], fill=GOLD)
    draw.text((1025, 969), "Vina ≤ -6.0 kcal/mol", fill="#222", font=get_font(22))
    return save_figure(img, "图4_RMSD与Vina通过率.png")


def fig_sequence_qc(candidate_df):
    qc = candidate_df[(candidate_df.candidate_type == "design") & candidate_df.kr_fraction.notna()].copy()
    grouped = qc.groupby("target_span_A").agg(
        kr_fraction=("kr_fraction", "mean"),
        hydrophobic_fraction=("hydrophobic_fraction", "mean"),
        net_charge=("net_charge", "median"),
        qc_pass_rate=("qc_pass", "mean"),
    ).reset_index()
    img, draw = canvas("图 5  Linker 序列组成与 QC", "各距离的候选均值；净电荷显示为中位数")
    box = (150, 190, 1710, 900)
    spans = grouped.target_span_A.astype(int).tolist()
    draw_axes(draw, box, spans, 100, "比例 %")
    x0, y0, x1, y1 = box
    slot = (x1 - x0) / len(spans)
    for i, row in grouped.iterrows():
        vals = [100 * row.kr_fraction, 100 * row.hydrophobic_fraction, 100 * row.qc_pass_rate]
        for j, (value, color) in enumerate(zip(vals, [RED, BLUE, TEAL])):
            x = x0 + i * slot + slot * (0.12 + j * 0.24)
            h = (y1 - y0) * value / 100
            draw.rectangle([x, y1 - h, x + slot * 0.18, y1], fill=color)
        draw.text((x0 + i * slot + 48, y0 + 12), f"q={row.net_charge:.0f}", fill="#444", font=get_font(16))
    legend = [("K/R比例", RED), ("疏水比例", BLUE), ("QC通过率", TEAL)]
    for i, (label, color) in enumerate(legend):
        x = 430 + i * 360
        draw.rectangle([x, 970, x + 32, 1002], fill=color)
        draw.text((x + 44, 969), label, fill="#222", font=get_font(22))
    return save_figure(img, "图5_序列组成与QC.png")


def fig_16_comparison(early_summary, online_summary, early_rows, online_candidates):
    img, draw = canvas("图 6  两个 16 Å 批次的敏感性比较", "MSA方式和Vina阈值不同，因此仅用于批次敏感性分析")
    headers = ["指标", "早期单序列MSA", "后期在线MMseqs2"]
    rows = [
        ("Vina阈值", "≤ -7.0", "≤ -6.0"),
        ("MPNN去重", early_summary.get("mpnn_unique"), online_summary.get("mpnn_unique")),
        ("QC通过", early_summary.get("qc_pass_design"), online_summary.get("qc_pass_design")),
        ("RMSD通过", early_summary.get("rmsd_pass_design"), online_summary.get("rmsd_pass_design")),
        ("Vina通过", early_summary.get("vina_pass_design"), online_summary.get("vina_pass_design")),
        ("基线分", f"{early_summary.get('baseline_score', 17.0274):.4f}", f"{BASELINE_SCORE_ONLINE:.4f}"),
    ]
    ex = [r for r in early_rows if r["candidate_type"] == "design" and r["final_score_median"] is not None]
    ox = online_candidates[(online_candidates.candidate_type == "design") & online_candidates.final_score_median.notna()]
    rows.append(("最高候选分", f"{max((r['final_score_median'] for r in ex), default=float('nan')):.4f}", f"{ox.final_score_median.max():.4f}"))
    cols = [130, 660, 1160, 1680]
    y = 220
    for i, head in enumerate(headers):
        draw.rectangle([cols[i], y, cols[i + 1], y + 70], fill=NAVY)
        draw.text((cols[i] + 24, y + 18), head, fill="white", font=get_font(24, True))
    y += 70
    for ri, row in enumerate(rows):
        fill = "#FFFFFF" if ri % 2 == 0 else "#F2F2F2"
        for i, value in enumerate(row):
            draw.rectangle([cols[i], y, cols[i + 1], y + 78], fill=fill, outline="#D9D9D9", width=2)
            draw.text((cols[i] + 24, y + 22), str(value), fill="#222", font=get_font(24, i == 0))
        y += 78
    draw.text((150, 900), "注意：批次之间同时改变了MSA来源和Vina阈值，不能把差异解释为16 Å本身造成。", fill=RED, font=get_font(25, True))
    return save_figure(img, "图6_16A批次敏感性.png")


def fig_evidence_hierarchy():
    img, draw = canvas("图 7  当前证据层级与下一步验证", "计算筛选支持候选优先级，但不能替代生化与细胞实验")
    steps = [
        ("层级 1", "生成", "RFdiffusion\nProteinMPNN", BLUE),
        ("层级 2", "三模型重复", "Boltz-2\nRMSD门控", TEAL),
        ("层级 3", "结构门控", "Vina\nSD40 Ranker", GOLD),
        ("层级 4", "综合排序", "基线对照\n多指标一致性", "#B8B8B8"),
        ("下一步", "实验验证", "表达与结合\n活性与定位", RED),
    ]
    y = 190
    for idx, (level, title, detail, color) in enumerate(steps):
        x = 180 + idx * 300
        draw.rounded_rectangle([x, y + idx * 75, x + 250, y + idx * 75 + 310], radius=12, fill=color)
        draw.text((x + 25, y + idx * 75 + 28), level, fill="white", font=get_font(24, True))
        draw.text((x + 25, y + idx * 75 + 88), title, fill="white", font=get_font(26, True))
        lines = detail.split("\n")
        for j, line in enumerate(lines):
            draw.text((x + 25, y + idx * 75 + 150 + j * 38), line, fill="white", font=get_font(21))
        if idx < len(steps) - 1:
            ax = x + 255
            ay = y + idx * 75 + 290
            draw.line([ax, ay, ax + 55, ay + 70], fill="#555", width=6)
            draw.polygon([(ax + 55, ay + 70), (ax + 35, ay + 58), (ax + 48, ay + 45)], fill="#555")
    return save_figure(img, "图7_证据层级.png")


def style_doc(document: Document):
    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = "Microsoft YaHei"
    normal.font.size = Pt(10.5)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.25
    for style_name, size in [("Title", 24), ("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11)]:
        style = styles[style_name]
        style.font.name = "Microsoft YaHei"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
        style.paragraph_format.keep_with_next = True
        p_pr = style._element.get_or_add_pPr()
        for border in p_pr.findall(qn("w:pBdr")):
            p_pr.remove(border)
    section = document.sections[0]
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    section.header_distance = Cm(0.9)
    section.footer_distance = Cm(0.9)


def shade_cell(cell, fill, white=False):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    if white:
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.color.rgb = RGBColor(255, 255, 255)
                run.font.bold = True


def set_cell_text(cell, value, bold=False, center=False):
    cell.text = "" if value is None else str(value)
    p = cell.paragraphs[0]
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in p.runs:
        run.font.name = "Microsoft YaHei"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
        run.font.size = Pt(8.5)
        run.font.bold = bold


def add_table(document, headers, rows, widths=None):
    table = document.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, head in enumerate(headers):
        set_cell_text(hdr[i], head, bold=True, center=True)
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)
    for ri, row in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row):
            set_cell_text(cells[i], value, center=i != 1)
    if widths:
        for row in table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = Cm(width)
    document.add_paragraph()
    return table


def add_figure(document, path: Path, caption: str):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(path), width=Inches(6.4))
    cap = document.add_paragraph(caption)
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in cap.runs:
        run.font.size = Pt(9)
        run.font.bold = True
    cap.paragraph_format.keep_with_next = False


def build_docx(span_df, candidate_df, top_df, early_summary, online16, early_rows, figure_paths, inventory_df):
    doc = Document()
    doc.core_properties.author = "Anonymous competition team"
    doc.core_properties.last_modified_by = "Anonymous competition team"
    doc.core_properties.title = "ADAR2 NES SD40 Linker Design Computational Results"
    doc.core_properties.subject = "Anonymous computational design report"
    doc.core_properties.keywords = "ADAR2, SD40, linker, RFdiffusion, ProteinMPNN, Boltz-2"
    style_doc(doc)
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("ADAR2 NES SD40 Linker 计算结果汇总")
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run("基于 11–20 Å 多距离设计、三模型结构预测、RMSD/Vina 门控与 SD40 几何评分").bold = True
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run("数据范围：匿名化全量结果档案  |  整理日期：2026-09-30")

    doc.add_heading("执行摘要", level=1)
    scored = candidate_df[(candidate_df.candidate_type == "design") & candidate_df.final_score_median.notna()]
    best = top_df.iloc[0]
    above_count = len(top_df)
    total_unique = int(span_df.mpnn_unique.sum())
    total_models = int(span_df.boltz_models.sum())
    doc.add_paragraph(
        f"本次整理覆盖匿名提交包中的 {len(inventory_df):,} 条来源记录及归档中的补充结果文件。在线 MMseqs2 批次共获得 "
        f"{total_unique} 条去重 ProteinMPNN 设计序列，完成 {total_models} 个 Boltz-2 模型预测。采用 Linker Cα RMSD 严格小于 "
        f"{RMSD_THRESHOLD:.1f} Å、至少 2/3 模型通过，以及 Vina 最佳分数不高于 {VINA_THRESHOLD_ONLINE:.1f} kcal/mol、至少 2/3 模型通过的门控。"
    )
    doc.add_paragraph(
        f"共有 {above_count} 个正式候选的最终分严格高于 GGGGSGGGGS 基线 {BASELINE_SCORE_ONLINE:.4f}。当前最高候选为 "
        f"{best.linker_sequence}（{int(best.target_span_A)} Å），最终分 {best.final_score_median:.4f}，高于基线 {best.score_minus_baseline:.4f}。"
    )
    doc.add_paragraph(
        "这些结果支持候选优先级排序，但仍属于计算筛选证据。Vina 分数不等价于实验结合自由能，Ranker 是基于设定权重的几何复合指标，最终入选仍需表达、结合、编辑活性、定位与细胞毒性实验验证。"
    )

    doc.add_heading("研究设计与结果组织", level=1)
    doc.add_paragraph(
        "结果按文献常见的证据链组织：先说明研究设计和数据完整性，再展示跨候选标准化比较、三模型重复稳健性、结构与对接解释，最后给出综合候选分层、限制和验证路线。三篇参考文献仅用于结果呈现逻辑，不作为本项目数值来源。"
    )
    add_figure(doc, figure_paths[6], "图 7  当前证据层级与下一步验证")

    doc.add_heading("数据完整性与分析范围", level=1)
    doc.add_paragraph(
        "匿名包的 VALIDATION_REPORT 状态为 PASS；在线批次 11–20 Å 均包含 RFdiffusion、ProteinMPNN、序列 QC、Boltz-2、Linker RMSD、Vina 和 Ranker 阶段。归档中的两份补充 XLSX 与包内副本哈希一致。全部大体积结构、MSA 和日志文件通过相对路径、大小、SHA256、阶段和用途写入全量来源索引，并作为 GitHub Release 的分卷复现附件提供。"
    )
    add_table(
        doc,
        ["来源类别", "文件数", "总大小 GiB"],
        [(stage, int(group.shape[0]), f"{group.size_bytes.sum() / 1024**3:.2f}") for stage, group in inventory_df.groupby("stage")],
        [6.5, 3.0, 3.5],
    )

    doc.add_heading("筛选漏斗", level=1)
    add_figure(doc, figure_paths[0], "图 1  11–20 Å 在线批次的候选筛选漏斗")
    rows = []
    for _, r in span_df.iterrows():
        rows.append([
            int(r.target_span_A), int(r.rf_backbones), int(r.mpnn_unique), int(r.qc_pass_design),
            int(r.boltz_candidates), int(r.rmsd_pass_design), int(r.vina_pass_design), int(r.ranker_models),
        ])
    add_table(doc, ["距离 Å", "RF骨架", "MPNN去重", "QC通过", "Boltz候选", "RMSD通过", "Vina通过", "Ranker模型"], rows)

    doc.add_heading("候选分数与基线比较", level=1)
    add_figure(doc, figure_paths[1], "图 2  正式评分候选与 GGGGSGGGGS 基线比较")
    add_figure(doc, figure_paths[2], "图 3  优于基线的头部候选")
    top_rows = []
    for _, r in top_df.head(12).iterrows():
        top_rows.append([
            int(r.target_span_A), r.linker_sequence, f"{r.final_score_median:.4f}", f"{r.score_minus_baseline:+.4f}",
            f"{r.linker_rmsd_median_A:.3f}" if pd.notna(r.linker_rmsd_median_A) else "",
            f"{r.vina_median_kcal_mol:.2f}" if pd.notna(r.vina_median_kcal_mol) else "",
            f"{r.sd40_rmsd_median_A:.3f}" if pd.notna(r.sd40_rmsd_median_A) else "",
        ])
    add_table(doc, ["距离 Å", "Linker", "最终分", "较基线", "Linker RMSD Å", "Vina", "SD40 RMSD Å"], top_rows)

    doc.add_heading("三模型稳健性与门控", level=1)
    add_figure(doc, figure_paths[3], "图 4  Linker RMSD 与 Vina 候选通过率")
    doc.add_paragraph(
        "RMSD 采用每个候选的三个 Boltz-2 模型分别判定，单模型 Linker Cα RMSD 必须严格小于 2.0 Å；候选至少 2/3 模型通过。Vina 同样按模型判定，在线批次阈值为不高于 -6.0 kcal/mol，候选至少 2/3 模型通过。最终分取三个 Ranker 模型总分的中位数，以降低单个结构预测的偶然性。"
    )

    doc.add_heading("序列组成与质量控制", level=1)
    add_figure(doc, figure_paths[4], "图 5  Linker 序列组成与 QC 概览")
    doc.add_paragraph(
        "序列 QC 表保留了 K/R 比例、疏水比例、净电荷和失败原因，可用于识别过强正电、过度疏水或其他不利组成。图中展示各距离的整体分布，不应以单一组成指标替代结构和功能证据。"
    )

    doc.add_heading("16 Å 批次敏感性", level=1)
    add_figure(doc, figure_paths[5], "图 6  早期单序列 MSA 与后期在线 MMseqs2 的 16 Å 批次比较")
    doc.add_paragraph(
        "早期 16 Å 批次使用本地单序列 A3M，Vina 阈值为不高于 -7.0 kcal/mol，基线分 17.0274；后期 16 Å 重跑使用在线 MMseqs2 MSA，Vina 阈值为不高于 -6.0 kcal/mol，基线分 24.1035。由于 MSA 来源和筛选阈值同时变化，两个批次只能用于流程敏感性分析，不能解释为距离效应。跨距离主比较统一采用后期在线批次。"
    )

    doc.add_page_break()
    doc.add_heading("综合候选分层", level=1)
    doc.add_paragraph(
        "建议把候选分为三级。一级候选同时满足：最终分高于基线、RMSD 与 Vina 均至少 2/3 通过、三模型分数离散较小、序列 QC 通过；二级候选满足硬门控但存在某一项边缘指标；三级候选保留为机制或序列多样性备选。派生工作簿保留所有候选和逐模型字段，便于按不同实验优先级重新筛选。"
    )
    tier1 = top_df[(top_df.rmsd_pass_count >= 2) & (top_df.vina_pass_count >= 2) & (top_df.qc_pass == True)].head(10)
    add_table(doc, ["优先级", "距离 Å", "Linker", "最终分", "RMSD通过", "Vina通过", "QC"], [
        [i + 1, int(r.target_span_A), r.linker_sequence, f"{r.final_score_median:.4f}", f"{int(r.rmsd_pass_count)}/3", f"{int(r.vina_pass_count)}/3", "通过"]
        for i, (_, r) in enumerate(tier1.iterrows())
    ])

    doc.add_heading("方法与参数", level=1)
    methods = [
        ("结构骨架", "RFdiffusion，每个目标距离 3 个 backbone"),
        ("序列设计", "ProteinMPNN，每个距离请求 30 条，结果按唯一序列统计"),
        ("结构预测", "Boltz-2，每候选 3 个模型；在线批次使用 MMseqs2 MSA"),
        ("RMSD门控", "Linker Cα RMSD < 2.0 Å；至少 2/3 模型通过"),
        ("Vina门控", "在线批次最佳分数 ≤ -6.0 kcal/mol；至少 2/3 模型通过"),
        ("Ranker模型分", "100 × (0.3×S_RMSD + 0.3×S_contact + 0.4×S_clash)"),
        ("候选最终分", "三个 Boltz-2 模型 Ranker 总分的中位数"),
        ("对照", "GGGGSGGGGS；在线批次基线 24.1035"),
    ]
    add_table(doc, ["项目", "设置"], methods, [4.5, 10.5])

    doc.add_heading("限制与下一步", level=1)
    limitations = [
        "Boltz-2 单序列或 MSA 质量会影响结构置信度；模型间一致性可降低但不能消除该不确定性。",
        "Linker RMSD 衡量与 RFdiffusion 骨架的一致性，不直接等价于功能保持或真实构象分布。",
        "Vina 是近似打分；当前阈值是流程门控，不应解释为实验结合常数。",
        "Ranker 权重属于预设决策函数，候选排序需通过权重敏感性和实验数据校准。",
        "下一步应优先验证一级候选，并保留基线、空白连接和代表性失败候选作为对照。",
    ]
    for item in limitations:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_heading("数据可用性与复现", level=1)
    doc.add_paragraph(
        "本报告的主表和图均由匿名化全量结果档案重建。主仓库提供可直接浏览的报告、表格、图、最终结构、代码与关键日志；GitHub Release 提供 11 个完整复现分卷及统一 SHA256 清单。完整相对路径和 SHA256 位于 06_全量来源索引。第三方预训练权重、Conda 环境和软件缓存不随提交包分发，应按官方来源另行获取。"
    )

    doc.add_heading("参考文献", level=1)
    for paper in PAPERS:
        doc.add_paragraph(paper, style="List Number")

    path = OUTPUT_ROOT / "01_主结果报告" / "ADAR2_SD40_计算结果_文献式全量报告.docx"
    doc.save(path)
    return path


def write_readmes(span_df, candidate_df, top_df, inventory_df):
    source_note = f"""# 阅读说明

本目录是匿名化全量结果档案的派生整理，不修改、不替换原始文件。

## 数据纳入原则

- 匿名包内清单的全部 {len(inventory_df):,} 条记录均进入 `06_全量来源索引`。
- JSON、CSV、XLSX 用于直接重建表格和交叉核验。
- A3M、PDB、NPZ、PDBQT、日志、脚本和配置通过相对路径、SHA256、阶段和用途保持追溯。
- 11–20 Å 跨距离比较统一使用在线 MMseqs2 批次。
- 早期 16 Å 单序列 MSA 批次独立呈现，不与在线 16 Å 混为同一批数据。

## 主要文件

- `01_主结果报告`：中文 DOCX 主报告。
- `02_核心数据表`：汇总工作簿和核心 CSV。
- `03_主图`：7 张主图。
- `04_补充表与补充图`：候选级、模型级和早期 16 Å 明细。
- `05_方法与参数`：筛选规则和字段字典。
- `06_全量来源索引`：全部来源文件索引与阶段统计。
- `07_GitHub_ready`：可公开整理的轻量目录，不含大文件。

## 关键阈值

- Linker Cα RMSD：严格 `< 2.0 Å`，候选至少 2/3 模型通过。
- 在线批次 Vina：`≤ -6.0 kcal/mol`，候选至少 2/3 模型通过。
- 基线：GGGGSGGGGS，在线批次最终分 24.1035。
"""
    (OUTPUT_ROOT / "00_阅读说明" / "README.md").write_text(source_note, encoding="utf-8")

    github_readme = f"""# ADAR2 NES SD40 linker design computational results

The main repository contains reader-facing tables, figures, final structures, analysis code, key logs, and provenance records. The complete non-duplicate reproduction archive is distributed as 11 GitHub Release ZIP assets with a shared SHA256 manifest.

## Scope

- Target spans: 11–20 Å
- RFdiffusion: 3 backbones per span
- ProteinMPNN: 30 requested sequences per span
- Boltz-2: 3 models per candidate
- Linker Cα RMSD gate: `< 2.0 Å` in at least 2/3 models
- Online-batch Vina gate: `≤ -6.0 kcal/mol` in at least 2/3 models
- Ranker model score: `100 × (0.3×S_RMSD + 0.3×S_contact + 0.4×S_clash)`
- Candidate score: median of three model scores
- Baseline: GGGGSGGGGS, score 24.1035

## Results snapshot

- MPNN unique sequences: {int(span_df.mpnn_unique.sum())}
- Boltz-2 models: {int(span_df.boltz_models.sum())}
- Candidates strictly above baseline: {len(top_df)}
- Best candidate: {top_df.iloc[0].linker_sequence} at {int(top_df.iloc[0].target_span_A)} Å, score {top_df.iloc[0].final_score_median:.4f}

## Data availability

The complete archive is indexed by relative path and SHA256 in `source_inventory.csv`. Download all 11 `full-reproduction-*.zip` assets and `FULL_REPRODUCTION_SHA256SUMS.txt` from the complete-submission GitHub Release, verify the hashes, and extract all ZIP files into the same empty directory. Third-party pretrained weights, Conda environments, software caches, private competition documents, and identity-bearing source files are intentionally excluded.

## Important interpretation note

The early 16 Å single-sequence-MSA batch and the later online-MMseqs2 16 Å batch use different MSA settings and Vina thresholds. They are retained as a sensitivity comparison and must not be interpreted as a distance effect.
"""
    (OUTPUT_ROOT / "07_GitHub_ready" / "README.md").write_text(github_readme, encoding="utf-8")
    (OUTPUT_ROOT / "07_GitHub_ready" / ".gitignore").write_text(
        "*.a3m\n*.npz\n*.pdb\n*.pdbqt\n*.gz\n*.zip\n*.ckpt\ncache/\noutputs/\nraw/\n",
        encoding="utf-8",
    )
    method_text = """# Methods and thresholds

The cross-distance analysis uses only the online MMseqs2 batch for 11–20 Å.

1. Generate three RFdiffusion backbones per target span.
2. Request thirty ProteinMPNN linker sequences per span and retain unique sequences.
3. Apply sequence-composition QC.
4. Predict three Boltz-2 models per candidate.
5. Require linker C-alpha RMSD strictly below 2.0 Å in at least two of three models.
6. Require AutoDock Vina best score at or below -6.0 kcal/mol in at least two of three models.
7. Score SD40 geometry per model with 100 × (0.3×S_RMSD + 0.3×S_contact + 0.4×S_clash).
8. Use the median of three model scores as the candidate final score.
9. Compare formally scored candidates with the GGGGSGGGGS baseline score of 24.1035.
"""
    (OUTPUT_ROOT / "05_方法与参数" / "方法与阈值.md").write_text(method_text, encoding="utf-8")
    shutil.copy2(OUTPUT_ROOT / "05_方法与参数" / "方法与阈值.md", OUTPUT_ROOT / "07_GitHub_ready" / "methods" / "methods.md")


def write_csvs(span_df, candidate_df, model_df, top_df, early_df, inventory_df):
    core = OUTPUT_ROOT / "02_核心数据表"
    supp = OUTPUT_ROOT / "04_补充表与补充图"
    index_dir = OUTPUT_ROOT / "06_全量来源索引"
    github_data = OUTPUT_ROOT / "07_GitHub_ready" / "data"
    span_df.to_csv(core / "跨距离漏斗汇总.csv", index=False, encoding="utf-8-sig")
    top_df.to_csv(core / "严格高于GGGGSGGGGS的候选.csv", index=False, encoding="utf-8-sig")
    candidate_df.to_csv(supp / "在线批次_全候选级记录.csv", index=False, encoding="utf-8-sig")
    model_df.to_csv(supp / "在线批次_全模型级记录.csv", index=False, encoding="utf-8-sig")
    early_df.to_csv(supp / "早期16A_单序列MSA候选记录.csv", index=False, encoding="utf-8-sig")
    inventory_df.to_csv(index_dir / "全量来源索引.csv", index=False, encoding="utf-8-sig")

    stage = inventory_df.groupby(["stage", "extension"], dropna=False).agg(
        file_count=("relative_path", "count"), total_bytes=("size_bytes", "sum")
    ).reset_index().sort_values(["stage", "file_count"], ascending=[True, False])
    stage.to_csv(index_dir / "来源阶段与文件类型统计.csv", index=False, encoding="utf-8-sig")

    for src, dst in [
        (core / "跨距离漏斗汇总.csv", github_data / "span_summary.csv"),
        (core / "严格高于GGGGSGGGGS的候选.csv", github_data / "top_candidates_above_baseline.csv"),
        (supp / "在线批次_全候选级记录.csv", github_data / "all_candidate_records.csv"),
        (supp / "在线批次_全模型级记录.csv", github_data / "all_model_records.csv"),
        (index_dir / "全量来源索引.csv", OUTPUT_ROOT / "07_GitHub_ready" / "source_inventory.csv"),
    ]:
        shutil.copy2(src, dst)


def write_build_metadata(span_df, candidate_df, model_df, top_df, inventory_df):
    validation = read_json(PACKAGE_ROOT / "VALIDATION_REPORT.json")
    metadata = {
        "generated_at": "2026-09-30",
        "source_root": str(SOURCE_ROOT),
        "source_package_root": str(PACKAGE_ROOT),
        "package_validation_status": validation.get("status"),
        "source_inventory_rows": int(len(inventory_df)),
        "online_spans": span_df.target_span_A.astype(int).tolist(),
        "online_mpnn_unique_total": int(span_df.mpnn_unique.sum()),
        "online_boltz_model_total": int(span_df.boltz_models.sum()),
        "candidate_rows": int(len(candidate_df)),
        "model_rows": int(len(model_df)),
        "candidates_above_baseline": int(len(top_df)),
        "thresholds": {
            "linker_ca_rmsd_A": {"operator": "<", "value": 2.0, "required_models": 2, "models_total": 3},
            "online_vina_kcal_mol": {"operator": "<=", "value": -6.0, "required_models": 2, "models_total": 3},
            "early16_vina_kcal_mol": {"operator": "<=", "value": -7.0, "required_models": 2, "models_total": 3},
        },
    }
    path = OUTPUT_ROOT / "00_阅读说明" / "BUILD_METADATA.json"
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def write_workbook_payload(span_df, candidate_df, model_df, top_df, early_df, inventory_df):
    stage_df = inventory_df.groupby(["stage", "extension"], dropna=False).agg(
        file_count=("relative_path", "count"), total_bytes=("size_bytes", "sum")
    ).reset_index().sort_values(["stage", "file_count"], ascending=[True, False])
    payload = {
        "span_summary": json.loads(span_df.to_json(orient="records", force_ascii=False)),
        "top_candidates": json.loads(top_df.to_json(orient="records", force_ascii=False)),
        "all_candidates": json.loads(candidate_df.to_json(orient="records", force_ascii=False)),
        "all_models": json.loads(model_df.to_json(orient="records", force_ascii=False)),
        "early16": json.loads(early_df.to_json(orient="records", force_ascii=False)),
        "source_stage_summary": json.loads(stage_df.to_json(orient="records", force_ascii=False)),
        "source_inventory": json.loads(inventory_df.to_json(orient="records", force_ascii=False)),
    }
    (OUTPUT_ROOT / "00_阅读说明" / "workbook_payload.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def main():
    ensure_dirs()
    summaries, candidates, models = [], [], []
    for span in range(11, 21):
        s, c, m = parse_online_batch(span)
        summaries.append(s)
        candidates.extend(c)
        models.extend(m)

    early_summary, early_rows = parse_early16()
    inventory = build_source_inventory()
    span_df = pd.DataFrame(summaries).sort_values("target_span_A")
    candidate_df = pd.DataFrame(candidates).sort_values(["target_span_A", "candidate_type", "candidate_id"])
    model_df = pd.DataFrame(models).sort_values(["target_span_A", "candidate_id", "model_index"])
    early_df = pd.DataFrame(early_rows)
    inventory_df = pd.DataFrame(inventory)
    top_df = candidate_df[
        (candidate_df.candidate_type == "design")
        & candidate_df.final_score_median.notna()
        & (candidate_df.final_score_median > BASELINE_SCORE_ONLINE)
    ].sort_values("final_score_median", ascending=False).copy()

    write_csvs(span_df, candidate_df, model_df, top_df, early_df, inventory_df)
    write_readmes(span_df, candidate_df, top_df, inventory_df)
    write_build_metadata(span_df, candidate_df, model_df, top_df, inventory_df)
    write_workbook_payload(span_df, candidate_df, model_df, top_df, early_df, inventory_df)

    online16 = summaries[5]
    figure_paths = [
        fig_funnel(span_df),
        fig_scores(candidate_df),
        fig_top_candidates(top_df),
        fig_pass_rates(span_df),
        fig_sequence_qc(candidate_df),
        fig_16_comparison(early_summary, online16, early_rows, candidate_df[candidate_df.target_span_A == 16]),
        fig_evidence_hierarchy(),
    ]
    docx_path = build_docx(span_df, candidate_df, top_df, early_summary, online16, early_rows, figure_paths, inventory_df)
    print(json.dumps({
        "output_root": str(OUTPUT_ROOT),
        "docx": str(docx_path),
        "candidate_rows": len(candidate_df),
        "model_rows": len(model_df),
        "top_rows": len(top_df),
        "inventory_rows": len(inventory_df),
        "best_candidate": top_df.iloc[0][["target_span_A", "linker_sequence", "final_score_median"]].to_dict(),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
