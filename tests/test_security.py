import os
os.environ["THE_THREE_MAPS_AUTH_TOKENS"]="test-token=user-1,other-token=user-2"
HEADERS={"Authorization":"Bearer test-token"}
import pytest
from fastapi.testclient import TestClient
from three_maps.api.app import app

client = TestClient(app)
TARGET = {"theme_id":"T01","subtheme_id":"ST01","axis_id":"A01","semantic_level":"SUB_THEME","temporal_scope":"CURRENT","context_scope":"GENERAL"}

def payload(**kw):
    p={"target":TARGET, "name":"Test User", "birth_date":"1990-01-20", "requested_maps":["NUMEROLOGY"]}
    p.update(kw); return p

def test_security_headers_present():
    r=client.get('/health')
    assert r.status_code==200
    assert r.headers['X-Content-Type-Options']=='nosniff'
    assert r.headers['X-Frame-Options']=='DENY'
    assert r.headers['Cache-Control']=='no-store'

def test_unknown_map_rejected():
    r=client.post('/v1/analyses', headers=HEADERS, json=payload(requested_maps=['HACK']))
    assert r.status_code==422

def test_duplicate_maps_rejected():
    r=client.post('/v1/analyses', headers=HEADERS, json=payload(requested_maps=['NUMEROLOGY','NUMEROLOGY']))
    assert r.status_code==422

def test_name_length_rejected():
    r=client.post('/v1/analyses', headers=HEADERS, json=payload(name='x'*201))
    assert r.status_code==422

def test_invalid_analysis_id_rejected():
    r=client.get('/v1/analyses/not-an-analysis', headers=HEADERS)
    assert r.status_code==400
