"""Generate deterministic good/medium/bad candidates from a real 8TNQ PDB.

This is a geometric loopback fixture generator, not a biological structure
prediction workflow. It is included so the validation can be reproduced.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def change_xyz(line: str, xyz: np.ndarray, serial: int | None = None) -> str:
    line = line.rstrip("\n").ljust(80)
    if serial is not None:
        line = line[:6] + f"{serial:5d}" + line[11:]
    return line[:30] + f"{xyz[0]:8.3f}{xyz[1]:8.3f}{xyz[2]:8.3f}" + line[54:] + "\n"


def xyz(line: str) -> np.ndarray:
    return np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])])


def write_candidate(path: Path, sd40_lines: list[str], transform_fn, extras: list[str] | None = None):
    output = []
    for serial, line in enumerate(sd40_lines, 1):
        output.append(change_xyz(line, transform_fn(xyz(line)), serial))
    if extras:
        output.extend(extras)
    output.append("END\n")
    path.write_text("".join(output))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reference")
    parser.add_argument("output_dir")
    args = parser.parse_args()
    reference = Path(args.reference)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    lines = reference.read_text(errors="replace").splitlines(keepends=True)
    sd40 = [line for line in lines if line.startswith("ATOM") and line[21:22] == "C"]
    crbn = [line for line in lines if line.startswith("ATOM") and line[21:22] == "B" and line[12:16].strip() != "H"]
    if not sd40 or not crbn:
        raise SystemExit("Reference must contain ATOM records in chains B and C")

    identity = lambda p: p
    theta = np.deg2rad(57.0)
    rotation = np.array([[np.cos(theta), -np.sin(theta), 0], [np.sin(theta), np.cos(theta), 0], [0, 0, 1]])
    rigid = lambda p: p @ rotation + np.array([35.0, -21.0, 12.0])
    rng_mild = np.random.default_rng(1001)
    rng_severe = np.random.default_rng(2002)
    mild_noise = {i: rng_mild.normal(0, 0.45, 3) for i in range(len(sd40))}
    severe_noise = {i: rng_severe.normal(0, 2.2, 3) for i in range(len(sd40))}

    write_candidate(out / "01_reference_like.pdb", sd40, identity)
    write_candidate(out / "02_rigid_body_moved.pdb", sd40, rigid)
    renumbered = []
    for line in sd40:
        new_resseq = int(line[22:26]) + 500
        renumbered.append(line[:21] + "Q" + f"{new_resseq:4d}" + line[26:])
    write_candidate(out / "02b_chain_and_number_changed.pdb", renumbered, identity)

    idx = iter(range(len(sd40)))
    write_candidate(out / "03_mild_deformation.pdb", sd40, lambda p: p + mild_noise[next(idx)])
    idx = iter(range(len(sd40)))
    write_candidate(out / "04_severe_deformation.pdb", sd40, lambda p: p + severe_noise[next(idx)])

    extras = []
    start_serial = len(sd40) + 1
    # 24 non-SD40 CA atoms placed exactly on selected CRBN heavy atoms.
    for i, source in enumerate(crbn[::max(1, len(crbn) // 24)][:24]):
        p = xyz(source)
        serial = start_serial + i
        extras.append(
            f"ATOM  {serial:5d}  CA  ALA Z{900+i:4d}    {p[0]:8.3f}{p[1]:8.3f}{p[2]:8.3f}  1.00 20.00           C  \n"
        )
    write_candidate(out / "05_artificial_clashes.pdb", sd40, identity, extras)

    invalid = []
    for i in range(40):
        p = np.array([float(i) * 3.8, 0.0, 0.0])
        invalid.append(f"ATOM  {i+1:5d}  CA  ALA X{i+1:4d}    {p[0]:8.3f}{p[1]:8.3f}{p[2]:8.3f}  1.00 20.00           C  \n")
    (out / "06_invalid_no_sd40.pdb").write_text("".join(invalid) + "END\n")


if __name__ == "__main__":
    main()
