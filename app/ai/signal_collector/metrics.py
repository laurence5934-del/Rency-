from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import RLock


@dataclass(slots=True)
class SignalCollectorMetricsSnapshot:
    collection_cycles: int = 0
    providers_polled: int = 0
    raw_signals_received: int = 0
    signals_accepted: int = 0
    signals_rejected: int = 0
    signals_duplicated: int = 0
    provider_failures: int = 0
    publish_failures: int = 0


class SignalCollectorMetrics:
    def __init__(self) -> None:
        self._values = SignalCollectorMetricsSnapshot()
        self._lock = RLock()

    def increment(self, field_name: str, amount: int = 1) -> None:
        if amount < 0:
            raise ValueError("metric increment cannot be negative")
        with self._lock:
            if not hasattr(self._values, field_name):
                raise AttributeError(f"unknown metric: {field_name}")
            setattr(
                self._values,
                field_name,
                getattr(self._values, field_name) + amount,
            )

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return asdict(self._values)
