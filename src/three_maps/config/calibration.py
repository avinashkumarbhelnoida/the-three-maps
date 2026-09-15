"""Phase III golden-dataset calibration utilities.

Calibration is deliberately diagnostic: it never mutates production thresholds or
changes the canonical fusion formula. It compares observed engine outputs with
versioned expected outcomes and reports drift.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from three_maps.config.golden_dataset import golden_cases, load_golden_dataset

@dataclass(frozen=True)
class CalibrationResult:
    case_id: str
    passed: bool
    mismatches: tuple[str, ...] = ()

@dataclass(frozen=True)
class CalibrationReport:
    dataset_id: str
    dataset_version: str
    total: int
    passed: int
    failed: int
    results: tuple[CalibrationResult, ...]

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0


def compare_expected(case: dict[str, Any], observed: dict[str, Any]) -> CalibrationResult:
    mismatches: list[str] = []
    for key, expected in case.get("expected", {}).items():
        actual = observed.get(key)
        if isinstance(expected, float):
            if actual is None or abs(float(actual) - expected) > 1e-5:
                mismatches.append(f"{key}: expected={expected!r} observed={actual!r}")
        else:
            if actual != expected:
                mismatches.append(f"{key}: expected={expected!r} observed={actual!r}")
    return CalibrationResult(case["id"], not mismatches, tuple(mismatches))


def calibrate(case_runner: Callable[[dict[str, Any]], dict[str, Any]], cases: Iterable[dict[str, Any]] | None = None) -> CalibrationReport:
    dataset = load_golden_dataset()
    selected = tuple(cases if cases is not None else golden_cases())
    results = tuple(compare_expected(c, case_runner(c)) for c in selected)
    passed = sum(r.passed for r in results)
    return CalibrationReport(dataset["dataset_id"], dataset["version"], len(results), passed, len(results) - passed, results)
