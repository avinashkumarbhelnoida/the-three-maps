from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from three_maps.domain.types import IndicatorWeightClass, Signal, SystemScore, SystemScoreStatus
from three_maps.engines.status import resolve_system_status


DEFAULT_INDICATOR_WEIGHTS: Mapping[str, float] = {
    IndicatorWeightClass.MINOR: 0.50,
    IndicatorWeightClass.STANDARD: 1.00,
    IndicatorWeightClass.STRONG: 1.25,
    IndicatorWeightClass.PRIMARY: 1.50,
}


@dataclass(frozen=True)
class SystemScoreIndicator:
    signal: Signal
    weight_class: IndicatorWeightClass | None = None
    expected: bool = True
    target_relevant: bool = True
    available: bool = True
    valid: bool = True
    sufficiency: float = 1.0
    material_gap: bool = False

    @property
    def weight(self) -> float:
        weight_class = self.weight_class or self.signal.weight_class
        try:
            return DEFAULT_INDICATOR_WEIGHTS[weight_class]
        except KeyError as exc:
            raise ValueError(f"Unknown indicator weight class: {weight_class}") from exc


@dataclass(frozen=True)
class SystemScoreInput:
    system: str
    indicators: tuple[SystemScoreIndicator, ...]
    target_valid: bool = True
    minimum_sufficiency: float = 0.50


def _relevant_expected(items: Iterable[SystemScoreIndicator]) -> list[SystemScoreIndicator]:
    return [i for i in items if i.expected and i.target_relevant]


def calculate_system_score(x: SystemScoreInput) -> SystemScore:
    """Calculate a map-level System Score using the canonical weighted formula.

    Missing/unavailable/invalid indicators are never zero-filled. Coverage is
    diagnostic and does not multiply or otherwise penalize the calculated score.
    """
    items = list(x.indicators)
    expected = _relevant_expected(items)
    valid_available = [
        i for i in expected
        if i.available and i.valid and i.sufficiency >= x.minimum_sufficiency
    ]

    target_level_invalid = not x.target_valid
    # Invalid target-level evidence/calculation has absolute precedence.
    if target_level_invalid:
        status = resolve_system_status(
            target_valid=False, score_calculable=True, material_gap=False
        )
        return SystemScore(
            system=x.system,
            status=status,
            coverage=0.0,
            data_confidence=0.0,
            valid_indicator_count=0,
            expected_indicator_count=len(expected),
        )

    # Invalid individual indicators are excluded when they are safely excludable.
    # If no valid usable indicator remains, score calculation is unavailable.
    score_calculable = bool(valid_available)
    available_weight = sum(i.weight for i in valid_available)
    expected_weight = sum(i.weight for i in expected)
    coverage = available_weight / expected_weight if expected_weight else 0.0

    if not score_calculable:
        status = resolve_system_status(
            target_valid=True, score_calculable=False, material_gap=False
        )
        return SystemScore(
            system=x.system,
            status=status,
            coverage=coverage,
            data_confidence=0.0,
            valid_indicator_count=0,
            expected_indicator_count=len(expected),
        )

    numerator = 0.0
    denominator = 0.0
    confidence_numerator = 0.0
    confidence_denominator = 0.0
    for item in valid_available:
        s_norm = item.signal.strength / 4.0
        effective = s_norm * item.signal.confidence * item.weight * item.signal.relevance
        numerator += effective
        denominator += item.weight * item.signal.relevance
        confidence_numerator += item.signal.confidence * item.weight * item.signal.relevance
        confidence_denominator += item.weight * item.signal.relevance

    score = numerator / denominator if denominator else None
    if score is None:
        status = resolve_system_status(
            target_valid=True, score_calculable=False, material_gap=False
        )
        return SystemScore(
            system=x.system,
            status=status,
            coverage=coverage,
            data_confidence=0.0,
            valid_indicator_count=len(valid_available),
            expected_indicator_count=len(expected),
        )

    material_gap = coverage < 1.0 or any(i.material_gap for i in expected if i not in valid_available)
    status = resolve_system_status(
        target_valid=True, score_calculable=True, material_gap=material_gap
    )
    data_confidence = (
        confidence_numerator / confidence_denominator
        if confidence_denominator else 0.0
    )

    return SystemScore(
        system=x.system,
        score=max(0.0, min(1.0, score)),
        status=status,
        coverage=max(0.0, min(1.0, coverage)),
        data_confidence=max(0.0, min(1.0, data_confidence)),
        valid_indicator_count=len(valid_available),
        expected_indicator_count=len(expected),
    )


def count_valid_systems(results: Iterable[SystemScore]) -> int:
    """Downstream k: valid score-bearing systems only."""
    return sum(
        1 for result in results
        if result.status in (SystemScoreStatus.EVALUATED, SystemScoreStatus.PARTIAL)
        and result.score is not None
    )
