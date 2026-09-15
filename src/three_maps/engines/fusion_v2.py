"""Fusion Intelligence v2 (201.81L).

Adds explicit temporal salience and coverage diagnostics around the canonical
Fusion Strength formula without changing the formula's meaning or treating
salience as a probability.
"""
from __future__ import annotations
from dataclasses import dataclass
from three_maps.engines.fusion import FusionContext, calculate_fusion_result
from three_maps.domain.types import FusionResult, RelationshipState, SystemScore, SystemScoreStatus


@dataclass(frozen=True)
class FusionV2Context:
    system_scores: tuple[SystemScore, ...]
    relationship_state: RelationshipState = RelationshipState.S0
    meaningful_system_count: int = 0
    independence: float = 0.0
    contradiction_strength: float = 0.0
    temporal_salience: float | None = None
    expected_temporal_coverage: float | None = None


@dataclass(frozen=True)
class FusionV2Result:
    canonical: FusionResult
    temporal_salience: float | None
    temporal_coverage: float | None
    interpretation_readiness: str
    diagnostic_flags: tuple[str, ...]


def calculate_fusion_v2(ctx: FusionV2Context) -> FusionV2Result:
    canonical = calculate_fusion_result(FusionContext(
        system_scores=ctx.system_scores,
        relationship_state=ctx.relationship_state,
        meaningful_system_count=ctx.meaningful_system_count,
        independence=ctx.independence,
        contradiction_strength=ctx.contradiction_strength,
    ))
    flags: list[str] = []
    if ctx.temporal_salience is not None and not 0 <= ctx.temporal_salience <= 1:
        raise ValueError("temporal_salience must be between 0 and 1")
    if ctx.expected_temporal_coverage is not None and not 0 <= ctx.expected_temporal_coverage <= 1:
        raise ValueError("expected_temporal_coverage must be between 0 and 1")
    if ctx.temporal_salience is None:
        flags.append("TEMPORAL_SALIENCE_UNAVAILABLE")
    if ctx.expected_temporal_coverage is not None and ctx.expected_temporal_coverage < .60:
        flags.append("TEMPORAL_COVERAGE_LOW")
    if canonical.valid_system_count < 2:
        flags.append("MULTI_MAP_REINFORCEMENT_LIMITED")
    if canonical.data_confidence < .60:
        flags.append("DATA_CONFIDENCE_LOW")
    readiness = "READY" if canonical.valid_system_count and canonical.data_confidence >= .60 else "QUALIFIED"
    return FusionV2Result(canonical, ctx.temporal_salience, ctx.expected_temporal_coverage,
                          readiness, tuple(flags))
