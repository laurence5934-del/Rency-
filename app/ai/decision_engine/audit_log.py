from __future__ import annotations

from collections import deque
from threading import RLock

from .models import DecisionReport


class DecisionAuditLog:
    def __init__(self, max_entries: int = 1000) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._entries: deque[DecisionReport] = deque(maxlen=max_entries)
        self._lock = RLock()

    def append(self, report: DecisionReport) -> None:
        with self._lock:
            self._entries.append(report)

    def recent(self, limit: int = 50) -> tuple[DecisionReport, ...]:
        if limit <= 0:
            return ()
        with self._lock:
            return tuple(list(self._entries)[-limit:])

    def count(self) -> int:
        with self._lock:
            return len(self._entries)
