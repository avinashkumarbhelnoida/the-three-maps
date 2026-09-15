"""Canonical THE THREE MAPS Fusion Engine."""
from dataclasses import dataclass
from typing import Sequence

from three_maps.domain.types import RelationshipState, SystemScore, SystemScoreStatus, FusionResult

LABELS = ((20, "INSUFFICIENT"), (40, "LOW"), (60, "MODERATE"), (75, "STRONG"), (90, "HIGH"), (101, "VERY HIGH"))

@dataclass(frozen=True)
class FusionInput:
    base: float
    convergence_bonus: float
    independence_bonus: float
    contradiction_strength: float = 0.0
    valid_system_count: int = 0
    meaningful_system_count: int = 0
    dominant_map: str | None = None
    data_confidence: float = 1.0
    coverage: float = 1.0

@dataclass(frozen=True)
class FusionContext:
    system_scores: Sequence[SystemScore]
    relationship_state: RelationshipState = RelationshipState.S0
    meaningful_system_count: int | None = None
    independence: float = 0.0
    contradiction_strength: float = 0.0


def _label(score: float) -> str:
    for ceiling, label in LABELS:
        if score < ceiling:
            return label
    return "VERY HIGH"


def calculate_fusion(x: FusionInput) -> float:
    """Return canonical Fusion Strength on a 0-100 scale."""
    raw = x.base + x.convergence_bonus + x.independence_bonus - (0.20 * x.contradiction_strength)
    return 100.0 * max(0.0, min(1.0, raw))


def calculate_fusion_result(ctx: FusionContext) -> FusionResult:
    """Calculate B, bonuses, S7-only penalty, and final Fusion Strength."""
    valid = [s for s in ctx.system_scores if s.status in (SystemScoreStatus.EVALUATED, SystemScoreStatus.PARTIAL) and s.score is not None]
    if not valid:
        return FusionResult(base=0.0, convergence_bonus=0.0, independence_bonus=0.0,
            contradiction_penalty=0.0, raw_score=0.0, final_score=0.0,
            label="INSUFFICIENT", valid_system_count=0,
            meaningful_system_count=ctx.meaningful_system_count or 0,
            data_confidence=0.0, coverage=0.0)

    base = sum(s.score for s in valid) / len(valid)
    k = len(valid)
    convergence_bonus = 0.20 * base * ((k - 1) / 2) if k >= 1 else 0.0
    independence_bonus = 0.10 * base * max(0.0, min(1.0, ctx.independence))
    # Only formal S7 is allowed to create the contradiction penalty.
    contradiction_penalty = 0.20 * max(0.0, min(1.0, ctx.contradiction_strength)) if ctx.relationship_state == RelationshipState.S7 else 0.0
    raw = base + convergence_bonus + independence_bonus - contradiction_penalty
    final = 100.0 * max(0.0, min(1.0, raw))
    confidence = sum(s.data_confidence for s in valid) / len(valid)
    coverage = sum(s.coverage for s in valid) / len(valid)
    meaningful = ctx.meaningful_system_count if ctx.meaningful_system_count is not None else 0
    dominant = max(valid, key=lambda s: s.score).system if valid else None
    return FusionResult(base=base, convergence_bonus=convergence_bonus,
        independence_bonus=independence_bonus, contradiction_penalty=contradiction_penalty,
        raw_score=raw, final_score=final, label=_label(final),
        valid_system_count=k, meaningful_system_count=meaningful,
        dominant_map=dominant, data_confidence=confidence, coverage=coverage)
