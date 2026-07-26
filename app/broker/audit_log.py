from __future__ import annotations

from collections import deque
from threading import RLock

from .broker_models import BrokerOrderResult


class BrokerAuditLog:
    def __init__(self, max_entries: int = 5000) -> None:
        self._entries: deque[BrokerOrderResult] = deque(maxlen=max_entries)
        self._lock = RLock()

    def append(self, result: BrokerOrderResult) -> None:
        with self._lock:
            self._entries.append(result)

    def recent(self, limit: int = 50) -> tuple[BrokerOrderResult, ...]:
        with self._lock:
            return tuple(list(self._entries)[-limit:])
