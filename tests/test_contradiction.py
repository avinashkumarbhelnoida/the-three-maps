from three_maps.domain.types import Target, RelationshipState
from three_maps.engines.relationship import RelationshipSystem
from three_maps.engines.contradiction import ContradictionInput, evaluate_contradiction

T = Target(theme_id="TH-1", sub_theme_id="ST-1", axis_id="A01", semantic_level="SUB_THEME")
def s(name,a,b,cluster=None,streams=1):
    return RelationshipSystem(name,a,b,"SUB_THEME","CURRENT",evidence_cluster_ids=(cluster or name,),evidence_stream_count=streams)

def test_vmo_s6_when_independence_fails():
    r=evaluate_contradiction(ContradictionInput("A01",.8,.75,(s("ASTROLOGY",.8,.1),),(s("NUMEROLOGY",.1,.75),),True,.9,True,False,.3))
    assert r.validated_opposition and r.state==RelationshipState.S6

def test_s7_requires_independence_and_balance():
    r=evaluate_contradiction(ContradictionInput("A01",.8,.75,(s("ASTROLOGY",.8,.1),),(s("NUMEROLOGY",.1,.75),),True,.9,True,False,.8))
    assert r.state==RelationshipState.S7 and r.contradiction_strength is not None

def test_dual_pole_without_distinct_streams_is_not_contradiction():
    r=evaluate_contradiction(ContradictionInput("A01",.8,.75,(s("ASTROLOGY",.8,.1,"EC-SAME"),),(s("NUMEROLOGY",.1,.75,"EC-SAME"),),True,.9,True,False,.8))
    assert not r.validated_opposition and r.state==RelationshipState.S0

def test_context_resolved_fails_vmo():
    r=evaluate_contradiction(ContradictionInput("A01",.8,.8,(s("ASTROLOGY",.8,.1),),(s("NUMEROLOGY",.1,.8),),True,.9,True,True,.8))
    assert r.state==RelationshipState.S0
