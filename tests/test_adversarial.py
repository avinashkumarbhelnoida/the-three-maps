import pytest
from pydantic import ValidationError

from three_maps.domain.types import (
    ApplicabilityState, ActivationState, RelationshipState, Signal, SystemScore,
    SystemScoreStatus, Target,
)
from three_maps.engines.relationship import RelationshipInput, RelationshipSystem, evaluate_relationship
from three_maps.engines.contradiction import ContradictionInput, evaluate_contradiction
from three_maps.engines.fusion import FusionContext, calculate_fusion_result


def _target():
    return Target(theme_id="T1", sub_theme_id="ST1", axis_id="A01", semantic_level="AXIS")


def _sys(name, a, b, clusters, *, level="AXIS", streams=1, qualification=False):
    return RelationshipSystem(
        system=name, pole_a_strength=a, pole_b_strength=b,
        semantic_level=level, evidence_stream_count=streams,
        evidence_cluster_ids=tuple(clusters), material_qualification=qualification,
    )


def _score(system, score, status=SystemScoreStatus.EVALUATED, coverage=1.0, confidence=1.0):
    return SystemScore(system=system, score=score, status=status, coverage=coverage,
                       data_confidence=confidence, valid_indicator_count=1, expected_indicator_count=1)


def test_adversarial_2v1_does_not_use_majority_as_convergence():
    systems = (
        _sys("ASTROLOGY", .80, .10, ["c1"]),
        _sys("NUMEROLOGY", .80, .10, ["c2"]),
        _sys("PALMISTRY", .10, .80, ["c3"]),
    )
    r = evaluate_relationship(RelationshipInput("R", _target(), systems))
    assert not r.broad_directional_convergence
    assert r.state == RelationshipState.S0


def test_adversarial_same_cluster_cannot_be_independent_s4():
    systems = (
        _sys("ASTROLOGY", .80, .10, ["same"]),
        _sys("NUMEROLOGY", .80, .10, ["same"]),
        _sys("PALMISTRY", .80, .10, ["same"]),
    )
    r = evaluate_relationship(RelationshipInput("R", _target(), systems, independence=.90))
    assert r.state == RelationshipState.S3
    assert not r.evidence_cluster_separation


def test_adversarial_context_resolved_opposition_never_becomes_s7():
    x = ContradictionInput("A01", .80, .80,
        (_sys("ASTROLOGY", .80, .10, ["a"]),),
        (_sys("NUMEROLOGY", .10, .80, ["b"]),),
        True, .90, True, True, .90)
    result = evaluate_contradiction(x)
    assert result.state == RelationshipState.S0
    assert not result.validated_opposition


def test_adversarial_duplicate_cluster_never_becomes_s7():
    x = ContradictionInput("A01", .80, .80,
        (_sys("ASTROLOGY", .80, .10, ["same"]),),
        (_sys("NUMEROLOGY", .10, .80, ["same"]),),
        True, .90, True, False, .90)
    result = evaluate_contradiction(x)
    assert result.state == RelationshipState.S0
    assert not result.validated_opposition


def test_adversarial_s6_has_no_fusion_penalty():
    scores = (_score("ASTROLOGY", .70), _score("NUMEROLOGY", .70))
    no_conflict = calculate_fusion_result(FusionContext(scores, RelationshipState.S2, independence=0))
    tension = calculate_fusion_result(FusionContext(scores, RelationshipState.S6, independence=0, contradiction_strength=1))
    assert tension.contradiction_penalty == 0
    assert tension.final_score == pytest.approx(no_conflict.final_score)


def test_adversarial_unavailable_is_not_zero_filled():
    scores = (_score("ASTROLOGY", .80), _score("NUMEROLOGY", None, SystemScoreStatus.UNAVAILABLE, 0, 0))
    f = calculate_fusion_result(FusionContext(scores))
    assert f.valid_system_count == 1
    assert f.base == pytest.approx(.80)


def test_adversarial_invalid_is_not_negative_evidence():
    scores = (_score("ASTROLOGY", .80), _score("NUMEROLOGY", None, SystemScoreStatus.INVALID, 0, 0))
    f = calculate_fusion_result(FusionContext(scores))
    assert f.base == pytest.approx(.80)
    assert f.valid_system_count == 1


def test_adversarial_domain_rejects_out_of_range_scores():
    with pytest.raises(ValidationError):
        _score("ASTROLOGY", 1.01)
    with pytest.raises(ValidationError):
        _score("ASTROLOGY", -0.01)


def test_adversarial_mismatched_semantic_level_blocks_convergence():
    systems = (
        _sys("ASTROLOGY", .80, .10, ["a"], level="AXIS"),
        _sys("NUMEROLOGY", .80, .10, ["b"], level="THEME"),
    )
    r = evaluate_relationship(RelationshipInput("R", _target(), systems))
    assert not r.broad_directional_convergence
    assert r.state == RelationshipState.S0
