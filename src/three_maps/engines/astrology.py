from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from math import floor
from zoneinfo import ZoneInfo

import swisseph as swe

# Initial deterministic Vedic calculation layer.  Interpretation/yoga mapping
# belongs downstream; this module returns astronomical and classical structural facts.
SIDEREAL_MODE = swe.SIDM_LAHIRI
NAKSHATRA_SPAN = 360.0 / 27.0
PADA_SPAN = NAKSHATRA_SPAN / 4.0

PLANETS = {
    "SUN": swe.SUN,
    "MOON": swe.MOON,
    "MARS": swe.MARS,
    "MERCURY": swe.MERCURY,
    "JUPITER": swe.JUPITER,
    "VENUS": swe.VENUS,
    "SATURN": swe.SATURN,
    "RAHU": swe.MEAN_NODE,
}

NAKSHATRAS = (
    "ASHWINI", "BHARANI", "KRITTIKA", "ROHINI", "MRIGASHIRA", "ARDRA",
    "PUNARVASU", "PUSHYA", "ASHLESHA", "MAGHA", "PURVA_PHALGUNI",
    "UTTARA_PHALGUNI", "HASTA", "CHITRA", "SWATI", "VISHAKHA", "ANURADHA",
    "JYESHTHA", "MOOLA", "PURVA_ASHADHA", "UTTARA_ASHADHA", "SHRAVANA",
    "DHANISHTHA", "SHATABHISHA", "PURVA_BHADRAPADA", "UTTARA_BHADRAPADA", "REVATI",
)

SIGNS = (
    "ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO",
    "LIBRA", "SCORPIO", "SAGITTARIUS", "CAPRICORN", "AQUARIUS", "PISCES",
)

# Classical exaltation/debilitation placements used as structural facts.
EXALTATION = {"SUN": 0, "MOON": 1, "MARS": 9, "MERCURY": 5, "JUPITER": 3, "VENUS": 11, "SATURN": 6}
DEBILITATION = {p: (s + 6) % 12 for p, s in EXALTATION.items()}

# Classical own signs.  Rahu/Ketu are deliberately excluded from dignity here;
# their treatment is methodology-controlled and must not be silently invented.
OWN_SIGNS = {
    "SUN": {4}, "MOON": {3}, "MARS": {0, 7}, "MERCURY": {2, 5},
    "JUPITER": {8, 11}, "VENUS": {1, 6}, "SATURN": {9, 10},
}

VIMSHOTTARI = (
    ("KETU", 7), ("VENUS", 20), ("SUN", 6), ("MOON", 10),
    ("MARS", 7), ("RAHU", 18), ("JUPITER", 16), ("SATURN", 19), ("MERCURY", 17),
)

@dataclass(frozen=True)
class PlanetPosition:
    planet: str
    longitude: float
    latitude: float
    speed: float
    sign_index: int
    sign: str
    house: int
    nakshatra_index: int
    nakshatra: str
    pada: int
    retrograde: bool

@dataclass(frozen=True)
class Aspect:
    source: str
    target: str
    distance_signs: int
    aspect_type: str

@dataclass(frozen=True)
class Conjunction:
    planets: tuple[str, ...]
    distance_degrees: float

@dataclass(frozen=True)
class Dignity:
    planet: str
    status: str

@dataclass(frozen=True)
class DashaPeriod:
    lord: str
    start: datetime
    end: datetime
    years: float

@dataclass(frozen=True)
class YogaDefinition:
    """Versioned structural yoga rule; conditions are declarative, not interpretive."""
    id: str
    name: str
    required_planets: tuple[str, ...]
    formation_rule: str
    methodology_version: str


@dataclass(frozen=True)
class YogaEvaluation:
    yoga_id: str
    name: str
    formed: bool
    strength: float
    context_satisfied: bool
    activated: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class AstrologyResult:
    julian_day_ut: float
    ascendant_longitude: float
    ascendant_sign_index: int
    ascendant_sign: str
    ayanamsha: float
    planets: tuple[PlanetPosition, ...]
    aspects: tuple[Aspect, ...]
    conjunctions: tuple[Conjunction, ...]
    dignities: tuple[Dignity, ...]
    dasha_start_lord: str
    dasha_balance_years: float
    mahadashas: tuple[DashaPeriod, ...]
    methodology_version: str
    calculation_version: str


def _validate_datetime(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("birth_datetime must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("birth_datetime must be timezone-aware")
    return value


def _sign_index(longitude: float) -> int:
    return int(longitude // 30.0) % 12


def _nakshatra(longitude: float) -> tuple[int, str, int]:
    idx = int(longitude // NAKSHATRA_SPAN) % 27
    within = longitude - idx * NAKSHATRA_SPAN
    pada = int(within // PADA_SPAN) + 1
    return idx, NAKSHATRAS[idx], min(4, pada)


def _whole_sign_house(planet_sign: int, asc_sign: int) -> int:
    return ((planet_sign - asc_sign) % 12) + 1


def _sidereal_longitudes(jd_ut: float) -> dict[str, tuple[float, float, float]]:
    swe.set_sid_mode(SIDEREAL_MODE)
    result: dict[str, tuple[float, float, float]] = {}
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
    for name, body in PLANETS.items():
        xx, _ = swe.calc_ut(jd_ut, body, flags)
        result[name] = (xx[0] % 360.0, xx[1], xx[3])
    # Ketu is always 180 degrees from Rahu.
    rahu = result["RAHU"]
    result["KETU"] = ((rahu[0] + 180.0) % 360.0, -rahu[1], rahu[2])
    return result


def _ascendant(jd_ut: float, longitude: float, latitude: float) -> float:
    # Tropical houses are used only to obtain the astronomical Ascendant;
    # sidereal conversion is then applied using the same Lahiri ayanamsha.
    cusps, ascmc = swe.houses_ex(jd_ut, latitude, longitude, b"P")
    tropical_asc = ascmc[0]
    ay = swe.get_ayanamsa_ut(jd_ut)
    return (tropical_asc - ay) % 360.0


def _dignity(planet: str, sign_index: int) -> str:
    if planet in EXALTATION and sign_index == EXALTATION[planet]:
        return "EXALTED"
    if planet in DEBILITATION and sign_index == DEBILITATION[planet]:
        return "DEBILITATED"
    if planet in OWN_SIGNS and sign_index in OWN_SIGNS[planet]:
        return "OWN_SIGN"
    return "OTHER"


def _aspects(planets: tuple[PlanetPosition, ...]) -> tuple[Aspect, ...]:
    # Parashari graha drishti: all planets 7th; Mars 4th/8th; Jupiter 5th/9th;
    # Saturn 3rd/10th.  Nodes are excluded pending the versioned Rahu/Ketu rule.
    out: list[Aspect] = []
    special = {"MARS": {4, 7, 8}, "JUPITER": {5, 7, 9}, "SATURN": {3, 7, 10}}
    for src in planets:
        if src.planet in {"RAHU", "KETU"}:
            continue
        offsets = special.get(src.planet, {7})
        for dst in planets:
            if src.planet == dst.planet:
                continue
            distance = ((dst.sign_index - src.sign_index) % 12) + 1
            if distance in offsets:
                typ = "7TH" if distance == 7 else f"{distance}TH"
                out.append(Aspect(src.planet, dst.planet, distance, typ))
    return tuple(out)


def _conjunctions(planets: tuple[PlanetPosition, ...], orb: float = 8.0) -> tuple[Conjunction, ...]:
    out: list[Conjunction] = []
    for i, a in enumerate(planets):
        for b in planets[i + 1:]:
            d = abs(a.longitude - b.longitude)
            d = min(d, 360.0 - d)
            if d <= orb:
                out.append(Conjunction((a.planet, b.planet), d))
    return tuple(out)


def _dasha_schedule(birth_dt: datetime, moon_longitude: float, years: int = 120) -> tuple[str, float, tuple[DashaPeriod, ...]]:
    nak_idx, _, _ = _nakshatra(moon_longitude)
    start_lord, start_years = VIMSHOTTARI[nak_idx % 9]
    nak_fraction = (moon_longitude % NAKSHATRA_SPAN) / NAKSHATRA_SPAN
    balance = start_years * (1.0 - nak_fraction)

    # Convert year fractions to days for deterministic scheduling. The schedule is
    # a computational representation; exact calendar presentation belongs upstream/downstream config.
    day_per_year = 365.2425
    cursor = birth_dt
    periods: list[DashaPeriod] = []
    start_idx = nak_idx % 9
    first = True
    accumulated = 0.0
    while accumulated < years:
        for step in range(9):
            lord, full_years = VIMSHOTTARI[(start_idx + step) % 9]
            dur = balance if first else float(full_years)
            first = False
            end = cursor + timedelta(days=dur * day_per_year)
            periods.append(DashaPeriod(lord, cursor, end, dur))
            cursor = end
            accumulated += dur
            if accumulated >= years:
                break
    return start_lord, balance, tuple(periods)


def active_mahadasha(result: AstrologyResult, at: datetime) -> DashaPeriod | None:
    """Return the active Mahadasha at a timezone-aware instant, if represented."""
    at = _validate_datetime(at)
    for period in result.mahadashas:
        if period.start <= at < period.end:
            return period
    return None


def evaluate_yoga_definition(
    result: AstrologyResult,
    definition: YogaDefinition,
    *,
    at: datetime | None = None,
    context_satisfied: bool = True,
) -> YogaEvaluation:
    """Evaluate a declarative yoga definition through formation→strength→context→activation.

    This function deliberately supports only explicit, versioned formation rules. It never
    assigns a yoga from a planet keyword alone. Supported initial formation_rule values:
    ``SAME_SIGN`` and ``MUTUAL_ASPECT``.
    """
    if definition.methodology_version != result.methodology_version:
        return YogaEvaluation(definition.id, definition.name, False, 0.0, False, False, ("VERSION_MISMATCH",))
    if not definition.required_planets:
        return YogaEvaluation(definition.id, definition.name, False, 0.0, False, False, ("NO_REQUIRED_PLANETS",))
    positions = {p.planet: p for p in result.planets}
    if any(x not in positions for x in definition.required_planets):
        return YogaEvaluation(definition.id, definition.name, False, 0.0, False, False, ("MISSING_PLANET",))
    required = [positions[x] for x in definition.required_planets]
    if definition.formation_rule == "SAME_SIGN":
        formed = len({p.sign_index for p in required}) == 1
    elif definition.formation_rule == "MUTUAL_ASPECT":
        pairs = {(a.source, a.target) for a in result.aspects}
        formed = all((a.planet, b.planet) in pairs and (b.planet, a.planet) in pairs
                     for i, a in enumerate(required) for b in required[i + 1:])
    else:
        raise ValueError(f"Unsupported yoga formation rule: {definition.formation_rule}")
    if not formed:
        return YogaEvaluation(definition.id, definition.name, False, 0.0, False, False, ("FORMATION_NOT_MET",))

    # Strength is a structural bounded modifier, not a claim of life outcome.
    dignity_bonus = sum(1 for p in required if _dignity(p.planet, p.sign_index) in {"EXALTED", "OWN_SIGN"}) / len(required)
    retrograde_penalty = sum(1 for p in required if p.retrograde) / len(required)
    strength = max(0.0, min(1.0, 0.5 + 0.5 * dignity_bonus - 0.15 * retrograde_penalty))
    active = context_satisfied and (at is None or active_mahadasha(result, at) is not None)
    reasons = ("FORMATION_MET", "CONTEXT_MET" if context_satisfied else "CONTEXT_UNSATISFIED",
               "ACTIVATED" if active else "NOT_ACTIVATED")
    return YogaEvaluation(definition.id, definition.name, True, strength, context_satisfied, active, reasons)


def structural_signals(result: AstrologyResult) -> tuple[dict[str, object], ...]:
    """Expose auditable astrology facts for downstream Signal/Mapping layers."""
    out: list[dict[str, object]] = []
    for p in result.planets:
        dignity = _dignity(p.planet, p.sign_index)
        out.extend((
            {"source_variable": "PLANET_SIGN", "planet": p.planet, "sign": p.sign, "house": p.house},
            {"source_variable": "PLANET_NAKSHATRA", "planet": p.planet, "nakshatra": p.nakshatra, "pada": p.pada},
            {"source_variable": "PLANET_DIGNITY", "planet": p.planet, "dignity": dignity},
            {"source_variable": "PLANET_RETROGRADE", "planet": p.planet, "retrograde": p.retrograde},
        ))
    for a in result.aspects:
        out.append({"source_variable": "ASPECT", "source": a.source, "target": a.target, "aspect_type": a.aspect_type})
    for c in result.conjunctions:
        out.append({"source_variable": "CONJUNCTION", "planets": c.planets, "distance_degrees": c.distance_degrees})
    return tuple(out)


def calculate_astrology(
    birth_datetime: datetime,
    longitude: float,
    latitude: float,
    *,
    methodology_version: str = "MV-001",
    calculation_version: str = "CV-001",
) -> AstrologyResult:
    """Calculate the deterministic Vedic structural layer using Lahiri sidereal positions and Whole Sign houses."""
    birth_datetime = _validate_datetime(birth_datetime)
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError("longitude must be between -180 and 180")
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError("latitude must be between -90 and 90")

    utc = birth_datetime.astimezone(timezone.utc)
    hour = utc.hour + utc.minute / 60.0 + utc.second / 3600.0 + utc.microsecond / 3_600_000_000.0
    jd = swe.julday(utc.year, utc.month, utc.day, hour)
    swe.set_sid_mode(SIDEREAL_MODE)
    ay = swe.get_ayanamsa_ut(jd)
    asc = _ascendant(jd, longitude, latitude)
    asc_sign = _sign_index(asc)

    raw = _sidereal_longitudes(jd)
    positions: list[PlanetPosition] = []
    for planet, (lon, lat, speed) in raw.items():
        sign_idx = _sign_index(lon)
        nk_idx, nk_name, pada = _nakshatra(lon)
        positions.append(PlanetPosition(
            planet, lon, lat, speed, sign_idx, SIGNS[sign_idx],
            _whole_sign_house(sign_idx, asc_sign), nk_idx, nk_name, pada, speed < 0
        ))
    positions = sorted(positions, key=lambda p: p.planet)
    planets = tuple(positions)

    aspects = _aspects(planets)
    conjunctions = _conjunctions(planets)
    dignities = tuple(Dignity(p.planet, _dignity(p.planet, p.sign_index)) for p in planets)
    moon = next(p for p in planets if p.planet == "MOON")
    dasha_lord, dasha_balance, dashas = _dasha_schedule(birth_datetime, moon.longitude)

    return AstrologyResult(
        jd, asc, asc_sign, SIGNS[asc_sign], ay, planets, aspects,
        conjunctions, dignities, dasha_lord, dasha_balance, dashas,
        methodology_version, calculation_version,
    )
