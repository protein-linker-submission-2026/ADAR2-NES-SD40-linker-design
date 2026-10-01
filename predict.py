#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
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
    "model_versions",
    "notes",
]


def as_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("-inf")


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
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in selected:
            writer.writerow(
                {
                    "candidate_id": row["candidate_id"],
                    "track": "AI gene editing and nucleic acid tool design",
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
                    "model_versions": versions,
                    "notes": "Computational candidate; experimental validation required",
                }
            )

    print(f"Wrote {len(selected)} formal candidates to {output_path}")


if __name__ == "__main__":
    main()

