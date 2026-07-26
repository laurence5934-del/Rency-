from __future__ import annotations

import uuid
from threading import RLock
from typing import Any, Mapping

from .models import Incident, IncidentSeverity, IncidentStatus, utc_now
from .timeline import RecoveryTimeline


class IncidentManager:
    def __init__(self, timeline: RecoveryTimeline) -> None:
        self.timeline = timeline
        self._lock = RLock()
        self._incidents: dict[str, Incident] = {}

    def open(
        self,
        title: str,
        severity: IncidentSeverity,
        *,
        component: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Incident:
        now = utc_now()
        incident = Incident(
            incident_id=str(uuid.uuid4()),
            title=title,
            severity=severity,
            status=IncidentStatus.OPEN,
            component=component,
            opened_at_utc=now,
            updated_at_utc=now,
            metadata=dict(metadata or {}),
        )
        with self._lock:
            self._incidents[incident.incident_id] = incident
        self.timeline.record(
            "incident.opened",
            title,
            component=component,
            incident_id=incident.incident_id,
            payload={"severity": severity.value},
        )
        return incident

    def add_action(self, incident_id: str, action: str) -> None:
        incident = self.get(incident_id)
        with self._lock:
            incident.recovery_actions.append(action)
            incident.status = IncidentStatus.RECOVERING
            incident.updated_at_utc = utc_now()
        self.timeline.record(
            "incident.action",
            action,
            component=incident.component,
            incident_id=incident_id,
        )

    def resolve(self, incident_id: str, *, root_cause: str | None = None) -> Incident:
        incident = self.get(incident_id)
        now = utc_now()
        with self._lock:
            incident.status = IncidentStatus.RESOLVED
            incident.root_cause = root_cause
            incident.resolved_at_utc = now
            incident.updated_at_utc = now
        self.timeline.record(
            "incident.resolved",
            incident.title,
            component=incident.component,
            incident_id=incident_id,
            payload={"root_cause": root_cause},
        )
        return incident

    def get(self, incident_id: str) -> Incident:
        with self._lock:
            incident = self._incidents.get(incident_id)
            if incident is None:
                raise KeyError(f"unknown incident: {incident_id}")
            return incident

    def active(self) -> tuple[Incident, ...]:
        with self._lock:
            return tuple(
                item for item in self._incidents.values()
                if item.status != IncidentStatus.RESOLVED
            )

    def all(self) -> tuple[Incident, ...]:
        with self._lock:
            return tuple(self._incidents.values())
