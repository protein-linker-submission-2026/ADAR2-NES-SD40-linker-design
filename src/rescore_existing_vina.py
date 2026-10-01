#!/usr/bin/env python3
"""Re-evaluate existing Vina scores with the current -6 kcal/mol gate.

This deliberately writes derived JSON files and never changes the original
10_docking JSON/log/PDBQT files.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

VINA_SCORE_CUTOFF = -6.0


def rescore(root: Path, output_dir: Path | None = None) -> dict:
    source = root / "10_docking"
    target = output_dir or (root / "05_reports" / "vina_rescored_minus6")
    target.mkdir(parents=True, exist_ok=True)
    count = 0
    for src in sorted(source.glob("*.json")):
        data = json.loads(src.read_text(encoding="utf-8"))
        models = data.get("models", [])
        scores = [float(m["vina_best_score_kcal_mol"]) for m in models]
        if len(scores) != 3:
            raise ValueError(f"{src.name}: expected 3 Vina model scores, got {len(scores)}")
        passed = [score <= VINA_SCORE_CUTOFF for score in scores]
        for model, ok in zip(models, passed):
            model["vina_model_pass_minus6"] = ok
        data["vina_gate_minus6"] = {
            "model_pass": passed,
            "pass_count": sum(passed),
            "required": 2,
            "candidate_pass": sum(passed) >= 2,
            "operator": "<=",
            "threshold_kcal_mol": VINA_SCORE_CUTOFF,
            "source_json": str(src),
        }
        (target / src.name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        count += 1
    manifest = {
        "status": "ok",
        "source": str(source),
        "derived_output": str(target),
        "threshold_kcal_mol": VINA_SCORE_CUTOFF,
        "required_models": 2,
        "models_per_candidate": 3,
        "candidate_files": count,
        "original_files_modified": False,
    }
    (target / "rescore_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path)
    args = ap.parse_args()
    print(json.dumps(rescore(args.root, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
