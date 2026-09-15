from three_maps.domain.types import (
    ActivationState, ApplicabilityState, IndicatorWeightClass, RelationshipState,
    Signal, SystemScoreStatus, Target,
)
from three_maps.engines.integration import CrossEngineInput, MapEvaluation, integrate_cross_engine
from three_maps.engines.system_score import SystemScoreIndicator, SystemScoreInput, calculate_system_score


def _signal(identifier: str, pole: str, source: str, strength: int = 4) -> Signal:
    return Signal(
        id=identifier, source_system=source, source_variable="TEST",
        evidence_ids=[f"RAW-{identifier}"], evidence_cluster_ids=[f"EC-{identifier}"],
        theme_id="TH-1", axis_id="A01", pole_id=pole, strength=strength,
        confidence=1.0, relevance=1.0, weight_class=IndicatorWeightClass.STANDARD,
        applicability=ApplicabilityState.CORE, activation=ActivationState.ACTIVE,
        methodology_version="MV-0.1.0", calculation_version="CV-0.1.0",
    )


def _score(system: str, identifier: str, strength: int = 4):
    return calculate_system_score(SystemScoreInput(system, (SystemScoreIndicator(_signal(identifier, "P-A01-A", system, strength)),)))


def _target():
    return Target(theme_id="TH-1", sub_theme_id="ST-1", axis_id="A01", semantic_level="SUB_THEME", temporal_scope="CURRENT", context_scope="GENERAL")


def test_three_map_clean_convergence_reaches_s3_and_fusion():
    maps = tuple(MapEvaluation(s, "A01", .80, .10, _score(s, s.lower()), "SUB_THEME", evidence_cluster_ids=(f"EC-{s}",)) for s in ("ASTROLOGY", "NUMEROLOGY", "PALMISTRY"))
    result = integrate_cross_engine(CrossEngineInput("INT-3", _target(), maps, independence=.8))
    assert result.relationship.state == RelationshipState.S4  # clean S3 + differentiated evidence
    assert result.contradiction.validated_opposition is False
    assert result.fusion.valid_system_count == 3
    assert result.fusion.contradiction_penalty == 0


def test_two_maps_plus_unavailable_third_does_not_create_s3():
    maps = (
        MapEvaluation("ASTROLOGY", "A01", .80, .10, _score("ASTROLOGY", "a"), "SUB_THEME", evidence_cluster_ids=("EA",)),
        MapEvaluation("NUMEROLOGY", "A01", .80, .10, _score("NUMEROLOGY", "n"), "SUB_THEME", evidence_cluster_ids=("EN",)),
        MapEvaluation("PALMISTRY", "A01", .80, .10, calculate_system_score(SystemScoreInput("PALMISTRY", (SystemScoreIndicator(_signal("p", "P-A01-A", "PALMISTRY"), available=False),))), "SUB_THEME", evidence_cluster_ids=("EP",)),
    )
    result = integrate_cross_engine(CrossEngineInput("INT-2", _target(), maps))
    assert result.relationship.state == RelationshipState.S2
    assert result.fusion.valid_system_count == 2


def test_two_sided_opposition_reaches_s7_only_when_all_gates_pass():
    a = MapEvaluation("ASTROLOGY", "A01", .80, .10, _score("ASTROLOGY", "a"), "SUB_THEME", evidence_cluster_ids=("EA",))
    b = MapEvaluation("NUMEROLOGY", "A01", .10, .80, _score("NUMEROLOGY", "n"), "SUB_THEME", evidence_cluster_ids=("EN",))
    result = integrate_cross_engine(CrossEngineInput("INT-S7", _target(), (a, b), independence=.8))
    assert result.contradiction.state == RelationshipState.S7
    assert result.contradiction.validated_opposition is True
    assert result.fusion.contradiction_penalty > 0


def test_duplicate_cluster_does_not_become_formal_contradiction():
    a = MapEvaluation("ASTROLOGY", "A01", .80, .10, _score("ASTROLOGY", "a"), "SUB_THEME", evidence_cluster_ids=("SAME",))
    b = MapEvaluation("NUMEROLOGY", "A01", .10, .80, _score("NUMEROLOGY", "n"), "SUB_THEME", evidence_cluster_ids=("SAME",))
    result = integrate_cross_engine(CrossEngineInput("INT-DUP", _target(), (a, b), independence=.8))
    assert result.contradiction.validated_opposition is False
    assert result.contradiction.state == RelationshipState.S0
    assert result.fusion.contradiction_penalty == 0
