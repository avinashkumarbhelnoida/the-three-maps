from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from three_maps.engines.astrology import calculate_astrology


def sample():
    return calculate_astrology(
        datetime(1990, 1, 1, 12, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
        77.5946,
        12.9716,
    )


def test_astrology_is_deterministic_and_lahiri_whole_sign():
    a = sample(); b = sample()
    assert a == b
    assert 0 <= a.ascendant_longitude < 360
    assert a.ascendant_sign_index in range(12)
    assert 0 <= a.ayanamsha < 30
    assert len(a.planets) == 9
    assert all(1 <= p.house <= 12 for p in a.planets)
    assert all(0 <= p.longitude < 360 for p in a.planets)


def test_nakshatra_and_pada_ranges():
    a = sample()
    assert all(0 <= p.nakshatra_index < 27 for p in a.planets)
    assert all(1 <= p.pada <= 4 for p in a.planets)


def test_ketu_is_opposite_rahu():
    a = sample()
    r = next(p for p in a.planets if p.planet == "RAHU")
    k = next(p for p in a.planets if p.planet == "KETU")
    d = abs(r.longitude - k.longitude)
    assert min(d, 360-d) == pytest.approx(180.0)


def test_parashari_special_aspects_exist():
    a = sample()
    assert any(x.source == "MARS" and x.distance_signs in {4, 8} for x in a.aspects)
    assert any(x.source == "JUPITER" and x.distance_signs in {5, 9} for x in a.aspects)
    assert any(x.source == "SATURN" and x.distance_signs in {3, 10} for x in a.aspects)


def test_dasha_has_start_lord_and_future_periods():
    a = sample()
    assert a.dasha_start_lord in {x[0] for x in __import__('three_maps.engines.astrology', fromlist=['VIMSHOTTARI']).VIMSHOTTARI}
    assert a.dasha_balance_years > 0
    assert len(a.mahadashas) >= 8
    assert a.mahadashas[0].start == datetime(1990,1,1,12,0,tzinfo=ZoneInfo('Asia/Kolkata'))


def test_invalid_coordinates_and_naive_datetime_rejected():
    with pytest.raises(ValueError):
        calculate_astrology(datetime(1990,1,1,12,0), 77.0, 28.0)
    with pytest.raises(ValueError):
        calculate_astrology(datetime(1990,1,1,12,0,tzinfo=ZoneInfo('Asia/Kolkata')), 181, 28.0)


def test_structural_signals_are_explicit_and_auditable():
    from three_maps.engines.astrology import structural_signals
    signals = structural_signals(sample())
    kinds = {x["source_variable"] for x in signals}
    assert {"PLANET_SIGN", "PLANET_NAKSHATRA", "PLANET_DIGNITY", "PLANET_RETROGRADE"} <= kinds
    assert all("source_variable" in x for x in signals)


def test_active_mahadasha_is_time_resolved():
    from three_maps.engines.astrology import active_mahadasha
    a = sample()
    p = active_mahadasha(a, a.mahadashas[0].start)
    assert p == a.mahadashas[0]


def test_yoga_pipeline_requires_explicit_formation_and_version():
    from three_maps.engines.astrology import YogaDefinition, evaluate_yoga_definition
    a = sample()
    definition = YogaDefinition("Y-TEST", "Test Yoga", ("SUN", "MOON"), "SAME_SIGN", a.methodology_version)
    result = evaluate_yoga_definition(a, definition)
    assert isinstance(result.formed, bool)
    assert isinstance(result.strength, float) and 0 <= result.strength <= 1
    bad = YogaDefinition("Y-BAD", "Bad Yoga", ("SUN",), "UNKNOWN", a.methodology_version)
    import pytest
    with pytest.raises(ValueError):
        evaluate_yoga_definition(a, bad)
    mismatch = YogaDefinition("Y-M", "Mismatch", ("SUN", "MOON"), "SAME_SIGN", "OTHER")
    assert evaluate_yoga_definition(a, mismatch).reason_codes == ("VERSION_MISMATCH",)
