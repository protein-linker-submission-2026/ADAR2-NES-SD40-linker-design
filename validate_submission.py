#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import sys
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
        r"C:\\Users\\",
        r"/home/user",
        r"D:\\Download",
        r"E:\\01_中期结果",
        r"api[_-]?key\s*[:=]",
        r"password\s*[:=]",
    ]
]
TEXT_EXTENSIONS = {".md", ".txt", ".csv", ".json", ".jsonl", ".yaml", ".yml", ".py", ".sh", ".ps1"}


def csv_rows(relative: str) -> int:
    with (ROOT / relative).open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


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

    if (ROOT / ".git").exists():
        errors.append(".git history must not be included in the anonymous submission")

    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        try:
            text = path.read_text(encoding="utf-8-sig", errors="strict")
        except UnicodeError:
            continue
        for pattern in FORBIDDEN:
            if pattern.search(text):
                errors.append(f"possible identity/secret leak in {path.relative_to(ROOT)}: {pattern.pattern}")

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

