from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from three_maps.config.thresholds import TAU_P, TAU_S
from three_maps.domain.types import (
    AxisDirectionState, RelationshipResult, RelationshipState, SystemScore, SystemScoreStatus,
    Target,
)


@dataclass(frozen=True)
class RelationshipSystem:
    system: str
    pole_a_strength: float
    pole_b_strength: float
    semantic_level: str
    temporal_scope: str | None = None
    context_scope: str | None = None
    semantic_similarity: float = 1.0
    evidence_stream_count: int = 1
    evidence_cluster_ids: tuple[str, ...] = ()
    meaningful: bool = True
    material_qualification: bool = False
    axis_direction: AxisDirectionState | None = None

    @property
    def meaningful_a(self) -> bool:
        return self.meaningful and self.pole_a_strength >= TAU_P

    @property
    def meaningful_b(self) -> bool:
        return self.meaningful and self.pole_b_strength >= TAU_P


@dataclass(frozen=True)
class RelationshipInput:
    relationship_id: str
    target: Target
    systems: tuple[RelationshipSystem, ...]
    target_semantic_level: str | None = None
    target_temporal_scope: str | None = None
    target_context_scope: str | None = None
    context_resolution: bool = False
    independence: float | None = None


def _valid_systems(systems: Iterable[RelationshipSystem]) -> list[RelationshipSystem]:
    return [s for s in systems if s.meaningful]


def _same_level(systems: list[RelationshipSystem], target_level: str | None) -> bool:
    if not systems:
        return False
    level = target_level or systems[0].semantic_level
    return all(s.semantic_level == level for s in systems)


def _temporal_compatible(systems: list[RelationshipSystem], target_scope: str | None) -> bool:
    if not systems:
        return False
    scopes = [s.temporal_scope for s in systems if s.temporal_scope is not None]
    if target_scope is not None:
        scopes.append(target_scope)
    return len(set(scopes)) <= 1 or not scopes


def _context_resolved(inp: RelationshipInput) -> bool:
    return inp.context_resolution


def _clusters_distinct(systems: list[RelationshipSystem]) -> bool:
    clusters: list[str] = []
    for s in systems:
        clusters.extend(s.evidence_cluster_ids)
    return len(clusters) == len(set(clusters)) if clusters else True


def _direction_groups(systems: list[RelationshipSystem]) -> tuple[list[RelationshipSystem], list[RelationshipSystem]]:
    a = [s for s in systems if s.meaningful_a and not s.meaningful_b]
    b = [s for s in systems if s.meaningful_b and not s.meaningful_a]
    return a, b


def evaluate_relationship(inp: RelationshipInput) -> RelationshipResult:
    systems = _valid_systems(inp.systems)
    participating = [s.system for s in systems]
    same_level = _same_level(systems, inp.target_semantic_level)
    temporal = _temporal_compatible(systems, inp.target_temporal_scope)
    context_resolved = _context_resolved(inp)

    a_support, b_support = _direction_groups(systems)
    meaningful_poles: list[str] = []
    if a_support:
        meaningful_poles.append("A")
    if b_support:
        meaningful_poles.append("B")

    n_a, n_b = len(a_support), len(b_support)
    opposing = n_a > 0 and n_b > 0
    bdc_a = n_a >= 2 and n_b == 0
    bdc_b = n_b >= 2 and n_a == 0
    bdc = (bdc_a or bdc_b) and same_level and temporal and not context_resolved

    # Two-sided opposition is not yet S6/S7 here; contradiction validation owns that state.
    # Relationship Engine may identify tension, but formal S7 is explicitly prohibited here.
    if opposing and same_level and temporal and not context_resolved:
        # Opposition is a condition for the Contradiction Engine; Relationship does not own S6/S7.
        state = RelationshipState.S0
        direction = "MIXED"
    elif bdc:
        direction = "A" if bdc_a else "B"
        material_qualification = any(s.material_qualification for s in systems)
        if len(systems) >= 3 and not material_qualification:
            state = RelationshipState.S3
        elif len(systems) >= 2 and material_qualification:
            state = RelationshipState.S5
        else:
            state = RelationshipState.S2
    elif len(systems) == 1:
        direction = "A" if systems[0].meaningful_a else "B" if systems[0].meaningful_b else None
        state = RelationshipState.S1 if direction else RelationshipState.S0
    elif not systems:
        direction = None
        state = RelationshipState.S0
    else:
        direction = None
        state = RelationshipState.S0

    # S4 requires differentiated/independent reinforcement. It is a refinement of clean 3-map convergence.
    if state == RelationshipState.S3 and inp.independence is not None and inp.independence >= 0.50 and _clusters_distinct(systems):
        state = RelationshipState.S4

    # A two-map convergence with a third participating but balanced/non-directional map is qualified convergence only
    # when that qualification is explicitly material; otherwise it remains S2.
    if state == RelationshipState.S2 and len(systems) >= 3 and any(s.material_qualification for s in systems):
        state = RelationshipState.S5

    semantic_similarity = min((s.semantic_similarity for s in systems), default=0.0)
    stream_count = sum(s.evidence_stream_count for s in systems)
    separation = _clusters_distinct(systems)

    return RelationshipResult(
        relationship_id=inp.relationship_id,
        target=inp.target,
        participating_systems=participating,
        meaningful_systems=participating,
        meaningful_poles=meaningful_poles,
        direction=direction,
        state=state,
        broad_directional_convergence=bdc,
        semantic_similarity=semantic_similarity,
        same_semantic_level=same_level,
        temporal_compatibility=temporal,
        context_resolution=context_resolved,
        independence=None,
        evidence_stream_count=stream_count,
        evidence_cluster_separation=separation,
    )
