import os
os.environ["THE_THREE_MAPS_AUTH_TOKENS"]="test-token=user-1,other-token=user-2"
HEADERS={"Authorization":"Bearer test-token"}
from datetime import date

from fastapi.testclient import TestClient

from three_maps.api.app import app
from three_maps.domain.types import RelationshipState, SystemScoreStatus
from three_maps.engines.fusion import FusionContext, calculate_fusion_result
from three_maps.engines.relationship import RelationshipInput, RelationshipSystem, evaluate_relationship
from three_maps.engines.system_score import SystemScoreIndicator, SystemScoreInput, calculate_system_score
from three_maps.domain.types import ActivationState, ApplicabilityState, IndicatorWeightClass, Signal, Target

client = TestClient(app)


def test_full_api_to_map_results_and_lineage():
    payload = {
        "name": "John Doe",
        "birth_date": "1990-01-20",
        "birth_datetime": "1990-01-20T10:30:00+05:30",
        "latitude": 28.61,
        "longitude": 77.23,
        "target": {"theme_id": "TH-1", "sub_theme_id": "ST-1", "axis_id": "A01",
                   "semantic_level": "SUB_THEME", "temporal_scope": "CURRENT", "context_scope": "GENERAL"},
        "requested_maps": ["NUMEROLOGY", "ASTROLOGY"],
    }
    r = client.post("/v1/analyses", headers=HEADERS, json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "COMPLETED"
    assert set(body["available_maps"]) == {"NUMEROLOGY", "ASTROLOGY"}
    assert len(body["result_hash"]) == 64

    analysis = client.get(f"/v1/analyses/{body['analysis_id']}", headers=HEADERS)
    assert analysis.status_code == 200
    assert analysis.json()["input_snapshot"]["immutable"] is True

    num = client.get(f"/v1/analyses/{body['analysis_id']}/maps/numerology", headers=HEADERS)
    astro = client.get(f"/v1/analyses/{body['analysis_id']}/maps/astrology", headers=HEADERS)
    lineage = client.get(f"/v1/analyses/{body['analysis_id']}/lineage", headers=HEADERS)
    assert num.status_code == astro.status_code == lineage.status_code == 200
    assert "life_path" in num.json()["result"]
    assert "planets" in astro.json()["result"]
    assert len(lineage.json()) == 2


def test_missing_optional_map_is_partial_not_zero():
    payload = {
        "name": "John Doe",
        "birth_date": "1990-01-20",
        "target": {"theme_id": "TH-1", "sub_theme_id": "ST-1", "axis_id": "A01",
                   "semantic_level": "SUB_THEME", "temporal_scope": "CURRENT", "context_scope": "GENERAL"},
        "requested_maps": ["NUMEROLOGY", "ASTROLOGY", "PALMISTRY"],
    }
    r = client.post("/v1/analyses", headers=HEADERS, json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "COMPLETED"  # at least one requested map successfully calculated
    assert "NUMEROLOGY" in body["available_maps"]
    assert "ASTROLOGY" not in body["available_maps"]
    assert "PALMISTRY" not in body["available_maps"]


def _signal(identifier, strength=4, confidence=1.0, relevance=1.0):
    return Signal(
        id=identifier, source_system="NUMEROLOGY", source_variable="LIFE_PATH",
        evidence_ids=[f"RAW-{identifier}"], evidence_cluster_ids=[f"EC-{identifier}"],
        theme_id="TH-1", axis_id="A01", pole_id="P-A01-A", strength=strength,
        confidence=confidence, relevance=relevance, weight_class=IndicatorWeightClass.STANDARD,
        applicability=ApplicabilityState.CORE, activation=ActivationState.ACTIVE,
        methodology_version="MV-0.1.0", calculation_version="CV-0.1.0",
    )


def test_pipeline_score_relationship_fusion_with_partial_system():
    a = calculate_system_score(SystemScoreInput(
        "ASTROLOGY", (SystemScoreIndicator(_signal("a", 4)),)
    ))
    n = calculate_system_score(SystemScoreInput(
        "NUMEROLOGY", (SystemScoreIndicator(_signal("n", 3)),)
    ))
    p = calculate_system_score(SystemScoreInput(
        "PALMISTRY", (SystemScoreIndicator(_signal("p", 2), available=True),
                       SystemScoreIndicator(_signal("p-missing", 4), available=False))
    ))
    assert a.status == n.status == SystemScoreStatus.EVALUATED
    assert p.status == SystemScoreStatus.PARTIAL
    assert p.score == 0.5

    target = Target(theme_id="TH-1", sub_theme_id="ST-1", axis_id="A01",
                    semantic_level="SUB_THEME", temporal_scope="CURRENT", context_scope="GENERAL")
    rel = evaluate_relationship(RelationshipInput(
        "E2E", target,
        (RelationshipSystem("ASTROLOGY", a.score, 0.2, "SUB_THEME", "CURRENT", evidence_cluster_ids=("EA",)),
         RelationshipSystem("NUMEROLOGY", n.score, 0.2, "SUB_THEME", "CURRENT", evidence_cluster_ids=("EN",)),
         RelationshipSystem("PALMISTRY", p.score, 0.2, "SUB_THEME", "CURRENT", evidence_cluster_ids=("EP",))),
    ))
    assert rel.state == RelationshipState.S3

    fusion = calculate_fusion_result(FusionContext((a, n, p), relationship_state=rel.state,
                                                   meaningful_system_count=3, independence=0.5))
    assert fusion.valid_system_count == 3
    assert 0 <= fusion.final_score <= 100
    assert fusion.contradiction_penalty == 0


def test_end_to_end_s7_penalty_only_when_formal_contradiction_is_present():
    # Relationship tension by itself must not impose the S7 penalty.
    base = calculate_system_score(SystemScoreInput("A", (SystemScoreIndicator(_signal("x", 4)),)))
    other = calculate_system_score(SystemScoreInput("B", (SystemScoreIndicator(_signal("y", 4)),)))
    no_penalty = calculate_fusion_result(FusionContext((base, other), relationship_state=RelationshipState.S6,
                                                        independence=0.8, contradiction_strength=1.0))
    penalty = calculate_fusion_result(FusionContext((base, other), relationship_state=RelationshipState.S7,
                                                     independence=0.8, contradiction_strength=1.0))
    assert no_penalty.contradiction_penalty == 0
    assert penalty.contradiction_penalty == 0.2
    assert penalty.final_score < no_penalty.final_score
