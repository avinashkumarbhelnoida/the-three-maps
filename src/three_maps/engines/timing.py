"""Timing and temporal intelligence for THE THREE MAPS (201.81K).

Timing qualifies when an already-established signal is active; it never creates
semantic evidence. Dasha/cycle/lineage windows are treated as temporal evidence
and remain versioned, bounded, and auditable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Sequence


class TemporalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    UPCOMING = "UPCOMING"
    EXPIRED = "EXPIRED"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


class TemporalCompatibility(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    PARTIAL = "PARTIAL"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TemporalWindow:
    window_id: str
    source_system: str
    start: date
    end: date | None
    relevance: float = 1.0
    confidence: float = 1.0
    active: bool = True
    source_variable: str | None = None
    evidence_cluster_id: str | None = None

    def __post_init__(self) -> None:
        if self.end is not None and self.end < self.start:
            raise ValueError("Temporal window end cannot precede start")
        if not 0 <= self.relevance <= 1 or not 0 <= self.confidence <= 1:
            raise ValueError("relevance/confidence must be between 0 and 1")


@dataclass(frozen=True)
class TemporalSignal:
    source_system: str
    source_variable: str
    window_id: str
    status: TemporalStatus
    temporal_strength: float
    confidence: float
    relevance: float
    temporal_scope: str
    evidence_cluster_id: str | None = None


@dataclass(frozen=True)
class TimingAssessment:
    status: TemporalStatus
    activation_score: float
    confidence: float
    compatibility: TemporalCompatibility
    active_systems: tuple[str, ...]
    source_windows: tuple[str, ...]
    temporal_scope: str
    reason: str


def _as_date(value: date | datetime) -> date:
    return value.date() if isinstance(value, datetime) else value


def classify_window(window: TemporalWindow, *, at: date | datetime) -> TemporalStatus:
    if not window.active:
        return TemporalStatus.UNAVAILABLE
    d = _as_date(at)
    if d < window.start:
        return TemporalStatus.UPCOMING
    if window.end is not None and d > window.end:
        return TemporalStatus.EXPIRED
    return TemporalStatus.ACTIVE


def build_temporal_signal(window: TemporalWindow, *, at: date | datetime) -> TemporalSignal:
    status = classify_window(window, at=at)
    strength = 1.0 if status == TemporalStatus.ACTIVE else 0.0
    return TemporalSignal(
        source_system=window.source_system,
        source_variable=window.source_variable or "TEMPORAL_WINDOW",
        window_id=window.window_id,
        status=status,
        temporal_strength=strength,
        confidence=window.confidence,
        relevance=window.relevance,
        temporal_scope="ACTIVE" if status == TemporalStatus.ACTIVE else status.value,
        evidence_cluster_id=window.evidence_cluster_id,
    )


def assess_timing(signals: Sequence[TemporalSignal], *, target_scope: str | None = None) -> TimingAssessment:
    valid = [s for s in signals if s.status != TemporalStatus.INVALID]
    if not valid:
        return TimingAssessment(TemporalStatus.UNAVAILABLE, 0.0, 0.0,
                                TemporalCompatibility.UNKNOWN, (), (), target_scope or "UNKNOWN",
                                "No valid temporal evidence is available.")
    active = [s for s in valid if s.status == TemporalStatus.ACTIVE and s.temporal_strength > 0]
    if not active:
        upcoming = any(s.status == TemporalStatus.UPCOMING for s in valid)
        status = TemporalStatus.UPCOMING if upcoming else TemporalStatus.EXPIRED
        return TimingAssessment(status, 0.0, sum(s.confidence for s in valid) / len(valid),
                                TemporalCompatibility.UNKNOWN, (), tuple(s.window_id for s in valid),
                                target_scope or "NON_ACTIVE", "No temporal source is active at the evaluation date.")
    weighted = sum(s.temporal_strength * s.confidence * s.relevance for s in active)
    denom = sum(s.confidence * s.relevance for s in active)
    score = weighted / denom if denom else 0.0
    systems = tuple(sorted(set(s.source_system for s in active)))
    scopes = {s.temporal_scope for s in active}
    if target_scope and target_scope not in scopes and target_scope != "ACTIVE":
        compatibility = TemporalCompatibility.PARTIAL
    else:
        compatibility = TemporalCompatibility.COMPATIBLE
    return TimingAssessment(TemporalStatus.ACTIVE, score,
                            sum(s.confidence for s in active) / len(active), compatibility,
                            systems, tuple(s.window_id for s in active), target_scope or "ACTIVE",
                            "At least one validated temporal source is active.")
