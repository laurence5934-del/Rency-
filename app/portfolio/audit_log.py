from __future__ import annotations

from collections import deque
from threading import RLock
from typing import Any


class PortfolioAuditLog:
    def __init__(self, max_entries: int = 2000) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._entries: deque[dict[str, Any]] = deque(maxlen=max_entries)
        self._lock = RLock()

    def append(self, event: dict[str, Any]) -> None:
        with self._lock:
            self._entries.append(dict(event))

    def recent(self, limit: int = 50) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(list(self._entries)[-limit:])
