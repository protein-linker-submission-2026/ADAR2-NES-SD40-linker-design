from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .pdb_utils import Atom, Residue, SequenceMatch, heavy_atoms, locate_sequence, parse_pdb, residues_from_atoms


@dataclass
class ReferenceContext:
    atoms: list[Atom]
    sd40: SequenceMatch
    crbn_residues: list[Residue]
    receptor_atoms: list[Atom]
    contacts: set[tuple[int, tuple[str, int, str, str]]]


@dataclass
class ScoreResult:
    candidate: str
    total_score: float
    sd40_rmsd: float
    contact_recovery: float
    recovered_contacts: int
    reference_contacts: int
    clashing_atoms: int
    rmsd_score: float
    contact_score: float
    clash_score: float
    passed_filters: bool | None
    sd40_chain: str
    sd40_coverage: float


def kabsch(mobile: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if mobile.shape != target.shape or mobile.ndim != 2 or mobile.shape[1] != 3:
        raise ValueError("Kabsch inputs must have matching N x 3 shapes")
    if len(mobile) < 3:
        raise ValueError("At least three paired atoms are required for alignment")
    mob_center = mobile.mean(axis=0)
    tar_center = target.mean(axis=0)
    covariance = (mobile - mob_center).T @ (target - tar_center)
    u, _, vt = np.linalg.svd(covariance)
    correction = np.eye(3)
    correction[-1, -1] = np.sign(np.linalg.det(u @ vt))
    rotation = u @ correction @ vt
    translation = tar_center - mob_center @ rotation
    return rotation, translation


def transform(coords: np.ndarray, rotation: np.ndarray, translation: np.ndarray) -> np.ndarray:
    return coords @ rotation + translation


def _min_distance(coords_a: np.ndarray, coords_b: np.ndarray, block: int = 2000) -> float:
    best = np.inf
    for start in range(0, len(coords_a), block):
        delta = coords_a[start:start + block, None, :] - coords_b[None, :, :]
        best = min(best, float(np.sqrt(np.min(np.sum(delta * delta, axis=2)))))
    return best


def _has_contact(atoms_a: list[Atom], atoms_b: list[Atom], cutoff: float) -> bool:
    if not atoms_a or not atoms_b:
        return False
    a = np.array([x.xyz for x in atoms_a if x.is_heavy])
    b = np.array([x.xyz for x in atoms_b if x.is_heavy])
    return bool(len(a) and len(b) and _min_distance(a, b) <= cutoff)


def build_reference(path: str | Path, config: dict) -> ReferenceContext:
    atoms = parse_pdb(path)
    target = config["sd40"]["sequence"]
    min_cov = float(config["sd40"].get("min_sequence_coverage", 0.85))
    sd40 = locate_sequence(atoms, target, min_cov, config["reference"]["sd40_chain"])
    residues = residues_from_atoms(atoms)
    crbn_chain = config["reference"]["crbn_chain"]
    crbn = [r for r in residues if r.chain == crbn_chain]
    if not crbn:
        raise ValueError(f"No protein residues found for CRBN chain {crbn_chain!r}")
    ligand_name = config["reference"]["ligand_resname"].upper()
    receptor_atoms = [
        a for a in atoms
        if a.is_heavy and ((a.record == "ATOM" and a.chain == crbn_chain) or a.resname == ligand_name)
    ]
    cutoff = float(config["geometry"]["contact_cutoff_angstrom"])
    contacts: set[tuple[int, tuple[str, int, str, str]]] = set()
    for target_idx, sd_residue in zip(sd40.target_indices, sd40.residues):
        for crbn_residue in crbn:
            if _has_contact(sd_residue.atoms, crbn_residue.atoms, cutoff):
                contacts.add((target_idx, crbn_residue.key))
    if not contacts:
        raise ValueError("Reference contains no SD40-CRBN contacts at the configured cutoff")
    return ReferenceContext(atoms, sd40, crbn, receptor_atoms, contacts)


def _paired_ca(candidate: SequenceMatch, reference: SequenceMatch) -> tuple[np.ndarray, np.ndarray]:
    cand_by_idx = {i: r for i, r in zip(candidate.target_indices, candidate.residues)}
    ref_by_idx = {i: r for i, r in zip(reference.target_indices, reference.residues)}
    common = sorted(set(cand_by_idx) & set(ref_by_idx))
    mobile, target = [], []
    for idx in common:
        ca_c = cand_by_idx[idx].atom("CA")
        ca_r = ref_by_idx[idx].atom("CA")
        if ca_c is not None and ca_r is not None:
            mobile.append(ca_c.xyz)
            target.append(ca_r.xyz)
    if len(mobile) < 3:
        raise ValueError("Fewer than three common SD40 CA atoms are available")
    return np.array(mobile), np.array(target)


def _transformed_residue_atoms(residue: Residue, rotation: np.ndarray, translation: np.ndarray) -> np.ndarray:
    coords = np.array([a.xyz for a in residue.atoms if a.is_heavy])
    return transform(coords, rotation, translation) if len(coords) else coords


def score_candidate(path: str | Path, reference: ReferenceContext, config: dict) -> ScoreResult:
    atoms = parse_pdb(path)
    min_cov = float(config["sd40"].get("min_sequence_coverage", 0.85))
    sd40 = locate_sequence(atoms, config["sd40"]["sequence"], min_cov)
    mobile, target = _paired_ca(sd40, reference.sd40)
    rotation, translation = kabsch(mobile, target)
    fitted = transform(mobile, rotation, translation)
    rmsd = float(np.sqrt(np.mean(np.sum((fitted - target) ** 2, axis=1))))

    cand_by_idx = {i: r for i, r in zip(sd40.target_indices, sd40.residues)}
    crbn_by_key = {r.key: r for r in reference.crbn_residues}
    cutoff = float(config["geometry"]["contact_cutoff_angstrom"])
    recovered = 0
    for target_idx, crbn_key in reference.contacts:
        cand_res = cand_by_idx.get(target_idx)
        crbn_res = crbn_by_key[crbn_key]
        if cand_res is None:
            continue
        c = _transformed_residue_atoms(cand_res, rotation, translation)
        r = np.array([a.xyz for a in crbn_res.atoms if a.is_heavy])
        if len(c) and len(r) and _min_distance(c, r) <= cutoff:
            recovered += 1
    contact_recovery = recovered / len(reference.contacts)

    sd40_keys = {r.key for r in sd40.residues}
    other = [a for a in atoms if a.is_heavy and a.residue_key not in sd40_keys]
    clashing = 0
    if other and reference.receptor_atoms:
        other_coords = transform(np.array([a.xyz for a in other]), rotation, translation)
        receptor_coords = np.array([a.xyz for a in reference.receptor_atoms])
        cutoff2 = float(config["geometry"]["clash_cutoff_angstrom"]) ** 2
        for start in range(0, len(other_coords), 1000):
            delta = other_coords[start:start + 1000, None, :] - receptor_coords[None, :, :]
            clashing += int(np.sum(np.any(np.sum(delta * delta, axis=2) < cutoff2, axis=1)))

    score_cfg = config["scoring"]
    rmsd_score = 1.0 / (1.0 + (rmsd / float(score_cfg["rmsd_scale_angstrom"])) ** 2)
    clash_score = 1.0 / (1.0 + clashing / float(score_cfg["clash_scale_atoms"]))
    weights = score_cfg["weights"]
    weight_sum = sum(float(weights[k]) for k in ("rmsd", "contact", "clash"))
    if weight_sum <= 0:
        raise ValueError("Scoring weights must sum to a positive value")
    total = 100.0 * (
        float(weights["rmsd"]) * rmsd_score
        + float(weights["contact"]) * contact_recovery
        + float(weights["clash"]) * clash_score
    ) / weight_sum

    filters = config.get("filters", {})
    passed = None
    if filters.get("enabled", False):
        passed = (
            rmsd <= float(filters["max_rmsd_angstrom"])
            and contact_recovery >= float(filters["min_contact_recovery"])
            and clashing <= int(filters["max_clashing_atoms"])
        )
    return ScoreResult(
        candidate=Path(path).stem, total_score=total, sd40_rmsd=rmsd,
        contact_recovery=contact_recovery, recovered_contacts=recovered,
        reference_contacts=len(reference.contacts), clashing_atoms=clashing,
        rmsd_score=rmsd_score, contact_score=contact_recovery, clash_score=clash_score,
        passed_filters=passed, sd40_chain=sd40.chain, sd40_coverage=sd40.coverage,
    )
