from __future__ import annotations

from threading import RLock
from typing import Any

from .models import utc_now


class AnalyticsAuditLog:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._lock = RLock()

    def append(self, event: dict[str, Any]) -> None:
        with self._lock:
            self._events.append({"timestamp_utc": utc_now(), **event})

    def recent(self, limit: int = 50) -> tuple[dict[str, Any], ...]:
        if limit < 0:
            raise ValueError("limit cannot be negative")
        with self._lock:
            return tuple(self._events[-limit:]) if limit else ()
