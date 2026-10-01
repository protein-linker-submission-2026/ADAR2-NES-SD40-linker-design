from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


AA3_TO_1 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
    "MSE": "M",
}


@dataclass(frozen=True)
class Atom:
    record: str
    serial: int
    name: str
    altloc: str
    resname: str
    chain: str
    resseq: int
    icode: str
    xyz: np.ndarray
    element: str

    @property
    def residue_key(self) -> tuple[str, int, str, str]:
        return (self.chain, self.resseq, self.icode, self.resname)

    @property
    def is_heavy(self) -> bool:
        return self.element.upper() not in {"H", "D"}


@dataclass
class Residue:
    chain: str
    resseq: int
    icode: str
    resname: str
    atoms: list[Atom]

    @property
    def key(self) -> tuple[str, int, str, str]:
        return (self.chain, self.resseq, self.icode, self.resname)

    @property
    def one_letter(self) -> str:
        return AA3_TO_1.get(self.resname, "X")

    def atom(self, name: str) -> Atom | None:
        return next((a for a in self.atoms if a.name == name), None)


def _guess_element(atom_name: str) -> str:
    stripped = atom_name.strip()
    return "" if not stripped else stripped[0].upper()


def parse_pdb(path: str | Path) -> list[Atom]:
    """Parse the first PDB model, retaining blank/A altloc atoms."""
    atoms: list[Atom] = []
    saw_model = False
    with Path(path).open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            tag = line[:6].strip()
            if tag == "MODEL":
                if saw_model:
                    break
                saw_model = True
                continue
            if tag == "ENDMDL":
                break
            if tag not in {"ATOM", "HETATM"} or len(line) < 54:
                continue
            altloc = line[16:17].strip()
            if altloc not in {"", "A", "1"}:
                continue
            try:
                atom = Atom(
                    record=tag,
                    serial=int(line[6:11]),
                    name=line[12:16].strip(),
                    altloc=altloc,
                    resname=line[17:20].strip().upper(),
                    chain=line[21:22].strip(),
                    resseq=int(line[22:26]),
                    icode=line[26:27].strip(),
                    xyz=np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])]),
                    element=(line[76:78].strip() if len(line) >= 78 else "") or _guess_element(line[12:16]),
                )
            except ValueError as exc:
                raise ValueError(f"Malformed coordinate record in {path}: {line.rstrip()}") from exc
            atoms.append(atom)
    if not atoms:
        raise ValueError(f"No ATOM/HETATM coordinates found in {path}")
    return atoms


def residues_from_atoms(atoms: Iterable[Atom], protein_only: bool = True) -> list[Residue]:
    residues: list[Residue] = []
    lookup: dict[tuple[str, int, str, str], Residue] = {}
    for atom in atoms:
        if protein_only and atom.record != "ATOM":
            continue
        key = atom.residue_key
        if key not in lookup:
            lookup[key] = Residue(atom.chain, atom.resseq, atom.icode, atom.resname, [])
            residues.append(lookup[key])
        lookup[key].atoms.append(atom)
    return residues


@dataclass
class SequenceMatch:
    residues: list[Residue]
    target_indices: list[int]
    coverage: float
    chain: str


def _best_contiguous_match(chain_residues: list[Residue], target: str) -> tuple[int, int, int]:
    """Return chain start, target start and longest exact contiguous length."""
    seq = "".join(r.one_letter for r in chain_residues)
    best = (0, 0, 0)
    for i in range(len(seq)):
        for j in range(len(target)):
            k = 0
            while i + k < len(seq) and j + k < len(target) and seq[i + k] == target[j + k]:
                k += 1
            if k > best[2]:
                best = (i, j, k)
    return best


def locate_sequence(
    atoms: Iterable[Atom], target: str, min_coverage: float = 0.85, chain_hint: str | None = None
) -> SequenceMatch:
    """Locate an exact sequence or a long resolved contiguous portion of it.

    The fallback is important for experimental PDB structures with unresolved
    terminal residues (8TNQ chain C lacks the first target leucine in ATOM records).
    """
    residues = residues_from_atoms(atoms)
    by_chain: dict[str, list[Residue]] = {}
    for residue in residues:
        by_chain.setdefault(residue.chain, []).append(residue)
    if chain_hint is not None:
        by_chain = {chain_hint: by_chain.get(chain_hint, [])}

    matches: list[SequenceMatch] = []
    for chain, chain_residues in by_chain.items():
        seq = "".join(r.one_letter for r in chain_residues)
        start = seq.find(target)
        if start >= 0:
            matches.append(SequenceMatch(chain_residues[start:start + len(target)], list(range(len(target))), 1.0, chain))
            continue
        chain_start, target_start, length = _best_contiguous_match(chain_residues, target)
        coverage = length / len(target)
        if coverage >= min_coverage:
            matches.append(SequenceMatch(
                chain_residues[chain_start:chain_start + length],
                list(range(target_start, target_start + length)), coverage, chain
            ))
    if not matches:
        hint = f" in chain {chain_hint!r}" if chain_hint is not None else ""
        raise ValueError(f"SD40 sequence not found{hint} at >= {min_coverage:.0%} coverage")
    matches.sort(key=lambda m: (m.coverage, len(m.residues)), reverse=True)
    if len(matches) > 1 and matches[0].coverage == matches[1].coverage:
        raise ValueError(f"SD40 sequence is ambiguous: equal matches in chains {matches[0].chain!r} and {matches[1].chain!r}")
    return matches[0]


def heavy_atoms(residues: Iterable[Residue]) -> list[Atom]:
    return [atom for residue in residues for atom in residue.atoms if atom.is_heavy]

