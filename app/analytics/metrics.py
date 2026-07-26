from __future__ import annotations

from collections import Counter
from threading import RLock


class AnalyticsMetrics:
    def __init__(self) -> None:
        self._counters: Counter[str] = Counter()
        self._lock = RLock()

    def increment(self, name: str, value: int = 1) -> None:
        if value < 0:
            raise ValueError("metric increment cannot be negative")
        with self._lock:
            self._counters[name] += value

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)
