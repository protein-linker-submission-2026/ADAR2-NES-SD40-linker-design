#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path


OUTPUT_FIELDS = [
    "candidate_id",
    "track",
    "target_span_A",
    "linker_sequence",
    "final_score_median",
    "score_minus_baseline",
    "rmsd_pass_count",
    "linker_rmsd_median_A",
    "vina_pass_count",
    "vina_median_kcal_mol",
    "sd40_rmsd_median_A",
    "confidence_median",
    "rf_backbone_pdb",
    "boltz_model_0_pdb",
    "boltz_model_1_pdb",
    "boltz_model_2_pdb",
    "model_versions",
    "notes",
]


def as_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("-inf")


def structure_paths(candidate_id: str, target_span: str) -> dict[str, str]:
    """Return package-relative structure paths for one formal candidate."""
    parts = candidate_id.split("_")
    if len(parts) < 4 or parts[1] != "design" or not parts[2].isdigit():
        raise ValueError(f"cannot derive backbone from candidate ID: {candidate_id}")

    span_dir = f"{target_span}A"
    design_id = "_".join(parts[:3])
    prediction_dir = (
        Path("results")
        / "structures"
        / "boltz2"
        / span_dir
        / candidate_id
        / f"boltz_results_{candidate_id}"
        / "predictions"
        / candidate_id
    )
    paths = {
        "rf_backbone_pdb": str(
            Path("results") / "structures" / "rfdiffusion" / span_dir / f"{design_id}.pdb"
        ).replace("\\", "/"),
    }
    for model_index in range(3):
        paths[f"boltz_model_{model_index}_pdb"] = str(
            prediction_dir / f"{candidate_id}_model_{model_index}.pdb"
        ).replace("\\", "/")
    return paths


def package_file_exists(relative: str) -> bool:
    path = (Path.cwd() / relative).resolve()
    if os.name == "nt":
        path = Path("\\\\?\\" + str(path))
    return path.is_file()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the standardized linker candidate result list.")
    parser.add_argument("--input", default="results/all_candidate_records.csv")
    parser.add_argument("--output", default="results/results.csv")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    selected = [
        row
        for row in rows
        if row.get("batch") == "online_mmseqs2"
        and row.get("candidate_type") == "design"
        and row.get("final_status") == "正式候选"
        and row.get("final_score_median") not in (None, "")
    ]
    selected.sort(key=lambda row: as_float(row.get("final_score_median", "")), reverse=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    versions = (
        "RFdiffusion 86507b6538f51fce57b5a72477165f03999ed7ae; "
        "ProteinMPNN 8907e6671bfbfc92303b5f79c4b5e6ce47cdef57; "
        "Boltz 2.2.1/Boltz-2; AutoDock Vina 1.1.2"
    )
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in selected:
            paths = structure_paths(row["candidate_id"], row["target_span_A"])
            missing = [relative for relative in paths.values() if not package_file_exists(relative)]
            if missing:
                raise FileNotFoundError(
                    f"candidate {row['candidate_id']} has missing structure files: {missing}"
                )
            writer.writerow(
                {
                    "candidate_id": row["candidate_id"],
                    "track": "赛道二：AI基因编辑与核酸工具设计",
                    "target_span_A": row["target_span_A"],
                    "linker_sequence": row["linker_sequence"],
                    "final_score_median": row["final_score_median"],
                    "score_minus_baseline": row["score_minus_baseline"],
                    "rmsd_pass_count": row["rmsd_pass_count"],
                    "linker_rmsd_median_A": row["linker_rmsd_median_A"],
                    "vina_pass_count": row["vina_pass_count"],
                    "vina_median_kcal_mol": row["vina_median_kcal_mol"],
                    "sd40_rmsd_median_A": row["sd40_rmsd_median_A"],
                    "confidence_median": row["confidence_median"],
                    **paths,
                    "model_versions": versions,
                    "notes": "Computational candidate; experimental validation required",
                }
            )

    print(f"Wrote {len(selected)} formal candidates to {output_path}")


if __name__ == "__main__":
    main()

