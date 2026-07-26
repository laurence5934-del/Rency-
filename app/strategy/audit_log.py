from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Mapping


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    subject: str
    details: Mapping[str, Any]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class StrategyAuditLog:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._lock = RLock()

    def record(self, event_type: str, subject: str, details: Mapping[str, Any]) -> AuditEvent:
        event = AuditEvent(event_type, subject, dict(details))
        with self._lock:
            self._events.append(event)
        return event

    def events(self) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(self._events)
