from __future__ import annotations

import argparse
import csv
import sys
import urllib.request
from dataclasses import asdict
from pathlib import Path

import yaml

from .scoring import build_reference, score_candidate


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    required = ["reference", "sd40", "geometry", "scoring"]
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Missing config sections: {', '.join(missing)}")
    return config


def resolve(config_file: Path, configured_path: str) -> Path:
    path = Path(configured_path)
    return path if path.is_absolute() else config_file.parent / path


def cmd_prepare(args: argparse.Namespace) -> int:
    config_file = Path(args.config).resolve()
    config = load_config(config_file)
    destination = resolve(config_file, config["reference"]["path"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not args.force:
        print(f"Reference already exists: {destination}")
        return 0
    url = config["reference"]["download_url"]
    print(f"Downloading {config['reference']['pdb_id']} ...")
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
    if not data.startswith((b"HEADER", b"TITLE ", b"REMARK")):
        raise ValueError("Downloaded response does not look like a PDB file")
    destination.write_bytes(data)
    print(f"Saved: {destination}")
    return 0


def cmd_rank(args: argparse.Namespace) -> int:
    config_file = Path(args.config).resolve()
    config = load_config(config_file)
    reference_path = resolve(config_file, config["reference"]["path"])
    if not reference_path.exists():
        raise FileNotFoundError(f"Reference not found: {reference_path}; run 'prepare' first")
    reference = build_reference(reference_path, config)
    candidates_dir = Path(args.candidates).resolve()
    files = sorted(candidates_dir.glob("*.pdb"))
    if not files:
        raise FileNotFoundError(f"No .pdb files found in {candidates_dir}")

    results, errors = [], []
    for path in files:
        try:
            results.append(score_candidate(path, reference, config))
        except Exception as exc:
            errors.append({"candidate": path.stem, "error": f"{type(exc).__name__}: {exc}"})
    results.sort(key=lambda row: row.total_score, reverse=True)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["rank", "candidate", "total_score", "sd40_rmsd", "contact_recovery",
              "recovered_contacts", "reference_contacts", "clashing_atoms", "rmsd_score",
              "contact_score", "clash_score", "passed_filters", "sd40_chain", "sd40_coverage"]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rank, result in enumerate(results, 1):
            row = asdict(result)
            for key in ("total_score", "sd40_rmsd", "contact_recovery", "rmsd_score", "contact_score", "clash_score", "sd40_coverage"):
                row[key] = f"{row[key]:.4f}"
            writer.writerow({"rank": rank, **row})
    if errors:
        error_path = output.with_name(output.stem + "_errors.csv")
        with error_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["candidate", "error"])
            writer.writeheader(); writer.writerows(errors)
        print(f"Skipped {len(errors)} invalid file(s); details: {error_path}", file=sys.stderr)
    print(f"Reference contacts: {len(reference.contacts)}")
    print(f"Ranked {len(results)} candidate(s): {output}")
    return 0 if results else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sd40-linker-rank", description="Rank ADAR2-linker-SD40 PDB candidates")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Download the reference PDB")
    prepare.add_argument("--config", default="config.yaml")
    prepare.add_argument("--force", action="store_true")
    prepare.set_defaults(func=cmd_prepare)
    rank = sub.add_parser("rank", help="Score and rank candidate PDB files")
    rank.add_argument("--config", default="config.yaml")
    rank.add_argument("--candidates", default="candidates")
    rank.add_argument("--output", default="outputs/ranking.csv")
    rank.set_defaults(func=cmd_rank)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())

