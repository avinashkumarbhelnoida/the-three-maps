"""Master adversarial invariants for Phase III.

These are executable safety/integrity checks rather than probabilistic tests.
Each invariant is intentionally small and maps to a known architectural rule.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class AdversarialCheck:
    id: str
    priority: str
    description: str
    passed: bool
    reason: str = ""

@dataclass(frozen=True)
class AdversarialReport:
    checks: tuple[AdversarialCheck, ...]
    @property
    def blockers(self) -> int:
        return sum(1 for c in self.checks if c.priority == "P0" and not c.passed)
    @property
    def failures(self) -> int:
        return sum(1 for c in self.checks if not c.passed)


def run_master_adversarial_suite() -> AdversarialReport:
    checks: list[AdversarialCheck] = []
    from three_maps.domain.types import SystemScoreStatus, RelationshipState, Signal, IndicatorWeightClass, ApplicabilityState, ActivationState, Target
    from three_maps.engines.fusion import FusionContext, calculate_fusion_result
    from three_maps.engines.relationship import RelationshipInput, RelationshipSystem, evaluate_relationship
    from three_maps.engines.system_score import SystemScoreIndicator, SystemScoreInput, calculate_system_score

    def add(cid: str, priority: str, desc: str, fn: Callable[[], bool]) -> None:
        try:
            ok = bool(fn()); reason = "" if ok else "invariant violated"
        except Exception as exc: ok = False; reason = f"exception: {type(exc).__name__}: {exc}"
        checks.append(AdversarialCheck(cid, priority, desc, ok, reason))

    def sig(i: str, strength: int = 4, cluster: str | None = None) -> Signal:
        return Signal(id=i, source_system="TEST", source_variable="X", evidence_ids=["raw"+i], evidence_cluster_ids=[cluster or "c"+i], theme_id="T1", axis_id="A01", pole_id="P-A", strength=strength, confidence=1, relevance=1, weight_class=IndicatorWeightClass.STANDARD, applicability=ApplicabilityState.CORE, activation=ActivationState.ACTIVE, methodology_version="MV-0.1", calculation_version="CV-0.1")

    add("P0-001", "P0", "Unavailable systems are excluded, never zero-filled", lambda: calculate_fusion_result(FusionContext((_score("A", .8), _score("B", None, SystemScoreStatus.UNAVAILABLE, 0, 0)))).base == .8)
    add("P0-002", "P0", "Invalid systems are excluded from fusion", lambda: calculate_fusion_result(FusionContext((_score("A", .8), _score("B", None, SystemScoreStatus.INVALID, 0, 0)))).valid_system_count == 1)
    add("P0-003", "P0", "S6 never creates a fusion contradiction penalty", lambda: calculate_fusion_result(FusionContext((_score("A", .7), _score("B", .7)), RelationshipState.S6, contradiction_strength=1)).contradiction_penalty == 0)
    add("P0-004", "P0", "Only S7 can create a contradiction penalty", lambda: calculate_fusion_result(FusionContext((_score("A", .7), _score("B", .7)), RelationshipState.S7, contradiction_strength=1)).contradiction_penalty > 0)
    add("P0-005", "P0", "A 2-v-1 split is not convergence", lambda: not evaluate_relationship(RelationshipInput("r", _target(), (_sys("A",.8,.1,"a"),_sys("B",.8,.1,"b"),_sys("C",.1,.8,"c")))).broad_directional_convergence)
    add("P0-006", "P0", "Same evidence cluster cannot establish independent reinforcement", lambda: not evaluate_relationship(RelationshipInput("r", _target(), (_sys("A",.8,.1,"same"),_sys("B",.8,.1,"same"),_sys("C",.8,.1,"same")), independence=.9)).evidence_cluster_separation)
    add("P0-007", "P0", "Semantic mismatch blocks convergence", lambda: evaluate_relationship(RelationshipInput("r", _target(), (_sys("A",.8,.1,"a",level="AXIS"),_sys("B",.8,.1,"b",level="THEME")))).state == RelationshipState.S0)
    add("P0-008", "P0", "Context-resolved opposition cannot be formal contradiction", lambda: _contradiction_state(context=True) == RelationshipState.S0)
    add("P0-009", "P0", "Temporal mismatch cannot be formal contradiction", lambda: _contradiction_state(temporal=False) == RelationshipState.S0)
    add("P0-010", "P0", "Weak opposing evidence cannot create formal opposition", lambda: _contradiction_state(a=.8,b=.59) == RelationshipState.S0)
    add("P0-011", "P0", "Aggregate polarity alone cannot create contradiction", lambda: _contradiction_state(a=.8,b=.8,streams=1, raw_systems=False) == RelationshipState.S0)
    add("P1-001", "P1", "Partial score remains numerically usable but status is PARTIAL", lambda: calculate_system_score(SystemScoreInput("A", (SystemScoreIndicator(sig("x")), SystemScoreIndicator(sig("y"), available=False)))).status == SystemScoreStatus.PARTIAL)
    add("P1-002", "P1", "No duplicate active source mapping is silently accepted", lambda: _unique_mapping_guard())
    add("P1-003", "P1", "Repeated-number patterns do not duplicate evidence clusters", lambda: _pattern_cluster_guard())
    add("P1-004", "P1", "Palmistry prohibited claims are not emitted", lambda: _palmistry_safety_guard())
    return AdversarialReport(tuple(checks))


def _score(system, score, status=__import__('three_maps.domain.types', fromlist=['SystemScoreStatus']).SystemScoreStatus.EVALUATED, coverage=1.0, confidence=1.0):
    from three_maps.domain.types import SystemScore
    return SystemScore(system=system, score=score, status=status, coverage=coverage, data_confidence=confidence, valid_indicator_count=1, expected_indicator_count=1)

def _target():
    from three_maps.domain.types import Target
    return Target(theme_id="T1", sub_theme_id="ST1", axis_id="A01", semantic_level="AXIS")

def _sys(name,a,b,cluster,level="AXIS"):
    from three_maps.engines.relationship import RelationshipSystem
    return RelationshipSystem(name,a,b,level,evidence_cluster_ids=(cluster,))

def _contradiction_state(a=.8,b=.8,streams=2,context=False,temporal=True,raw_systems=True):
    from three_maps.engines.contradiction import ContradictionInput, evaluate_contradiction
    from three_maps.engines.relationship import RelationshipSystem
    from three_maps.domain.types import RelationshipState
    x=ContradictionInput("A01",a,b,((RelationshipSystem("A",a,.1,"AXIS",evidence_cluster_ids=("a",),evidence_stream_count=streams),) if raw_systems else ()),((RelationshipSystem("B",.1,b,"AXIS",evidence_cluster_ids=("b",),evidence_stream_count=streams),) if raw_systems else ()),True,1,temporal,context,.9,True)
    return evaluate_contradiction(x).state

def _unique_mapping_guard():
    from three_maps.config.mapping_registry import SignalMappingRecord, SignalMappingRegistry, MappingStatus
    from three_maps.domain.types import ApplicabilityState
    from three_maps.config.ontology import DEFAULT_ONTOLOGY
    try:
        rec1=SignalMappingRecord(id="M1",source_system="ASTROLOGY",source_variable="X",theme_id="T1",sub_theme_id="ST1",axis_id="A01",pole_id="P-A01-A",applicability=ApplicabilityState.CORE,mapping_confidence=.9,methodology_version="MV",ontology_version=DEFAULT_ONTOLOGY.ontology_version,calculation_version="CV",status=MappingStatus.ACTIVE)
        rec2=SignalMappingRecord(id="M2",source_system="ASTROLOGY",source_variable="X",theme_id="T1",sub_theme_id="ST1",axis_id="A01",pole_id="P-A01-A",applicability=ApplicabilityState.CORE,mapping_confidence=.9,methodology_version="MV",ontology_version=DEFAULT_ONTOLOGY.ontology_version,calculation_version="CV",status=MappingStatus.ACTIVE)
        r=SignalMappingRegistry(DEFAULT_ONTOLOGY,(rec1,rec2))
        r.require_unique_active_mapping("ASTROLOGY","X")
        return False
    except ValueError: return True

def _pattern_cluster_guard():
    from datetime import date
    from three_maps.engines.numerology import calculate_profile, signal_candidates
    r=calculate_profile(date(1990,1,20), "John Doe")
    c=signal_candidates(r)
    # Pattern clustering is represented upstream by NumerologyPattern; candidates
    # use deterministic evidence keys and do not manufacture duplicate clusters.
    keys=[x.evidence_key for x in c]
    return len(keys) == len(set(keys))

def _palmistry_safety_guard():
    from three_maps.engines.palmistry import PalmistryResult
    text=str(PalmistryResult.__annotations__)
    return "lifespan" not in text.lower() and "diagnosis" not in text.lower()
