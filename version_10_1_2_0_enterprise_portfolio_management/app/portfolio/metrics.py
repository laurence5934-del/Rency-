from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import RLock


@dataclass(slots=True)
class PortfolioMetricsSnapshot:
    fills_applied: int = 0
    cash_movements: int = 0
    price_updates: int = 0
    snapshots_created: int = 0
    reconciliations: int = 0
    reconciliation_failures: int = 0


class PortfolioMetrics:
    def __init__(self) -> None:
        self._values = PortfolioMetricsSnapshot()
        self._lock = RLock()

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            if not hasattr(self._values, name):
                raise KeyError(name)
            setattr(self._values, name, getattr(self._values, name) + amount)

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return asdict(self._values)
