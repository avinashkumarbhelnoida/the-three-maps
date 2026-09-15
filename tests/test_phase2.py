from datetime import date
import pytest
from three_maps.engines.timing import TemporalWindow, classify_window, build_temporal_signal, assess_timing, TemporalStatus, TemporalCompatibility
from three_maps.engines.fusion_v2 import FusionV2Context, calculate_fusion_v2
from three_maps.domain.types import SystemScore, SystemScoreStatus, RelationshipState


def ss(system, score=.8, status=SystemScoreStatus.EVALUATED, confidence=.9, coverage=1):
    return SystemScore(system=system, score=score, status=status, coverage=coverage,
                       data_confidence=confidence, valid_indicator_count=1, expected_indicator_count=1)


def test_timing_window_boundary_is_active():
    w = TemporalWindow("W1", "ASTROLOGY", date(2026,1,1), date(2026,1,31))
    assert classify_window(w, at=date(2026,1,1)) == TemporalStatus.ACTIVE
    assert classify_window(w, at=date(2025,12,31)) == TemporalStatus.UPCOMING
    assert classify_window(w, at=date(2026,2,1)) == TemporalStatus.EXPIRED


def test_timing_assessment_converges_active_sources():
    a = build_temporal_signal(TemporalWindow("A", "ASTROLOGY", date(2026,1,1), None, .9, .9), at=date(2026,9,1))
    n = build_temporal_signal(TemporalWindow("N", "NUMEROLOGY", date(2026,1,1), None, .8, .8), at=date(2026,9,1))
    r = assess_timing((a,n))
    assert r.status == TemporalStatus.ACTIVE
    assert r.compatibility == TemporalCompatibility.COMPATIBLE
    assert r.active_systems == ("ASTROLOGY", "NUMEROLOGY")


def test_timing_never_creates_activity_from_expired_window():
    s = build_temporal_signal(TemporalWindow("W", "PALMISTRY", date(2025,1,1), date(2025,2,1)), at=date(2026,1,1))
    r = assess_timing((s,))
    assert r.status == TemporalStatus.EXPIRED and r.activation_score == 0


def test_fusion_v2_does_not_change_canonical_score():
    ctx = FusionV2Context((ss("A",.7), ss("B",.6)), RelationshipState.S2, 2, .5, 0, .8, .9)
    r = calculate_fusion_v2(ctx)
    assert r.canonical.final_score == pytest.approx(74.75)
    assert r.temporal_salience == .8


def test_fusion_v2_treats_temporal_metrics_as_diagnostics():
    base = calculate_fusion_v2(FusionV2Context((ss("A"),), temporal_salience=0.0, expected_temporal_coverage=0.1))
    assert base.canonical.final_score == 80.0
    assert "TEMPORAL_COVERAGE_LOW" in base.diagnostic_flags


def test_fusion_v2_unavailable_temporal_is_flagged_not_zeroed():
    r = calculate_fusion_v2(FusionV2Context((ss("A"),), temporal_salience=None))
    assert r.canonical.final_score == 80.0
    assert "TEMPORAL_SALIENCE_UNAVAILABLE" in r.diagnostic_flags
