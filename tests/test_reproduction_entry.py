"""Local regression tests; no model downloads or external sequence submission."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pipeline_helper import baseline_row
from span_report import prepare_boltz_list, read_jsonl, write_jsonl
from collect_reproduction_results import RESULT_FIELDS, write_csv, runtime_versions


class ReproductionEntryTests(unittest.TestCase):
    def test_default_keeps_all_qc_designs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [dict(baseline_row(), candidate_id=f"design_{i}", candidate_type="design") for i in range(4)]
            write_jsonl(root / "07_sequence_qc/all_candidates.jsonl", rows)
            write_jsonl(root / "07_sequence_qc/baseline_candidate.jsonl", [baseline_row()])
            self.assertEqual(prepare_boltz_list(root)["candidates"], 5)

    def test_smoke_limits_design_not_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [dict(baseline_row(), candidate_id=f"design_{i}", candidate_type="design") for i in range(4)]
            write_jsonl(root / "07_sequence_qc/all_candidates.jsonl", rows)
            write_jsonl(root / "07_sequence_qc/baseline_candidate.jsonl", [baseline_row()])
            counts = prepare_boltz_list(root, 1)
            self.assertEqual(counts, {"candidates": 2, "design": 1, "baseline": 1})
            selected = read_jsonl(root / "08_boltz2_local/candidates_to_predict.jsonl")
            self.assertEqual(selected[0]["candidate_id"], "design_0")

    def test_smoke_rejects_baseline_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_jsonl(root / "07_sequence_qc/all_candidates.jsonl", [])
            write_jsonl(root / "07_sequence_qc/baseline_candidate.jsonl", [baseline_row()])
            with self.assertRaises(ValueError):
                prepare_boltz_list(root, 1)

    def test_empty_formal_results_keep_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.csv"
            write_csv(path, [], RESULT_FIELDS)
            with path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, RESULT_FIELDS)
                self.assertEqual(list(reader), [])

    def test_missing_runtime_snapshot_is_not_claimed_as_observed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertTrue(runtime_versions(root / '15', root).startswith('Runtime snapshot incomplete;'))

    @unittest.skipUnless(os.name == "nt", "PowerShell Windows entry test")
    def test_lightweight_entry_propagates_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            stub = Path(directory) / "fail-python.cmd"
            marker = Path(directory) / "invocations.txt"
            stub.write_text(f'@echo called>>"{marker}"\n@exit /b 7\n', encoding="ascii")
            result = subprocess.run([
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(ROOT / "run.ps1"), "-Python", str(stub),
            ], capture_output=True)
            self.assertEqual(result.returncode, 7, result.stderr)
            self.assertEqual(marker.read_text().splitlines(), ["called"])


if __name__ == "__main__":
    unittest.main()
