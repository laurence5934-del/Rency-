from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class AuditEvent:
    timestamp: datetime
    backtest_id: str
    event_type: str
    details: Mapping[str, Any]


class BacktestAuditLog:
    """Thread-safe, in-memory audit trail for deterministic backtest lifecycle events."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._lock = RLock()

    def record(self, backtest_id: str, event_type: str, **details: Any) -> AuditEvent:
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc),
            backtest_id=backtest_id,
            event_type=event_type,
            details=dict(details),
        )
        with self._lock:
            self._events.append(event)
        return event

    def events_for(self, backtest_id: str) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(event for event in self._events if event.backtest_id == backtest_id)

    def all_events(self) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(self._events)
