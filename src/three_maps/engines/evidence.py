"""Evidence and Signal engine for THE THREE MAPS.

Converts validated upstream observations/calculations into auditable evidence
clusters and ontology-mapped signals. This module never invents interpretation.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

from three_maps.domain.types import (
    ActivationState, ApplicabilityState, EvidenceCluster, RawEvidence, Signal
)


@dataclass(frozen=True)
class SignalMapping:
    """Explicit, versioned ontology mapping; no implicit semantic inference."""
    source_system: str
    source_variable: str
    theme_id: str
    sub_theme_id: str | None
    axis_id: str
    pole_id: str
    mapping_confidence: float
    methodology_version: str
    ontology_version: str = "OV-0.1.0"
    calculation_version: str = "CV-0.1.0"


def _stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(x) for x in parts)
    return f"{prefix}-{sha256(raw.encode()).hexdigest()[:12]}"


def build_evidence_cluster(
    evidence: Iterable[RawEvidence], *, source_system: str, distinctness_key: str
) -> EvidenceCluster:
    """Group causally related valid evidence into one counting boundary."""
    items = list(evidence)
    if not items:
        raise ValueError("Evidence cluster requires at least one evidence record.")
    if any(not e.validity for e in items):
        raise ValueError("Invalid raw evidence cannot enter an evidence cluster.")
    ids = sorted({e.id for e in items})
    return EvidenceCluster(
        id=_stable_id("EC", source_system, distinctness_key, *ids),
        evidence_ids=ids,
        source_system=source_system,
        distinctness_key=distinctness_key,
        confidence=1.0,
    )


def generate_signal(
    evidence: RawEvidence,
    *,
    mapping: SignalMapping,
    evidence_cluster: EvidenceCluster,
    strength: int,
    confidence: float,
    relevance: float,
    context_scope: str | None = None,
    temporal_scope: str | None = None,
    applicability: ApplicabilityState = ApplicabilityState.CORE,
    activation: ActivationState = ActivationState.ACTIVE,
) -> Signal:
    """Generate a signal only from valid evidence and an explicit mapping."""
    if not evidence.validity:
        raise ValueError("Invalid evidence cannot generate a signal.")
    if evidence.id not in evidence_cluster.evidence_ids:
        raise ValueError("Evidence must belong to the supplied evidence cluster.")
    if evidence.source_engine != mapping.source_system:
        raise ValueError("Mapping source system does not match evidence source.")
    if evidence.source_variable != mapping.source_variable:
        raise ValueError("Mapping source variable does not match evidence.")
    if not 0.75 <= mapping.mapping_confidence <= 1:
        raise ValueError("Mapping confidence must be at least 0.75.")
    signal_id = _stable_id(
        "SIG", evidence.id, mapping.theme_id, mapping.sub_theme_id,
        mapping.axis_id, mapping.pole_id, mapping.ontology_version
    )
    return Signal(
        id=signal_id,
        source_system=mapping.source_system,
        source_variable=mapping.source_variable,
        evidence_ids=[evidence.id],
        evidence_cluster_ids=[evidence_cluster.id],
        theme_id=mapping.theme_id,
        sub_theme_id=mapping.sub_theme_id,
        axis_id=mapping.axis_id,
        pole_id=mapping.pole_id,
        strength=strength,
        confidence=confidence,
        relevance=relevance,
        applicability=applicability,
        activation=activation,
        context_scope=context_scope,
        temporal_scope=temporal_scope,
        methodology_version=mapping.methodology_version,
        calculation_version=mapping.calculation_version,
    )
