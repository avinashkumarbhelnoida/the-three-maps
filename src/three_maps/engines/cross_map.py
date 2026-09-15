"""Phase-I cross-map intelligence boundary for THE THREE MAPS.

This module joins the three map engines without inventing semantic mappings or
new evidence. It provides:

201.81G - explicit mapping-registry resolution for unmapped candidates
201.81H - common evidence/signal normalization across Astrology, Numerology,
          and Palmistry
201.81I - relationship-unit construction and convergence qualification
201.81J - contradiction-ready directional evidence streams

All semantic meaning remains in the authoritative ontology/mapping registry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from three_maps.config.mapping_registry import SignalMappingRecord, SignalMappingRegistry
from three_maps.domain.types import (
    ActivationState, ApplicabilityState, AxisResult, PoleStrength, Signal,
    SystemScore, SystemScoreStatus, Target,
)
from three_maps.engines.evidence import SignalMapping, build_evidence_cluster, generate_signal
from three_maps.engines.relationship import RelationshipInput, RelationshipSystem, evaluate_relationship
from three_maps.engines.contradiction import ContradictionInput, evaluate_contradiction


@dataclass(frozen=True)
class MappingResolution:
    source_system: str
    source_variable: str
    mapping: SignalMappingRecord | None
    status: str
    reason: str | None = None


def resolve_mapping(registry: SignalMappingRegistry, *, source_system: str, source_variable: str) -> MappingResolution:
    """Resolve exactly one active mapping; absence is unavailable, never negative evidence."""
    matches = registry.active_for(source_system, source_variable)
    if not matches:
        return MappingResolution(source_system, source_variable, None, "UNAVAILABLE", "NO_ACTIVE_MAPPING")
    if len(matches) > 1:
        return MappingResolution(source_system, source_variable, None, "INVALID", "AMBIGUOUS_ACTIVE_MAPPING")
    return MappingResolution(source_system, source_variable, matches[0], "RESOLVED")


def mapping_record_to_signal_mapping(record: SignalMappingRecord) -> SignalMapping:
    return SignalMapping(
        source_system=record.source_system,
        source_variable=record.source_variable,
        theme_id=record.theme_id,
        sub_theme_id=record.sub_theme_id,
        axis_id=record.axis_id,
        pole_id=record.pole_id,
        mapping_confidence=record.mapping_confidence,
        methodology_version=record.methodology_version,
        ontology_version=record.ontology_version,
        calculation_version=record.calculation_version,
    )


@dataclass(frozen=True)
class NormalizedMapSignal:
    signal: Signal
    system: str
    axis_id: str
    pole_id: str
    evidence_cluster_ids: tuple[str, ...]
    semantic_level: str
    temporal_scope: str | None
    context_scope: str | None


def normalize_signals(signals: Iterable[Signal], *, target: Target) -> tuple[NormalizedMapSignal, ...]:
    """Normalize already-mapped signals to a common cross-map contract.

    Signals that are inactive, blocked, invalid for the target axis, or outside
    the target semantic unit are excluded from downstream relationship input.
    They remain upstream audit data and are not converted to zeros.
    """
    out: list[NormalizedMapSignal] = []
    for s in signals:
        if s.activation != ActivationState.ACTIVE:
            continue
        if s.applicability in {ApplicabilityState.BLOCKED, ApplicabilityState.NOT_APPLICABLE}:
            continue
        if target.axis_id is not None and s.axis_id != target.axis_id:
            continue
        if target.theme_id != s.theme_id:
            continue
        if target.sub_theme_id is not None and s.sub_theme_id not in {None, target.sub_theme_id}:
            continue
        out.append(NormalizedMapSignal(
            signal=s, system=s.source_system, axis_id=s.axis_id, pole_id=s.pole_id,
            evidence_cluster_ids=tuple(sorted(set(s.evidence_cluster_ids))),
            semantic_level="SUB_THEME" if s.sub_theme_id else "THEME",
            temporal_scope=s.temporal_scope, context_scope=s.context_scope,
        ))
    return tuple(out)


@dataclass(frozen=True)
class MapUnit:
    system: str
    target: Target
    axis: AxisResult | None
    system_score: SystemScore
    pole_strength: PoleStrength
    semantic_level: str
    temporal_scope: str | None
    context_scope: str | None
    evidence_cluster_ids: tuple[str, ...] = ()
    evidence_stream_count: int = 1
    material_qualification: bool = False

    @property
    def meaningful_a(self) -> bool:
        from three_maps.config.thresholds import TAU_P
        return self.pole_strength.pole_a >= TAU_P and self.pole_strength.pole_a >= self.pole_strength.pole_b

    @property
    def meaningful_b(self) -> bool:
        from three_maps.config.thresholds import TAU_P
        return self.pole_strength.pole_b >= TAU_P and self.pole_strength.pole_b > self.pole_strength.pole_a


def normalize_map_units(units: Sequence[MapUnit], *, target: Target) -> tuple[RelationshipSystem, ...]:
    """Convert map-specific units into the common RelationshipSystem contract."""
    out: list[RelationshipSystem] = []
    for u in units:
        if u.target.axis_id != target.axis_id or u.target.theme_id != target.theme_id:
            continue
        if u.system_score.status not in (SystemScoreStatus.EVALUATED, SystemScoreStatus.PARTIAL):
            continue
        if u.system_score.score is None:
            continue
        out.append(RelationshipSystem(
            system=u.system,
            pole_a_strength=u.pole_strength.pole_a,
            pole_b_strength=u.pole_strength.pole_b,
            semantic_level=u.semantic_level,
            temporal_scope=u.temporal_scope,
            context_scope=u.context_scope,
            semantic_similarity=1.0,
            evidence_stream_count=u.evidence_stream_count,
            evidence_cluster_ids=u.evidence_cluster_ids,
            meaningful=True,
            material_qualification=u.material_qualification,
        ))
    return tuple(out)


@dataclass(frozen=True)
class PhaseIRelationshipResult:
    relationship: object
    contradiction: object
    systems: tuple[RelationshipSystem, ...]
    systems_a: tuple[RelationshipSystem, ...]
    systems_b: tuple[RelationshipSystem, ...]


def evaluate_phase1_relationship(*, relationship_id: str, target: Target,
                                 units: Sequence[MapUnit], independence: float = 0.0,
                                 context_resolution: bool = False) -> PhaseIRelationshipResult:
    systems = normalize_map_units(units, target=target)
    relationship = evaluate_relationship(RelationshipInput(
        relationship_id=relationship_id, target=target, systems=systems,
        target_semantic_level=target.semantic_level,
        target_temporal_scope=target.temporal_scope,
        target_context_scope=target.context_scope,
        context_resolution=context_resolution, independence=independence,
    ))
    systems_a = tuple(s for s in systems if s.meaningful_a and not s.meaningful_b)
    systems_b = tuple(s for s in systems if s.meaningful_b and not s.meaningful_a)
    a = max((s.pole_a_strength for s in systems_a), default=0.0)
    b = max((s.pole_b_strength for s in systems_b), default=0.0)
    contradiction = evaluate_contradiction(ContradictionInput(
        axis_id=target.axis_id or "", pole_a_strength=a, pole_b_strength=b,
        systems_a=systems_a, systems_b=systems_b,
        same_semantic_level=relationship.same_semantic_level,
        semantic_similarity=relationship.semantic_similarity,
        temporal_compatibility=relationship.temporal_compatibility,
        context_resolution=relationship.context_resolution,
        independence=independence, same_axis=True,
    ))
    return PhaseIRelationshipResult(relationship, contradiction, systems, systems_a, systems_b)
