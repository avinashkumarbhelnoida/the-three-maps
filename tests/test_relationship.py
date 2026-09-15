from three_maps.domain.types import Target, RelationshipState
from three_maps.engines.relationship import RelationshipInput, RelationshipSystem, evaluate_relationship

T = Target(theme_id="TH-1", sub_theme_id="ST-1", axis_id="A01", semantic_level="SUB_THEME", temporal_scope="CURRENT", context_scope="GENERAL")

def s(name, a, b, **kw):
    return RelationshipSystem(name, a, b, semantic_level="SUB_THEME", temporal_scope="CURRENT", evidence_cluster_ids=(name,), **kw)

def test_single_map_signal():
    r = evaluate_relationship(RelationshipInput("R1", T, (s("ASTROLOGY", .8, .2),)))
    assert r.state == RelationshipState.S1 and r.direction == "A"

def test_two_map_convergence():
    r = evaluate_relationship(RelationshipInput("R2", T, (s("ASTROLOGY", .8, .1), s("NUMEROLOGY", .7, .2))))
    assert r.state == RelationshipState.S2
    assert r.broad_directional_convergence

def test_three_map_clean_convergence():
    r = evaluate_relationship(RelationshipInput("R3", T, (s("ASTROLOGY", .8, .1), s("NUMEROLOGY", .7, .2), s("PALMISTRY", .9, .1))))
    assert r.state == RelationshipState.S3

def test_three_map_independent_reinforcement_is_s4():
    r = evaluate_relationship(RelationshipInput("R4", T, (s("ASTROLOGY", .8, .1), s("NUMEROLOGY", .7, .2), s("PALMISTRY", .9, .1)), independence=.8))
    assert r.state == RelationshipState.S4

def test_material_qualification_is_s5():
    r = evaluate_relationship(RelationshipInput("R5", T, (s("ASTROLOGY", .8, .1), s("NUMEROLOGY", .7, .2), s("PALMISTRY", .9, .1, material_qualification=True))))
    assert r.state == RelationshipState.S5

def test_two_vs_one_does_not_use_majority():
    r = evaluate_relationship(RelationshipInput("R6", T, (s("ASTROLOGY", .8, .1), s("NUMEROLOGY", .7, .2), s("PALMISTRY", .1, .8))))
    assert r.state == RelationshipState.S0
    assert not r.broad_directional_convergence

def test_weak_opposition_below_tau_p_does_not_block_convergence():
    r = evaluate_relationship(RelationshipInput("R7", T, (s("ASTROLOGY", .8, .1), s("NUMEROLOGY", .7, .2), s("PALMISTRY", .1, .59))))
    assert r.state == RelationshipState.S3
    assert r.broad_directional_convergence

def test_context_resolved_opposition_is_not_s6():
    r = evaluate_relationship(RelationshipInput("R8", T, (s("ASTROLOGY", .8, .1), s("NUMEROLOGY", .1, .8)), context_resolution=True))
    assert r.state != RelationshipState.S6

def test_semantic_mismatch_prevents_convergence():
    x = RelationshipSystem("PALMISTRY", .9, .1, semantic_level="AXIS", temporal_scope="CURRENT", evidence_cluster_ids=("PALMISTRY",))
    r = evaluate_relationship(RelationshipInput("R9", T, (s("ASTROLOGY", .8, .1), s("NUMEROLOGY", .7, .2), x)))
    assert not r.broad_directional_convergence

def test_temporal_mismatch_prevents_convergence():
    x = RelationshipSystem("PALMISTRY", .9, .1, semantic_level="SUB_THEME", temporal_scope="FUTURE", evidence_cluster_ids=("PALMISTRY",))
    r = evaluate_relationship(RelationshipInput("R10", T, (s("ASTROLOGY", .8, .1), s("NUMEROLOGY", .7, .2), x)))
    assert not r.broad_directional_convergence

def test_same_cluster_not_independent_for_s4():
    systems = (
        RelationshipSystem("ASTROLOGY", .8, .1, "SUB_THEME", "CURRENT", evidence_cluster_ids=("EC-SAME",)),
        RelationshipSystem("NUMEROLOGY", .7, .2, "SUB_THEME", "CURRENT", evidence_cluster_ids=("EC-SAME",)),
        RelationshipSystem("PALMISTRY", .9, .1, "SUB_THEME", "CURRENT", evidence_cluster_ids=("EC-3",)),
    )
    r = evaluate_relationship(RelationshipInput("R11", T, systems, independence=.9))
    assert r.state == RelationshipState.S3
    assert not r.evidence_cluster_separation

def test_no_systems_is_s0():
    r = evaluate_relationship(RelationshipInput("R12", T, ()))
    assert r.state == RelationshipState.S0
