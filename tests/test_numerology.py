from datetime import date
import pytest
from three_maps.engines.numerology import (
    normalize_name, reduce_number, life_path, birthday_number, attitude_number,
    expression_number, soul_urge, personality_number, maturity_number,
    personal_year, personal_month, personal_day, pinnacles, challenges,
)


def test_pythagorean_normalization():
    assert normalize_name("José  Kumar-Singh") == "JOSEKUMARSINGH"


def test_master_numbers_preserved():
    assert reduce_number(38).reduced_value == 11
    assert reduce_number(38).is_master is True
    assert reduce_number(40).reduced_value == 4


def test_birth_numbers():
    dob = date(1990, 1, 20)
    assert life_path(dob).reduced_value == 22
    assert birthday_number(dob).reduced_value == 2
    assert attitude_number(dob).reduced_value == 3


def test_name_numbers():
    assert expression_number("JOHN DOE").reduced_value == 8
    assert soul_urge("JOHN DOE").reduced_value == 8
    assert personality_number("JOHN DOE").reduced_value == 9


def test_maturity_dependencies():
    dob = date(1990, 1, 20)
    assert maturity_number(dob, "JOHN DOE").reduced_value == 3


def test_cycles_are_date_explicit():
    dob = date(1990, 1, 20)
    assert personal_year(dob, 2026).reduced_value == 4
    assert personal_month(dob, 2026, 9).reduced_value == 4
    assert personal_day(dob, 2026, 9, 13).reduced_value == 8


def test_pinnacles_and_challenges_shape():
    dob = date(1990, 1, 20)
    ps = pinnacles(dob)
    cs = challenges(dob)
    assert len(ps) == 4
    assert len(cs) == 4
    assert all(0 <= x.reduced_value <= 33 for x in ps + cs)


def test_invalid_inputs():
    with pytest.raises(ValueError):
        personal_month(date(1990, 1, 20), 2026, 13)
    with pytest.raises(ValueError):
        expression_number("12345")
