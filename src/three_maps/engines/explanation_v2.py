"""Explanation v2 (201.81M): evidence-first interpretive synthesis."""
from __future__ import annotations
from dataclasses import dataclass
from three_maps.engines.fusion_v2 import FusionV2Result
from three_maps.engines.explanation import ExplanationContext, build_explanation, validate_explanation
from three_maps.domain.types import RelationshipResult, ContradictionResult, AxisDirectionState, SystemScore


@dataclass(frozen=True)
class ExplanationV2Context:
    explanation: ExplanationContext
    fusion_v2: FusionV2Result
    timing_statement: str | None = None
    interpretive_meaning: str | None = None


def build_explanation_v2(ctx: ExplanationV2Context):
    base = build_explanation(ctx.explanation)
    parts = [base.summary]
    if ctx.timing_statement:
        parts.append(ctx.timing_statement)
    if ctx.interpretive_meaning:
        parts.append(ctx.interpretive_meaning)
    readiness = f"Interpretation readiness: {ctx.fusion_v2.interpretation_readiness}."
    parts.append(readiness)
    return base.model_copy(update={"summary": " ".join(parts), "interpretation":
        (base.interpretation + " " + (ctx.interpretive_meaning or "") + " " + readiness).strip()})


def validate_explanation_v2(explanation) -> list[str]:
    errors = validate_explanation(explanation)
    text = " ".join([explanation.summary, explanation.interpretation, explanation.practical_reflection]).lower()
    prohibited = ("probability", "diagnos", "guaranteed", "certainly", "will happen")
    for term in prohibited:
        if term in text and term != "probability":
            errors.append(f"UNSUPPORTED_DETERMINISTIC_OR_DIAGNOSTIC_LANGUAGE:{term}")
    return errors
