from pathlib import Path

import yaml

from sd40_linker_ranker.scoring import build_reference, score_candidate


def test_real_reference_loopback_if_present():
    root = Path(__file__).parents[1]
    ref = root / "reference" / "8TNQ.pdb"
    candidate = root / "examples" / "loopback_candidates" / "01_reference_like.pdb"
    if not ref.exists() or not candidate.exists():
        return
    config = yaml.safe_load((root / "config.yaml").read_text())
    context = build_reference(ref, config)
    result = score_candidate(candidate, context, config)
    assert context.sd40.coverage == 35 / 36
    assert result.sd40_rmsd < 1e-6
    assert result.contact_recovery == 1.0
    assert result.clashing_atoms == 0
    assert result.total_score > 99.99


def test_real_loopback_ranking_and_filters_if_present():
    root = Path(__file__).parents[1]
    ref = root / "reference" / "8TNQ.pdb"
    candidates = root / "examples" / "loopback_candidates"
    if not ref.exists() or not candidates.exists():
        return
    config = yaml.safe_load((root / "config.yaml").read_text())
    config["filters"]["enabled"] = True
    context = build_reference(ref, config)
    results = {p.stem: score_candidate(p, context, config) for p in candidates.glob("*.pdb") if "invalid" not in p.name}
    assert results["02b_chain_and_number_changed"].sd40_chain == "Q"
    assert results["02b_chain_and_number_changed"].total_score > 99.99
    assert results["03_mild_deformation"].passed_filters is True
    assert results["04_severe_deformation"].passed_filters is False
    assert results["05_artificial_clashes"].passed_filters is False
