from __future__ import annotations

import uuid
from collections import deque
from threading import RLock
from typing import Any, Mapping

from .models import TimelineEvent, utc_now


class RecoveryTimeline:
    def __init__(self, max_events: int = 5000) -> None:
        if max_events < 1:
            raise ValueError("max_events must be positive")
        self._lock = RLock()
        self._events: deque[TimelineEvent] = deque(maxlen=max_events)

    def record(
        self,
        event_type: str,
        message: str,
        *,
        component: str | None = None,
        incident_id: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> TimelineEvent:
        event = TimelineEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            created_at_utc=utc_now(),
            component=component,
            incident_id=incident_id,
            message=message,
            payload=dict(payload or {}),
        )
        with self._lock:
            self._events.append(event)
        return event

    def events(self, limit: int | None = None) -> tuple[TimelineEvent, ...]:
        with self._lock:
            values = tuple(self._events)
        return values[-limit:] if limit is not None else values

    def for_incident(self, incident_id: str) -> tuple[TimelineEvent, ...]:
        return tuple(item for item in self.events() if item.incident_id == incident_id)
