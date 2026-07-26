from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import RLock


@dataclass(slots=True)
class DecisionMetricsSnapshot:
    total: int = 0
    approved: int = 0
    rejected: int = 0
    deferred: int = 0
    review_required: int = 0
    buy: int = 0
    sell: int = 0
    hold: int = 0
    scale_in: int = 0
    scale_out: int = 0
    close_position: int = 0
    cancel: int = 0


class DecisionMetrics:
    def __init__(self) -> None:
        self._values = DecisionMetricsSnapshot()
        self._lock = RLock()

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            if not hasattr(self._values, name):
                return
            setattr(self._values, name, getattr(self._values, name) + amount)

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return asdict(self._values)
