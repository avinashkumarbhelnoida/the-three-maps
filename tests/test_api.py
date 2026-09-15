import os
os.environ["THE_THREE_MAPS_AUTH_TOKENS"] = "test-token=user-1,other-token=user-2"
from datetime import date, datetime, timezone
from fastapi.testclient import TestClient

from three_maps.api.app import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer test-token"}
OTHER_HEADERS = {"Authorization": "Bearer other-token"}


def target():
    return {"theme_id": "TH-001", "sub_theme_id": None, "axis_id": "A01", "semantic_level": "AXIS",
            "temporal_scope": None, "context_scope": None}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_analysis_with_numerology():
    r = client.post("/v1/analyses", headers=HEADERS, json={
        "name": "JOHN DOE", "birth_date": "1990-01-20", "target": target(),
        "requested_maps": ["NUMEROLOGY"],
    })
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "COMPLETED"
    aid = body["analysis_id"]
    detail = client.get(f"/v1/analyses/{aid}", headers=HEADERS)
    assert detail.status_code == 200
    assert detail.json()["maps"]["numerology"]["life_path"]["reduced_value"] == 22
    lin = client.get(f"/v1/analyses/{aid}/lineage", headers=HEADERS)
    assert lin.status_code == 200
    assert len(lin.json()) == 1


def test_create_analysis_with_astrology():
    r = client.post("/v1/analyses", headers=HEADERS, json={
        "birth_datetime": "1990-01-20T12:00:00+05:30", "latitude": 28.6, "longitude": 77.2,
        "target": target(), "requested_maps": ["ASTROLOGY"],
    })
    assert r.status_code == 201
    aid = r.json()["analysis_id"]
    m = client.get(f"/v1/analyses/{aid}/maps/astrology", headers=HEADERS)
    assert m.status_code == 200
    assert "planets" in m.json()["result"]


def test_partial_when_requested_map_cannot_run():
    r = client.post("/v1/analyses", headers=HEADERS, json={
        "target": target(), "requested_maps": ["ASTROLOGY"],
    })
    assert r.status_code == 201
    assert r.json()["status"] == "PARTIAL"
    assert r.json()["available_maps"] == []


def test_unknown_analysis_is_404():
    assert client.get("/v1/analyses/ANL-does-not-exist", headers=HEADERS).status_code == 404


def test_protected_endpoint_requires_authentication():
    r = client.get("/v1/analyses/ANL-does-not-exist")
    assert r.status_code == 401


def test_analysis_is_owner_isolated():
    r = client.post("/v1/analyses", headers=HEADERS, json={"name":"OWNER","birth_date":"1990-01-20","target":target(),"requested_maps":["NUMEROLOGY"]})
    aid = r.json()["analysis_id"]
    assert client.get(f"/v1/analyses/{aid}", headers=OTHER_HEADERS).status_code == 404


def test_idempotency_key_replays_same_analysis():
    payload={"name":"IDEMPOTENT","birth_date":"1990-01-20","target":target(),"requested_maps":["NUMEROLOGY"]}
    h={**HEADERS,"Idempotency-Key":"idem-001"}
    first=client.post("/v1/analyses",headers=h,json=payload)
    second=client.post("/v1/analyses",headers=h,json=payload)
    assert first.status_code == second.status_code == 201
    assert first.json()["analysis_id"] == second.json()["analysis_id"]
