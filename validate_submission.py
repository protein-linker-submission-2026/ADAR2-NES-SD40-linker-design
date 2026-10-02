#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED = [
    "README.md",
    "requirements.txt",
    "environment.yml",
    "predict.py",
    "MODEL_CARD.md",
    "DATA_SOURCES.md",
    "THIRD_PARTY_SOFTWARE.md",
    "SUBMISSION_COMPLIANCE.md",
    "JUDGES_GUIDE.md",
    "REPRODUCE_FROM_ZERO.md",
    "run_full.ps1",
    "data/README.md",
    "models/README.md",
    "notebooks/workflow_demo.ipynb",
    "src/run_full_pipeline.ps1",
    "src/run_single_span.sh",
    "src/collect_reproduction_results.py",
    "src/setup_external_sources.sh",
    "src/local_paths.example.sh",
    ".github/workflows/validate-submission.yml",
    "provenance/ATTACHMENT5_AUDIT_20261002.json",
    "results/results.xlsx",
    "results/results.csv",
    "results/all_candidate_records.csv",
    "results/all_model_records.csv",
    "results/top_candidates_above_baseline.csv",
    "results/span_summary.csv",
    "results/report.pdf",
    "provenance/source_inventory.csv",
]
FORBIDDEN = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"Wei-Shaw",
        r"scmc071578",
        r"zhz050503",
        r"[/\\]15242[/\\]",
        r"C:\\Users\\",
        r"/home/user",
        r"/mnt/[a-z]/",
        r"D:\\Download",
        r"E:\\01_中期结果",
        r"api[_-]?key\s*[:=]",
        r"password\s*[:=]",
    ]
]
TEXT_EXTENSIONS = {
    ".md", ".txt", ".csv", ".json", ".jsonl", ".yaml", ".yml",
    ".py", ".sh", ".ps1", ".ipynb",
}
OFFICE_EXTENSIONS = {".docx", ".xlsx", ".pptx"}


def csv_rows(relative: str) -> int:
    with (ROOT / relative).open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def package_file_exists(relative: str) -> bool:
    path = (ROOT / relative).resolve()
    if os.name == "nt":
        path = Path("\\\\?\\" + str(path))
    return path.is_file()


def scan_forbidden(text: str, label: str, errors: list[str]) -> None:
    for pattern in FORBIDDEN:
        if pattern.search(text):
            errors.append(f"possible identity/secret leak in {label}: {pattern.pattern}")


def main() -> None:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    expected_counts = {
        "results/all_candidate_records.csv": 302,
        "results/all_model_records.csv": 588,
        "results/top_candidates_above_baseline.csv": 22,
    }
    for relative, expected in expected_counts.items():
        path = ROOT / relative
        if path.is_file():
            actual = csv_rows(relative)
            if actual != expected:
                errors.append(f"unexpected row count for {relative}: {actual} != {expected}")

    pdb_count = len(list((ROOT / "results" / "structures" / "boltz2").rglob("*.pdb")))
    if pdb_count != 588:
        errors.append(f"unexpected Boltz-2 PDB count: {pdb_count} != 588")

    result_path = ROOT / "results" / "results.csv"
    if result_path.is_file():
        with result_path.open("r", encoding="utf-8-sig", newline="") as handle:
            result_rows = list(csv.DictReader(handle))
        structure_fields = [
            "rf_backbone_pdb",
            "boltz_model_0_pdb",
            "boltz_model_1_pdb",
            "boltz_model_2_pdb",
        ]
        if result_rows:
            missing_fields = [field for field in structure_fields if field not in result_rows[0]]
            if missing_fields:
                errors.append(f"results.csv missing structure fields: {missing_fields}")
            for row in result_rows:
                for field in structure_fields:
                    relative = row.get(field, "")
                    if not relative or Path(relative).is_absolute() or not package_file_exists(relative):
                        errors.append(
                            f"invalid structure mapping for {row.get('candidate_id', '?')} {field}: {relative}"
                        )
                        break

    # A local clone necessarily contains .git. GitHub source archives and the
    # competition ZIP generated from tracked files do not include it.

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        relative = str(path.relative_to(ROOT))
        scan_forbidden(relative, f"path {relative}", errors)
        suffix = path.suffix.lower()
        if suffix in TEXT_EXTENSIONS:
            try:
                text = path.read_text(encoding="utf-8-sig", errors="strict")
            except UnicodeError:
                continue
            scan_forbidden(text, relative, errors)
        elif suffix in OFFICE_EXTENSIONS:
            with zipfile.ZipFile(path) as package:
                for member in package.namelist():
                    if not member.endswith((".xml", ".rels")):
                        continue
                    text = package.read(member).decode("utf-8", errors="ignore")
                    scan_forbidden(text, f"{relative}:{member}", errors)
        elif suffix == ".pdf":
            text = path.read_bytes().decode("latin-1", errors="ignore")
            scan_forbidden(text, relative, errors)

    if errors:
        print("VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)
    print("VALIDATION PASS")
    print(f"candidate rows: {csv_rows('results/all_candidate_records.csv')}")
    print(f"model rows: {csv_rows('results/all_model_records.csv')}")
    print(f"above-baseline candidates: {csv_rows('results/top_candidates_above_baseline.csv')}")
    print(f"Boltz-2 PDB structures: {pdb_count}")


if __name__ == "__main__":
    main()

