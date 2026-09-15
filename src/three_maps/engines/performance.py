from __future__ import annotations
from dataclasses import dataclass
from time import perf_counter
from typing import Callable, Any

@dataclass(frozen=True)
class PerformanceResult:
    iterations: int
    elapsed_seconds: float
    operations_per_second: float
    average_ms: float
    passed: bool


def benchmark(fn: Callable[[], Any], *, iterations: int = 100, max_average_ms: float = 250.0) -> PerformanceResult:
    if iterations < 1: raise ValueError('iterations must be >= 1')
    start = perf_counter()
    for _ in range(iterations): fn()
    elapsed = perf_counter() - start
    avg_ms = elapsed * 1000 / iterations
    return PerformanceResult(iterations, elapsed, iterations / elapsed if elapsed else float('inf'), avg_ms, avg_ms <= max_average_ms)
