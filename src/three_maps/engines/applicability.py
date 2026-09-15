"""Applicability and activation engine for THE THREE MAPS.

State resolution is evidence-independent. Activation applies availability and
context gates to an already-resolved applicability state.
"""
from __future__ import annotations

from three_maps.domain.types import (
    ActivationRecord,
    ActivationState,
    ApplicabilityRecord,
    ApplicabilityState,
    Signal,
    Target,
    UnavailableReason,
)

# Versioned methodology defaults; values are gates, not scores.
MAPPING_CONFIDENCE_MIN = {
    ApplicabilityState.CORE: 0.75,
    ApplicabilityState.SECONDARY: 0.80,
    ApplicabilityState.CONTEXTUAL: 0.85,
}


def resolve_applicability(
    *,
    signal: Signal,
    target: Target,
    state: ApplicabilityState,
    mapping_confidence: float,
    reason: str | None = None,
) -> ApplicabilityRecord:
    """Resolve applicability without inspecting evidence strength.

    Parent/child narrowing is handled by callers by supplying the resolved
    state. This function deliberately never broadens permission.
    """
    if not 0 <= mapping_confidence <= 1:
        raise ValueError("mapping_confidence must be between 0 and 1.")
    minimum = MAPPING_CONFIDENCE_MIN.get(state)
    if minimum is not None and mapping_confidence < minimum:
        raise ValueError(
            f"{state.value} mapping confidence must be at least {minimum:.2f}."
        )
    if target.axis_id is not None and target.axis_id != signal.axis_id:
        raise ValueError("Target axis does not match signal axis.")
    if target.theme_id != signal.theme_id:
        raise ValueError("Target theme does not match signal theme.")
    if target.sub_theme_id is not None and target.sub_theme_id != signal.sub_theme_id:
        raise ValueError("Target sub-theme does not match signal sub-theme.")
    return ApplicabilityRecord(
        signal_id=signal.id,
        target=target,
        state=state,
        mapping_confidence=mapping_confidence,
        reason=reason,
    )


def resolve_activation_record(
    *,
    signal_id: str,
    valid: bool,
    required_inputs_available: bool,
    applicability: ApplicabilityState,
    context_available: bool = True,
    evidence_available: bool = True,
    evidence_sufficient: bool = True,
    confidence: float = 1.0,
) -> ActivationRecord:
    """Apply the canonical availability-first activation sequence."""
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1.")

    # Canonical precedence: validity → required input → permission → context
    # → evidence availability → evidence sufficiency.
    if not valid:
        state = ActivationState.INVALID
        reason = "Target-level validity failed."
        unavailable_reason = None
    elif not required_inputs_available:
        state = ActivationState.UNAVAILABLE
        reason = "Required input is unavailable."
        unavailable_reason = UnavailableReason.REQUIRED_INPUT
    elif applicability in {
        ApplicabilityState.BLOCKED,
        ApplicabilityState.NOT_APPLICABLE,
    }:
        state = ActivationState.NOT_PERMITTED
        reason = "Applicability does not permit participation."
        unavailable_reason = None
    elif applicability == ApplicabilityState.CONTEXTUAL and not context_available:
        state = ActivationState.UNAVAILABLE
        reason = "Required context is unavailable."
        unavailable_reason = UnavailableReason.CONTEXT
    elif not evidence_available or not evidence_sufficient:
        state = ActivationState.UNAVAILABLE
        reason = (
            "Required evidence is unavailable."
            if not evidence_available
            else "Evidence is not sufficient for activation."
        )
        unavailable_reason = UnavailableReason.EVIDENCE
    else:
        state = ActivationState.ACTIVE
        reason = "All activation gates passed."
        unavailable_reason = None

    return ActivationRecord(
        signal_id=signal_id,
        state=state,
        unavailable_reason=unavailable_reason,
        validity=valid,
        required_inputs_available=required_inputs_available,
        context_available=context_available,
        evidence_available=evidence_available,
        evidence_sufficient=evidence_sufficient,
        confidence=confidence,
        reason=reason,
    )


def resolve_activation(
    *,
    valid: bool,
    required_inputs_available: bool,
    applicability: ApplicabilityState,
    context_available: bool = True,
    evidence_available: bool = True,
    evidence_sufficient: bool = True,
) -> ActivationState:
    """Backward-compatible state-only activation resolver."""
    return resolve_activation_record(
        signal_id="UNSPECIFIED",
        valid=valid,
        required_inputs_available=required_inputs_available,
        applicability=applicability,
        context_available=context_available,
        evidence_available=evidence_available,
        evidence_sufficient=evidence_sufficient,
    ).state
