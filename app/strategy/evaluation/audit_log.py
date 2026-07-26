from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    action: str
    subject: str
    details: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EvaluationAuditLog:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._lock = RLock()

    def record(self, action: str, subject: str, **details: Any) -> None:
        with self._lock:
            self._events.append(AuditEvent(action, subject, dict(details)))

    def snapshot(self) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(self._events)
