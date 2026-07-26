from __future__ import annotations

from collections import Counter
from threading import RLock


class StrategyMetrics:
    def __init__(self) -> None:
        self._counters: Counter[str] = Counter()
        self._lock = RLock()

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)
