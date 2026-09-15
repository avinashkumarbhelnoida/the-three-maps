from datetime import datetime, timezone
import pytest

from three_maps.domain.types import (
    ApplicabilityState, Axis, Pole, RawEvidence, Signal, Target, ActivationState,
    UnavailableReason,
)
from three_maps.engines.applicability import (
    resolve_applicability, resolve_activation_record, resolve_activation,
)


def sig():
    return Signal(
        id="SIG-1", source_system="NUMEROLOGY", source_variable="LIFE_PATH",
        evidence_ids=["RAW-1"], evidence_cluster_ids=["EC-1"], theme_id="T01",
        sub_theme_id="ST01", axis_id="A01", pole_id="A01-A", strength=3,
        confidence=.9, relevance=.8, applicability=ApplicabilityState.CORE,
        activation=ActivationState.ACTIVE, methodology_version="MV-0.1.0",
        calculation_version="CV-0.1.0",
    )


def target():
    return Target(theme_id="T01", sub_theme_id="ST01", axis_id="A01", semantic_level="SUB_THEME")


def test_applicability_is_evidence_independent():
    r = resolve_applicability(signal=sig(), target=target(), state=ApplicabilityState.CORE, mapping_confidence=.75)
    assert r.state is ApplicabilityState.CORE


def test_confidence_defaults_are_gates_not_scores():
    with pytest.raises(ValueError):
        resolve_applicability(signal=sig(), target=target(), state=ApplicabilityState.SECONDARY, mapping_confidence=.79)
    with pytest.raises(ValueError):
        resolve_applicability(signal=sig(), target=target(), state=ApplicabilityState.CONTEXTUAL, mapping_confidence=.84)


def test_blocked_and_not_applicable_are_not_permitted():
    for state in (ApplicabilityState.BLOCKED, ApplicabilityState.NOT_APPLICABLE):
        result = resolve_activation_record(
            signal_id="SIG-1", valid=True, required_inputs_available=True,
            applicability=state,
        )
        assert result.state is ActivationState.NOT_PERMITTED


def test_contextual_without_context_is_unavailable_context_reason():
    result = resolve_activation_record(
        signal_id="SIG-1", valid=True, required_inputs_available=True,
        applicability=ApplicabilityState.CONTEXTUAL, context_available=False,
    )
    assert result.state is ActivationState.UNAVAILABLE
    assert result.unavailable_reason is UnavailableReason.CONTEXT


def test_required_input_precedes_permission():
    result = resolve_activation_record(
        signal_id="SIG-1", valid=True, required_inputs_available=False,
        applicability=ApplicabilityState.BLOCKED,
    )
    assert result.state is ActivationState.UNAVAILABLE
    assert result.unavailable_reason is UnavailableReason.REQUIRED_INPUT


def test_invalid_has_highest_activation_precedence():
    result = resolve_activation_record(
        signal_id="SIG-1", valid=False, required_inputs_available=False,
        applicability=ApplicabilityState.BLOCKED, context_available=False,
        evidence_available=False,
    )
    assert result.state is ActivationState.INVALID


def test_evidence_unavailable_is_distinct_from_not_permitted():
    result = resolve_activation_record(
        signal_id="SIG-1", valid=True, required_inputs_available=True,
        applicability=ApplicabilityState.CORE, evidence_available=False,
    )
    assert result.state is ActivationState.UNAVAILABLE
    assert result.unavailable_reason is UnavailableReason.EVIDENCE


def test_evidence_sufficiency_gate_prevents_activation():
    result = resolve_activation_record(
        signal_id="SIG-1", valid=True, required_inputs_available=True,
        applicability=ApplicabilityState.CORE, evidence_available=True,
        evidence_sufficient=False,
    )
    assert result.state is ActivationState.UNAVAILABLE
    assert result.unavailable_reason is UnavailableReason.EVIDENCE


def test_all_gates_pass_means_active():
    result = resolve_activation_record(
        signal_id="SIG-1", valid=True, required_inputs_available=True,
        applicability=ApplicabilityState.CORE, context_available=True,
        evidence_available=True, evidence_sufficient=True,
    )
    assert result.state is ActivationState.ACTIVE


def test_legacy_resolver_remains_consistent():
    assert resolve_activation(
        valid=True, required_inputs_available=True,
        applicability=ApplicabilityState.CORE,
    ) is ActivationState.ACTIVE
