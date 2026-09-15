from three_maps.domain.types import (
    ActivationState, ApplicabilityState, IndicatorWeightClass, PoleStrength,
    Signal, SystemScoreStatus, SystemScore, Target, AxisDirectionState,
)
from three_maps.engines.cross_map import normalize_signals, normalize_map_units, evaluate_phase1_relationship
from three_maps.engines.cross_map import resolve_mapping
from three_maps.config.mapping_registry import SignalMappingRecord, SignalMappingRegistry, MappingStatus
from three_maps.config.ontology import DEFAULT_ONTOLOGY
from three_maps.domain.types import RelationshipState


def sig(system, sid="S1", pole="P-A01-A", sub="ST-1", active=True):
    return Signal(
        id=sid, source_system=system, source_variable="X", evidence_ids=[sid],
        evidence_cluster_ids=["EC-"+sid], theme_id="TH-1", sub_theme_id=sub,
        axis_id="A01", pole_id=pole, strength=4, confidence=1, relevance=1,
        weight_class=IndicatorWeightClass.STANDARD, applicability=ApplicabilityState.CORE,
        activation=ActivationState.ACTIVE if active else ActivationState.NOT_ACTIVATED,
        methodology_version="MV-0.1.0", calculation_version="CV-0.1.0",
    )


def target():
    return Target(theme_id="TH-1", sub_theme_id="ST-1", axis_id="A01", semantic_level="SUB_THEME", temporal_scope="CURRENT")


def score(system):
    return SystemScore(system=system, score=.8, status=SystemScoreStatus.EVALUATED, coverage=1, data_confidence=.9, valid_indicator_count=1, expected_indicator_count=1)


def unit(system, a, b, cluster):
    return __import__('three_maps.engines.cross_map', fromlist=['MapUnit']).MapUnit(
        system=system, target=target(), axis=None, system_score=score(system),
        pole_strength=PoleStrength(axis_id="A01", pole_a=a, pole_b=b),
        semantic_level="SUB_THEME", temporal_scope="CURRENT", context_scope="GENERAL",
        evidence_cluster_ids=(cluster,),
    )


def test_mapping_resolution_missing_is_unavailable():
    r = resolve_mapping(DEFAULT_ONTOLOGY and SignalMappingRegistry(DEFAULT_ONTOLOGY), source_system="ASTROLOGY", source_variable="MISSING")
    assert r.status == "UNAVAILABLE"


def test_normalization_drops_inactive_and_wrong_axis():
    t = target()
    assert len(normalize_signals([sig("ASTROLOGY"), sig("NUMEROLOGY", "S2", active=False)], target=t)) == 1


def test_phase1_clean_three_map_convergence():
    r = evaluate_phase1_relationship(relationship_id="P1", target=target(), units=(
        unit("ASTROLOGY", .8, .1, "EA"), unit("NUMEROLOGY", .75, .1, "EN"), unit("PALMISTRY", .9, .1, "EP"),
    ), independence=.8)
    assert r.relationship.state == RelationshipState.S4
    assert not r.contradiction.validated_opposition


def test_phase1_formal_opposition_is_s7_only_after_contradiction_gates():
    r = evaluate_phase1_relationship(relationship_id="P2", target=target(), units=(
        unit("ASTROLOGY", .8, .1, "EA"), unit("NUMEROLOGY", .1, .8, "EN"),
    ), independence=.8)
    assert r.contradiction.state == RelationshipState.S7


def test_phase1_duplicate_clusters_block_formal_contradiction():
    r = evaluate_phase1_relationship(relationship_id="P3", target=target(), units=(
        unit("ASTROLOGY", .8, .1, "SAME"), unit("NUMEROLOGY", .1, .8, "SAME"),
    ), independence=.8)
    assert r.contradiction.state == RelationshipState.S0
