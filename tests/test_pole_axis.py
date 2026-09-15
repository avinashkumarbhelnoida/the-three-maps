from three_maps.domain.types import *
from three_maps.engines.pole import evaluate_pole, aggregate_axis


def sig(id_, pole, strength=4, confidence=.9, relevance=1.0, app=ApplicabilityState.CORE):
    return Signal(id=id_, source_system="NUMEROLOGY", source_variable="LIFE_PATH", theme_id="TH-001", axis_id="A01", pole_id=pole, strength=strength, confidence=confidence, relevance=relevance, applicability=app, activation=ActivationState.ACTIVE, evidence_ids=[f"RAW-{id_}"], evidence_cluster_ids=[f"EC-{id_}"], methodology_version="MV-0.1.0", calculation_version="CV-0.1.0")


def test_pole_strength_uses_normalized_strength_confidence_relevance():
    pole = Pole(id="P-A01-A", axis_id="A01", name="Structure", side="A", ontology_version="OV-0.1.0")
    result = evaluate_pole(pole, [sig("1", pole.id, strength=4, confidence=.8, relevance=.5)])
    assert round(result.support, 6) == .4
    assert result.evidence_state == EvidenceState.SUPPORTS


def test_inactive_signal_cannot_contribute_to_pole():
    pole = Pole(id="P-A01-A", axis_id="A01", name="Structure", side="A", ontology_version="OV-0.1.0")
    s = sig("1", pole.id)
    s = s.model_copy(update={"activation": ActivationState.NOT_ACTIVATED})
    result = evaluate_pole(pole, [s])
    assert result.support == 0
    assert result.evidence_state == EvidenceState.UNAVAILABLE


def test_axis_meaningful_tie():
    a = PoleEvaluation(axis_id="A01", pole_id="P-A01-A", eligibility=PoleEligibility.ELIGIBLE, evidence_state=EvidenceState.SUPPORTS, support=.70, confidence=.9, relevance=1, signal_ids=["NUMEROLOGY:1"])
    b = PoleEvaluation(axis_id="A01", pole_id="P-A01-B", eligibility=PoleEligibility.ELIGIBLE, evidence_state=EvidenceState.SUPPORTS, support=.68, confidence=.9, relevance=1, signal_ids=["ASTROLOGY:1"])
    result = aggregate_axis("A01", [a], [b])
    assert result.direction_state == AxisDirectionState.MEANINGFUL_TIE
    assert result.dual_pole_support is True


def test_axis_one_sided_support():
    a = PoleEvaluation(axis_id="A01", pole_id="P-A01-A", eligibility=PoleEligibility.ELIGIBLE, evidence_state=EvidenceState.SUPPORTS, support=.61, confidence=.9, relevance=1, signal_ids=["NUMEROLOGY:1"])
    b = PoleEvaluation(axis_id="A01", pole_id="P-A01-B", eligibility=PoleEligibility.ELIGIBLE, evidence_state=EvidenceState.DOES_NOT_SUPPORT, support=.40, confidence=.9, relevance=1, signal_ids=["ASTROLOGY:1"])
    result = aggregate_axis("A01", [a], [b])
    assert result.direction_state == AxisDirectionState.A_ONE_SIDED_SUPPORT


def test_axis_insufficient_when_both_below_threshold():
    a = PoleEvaluation(axis_id="A01", pole_id="P-A01-A", eligibility=PoleEligibility.ELIGIBLE, evidence_state=EvidenceState.SUPPORTS, support=.4, confidence=.9, relevance=1, signal_ids=["NUMEROLOGY:1"])
    b = PoleEvaluation(axis_id="A01", pole_id="P-A01-B", eligibility=PoleEligibility.ELIGIBLE, evidence_state=EvidenceState.SUPPORTS, support=.5, confidence=.9, relevance=1, signal_ids=["ASTROLOGY:1"])
    result = aggregate_axis("A01", [a], [b])
    assert result.direction_state == AxisDirectionState.INSUFFICIENT


def test_axis_does_not_create_contradiction_state():
    a = PoleEvaluation(axis_id="A01", pole_id="P-A01-A", eligibility=PoleEligibility.ELIGIBLE, evidence_state=EvidenceState.SUPPORTS, support=.8, confidence=.9, relevance=1, signal_ids=["NUMEROLOGY:1"])
    b = PoleEvaluation(axis_id="A01", pole_id="P-A01-B", eligibility=PoleEligibility.ELIGIBLE, evidence_state=EvidenceState.SUPPORTS, support=.8, confidence=.9, relevance=1, signal_ids=["ASTROLOGY:1"])
    result = aggregate_axis("A01", [a], [b])
    assert result.dual_pole_support is True
    assert not hasattr(result, "contradiction_state")
