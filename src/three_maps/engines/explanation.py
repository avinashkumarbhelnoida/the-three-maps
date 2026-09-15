"""Read-only explanation engine for THE THREE MAPS.

This layer translates already validated structured outputs into user-facing
language. It never recalculates scores, creates evidence, or upgrades a state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from three_maps.domain.types import (
    AxisDirectionState,
    Claim,
    ClaimType,
    ContradictionResult,
    Explanation,
    FusionResult,
    RelationshipResult,
    RelationshipState,
    SystemScore,
    SystemScoreStatus,
)


@dataclass(frozen=True)
class ExplanationContext:
    explanation_id: str
    fusion_unit_id: str
    fusion: FusionResult
    relationship: RelationshipResult | None = None
    contradiction: ContradictionResult | None = None
    system_scores: Sequence[SystemScore] = ()
    direction_state: AxisDirectionState | None = None
    pole_a_name: str = "Pole A"
    pole_b_name: str = "Pole B"
    methodology_version: str = "MV-0.1.0"
    calculation_version: str = "CV-0.1.0"
    lineage_ids: Sequence[str] = ()
    explanation_depth: str = "STANDARD"


def _strength_label(score: float) -> str:
    if score < 20:
        return "INSUFFICIENT"
    if score < 40:
        return "LOW"
    if score < 60:
        return "MODERATE"
    if score < 75:
        return "STRONG"
    if score < 90:
        return "HIGH"
    return "VERY HIGH"


def _direction_text(state: AxisDirectionState | None, a: str, b: str) -> str | None:
    if state is None:
        return None
    return {
        AxisDirectionState.INSUFFICIENT: "The available evidence is insufficient to establish a meaningful direction.",
        AxisDirectionState.A_ONE_SIDED_SUPPORT: f"The evidence supports {a}, but {b} does not reach the meaningful-support threshold.",
        AxisDirectionState.B_ONE_SIDED_SUPPORT: f"The evidence supports {b}, but {a} does not reach the meaningful-support threshold.",
        AxisDirectionState.A_DOMINANT: f"{a} is the materially dominant direction in the evaluated evidence.",
        AxisDirectionState.B_DOMINANT: f"{b} is the materially dominant direction in the evaluated evidence.",
        AxisDirectionState.MEANINGFUL_TIE: f"Both {a} and {b} reach meaningful support and remain within the defined tie tolerance.",
        AxisDirectionState.BALANCED: f"Both {a} and {b} are represented, but neither direction establishes material dominance.",
    }[state]


def _system_statements(scores: Sequence[SystemScore]) -> list[str]:
    out: list[str] = []
    for s in scores:
        if s.status == SystemScoreStatus.INVALID:
            out.append(f"{s.system}: excluded because the target-level result is invalid.")
        elif s.status == SystemScoreStatus.UNAVAILABLE:
            out.append(f"{s.system}: unavailable; no valid system score is included.")
        elif s.status == SystemScoreStatus.PARTIAL:
            out.append(f"{s.system}: {s.score:.2f} system score, with {s.coverage:.0%} expected relevant evidence coverage (PARTIAL).")
        else:
            out.append(f"{s.system}: {s.score:.2f} system score (EVALUATED).")
    return out


def _relationship_text(r: RelationshipResult | None) -> str | None:
    if r is None:
        return None
    labels = {
        RelationshipState.S0: "The maps do not provide enough validated directional evidence for a relationship conclusion.",
        RelationshipState.S1: "A meaningful signal is present in a single map.",
        RelationshipState.S2: "Two maps provide meaningful directional support in the same direction.",
        RelationshipState.S3: "All three maps provide clean meaningful directional convergence.",
        RelationshipState.S4: "The maps show clean convergence with differentiated evidence supporting the relationship.",
        RelationshipState.S5: "The maps show convergence with a material qualification that should remain visible in interpretation.",
        RelationshipState.S6: "Meaningful opposing evidence is present, indicating tension rather than a formal contradiction.",
        RelationshipState.S7: "A formal contradiction state is recorded by the contradiction engine.",
    }
    return labels[r.state]


def _contradiction_text(c: ContradictionResult | None) -> str | None:
    if c is None:
        return None
    if c.state == RelationshipState.S7 and c.validated_opposition:
        strength = f" Contradiction strength is {c.contradiction_strength:.2f}." if c.contradiction_strength is not None else ""
        return "Formal contradiction is established after the required validation gates passed." + strength
    if c.validated_opposition and c.state == RelationshipState.S6:
        return "Validated meaningful opposition remains, but the formal S7 gates are not all satisfied; the result is classified as tension (S6)."
    return "No formal contradiction is established by the contradiction engine."


def _qualification(scores: Sequence[SystemScore]) -> str | None:
    partial = [s for s in scores if s.status == SystemScoreStatus.PARTIAL]
    unavailable = [s for s in scores if s.status == SystemScoreStatus.UNAVAILABLE]
    invalid = [s for s in scores if s.status == SystemScoreStatus.INVALID]
    parts = []
    if partial:
        parts.append("Some system evidence is partial; its valid score is retained while coverage remains qualified.")
    if unavailable:
        parts.append("Unavailable systems are omitted rather than treated as negative evidence or zero scores.")
    if invalid:
        parts.append("Invalid system results are excluded from downstream scoring.")
    return " ".join(parts) if parts else None


def build_explanation(ctx: ExplanationContext) -> Explanation:
    """Build a deterministic, traceable explanation from validated outputs."""
    f = ctx.fusion
    label = f.label or _strength_label(f.final_score)
    direction = _direction_text(ctx.direction_state, ctx.pole_a_name, ctx.pole_b_name)
    relationship = _relationship_text(ctx.relationship)
    contradiction = _contradiction_text(ctx.contradiction)
    qualification = _qualification(ctx.system_scores)

    result = f"Fusion Strength is {f.final_score:.2f}/100 ({label})."
    summary = result
    if relationship:
        summary += " " + relationship

    interpretation = (
        "This explanation describes the validated analytical result; it does not convert Fusion Strength into a probability, "
        "diagnosis, or deterministic prediction."
    )
    practical = (
        "Use the result as a structured reflection aid, keeping the stated direction, relationship state, qualifications, and data limitations in view."
    )

    claims: list[Claim] = [
        Claim(id=f"{ctx.explanation_id}:result", claim_type=ClaimType.FACTUAL_ENGINE_CLAIM,
              text=result, source_ids=[ctx.fusion_unit_id], validated=True),
    ]
    if relationship and ctx.relationship:
        claims.append(Claim(id=f"{ctx.explanation_id}:relationship", claim_type=ClaimType.RELATIONSHIP_CLAIM,
                             text=relationship, source_ids=[ctx.relationship.relationship_id], validated=True))
    if contradiction and ctx.contradiction:
        claims.append(Claim(id=f"{ctx.explanation_id}:contradiction", claim_type=ClaimType.RELATIONSHIP_CLAIM,
                             text=contradiction, source_ids=[ctx.contradiction.axis_id], validated=True))
    if qualification:
        claims.append(Claim(id=f"{ctx.explanation_id}:qualification", claim_type=ClaimType.QUALIFICATION,
                             text=qualification, source_ids=[s.system for s in ctx.system_scores], validated=True))
    claims.append(Claim(id=f"{ctx.explanation_id}:caution", claim_type=ClaimType.CAUTION,
                        text=interpretation, source_ids=[ctx.fusion_unit_id], validated=True))

    return Explanation(
        explanation_id=ctx.explanation_id,
        fusion_unit_id=ctx.fusion_unit_id,
        summary=summary,
        result_statement=result,
        direction_statement=direction,
        system_contributions=_system_statements(ctx.system_scores),
        relationship_statement=relationship,
        contradiction_statement=contradiction,
        qualification_statement=qualification,
        interpretation=interpretation,
        practical_reflection=practical,
        strength_label=label,
        confidence_statement=f"Data Confidence is {f.data_confidence:.0%}; this is separate from Fusion Strength.",
        coverage_statement=f"Reported coverage is {f.coverage:.0%}; coverage is diagnostic and is not used to multiply the Fusion Strength.",
        claim_objects=claims,
        explanation_depth=ctx.explanation_depth,
        methodology_version=ctx.methodology_version,
        calculation_version=ctx.calculation_version,
        lineage_ids=list(ctx.lineage_ids),
    )


def validate_explanation(explanation: Explanation) -> list[str]:
    """Return violations of the Explanation Engine safety/traceability contract."""
    errors: list[str] = []
    if not explanation.result_statement.strip():
        errors.append("RESULT_EMPTY")
    if explanation.strength_label not in {"INSUFFICIENT", "LOW", "MODERATE", "STRONG", "HIGH", "VERY HIGH"}:
        errors.append("INVALID_STRENGTH_LABEL")
    if not explanation.methodology_version or not explanation.calculation_version:
        errors.append("MISSING_VERSION")
    for claim in explanation.claim_objects:
        if not claim.validated:
            errors.append(f"UNVALIDATED_CLAIM:{claim.id}")
        if not claim.source_ids:
            errors.append(f"ORPHAN_CLAIM:{claim.id}")
    return errors
