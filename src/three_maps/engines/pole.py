from __future__ import annotations

from collections import defaultdict
from math import prod
from typing import Iterable, Mapping

from three_maps.config.thresholds import TAU_P
from three_maps.domain.types import (
    ActivationState,
    ApplicabilityState,
    AxisDirectionState,
    AxisResult,
    AxisStatus,
    DirectionalAgreement,
    EvidenceState,
    Pole,
    PoleEligibility,
    PoleEvaluation,
    PoleStrength,
    Signal,
)


def _eligible(signal: Signal) -> PoleEligibility:
    if signal.activation != ActivationState.ACTIVE:
        return PoleEligibility.BLOCKED
    if signal.applicability == ApplicabilityState.CORE:
        return PoleEligibility.ELIGIBLE
    if signal.applicability == ApplicabilityState.SECONDARY:
        return PoleEligibility.ELIGIBLE
    if signal.applicability == ApplicabilityState.CONTEXTUAL:
        return PoleEligibility.CONDITIONAL
    return PoleEligibility.BLOCKED


def evaluate_pole(
    pole: Pole,
    signals: Iterable[Signal],
    evidence_cluster_confidence: Mapping[str, float] | None = None,
) -> PoleEvaluation:
    """Evaluate active signals mapped to one pole without creating relationships."""
    cluster_conf = evidence_cluster_confidence or {}
    eligible = []
    for signal in signals:
        if signal.axis_id != pole.axis_id or signal.pole_id != pole.id:
            continue
        eligibility = _eligible(signal)
        if eligibility in (PoleEligibility.ELIGIBLE, PoleEligibility.CONDITIONAL):
            eligible.append(signal)

    if not eligible:
        return PoleEvaluation(
            axis_id=pole.axis_id,
            pole_id=pole.id,
            eligibility=PoleEligibility.NOT_APPLICABLE,
            evidence_state=EvidenceState.UNAVAILABLE,
            support=0.0,
            confidence=0.0,
            relevance=0.0,
        )

    contributions = []
    confidence_values = []
    relevance_values = []
    signal_ids = []
    cluster_ids = []
    for signal in eligible:
        cluster_factor = sum(cluster_conf.get(cid, 1.0) for cid in signal.evidence_cluster_ids) / max(len(signal.evidence_cluster_ids), 1)
        normalized_strength = signal.strength / 4.0
        contribution = normalized_strength * signal.confidence * cluster_factor * signal.relevance
        contributions.append(max(0.0, min(1.0, contribution)))
        confidence_values.append(signal.confidence)
        relevance_values.append(signal.relevance)
        signal_ids.append(signal.id)
        cluster_ids.extend(signal.evidence_cluster_ids)

    pole_strength = 1.0 - prod(1.0 - c for c in contributions)
    evidence_state = EvidenceState.SUPPORTS if pole_strength > 0 else EvidenceState.DOES_NOT_SUPPORT
    eligibility = PoleEligibility.CONDITIONAL if any(_eligible(s) == PoleEligibility.CONDITIONAL for s in eligible) else PoleEligibility.ELIGIBLE

    return PoleEvaluation(
        axis_id=pole.axis_id,
        pole_id=pole.id,
        eligibility=eligibility,
        evidence_state=evidence_state,
        signal_ids=signal_ids,
        evidence_cluster_ids=sorted(set(cluster_ids)),
        support=pole_strength,
        confidence=sum(confidence_values) / len(confidence_values),
        relevance=sum(relevance_values) / len(relevance_values),
    )


def aggregate_axis(
    axis_id: str,
    evaluations_a: Iterable[PoleEvaluation],
    evaluations_b: Iterable[PoleEvaluation],
    system_weights: Mapping[str, float] | None = None,
    tie_tolerance: float = 0.05,
) -> AxisResult:
    """Aggregate already-evaluated poles. No new evidence is created here."""
    weights = system_weights or {}

    def aggregate(evaluations: Iterable[PoleEvaluation]) -> float:
        by_system: dict[str, list[PoleEvaluation]] = defaultdict(list)
        for evaluation in evaluations:
            for sid in evaluation.signal_ids:
                by_system[sid.split(":", 1)[0]].append(evaluation)
        # If no system encoding exists, use equal contribution of supplied evaluations.
        if not by_system:
            vals = [e.support for e in evaluations]
            return sum(vals) / len(vals) if vals else 0.0
        numer = denom = 0.0
        for system, items in by_system.items():
            w = weights.get(system, 1.0)
            value = max(i.support for i in items)
            numer += w * value
            denom += w
        return numer / denom if denom else 0.0

    a_evals = list(evaluations_a)
    b_evals = list(evaluations_b)
    a = aggregate(a_evals)
    b = aggregate(b_evals)

    if a + b == 0:
        balance = None
        polarity = None
    else:
        dominant = max(a, b)
        opposing = min(a, b)
        balance = opposing / dominant if dominant > 0 else None
        polarity = (a - b) / (a + b)

    # Meaningfulness is checked before tie resolution.
    a_meaningful = a >= TAU_P
    b_meaningful = b >= TAU_P
    dual = a_meaningful and b_meaningful

    if not a_meaningful and not b_meaningful:
        direction = AxisDirectionState.INSUFFICIENT
    elif a_meaningful and not b_meaningful:
        direction = AxisDirectionState.A_DOMINANT if a - b >= 0.25 else AxisDirectionState.A_ONE_SIDED_SUPPORT
    elif b_meaningful and not a_meaningful:
        direction = AxisDirectionState.B_DOMINANT if b - a >= 0.25 else AxisDirectionState.B_ONE_SIDED_SUPPORT
    elif abs(a - b) <= tie_tolerance:
        direction = AxisDirectionState.MEANINGFUL_TIE
    elif abs(a - b) >= 0.25:
        direction = AxisDirectionState.A_DOMINANT if a > b else AxisDirectionState.B_DOMINANT
    else:
        direction = AxisDirectionState.BALANCED

    coverage = 1.0 if (a_evals or b_evals) else 0.0
    confidence_values = [e.confidence for e in a_evals + b_evals]
    confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
    agreement = DirectionalAgreement.UNAVAILABLE if not (a_evals or b_evals) else DirectionalAgreement.FULL
    status = AxisStatus.EVALUATED if (a_evals or b_evals) else AxisStatus.UNAVAILABLE

    return AxisResult(
        axis_id=axis_id,
        pole_a_strength=a,
        pole_b_strength=b,
        balance_ratio=balance,
        polarity=polarity,
        direction_state=direction,
        dual_pole_support=dual,
        directional_agreement=agreement,
        coverage=coverage,
        confidence=confidence,
        status=status,
    )
