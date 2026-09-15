from three_maps.engines.explanation import ExplanationContext, build_explanation, validate_explanation
from three_maps.domain.types import (
    AxisDirectionState, ContradictionResult, FusionResult, RelationshipResult,
    RelationshipState, SystemScore, SystemScoreStatus, Target,
)


def fusion(score=77.35):
    return FusionResult(base=.68, convergence_bonus=.13, independence_bonus=.05,
                        contradiction_penalty=.0, raw_score=score/100, final_score=score,
                        label="HIGH", valid_system_count=3, meaningful_system_count=3,
                        dominant_map="Astrology", data_confidence=.87, coverage=.92)


def relationship(state=RelationshipState.S3):
    return RelationshipResult(
        relationship_id="REL-1", target=Target(theme_id="T1", semantic_level="AXIS"),
        participating_systems=["ASTROLOGY", "NUMEROLOGY", "PALMISTRY"],
        meaningful_systems=["ASTROLOGY", "NUMEROLOGY", "PALMISTRY"],
        meaningful_poles=["A"], direction="A", state=state,
        broad_directional_convergence=True, semantic_similarity=.9,
        same_semantic_level=True, temporal_compatibility=True,
        context_resolution=False, evidence_stream_count=3,
        evidence_cluster_separation=True)


def test_explanation_starts_with_result_and_preserves_direction():
    e = build_explanation(ExplanationContext(
        explanation_id="EXP-1", fusion_unit_id="FUS-1", fusion=fusion(),
        relationship=relationship(), direction_state=AxisDirectionState.A_DOMINANT,
        pole_a_name="Structure", pole_b_name="Freedom", lineage_ids=["LIN-1"]))
    assert e.result_statement == "Fusion Strength is 77.35/100 (HIGH)."
    assert "Structure is the materially dominant" in e.direction_statement
    assert e.relationship_statement.startswith("All three maps")
    assert validate_explanation(e) == []


def test_partial_is_qualification_not_score_penalty():
    scores = [SystemScore(system="ASTROLOGY", score=.8, status=SystemScoreStatus.EVALUATED,
                           coverage=1, data_confidence=.9, valid_indicator_count=4, expected_indicator_count=4),
              SystemScore(system="NUMEROLOGY", score=.6, status=SystemScoreStatus.PARTIAL,
                           coverage=.5, data_confidence=.7, valid_indicator_count=2, expected_indicator_count=4)]
    e = build_explanation(ExplanationContext(explanation_id="EXP-2", fusion_unit_id="FUS-2", fusion=fusion(), system_scores=scores))
    assert "partial" in e.qualification_statement.lower()
    assert "not used to multiply" in e.coverage_statement


def test_unavailable_is_not_negative_evidence():
    scores = [SystemScore(system="ASTROLOGY", score=.8, status=SystemScoreStatus.EVALUATED,
                           coverage=1, data_confidence=.9, valid_indicator_count=4, expected_indicator_count=4),
              SystemScore(system="PALMISTRY", score=None, status=SystemScoreStatus.UNAVAILABLE,
                           coverage=0, data_confidence=0, valid_indicator_count=0, expected_indicator_count=4)]
    e = build_explanation(ExplanationContext(explanation_id="EXP-3", fusion_unit_id="FUS-3", fusion=fusion(), system_scores=scores))
    assert "treated as negative evidence" in e.qualification_statement


def test_s6_and_s7_language_remain_distinct():
    c = ContradictionResult(axis_id="A01", state=RelationshipState.S6, pole_a_strength=.7,
                            pole_b_strength=.7, balance_ratio=1, contradiction_strength=.4,
                            gates={}, validated_opposition=True)
    e = build_explanation(ExplanationContext(explanation_id="EXP-4", fusion_unit_id="FUS-4",
                                             fusion=fusion(), contradiction=c))
    assert "tension (S6)" in e.contradiction_statement
    assert "formal contradiction" not in e.contradiction_statement.lower()


def test_claims_are_traceable():
    e = build_explanation(ExplanationContext(explanation_id="EXP-5", fusion_unit_id="FUS-5", fusion=fusion()))
    assert all(c.source_ids and c.validated for c in e.claim_objects)
    assert validate_explanation(e) == []
