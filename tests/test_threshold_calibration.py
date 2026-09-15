import pytest

from three_maps.config.thresholds import TAU_B, TAU_D, TAU_I, TAU_P, TAU_S
from three_maps.domain.types import AxisDirectionState, Pole, PoleEvaluation, PoleEligibility, EvidenceState
from three_maps.engines.pole import aggregate_axis
from three_maps.engines.contradiction import ContradictionInput, evaluate_contradiction
from three_maps.engines.relationship import RelationshipSystem


def pe(pole_id, support, system):
    return PoleEvaluation(
        axis_id="A01", pole_id=pole_id,
        eligibility=PoleEligibility.ELIGIBLE,
        evidence_state=EvidenceState.SUPPORTS,
        support=support, confidence=1.0, relevance=1.0,
        signal_ids=[f"{system}:sig"], evidence_cluster_ids=[f"EC-{system}"]
    )


def rs(system, direction_a, direction_b):
    return RelationshipSystem(system, direction_a, direction_b, "SUB_THEME", temporal_scope="CURRENT", evidence_stream_count=1, evidence_cluster_ids=(f"EC-{system}",))


def test_threshold_registry_values_are_frozen_defaults():
    assert TAU_P == pytest.approx(.60)
    assert TAU_D == pytest.approx(.25)
    assert TAU_B == pytest.approx(.70)
    assert TAU_I == pytest.approx(.50)
    assert TAU_S == pytest.approx(.60)

@pytest.mark.parametrize("value,expected", [
    (TAU_P - .000001, False), (TAU_P, True), (TAU_P + .000001, True),
])
def test_pole_meaningfulness_boundary(value, expected):
    assert (value >= TAU_P) is expected

@pytest.mark.parametrize("delta,expected", [
    (TAU_D - .000001, AxisDirectionState.A_ONE_SIDED_SUPPORT),
    (TAU_D, AxisDirectionState.A_DOMINANT),
    (TAU_D + .000001, AxisDirectionState.A_DOMINANT),
])
def test_dominance_boundary(delta, expected):
    result = aggregate_axis("A01", [pe("P-A", .80, "NUMEROLOGY")], [pe("P-B", .80-delta, "ASTROLOGY")])
    assert result.direction_state == expected

@pytest.mark.parametrize("value,expected", [
    (TAU_S - .000001, False), (TAU_S, True), (TAU_S + .000001, True),
])
def test_semantic_similarity_boundary(value, expected):
    r = evaluate_contradiction(ContradictionInput(
        "A01", .8, .8, (rs("ASTROLOGY", .8, .1),), (rs("NUMEROLOGY", .1, .8),),
        True, value, True, False, .8
    ))
    assert r.validated_opposition is expected

@pytest.mark.parametrize("value,expected", [
    (TAU_I - .000001, False), (TAU_I, True), (TAU_I + .000001, True),
])
def test_independence_boundary(value, expected):
    r = evaluate_contradiction(ContradictionInput(
        "A01", .8, .8, (rs("ASTROLOGY", .8, .1),), (rs("NUMEROLOGY", .1, .8),),
        True, .9, True, False, value
    ))
    assert (r.state.value == "S7") is expected

@pytest.mark.parametrize("b,expected", [
    (TAU_B - .000001, "S6"),
    (TAU_B, "S7"),
    (TAU_B + .000001, "S7"),
])
def test_balance_boundary(b, expected):
    r = evaluate_contradiction(ContradictionInput(
        "A01", 1.0, b, (rs("ASTROLOGY", 1.0, .1),), (rs("NUMEROLOGY", .1, b),),
        True, .9, True, False, .8
    ))
    assert r.state.value == expected


def test_tau_p_and_tau_s_interaction_does_not_create_false_opposition():
    r = evaluate_contradiction(ContradictionInput(
        "A01", TAU_P, TAU_P, (rs("ASTROLOGY", .8, .1),), (rs("NUMEROLOGY", .1, .8),),
        True, TAU_S, True, False, TAU_I
    ))
    assert r.state.value == "S7"
