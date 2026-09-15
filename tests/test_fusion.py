import pytest
from three_maps.domain.types import SystemScore, SystemScoreStatus, RelationshipState
from three_maps.engines.fusion import FusionInput, FusionContext, calculate_fusion, calculate_fusion_result


def ss(system, score, status=SystemScoreStatus.EVALUATED, coverage=1.0, confidence=1.0):
    return SystemScore(system=system, score=score, status=status, coverage=coverage,
                       data_confidence=confidence, valid_indicator_count=1, expected_indicator_count=1)


def test_legacy_formula():
    assert calculate_fusion(FusionInput(.68,.10,.05)) == 83.0


def test_golden_fusion_values():
    systems = (ss("ASTROLOGY", .73125, confidence=.90), ss("NUMEROLOGY", .69010067, confidence=.86), ss("PALMISTRY", .62710674, confidence=.85))
    r = calculate_fusion_result(FusionContext(systems, relationship_state=RelationshipState.S7,
        meaningful_system_count=3, independence=.75, contradiction_strength=.48558707))
    assert r.base == pytest.approx(.6828191367, abs=1e-8)
    assert r.convergence_bonus == pytest.approx(.1365638273, abs=1e-8)
    assert r.independence_bonus == pytest.approx(.0512114353, abs=1e-8)
    assert r.contradiction_penalty == pytest.approx(.097117414, abs=1e-8)
    assert r.final_score == pytest.approx(77.3476985, abs=1e-5)
    assert r.label == "HIGH"


def test_unavailable_is_omitted():
    r = calculate_fusion_result(FusionContext((ss("A", .8), ss("B", None, SystemScoreStatus.UNAVAILABLE))))
    assert r.base == .8 and r.valid_system_count == 1


def test_invalid_is_omitted():
    r = calculate_fusion_result(FusionContext((ss("A", .8), ss("B", None, SystemScoreStatus.INVALID))))
    assert r.base == .8 and r.valid_system_count == 1


def test_partial_is_score_bearing():
    r = calculate_fusion_result(FusionContext((ss("A", .8, coverage=.5),)))
    assert r.base == .8 and r.final_score == 80.0


def test_partial_coverage_does_not_penalize_score():
    full = calculate_fusion_result(FusionContext((ss("A", .8, coverage=1),)))
    partial = calculate_fusion_result(FusionContext((ss("A", .8, coverage=.2),)))
    assert partial.final_score == full.final_score
    assert partial.coverage < full.coverage


def test_s6_has_no_contradiction_penalty():
    r = calculate_fusion_result(FusionContext((ss("A", .7), ss("B", .7)), RelationshipState.S6, independence=0, contradiction_strength=.9))
    assert r.contradiction_penalty == 0


def test_s7_has_penalty():
    r = calculate_fusion_result(FusionContext((ss("A", .7),), RelationshipState.S7, contradiction_strength=.5))
    assert r.contradiction_penalty == .1


def test_independence_bonus_is_bounded():
    r0 = calculate_fusion_result(FusionContext((ss("A", .6),), independence=0))
    r1 = calculate_fusion_result(FusionContext((ss("A", .6),), independence=1))
    assert r1.final_score > r0.final_score


def test_all_unavailable_no_numeric_contribution():
    r = calculate_fusion_result(FusionContext((ss("A", None, SystemScoreStatus.UNAVAILABLE),)))
    assert r.final_score == 0 and r.data_confidence == 0
