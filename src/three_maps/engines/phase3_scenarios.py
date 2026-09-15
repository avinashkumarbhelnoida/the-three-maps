"""Executable end-to-end synthetic scenarios for Phase III.

Scenarios exercise the integration contracts with controlled evidence. They are
not real-person readings and do not assert semantic truth.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from three_maps.domain.types import RelationshipState
from three_maps.engines.relationship import RelationshipInput, RelationshipSystem, evaluate_relationship
from three_maps.engines.contradiction import ContradictionInput, evaluate_contradiction

@dataclass(frozen=True)
class ScenarioResult:
    id: str
    name: str
    relationship: RelationshipState
    contradiction: RelationshipState
    passed: bool
    reason: str = ""


def _sys(name,a,b,cluster,*,qualified=False,temporal="CURRENT",level="AXIS"):
    return RelationshipSystem(name,a,b,level,temporal_scope=temporal,evidence_cluster_ids=(cluster,),material_qualification=qualified)


def run_scenarios() -> tuple[ScenarioResult, ...]:
    cases: list[tuple[str,str,tuple[RelationshipSystem,...],str]] = [
        ("E2E-001","single-map",(_sys("ASTROLOGY",.75,.1,"a"),),"S1"),
        ("E2E-002","two-map convergence",(_sys("ASTROLOGY",.8,.1,"a"),_sys("NUMEROLOGY",.7,.1,"n")),"S2"),
        ("E2E-003","three-map convergence",(_sys("ASTROLOGY",.8,.1,"a"),_sys("NUMEROLOGY",.7,.1,"n"),_sys("PALMISTRY",.75,.1,"p")),"S3"),
        ("E2E-004","qualified convergence",(_sys("ASTROLOGY",.8,.1,"a"),_sys("NUMEROLOGY",.75,.1,"n"),_sys("PALMISTRY",.7,.1,"p",qualified=True)),"S5"),
        ("E2E-005","formal contradiction",(_sys("ASTROLOGY",.8,.1,"a"),_sys("NUMEROLOGY",.1,.8,"n")),"S0"),
        ("E2E-006","unavailable map omitted",(_sys("ASTROLOGY",.8,.1,"a"),),"S1"),
        ("E2E-007","temporal mismatch",(_sys("ASTROLOGY",.8,.1,"a",temporal="CURRENT"),_sys("NUMEROLOGY",.1,.8,"n",temporal="FUTURE")),"S0"),
        ("E2E-008","semantic mismatch",(_sys("ASTROLOGY",.8,.1,"a",level="AXIS"),_sys("NUMEROLOGY",.8,.1,"n",level="THEME")),"S0"),
    ]
    out=[]
    for sid,name,systems,expected in cases:
        rel=evaluate_relationship(RelationshipInput(sid,_target(),systems,target_semantic_level="AXIS",target_temporal_scope="CURRENT"))
        ca=[s for s in systems if s.meaningful_a and not s.meaningful_b]
        cb=[s for s in systems if s.meaningful_b and not s.meaningful_a]
        temporal=rel.temporal_compatibility
        c=evaluate_contradiction(ContradictionInput("A01",max((s.pole_a_strength for s in ca),default=0),max((s.pole_b_strength for s in cb),default=0),tuple(ca),tuple(cb),rel.same_semantic_level,rel.semantic_similarity,temporal,rel.context_resolution,.9,True))
        actual=rel.state.value
        # formal contradiction is expected only at the contradiction engine.
        passed=(actual==expected and (name!="formal contradiction" or c.state==RelationshipState.S7) and (name!="temporal mismatch" or c.state==RelationshipState.S0))
        out.append(ScenarioResult(sid,name,rel.state,c.state,passed,"" if passed else f"expected={expected}, relationship={rel.state.value}, contradiction={c.state.value}"))
    return tuple(out)

def _target():
    from three_maps.domain.types import Target
    return Target(theme_id="T1",sub_theme_id="ST1",axis_id="A01",semantic_level="AXIS",temporal_scope="CURRENT",context_scope="GENERAL")
