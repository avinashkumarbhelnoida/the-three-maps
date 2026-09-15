from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from three_maps.config.thresholds import TAU_B, TAU_I, TAU_P, TAU_S
from three_maps.domain.types import ContradictionResult, OppositionCandidate, RelationshipState, ValidatedOpposition
from three_maps.engines.relationship import RelationshipSystem


@dataclass(frozen=True)
class ContradictionInput:
    axis_id: str
    pole_a_strength: float
    pole_b_strength: float
    systems_a: tuple[RelationshipSystem, ...]
    systems_b: tuple[RelationshipSystem, ...]
    same_semantic_level: bool
    semantic_similarity: float
    temporal_compatibility: bool
    context_resolution: bool
    independence: float
    same_axis: bool = True


def build_opposition_candidate(x: ContradictionInput) -> OppositionCandidate:
    streams = sum(s.evidence_stream_count for s in x.systems_a + x.systems_b)
    clusters = [cid for s in x.systems_a + x.systems_b for cid in s.evidence_cluster_ids]
    distinct = len(clusters) == len(set(clusters)) if clusters else False
    formal_opposing = bool(x.systems_a and x.systems_b)
    dual = x.pole_a_strength >= TAU_P and x.pole_b_strength >= TAU_P
    return OppositionCandidate(
        axis_id=x.axis_id,
        pole_a_strength=x.pole_a_strength,
        pole_b_strength=x.pole_b_strength,
        contributing_systems_a=[s.system for s in x.systems_a],
        contributing_systems_b=[s.system for s in x.systems_b],
        dual_pole_support=dual,
        formal_opposing_direction=formal_opposing,
        same_semantic_level=x.same_semantic_level,
        same_axis=x.same_axis,
        semantic_similarity=x.semantic_similarity,
        temporal_compatibility=x.temporal_compatibility,
        context_resolution=x.context_resolution,
        evidence_stream_count=streams,
        evidence_cluster_separation=distinct,
    )


def validate_opposition(candidate: OppositionCandidate) -> ValidatedOpposition:
    failures: list[str] = []
    if candidate.pole_a_strength < TAU_P: failures.append("A_BELOW_TAU_P")
    if candidate.pole_b_strength < TAU_P: failures.append("B_BELOW_TAU_P")
    if not candidate.formal_opposing_direction: failures.append("NO_FORMAL_OPPOSITION")
    if not candidate.same_semantic_level: failures.append("SEMANTIC_LEVEL_MISMATCH")
    if not candidate.same_axis: failures.append("AXIS_MISMATCH")
    if candidate.semantic_similarity < TAU_S: failures.append("SEMANTIC_SIMILARITY_BELOW_TAU_S")
    if not candidate.temporal_compatibility: failures.append("TEMPORAL_MISMATCH")
    if candidate.context_resolution: failures.append("CONTEXT_RESOLVED")
    if candidate.evidence_stream_count < 2: failures.append("INSUFFICIENT_EVIDENCE_STREAMS")
    if not candidate.evidence_cluster_separation: failures.append("EVIDENCE_CLUSTERS_NOT_DISTINCT")
    ok = not failures
    return ValidatedOpposition(candidate=candidate, validated_meaningful_opposition=ok, reason=None if ok else ";".join(failures))


def evaluate_contradiction(x: ContradictionInput) -> ContradictionResult:
    candidate = build_opposition_candidate(x)
    vmo = validate_opposition(candidate)
    dominant = max(x.pole_a_strength, x.pole_b_strength)
    opposing = min(x.pole_a_strength, x.pole_b_strength)
    balance = opposing / dominant if dominant else None
    gates = {
        "G1_A_MEANINGFUL": x.pole_a_strength >= TAU_P,
        "G2_B_MEANINGFUL": x.pole_b_strength >= TAU_P,
        "G3_FORMAL_OPPOSING_DIRECTION": candidate.formal_opposing_direction,
        "G4_SAME_SEMANTIC_LEVEL": candidate.same_semantic_level,
        "G5_SAME_AXIS": candidate.same_axis,
        "G6_SEMANTIC_COMPARABILITY": candidate.semantic_similarity >= TAU_S,
        "G7_TEMPORAL_COMPATIBILITY": candidate.temporal_compatibility,
        "G8_CONTEXT_UNRESOLVED": not candidate.context_resolution,
        "G9_EVIDENCE_STREAMS": candidate.evidence_stream_count >= 2,
        "G10_EVIDENCE_CLUSTERS_DISTINCT": candidate.evidence_cluster_separation,
        "G11_INDEPENDENCE": x.independence >= TAU_I,
        "G12_BALANCE": balance is not None and balance >= TAU_B,
    }
    if not vmo.validated_meaningful_opposition:
        return ContradictionResult(
            axis_id=x.axis_id, state=RelationshipState.S0,
            pole_a_strength=x.pole_a_strength, pole_b_strength=x.pole_b_strength,
            balance_ratio=balance, contradiction_strength=None, gates=gates,
            validated_opposition=False,
        )
    s7 = gates["G11_INDEPENDENCE"] and gates["G12_BALANCE"]
    if s7:
        pcs = min(x.pole_a_strength, x.pole_b_strength)
        # Opposition strength is established by validated opposing streams, not aggregate polarity.
        opp = 1.0
        independence_modifier = 0.50 + 0.50 * max(0.0, min(1.0, x.independence))
        cs = max(0.0, min(1.0, pcs * opp * independence_modifier))
        state = RelationshipState.S7
    else:
        cs = None
        state = RelationshipState.S6
    return ContradictionResult(
        axis_id=x.axis_id, state=state,
        pole_a_strength=x.pole_a_strength, pole_b_strength=x.pole_b_strength,
        balance_ratio=balance, contradiction_strength=cs, gates=gates,
        validated_opposition=True,
    )
