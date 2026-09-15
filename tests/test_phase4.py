import os
from three_maps.api.hardening import FixedWindowRateLimiter
from three_maps.config.production import ProductionSettings
from three_maps.engines.performance import benchmark
from three_maps.persistence import SQLiteRepository

def test_rate_limiter_enforces_limit_and_window():
    r=FixedWindowRateLimiter(2,60)
    assert r.allow('x',0); assert r.allow('x',1); assert not r.allow('x',2); assert r.allow('x',61)

def test_production_requires_explicit_cors():
    try: ProductionSettings(environment='production', allowed_origins=()).validate()
    except ValueError: return
    assert False

def test_repository_uses_configured_path(tmp_path, monkeypatch):
    path=tmp_path/'tm.db'; monkeypatch.setenv('THE_THREE_MAPS_DB_PATH', str(path))
    r=SQLiteRepository(); assert r.path == str(path); r.close(); assert path.exists()

def test_performance_harness():
    result=benchmark(lambda: sum(range(100)), iterations=20, max_average_ms=50)
    assert result.passed and result.operations_per_second > 0
