"""Cross-engine integration boundary for THE THREE MAPS.

This module composes already-validated engine outputs. It does not recalculate
Astrology, Numerology, Palmistry, evidence, or ontology rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from three_maps.domain.types import (
    AxisDirectionState, FusionResult, RelationshipResult, RelationshipState,
    SystemScore, Target, ContradictionResult,
)
from three_maps.engines.contradiction import ContradictionInput, evaluate_contradiction
from three_maps.engines.fusion import FusionContext, calculate_fusion_result
from three_maps.engines.relationship import (
    RelationshipInput, RelationshipSystem, evaluate_relationship,
)


@dataclass(frozen=True)
class MapEvaluation:
    """Validated output from one map for one Relationship Unit."""
    system: str
    axis_id: str
    pole_a_strength: float
    pole_b_strength: float
    system_score: SystemScore
    semantic_level: str
    temporal_scope: str | None = None
    context_scope: str | None = None
    semantic_similarity: float = 1.0
    evidence_stream_count: int = 1
    evidence_cluster_ids: tuple[str, ...] = ()
    material_qualification: bool = False


@dataclass(frozen=True)
class CrossEngineInput:
    integration_id: str
    target: Target
    maps: Sequence[MapEvaluation]
    independence: float = 0.0
    context_resolution: bool = False


@dataclass(frozen=True)
class CrossEngineResult:
    integration_id: str
    system_scores: tuple[SystemScore, ...]
    relationship: RelationshipResult
    contradiction: ContradictionResult
    fusion: FusionResult


def _relationship_systems(maps: Sequence[MapEvaluation]) -> tuple[RelationshipSystem, ...]:
    return tuple(
        RelationshipSystem(
            system=m.system,
            pole_a_strength=m.pole_a_strength,
            pole_b_strength=m.pole_b_strength,
            semantic_level=m.semantic_level,
            temporal_scope=m.temporal_scope,
            context_scope=m.context_scope,
            semantic_similarity=m.semantic_similarity,
            evidence_stream_count=m.evidence_stream_count,
            evidence_cluster_ids=m.evidence_cluster_ids,
            meaningful=m.system_score.score is not None,
            material_qualification=m.material_qualification,
        )
        for m in maps
        if m.system_score.score is not None
    )


def integrate_cross_engine(x: CrossEngineInput) -> CrossEngineResult:
    """Compose map outputs through Relationship → Contradiction → Fusion.

    System scores are consumed as-is. The function deliberately does not turn
    unavailable/invalid scores into zeros and does not invent evidence.
    """
    if not x.maps:
        raise ValueError("At least one map evaluation is required")
    axis_ids = {m.axis_id for m in x.maps}
    if len(axis_ids) != 1 or x.target.axis_id not in axis_ids:
        raise ValueError("All map evaluations must target the same axis")
    systems = _relationship_systems(x.maps)
    relationship = evaluate_relationship(
        RelationshipInput(
            relationship_id=f"REL-{x.integration_id}",
            target=x.target,
            systems=systems,
            target_semantic_level=x.target.semantic_level,
            target_temporal_scope=x.target.temporal_scope,
            target_context_scope=x.target.context_scope,
            context_resolution=x.context_resolution,
            independence=x.independence,
        )
    )

    # Opposition streams are derived from directional evidence, not aggregate polarity.
    systems_a = tuple(s for s in systems if s.meaningful_a and not s.meaningful_b)
    systems_b = tuple(s for s in systems if s.meaningful_b and not s.meaningful_a)
    representative_a = max((m.pole_a_strength for m in x.maps), default=0.0)
    representative_b = max((m.pole_b_strength for m in x.maps), default=0.0)
    contradiction = evaluate_contradiction(
        ContradictionInput(
            axis_id=x.target.axis_id or "",
            pole_a_strength=representative_a,
            pole_b_strength=representative_b,
            systems_a=systems_a,
            systems_b=systems_b,
            same_semantic_level=relationship.same_semantic_level,
            semantic_similarity=relationship.semantic_similarity,
            temporal_compatibility=relationship.temporal_compatibility,
            context_resolution=relationship.context_resolution,
            independence=x.independence,
            same_axis=True,
        )
    )

    fusion = calculate_fusion_result(
        FusionContext(
            system_scores=tuple(m.system_score for m in x.maps),
            relationship_state=contradiction.state if contradiction.validated_opposition else relationship.state,
            meaningful_system_count=len(relationship.meaningful_systems),
            independence=x.independence,
            contradiction_strength=contradiction.contradiction_strength or 0.0,
        )
    )
    return CrossEngineResult(
        integration_id=x.integration_id,
        system_scores=tuple(m.system_score for m in x.maps),
        relationship=relationship,
        contradiction=contradiction,
        fusion=fusion,
    )
