from fastapi.testclient import TestClient
from three_maps.api.app import app

client = TestClient(app)

def test_frontend_root_served():
    r=client.get('/')
    assert r.status_code==200
    assert 'THE THREE MAPS' in r.text

def test_frontend_assets_served():
    assert client.get('/frontend/styles.css').status_code==200
    assert client.get('/frontend/app.js').status_code==200

def test_frontend_has_intelligence_sections():
    r = client.get('/')
    assert 'CONVERGENCE' in r.text
    assert 'FUSION STRENGTH' in r.text
    assert 'DATA CONFIDENCE' in r.text
    assert 'COVERAGE' in r.text
    assert 'Audit Trail' in r.text

def test_frontend_preserves_three_map_flow():
    r = client.get('/')
    for label in ('NUMEROLOGY', 'ASTROLOGY', 'PALMISTRY'):
        assert label in r.text
    assert 'OBSERVE → COMPARE → CONFIRM' in r.text
