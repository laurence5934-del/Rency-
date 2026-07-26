from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import RLock


@dataclass(slots=True)
class ConfidenceMetricsSnapshot:
    evaluations: int = 0
    trusted: int = 0
    reviewed: int = 0
    rejected: int = 0


class ConfidenceMetrics:
    def __init__(self) -> None:
        self._values = ConfidenceMetricsSnapshot()
        self._lock = RLock()

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            if not hasattr(self._values, name):
                raise AttributeError(f"unknown metric: {name}")
            setattr(self._values, name, getattr(self._values, name) + amount)

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return asdict(self._values)
