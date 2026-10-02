#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from pathlib import Path


VERSIONS = (
    "RFdiffusion 86507b6538f51fce57b5a72477165f03999ed7ae; "
    "ProteinMPNN 8907e6671bfbfc92303b5f79c4b5e6ce47cdef57; "
    "Boltz 2.2.1/Boltz-2; AutoDock Vina 1.1.2"
)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def median(values):
    clean = [float(value) for value in values if value is not None]
    return statistics.median(clean) if clean else None


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None):
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def relative(path: Path, root: Path):
    return path.absolute().relative_to(root.absolute()).as_posix()


def confidence(span_root: Path, candidate: str, model_index: int):
    matches = list(
        (span_root / "08_boltz2_local" / "outputs").glob(
            f"{candidate}/**/confidence_{candidate}_model_{model_index}.json"
        )
    )
    if not matches:
        return None
    return number(read_json(matches[0]).get("confidence_score"))


def load_ranker(path: Path):
    output = {}
    for row in read_csv(path):
        match = re.fullmatch(r"(.+)_model(\d+)", row.get("candidate", ""))
        if match:
            output[(match.group(1), int(match.group(2)))] = row
    return output


def main():
    parser = argparse.ArgumentParser(description="Collect a fresh full-pipeline run into standard result tables.")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--spans", default="11,12,13,14,15,16,17,18,19,20")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    run_root = args.run_root.resolve()
    output = (args.output_dir or run_root / "final").resolve()
    output.mkdir(parents=True, exist_ok=True)
    spans = [int(value) for value in args.spans.split(",") if value.strip()]

    candidate_rows = []
    model_rows = []
    summary_rows = []
    formal_rows = []

    for span in spans:
        root = run_root / str(span)
        required = [
            root / "05_reports" / f"span{span}A_summary.json",
            root / "05_reports" / "sequence_rows.json",
            root / "07_sequence_qc" / "sequence_qc.csv",
            root / "11_ranker" / "ranking.csv",
        ]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"span {span} is incomplete: {missing}")

        summary = read_json(required[0])
        summary_rows.append({"batch": "online_mmseqs2", "target_span_A": span, **summary})
        sequences = read_json(required[1])
        qc = {row["candidate_id"]: row for row in read_csv(required[2])}
        ranking = load_ranker(required[3])
        rmsd = {path.stem: read_json(path) for path in (root / "09_rmsd_gate_local").glob("*.json")}
        docking = {path.stem: read_json(path) for path in (root / "10_docking").glob("*.json")}
        baseline = next(
            (number(row.get("方案B中位数")) for row in sequences if row.get("候选ID") == "baseline_GGGGSGGGGS"),
            None,
        )

        for sequence in sequences:
            candidate = sequence.get("候选ID")
            if not candidate:
                continue
            candidate_type = "baseline" if candidate == "baseline_GGGGSGGGGS" else "design"
            rmsd_record = rmsd.get(candidate, {})
            dock_record = docking.get(candidate, {})
            rmsd_models = {int(row["model_index"]): row for row in rmsd_record.get("models", [])}
            dock_models = {int(row["model_index"]): row for row in dock_record.get("models", [])}
            per_candidate = []

            model_indices = sorted(
                set(rmsd_models)
                | set(dock_models)
                | {index for cid, index in ranking if cid == candidate}
            )
            for model_index in model_indices:
                rm = rmsd_models.get(model_index, {})
                dm = dock_models.get(model_index, {})
                rank = ranking.get((candidate, model_index), {})
                row = {
                    "batch": "online_mmseqs2",
                    "target_span_A": span,
                    "candidate_id": candidate,
                    "candidate_type": candidate_type,
                    "linker_sequence": sequence.get("Linker序列"),
                    "model_index": model_index,
                    "linker_ca_rmsd_A": number(rm.get("linker_ca_rmsd_A")),
                    "rmsd_model_pass": rm.get("rf_rmsd_pass"),
                    "vina_best_score_kcal_mol": number(dm.get("vina_best_score_kcal_mol")),
                    "vina_model_pass": dm.get("vina_model_pass"),
                    "total_score": number(rank.get("total_score")),
                    "sd40_rmsd_A": number(rank.get("sd40_rmsd")),
                    "contact_recovery": number(rank.get("contact_recovery")),
                    "clashing_atoms": number(rank.get("clashing_atoms")),
                    "confidence_score": confidence(root, candidate, model_index),
                }
                model_rows.append(row)
                per_candidate.append(row)

            final_score = number(sequence.get("方案B中位数"))
            q = qc.get(candidate, {})
            candidate_row = {
                "batch": "online_mmseqs2",
                "target_span_A": span,
                "candidate_id": candidate,
                "candidate_type": candidate_type,
                "linker_sequence": sequence.get("Linker序列"),
                "final_status": sequence.get("最终状态"),
                "final_score_median": final_score,
                "score_minus_baseline": None if final_score is None or baseline is None else final_score - baseline,
                "qc_pass": q.get("qc_pass"),
                "qc_reasons": q.get("reasons"),
                "rmsd_pass_count": rmsd_record.get("rf_rmsd_gate", {}).get("pass_count"),
                "linker_rmsd_median_A": median(row["linker_ca_rmsd_A"] for row in per_candidate),
                "vina_pass_count": dock_record.get("vina_gate", {}).get("pass_count"),
                "vina_median_kcal_mol": median(row["vina_best_score_kcal_mol"] for row in per_candidate),
                "sd40_rmsd_median_A": median(row["sd40_rmsd_A"] for row in per_candidate),
                "confidence_median": median(row["confidence_score"] for row in per_candidate),
            }
            candidate_rows.append(candidate_row)

            if candidate_type != "design" or sequence.get("最终状态") != "正式候选" or final_score is None:
                continue
            design_match = re.match(r"(span\d+A_design_\d+)_", candidate)
            if not design_match:
                raise ValueError(f"cannot map candidate to RF backbone: {candidate}")
            rf_path = root / "03_rfdiffusion_validated" / f"{design_match.group(1)}.pdb"
            boltz_paths = []
            for model_index in range(3):
                matches = list((root / "08_boltz2_local" / "outputs" / candidate).glob(f"**/{candidate}_model_{model_index}.pdb"))
                if len(matches) != 1:
                    raise FileNotFoundError(f"expected one Boltz model for {candidate} model {model_index}, found {len(matches)}")
                boltz_paths.append(relative(matches[0], run_root))
            if not rf_path.is_file():
                raise FileNotFoundError(rf_path)
            formal_rows.append({
                "candidate_id": candidate,
                "track": "赛道二：AI基因编辑与核酸工具设计",
                "target_span_A": span,
                "linker_sequence": sequence.get("Linker序列"),
                "final_score_median": final_score,
                "score_minus_baseline": candidate_row["score_minus_baseline"],
                "rmsd_pass_count": candidate_row["rmsd_pass_count"],
                "linker_rmsd_median_A": candidate_row["linker_rmsd_median_A"],
                "vina_pass_count": candidate_row["vina_pass_count"],
                "vina_median_kcal_mol": candidate_row["vina_median_kcal_mol"],
                "sd40_rmsd_median_A": candidate_row["sd40_rmsd_median_A"],
                "confidence_median": candidate_row["confidence_median"],
                "rf_backbone_pdb": relative(rf_path, run_root),
                "boltz_model_0_pdb": boltz_paths[0],
                "boltz_model_1_pdb": boltz_paths[1],
                "boltz_model_2_pdb": boltz_paths[2],
                "model_versions": VERSIONS,
                "notes": "Computational candidate; experimental validation required",
            })

    formal_rows.sort(key=lambda row: row["final_score_median"], reverse=True)
    write_csv(output / "results.csv", formal_rows)
    write_csv(output / "all_candidate_records.csv", candidate_rows)
    write_csv(output / "all_model_records.csv", model_rows)
    write_csv(output / "span_summary.csv", summary_rows)

    try:
        from openpyxl import Workbook
        workbook = Workbook()
        workbook.remove(workbook.active)
        for title, rows in (("results", formal_rows), ("all_candidates", candidate_rows), ("all_models", model_rows), ("span_summary", summary_rows)):
            sheet = workbook.create_sheet(title)
            if rows:
                sheet.append(list(rows[0]))
                for row in rows:
                    values = []
                    for field in rows[0]:
                        value = row.get(field)
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
                        values.append(value)
                    sheet.append(values)
        workbook.save(output / "results.xlsx")
    except ImportError:
        pass

    print(json.dumps({
        "status": "ok",
        "spans": spans,
        "formal_candidates": len(formal_rows),
        "candidate_records": len(candidate_rows),
        "model_records": len(model_rows),
        "results_csv": str(output / "results.csv"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
