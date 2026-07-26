from __future__ import annotations

from collections import Counter
from threading import RLock


class EvaluationMetrics:
    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()
        self._lock = RLock()

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counts[name] += amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)
