from __future__ import annotations
from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

class FixedWindowRateLimiter:
    def __init__(self, limit: int = 60, window_seconds: int = 60):
        if limit < 1 or window_seconds < 1: raise ValueError('invalid rate limiter configuration')
        self.limit, self.window_seconds = limit, window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        import time
        t = time.time() if now is None else now
        with self._lock:
            q = self._events[key]
            cutoff = t - self.window_seconds
            while q and q[0] <= cutoff: q.popleft()
            if len(q) >= self.limit: return False
            q.append(t)
            return True

    def reset(self) -> None:
        with self._lock: self._events.clear()


def request_id() -> str:
    return 'REQ-' + uuid4().hex[:16]
