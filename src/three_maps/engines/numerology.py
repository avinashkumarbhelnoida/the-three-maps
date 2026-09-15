from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import unicodedata
import re

MASTER_NUMBERS = frozenset({11, 22, 33})
PYTHAGOREAN = {
    **dict.fromkeys("AJS", 1), **dict.fromkeys("BKT", 2), **dict.fromkeys("CLU", 3),
    **dict.fromkeys("DMV", 4), **dict.fromkeys("ENW", 5), **dict.fromkeys("FOX", 6),
    **dict.fromkeys("GPY", 7), **dict.fromkeys("HQZ", 8), **dict.fromkeys("IR", 9),
}


@dataclass(frozen=True)
class ReducedValue:
    raw_value: int
    reduced_value: int
    is_master: bool
    trace: tuple[int, ...]


def normalize_name(name: str) -> str:
    """Return the methodology-normalized A-Z representation of a name."""
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z]", "", ascii_name).upper()


def reduce_number(value: int, preserve_master: bool = True) -> ReducedValue:
    if not isinstance(value, int) or value < 0:
        raise ValueError("value must be a non-negative integer")
    trace = [value]
    current = value
    while current >= 10:
        if preserve_master and current in MASTER_NUMBERS:
            return ReducedValue(value, current, True, tuple(trace))
        current = sum(int(d) for d in str(current))
        trace.append(current)
    return ReducedValue(value, current, False, tuple(trace))


def _date_sum_parts(value: date) -> int:
    return sum(int(d) for d in value.strftime("%Y%m%d"))


def life_path(birth_date: date) -> ReducedValue:
    return reduce_number(_date_sum_parts(birth_date))


def birthday_number(birth_date: date) -> ReducedValue:
    return reduce_number(birth_date.day)


def attitude_number(birth_date: date) -> ReducedValue:
    return reduce_number(birth_date.month + birth_date.day)


def _name_sum(name: str, *, vowels: bool | None = None) -> tuple[int, tuple[tuple[str, int], ...]]:
    normalized = normalize_name(name)
    pairs = []
    for ch in normalized:
        is_vowel = ch in "AEIOU"
        if vowels is None or is_vowel == vowels:
            pairs.append((ch, PYTHAGOREAN[ch]))
    return sum(v for _, v in pairs), tuple(pairs)


def expression_number(name: str) -> ReducedValue:
    raw, _ = _name_sum(name)
    if not normalize_name(name):
        raise ValueError("name must contain at least one alphabetic character")
    return reduce_number(raw)


def soul_urge(name: str) -> ReducedValue:
    raw, pairs = _name_sum(name, vowels=True)
    if not pairs:
        raise ValueError("name must contain at least one configured vowel")
    return reduce_number(raw)


def personality_number(name: str) -> ReducedValue:
    raw, pairs = _name_sum(name, vowels=False)
    if not pairs:
        raise ValueError("name must contain at least one consonant")
    return reduce_number(raw)


def maturity_number(birth_date: date, name: str) -> ReducedValue:
    lp = life_path(birth_date)
    ex = expression_number(name)
    return reduce_number(lp.reduced_value + ex.reduced_value)


def personal_year(birth_date: date, year: int) -> ReducedValue:
    if year < 1:
        raise ValueError("year must be positive")
    return reduce_number(birth_date.month + birth_date.day + sum(int(d) for d in str(year)))


def personal_month(birth_date: date, year: int, month: int) -> ReducedValue:
    if month not in range(1, 13):
        raise ValueError("month must be 1..12")
    py = personal_year(birth_date, year)
    return reduce_number(py.reduced_value + month)


def personal_day(birth_date: date, year: int, month: int, day: int) -> ReducedValue:
    target = date(year, month, day)
    pm = personal_month(birth_date, year, month)
    return reduce_number(pm.reduced_value + target.day)


def pinnacles(birth_date: date) -> tuple[ReducedValue, ReducedValue, ReducedValue, ReducedValue]:
    m = reduce_number(birth_date.month).reduced_value
    d = reduce_number(birth_date.day).reduced_value
    y = reduce_number(birth_date.year).reduced_value
    p1 = reduce_number(m + d)
    p2 = reduce_number(d + y)
    p3 = reduce_number(p1.reduced_value + p2.reduced_value)
    p4 = reduce_number(m + y)
    return p1, p2, p3, p4


def challenges(birth_date: date) -> tuple[ReducedValue, ReducedValue, ReducedValue, ReducedValue]:
    m = reduce_number(birth_date.month).reduced_value
    d = reduce_number(birth_date.day).reduced_value
    y = reduce_number(birth_date.year).reduced_value
    c1 = reduce_number(abs(d - m))
    c2 = reduce_number(abs(d - y))
    c3 = reduce_number(abs(c1.reduced_value - c2.reduced_value))
    c4 = reduce_number(abs(m - y))
    return c1, c2, c3, c4

# 201.81E — versioned Numerology methodology configuration and structured profile.
from enum import Enum

class YTreatment(str, Enum):
    CONSONANT = "CONSONANT"
    VOWEL = "VOWEL"
    CONTEXTUAL = "CONTEXTUAL"

@dataclass(frozen=True)
class NumerologyMethodology:
    version: str = "MV-0.1.0"
    calculation_version: str = "CV-0.1.1"
    y_treatment: YTreatment = YTreatment.CONSONANT
    preserve_master_numbers: bool = True

@dataclass(frozen=True)
class NumerologyPattern:
    pattern_type: str
    source_variables: tuple[str, ...]
    value: int | None
    occurrence_count: int
    methodology_version: str

@dataclass(frozen=True)
class NumerologySignalCandidate:
    source_variable: str
    value: int
    is_master: bool
    source_scope: str
    methodology_version: str
    calculation_version: str
    evidence_key: str

@dataclass(frozen=True)
class NumerologyResult:
    life_path: ReducedValue
    birthday: ReducedValue
    attitude: ReducedValue
    expression: ReducedValue | None
    soul_urge: ReducedValue | None
    personality: ReducedValue | None
    maturity: ReducedValue | None
    personal_year: ReducedValue | None
    personal_month: ReducedValue | None
    personal_day: ReducedValue | None
    pinnacles: tuple[ReducedValue, ...]
    challenges: tuple[ReducedValue, ...]
    patterns: tuple[NumerologyPattern, ...]
    methodology_version: str
    calculation_version: str

def _name_sum_configured(name: str, *, vowels: bool | None, methodology: NumerologyMethodology) -> tuple[int, tuple[tuple[str, int], ...]]:
    normalized = normalize_name(name)
    pairs: list[tuple[str, int]] = []
    for ch in normalized:
        if ch == "Y":
            is_vowel = methodology.y_treatment == YTreatment.VOWEL
            if methodology.y_treatment == YTreatment.CONTEXTUAL:
                # Contextual Y requires an explicit future phonetic layer; default safely to consonant.
                is_vowel = False
        else:
            is_vowel = ch in "AEIOU"
        if vowels is None or is_vowel == vowels:
            pairs.append((ch, PYTHAGOREAN[ch]))
    return sum(v for _, v in pairs), tuple(pairs)

def expression_number_configured(name: str, methodology: NumerologyMethodology) -> ReducedValue:
    if not normalize_name(name):
        raise ValueError("name must contain at least one alphabetic character")
    raw, _ = _name_sum_configured(name, vowels=None, methodology=methodology)
    return reduce_number(raw, methodology.preserve_master_numbers)

def soul_urge_configured(name: str, methodology: NumerologyMethodology) -> ReducedValue:
    raw, pairs = _name_sum_configured(name, vowels=True, methodology=methodology)
    if not pairs:
        raise ValueError("name must contain at least one configured vowel")
    return reduce_number(raw, methodology.preserve_master_numbers)

def personality_number_configured(name: str, methodology: NumerologyMethodology) -> ReducedValue:
    raw, pairs = _name_sum_configured(name, vowels=False, methodology=methodology)
    if not pairs:
        raise ValueError("name must contain at least one configured consonant")
    return reduce_number(raw, methodology.preserve_master_numbers)

def _pattern_catalog(values: dict[str, ReducedValue], methodology: NumerologyMethodology) -> tuple[NumerologyPattern, ...]:
    patterns: list[NumerologyPattern] = []
    master_vars = tuple(k for k, v in values.items() if v.is_master)
    if master_vars:
        # One pattern cluster: repeated master-number presence is not independent evidence.
        patterns.append(NumerologyPattern("MASTER_NUMBER_PRESENCE", master_vars, None, len(master_vars), methodology.version))
    by_value: dict[int, list[str]] = {}
    for key, value in values.items():
        by_value.setdefault(value.reduced_value, []).append(key)
    for value, vars_ in sorted(by_value.items()):
        if len(vars_) >= 2:
            patterns.append(NumerologyPattern("REPEATED_REDUCED_VALUE", tuple(vars_), value, len(vars_), methodology.version))
    return tuple(patterns)

def calculate_profile(
    birth_date: date,
    name: str | None = None,
    *,
    at: date | None = None,
    methodology: NumerologyMethodology = NumerologyMethodology(),
) -> NumerologyResult:
    """Return structured numerology facts; no semantic interpretation is performed."""
    lp = life_path(birth_date)
    bd = birthday_number(birth_date)
    att = attitude_number(birth_date)
    ex = su = pe = mat = None
    if name:
        ex = expression_number_configured(name, methodology)
        su = soul_urge_configured(name, methodology)
        pe = personality_number_configured(name, methodology)
        mat = reduce_number(lp.reduced_value + ex.reduced_value, methodology.preserve_master_numbers)
    target = at or date.today()
    py = personal_year(birth_date, target.year)
    pm = personal_month(birth_date, target.year, target.month)
    pd = personal_day(birth_date, target.year, target.month, target.day)
    pins = pinnacles(birth_date)
    ch = challenges(birth_date)
    values = {"LIFE_PATH": lp, "BIRTHDAY": bd, "ATTITUDE": att}
    if ex: values["EXPRESSION"] = ex
    if su: values["SOUL_URGE"] = su
    if pe: values["PERSONALITY"] = pe
    if mat: values["MATURITY"] = mat
    patterns = _pattern_catalog(values, methodology)
    return NumerologyResult(lp, bd, att, ex, su, pe, mat, py, pm, pd, pins, ch, patterns, methodology.version, methodology.calculation_version)

def signal_candidates(result: NumerologyResult) -> tuple[NumerologySignalCandidate, ...]:
    candidates: list[NumerologySignalCandidate] = []
    fields = ("life_path", "birthday", "attitude", "expression", "soul_urge", "personality", "maturity", "personal_year", "personal_month", "personal_day")
    for field in fields:
        value = getattr(result, field)
        if value is None:
            continue
        candidates.append(NumerologySignalCandidate(field.upper(), value.reduced_value, value.is_master, "BIRTH_DERIVED" if field in fields[:3] else ("NAME_DERIVED" if field in fields[3:7] else "CYCLE_DERIVED"), result.methodology_version, result.calculation_version, f"NUM:{field}:{value.raw_value}"))
    return tuple(candidates)
