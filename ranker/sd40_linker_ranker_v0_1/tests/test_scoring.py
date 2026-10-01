from pathlib import Path

import numpy as np

from sd40_linker_ranker.pdb_utils import Atom, locate_sequence
from sd40_linker_ranker.scoring import kabsch, transform


def atom(serial, name, resname, chain, resseq, xyz):
    return Atom("ATOM", serial, name, "", resname, chain, resseq, "", np.array(xyz, dtype=float), name[0])


def test_kabsch_recovers_rigid_transform():
    rng = np.random.default_rng(7)
    target = rng.normal(size=(20, 3))
    q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    if np.linalg.det(q) < 0:
        q[:, 0] *= -1
    mobile = target @ q + np.array([4.0, -2.0, 8.0])
    r, t = kabsch(mobile, target)
    assert np.sqrt(np.mean(np.sum((transform(mobile, r, t) - target) ** 2, axis=1))) < 1e-10


def test_sequence_locator_accepts_missing_terminal_residue_and_renumbering():
    names = {"L":"LEU", "F":"PHE", "C":"CYS", "P":"PRO", "I":"ILE", "G":"GLY", "T":"THR", "R":"ARG", "Q":"GLN", "K":"LYS", "N":"ASN", "H":"HIS", "E":"GLU", "Y":"TYR"}
    target = "LLLFCPICGFTCRQKGNLLRHINLHTGEKLFKYHLY"
    observed = target[1:]
    atoms = [atom(i, "CA", names[aa], "Z", 700 + i, [i, 0, 0]) for i, aa in enumerate(observed, 1)]
    match = locate_sequence(atoms, target, min_coverage=0.85)
    assert match.chain == "Z"
    assert match.target_indices[0] == 1
    assert match.coverage == len(observed) / len(target)


def test_sequence_locator_rejects_unrelated_sequence():
    atoms = [atom(i, "CA", "ALA", "A", i, [i, 0, 0]) for i in range(40)]
    try:
        locate_sequence(atoms, "LLLFCPICGFTCRQKGNLLRHINLHTGEKLFKYHLY")
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

