from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ComponentCriticality(str, Enum):
    OPTIONAL = "OPTIONAL"
    IMPORTANT = "IMPORTANT"
    CRITICAL = "CRITICAL"


class ComponentState(str, Enum):
    UNKNOWN = "UNKNOWN"
    STARTING = "STARTING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"
    STOPPED = "STOPPED"


class IncidentSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    RECOVERING = "RECOVERING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class RecoveryAction(str, Enum):
    NONE = "NONE"
    RETRY = "RETRY"
    OPEN_CIRCUIT = "OPEN_CIRCUIT"
    FAILOVER = "FAILOVER"
    CHECKPOINT = "CHECKPOINT"
    RESTORE = "RESTORE"
    PAUSE_TRADING = "PAUSE_TRADING"
    SHUTDOWN = "SHUTDOWN"


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    name: str
    state: ComponentState
    healthy: bool
    ready: bool
    score: float
    checked_at_utc: str
    latency_ms: float | None = None
    message: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data


@dataclass(frozen=True, slots=True)
class HealthSnapshot:
    created_at_utc: str
    healthy: bool
    ready: bool
    score: float
    components: tuple[ComponentHealth, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at_utc": self.created_at_utc,
            "healthy": self.healthy,
            "ready": self.ready,
            "score": self.score,
            "components": [item.to_dict() for item in self.components],
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    created_at_utc: str
    trading_allowed: bool
    score: float
    passed: tuple[str, ...]
    failed: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    event_id: str
    event_type: str
    created_at_utc: str
    component: str | None
    incident_id: str | None
    message: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Incident:
    incident_id: str
    title: str
    severity: IncidentSeverity
    status: IncidentStatus
    component: str | None
    opened_at_utc: str
    updated_at_utc: str
    resolved_at_utc: str | None = None
    root_cause: str | None = None
    recovery_actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        data["status"] = self.status.value
        return data


@dataclass(frozen=True, slots=True)
class RecoveryPolicy:
    name: str
    failure_type: str
    actions: tuple[RecoveryAction, ...]
    max_attempts: int = 1
    enabled: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("policy name cannot be empty")
        if not self.failure_type.strip():
            raise ValueError("failure_type cannot be empty")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["actions"] = [action.value for action in self.actions]
        return data


@dataclass(frozen=True, slots=True)
class DiagnosticFinding:
    code: str
    severity: IncidentSeverity
    component: str | None
    message: str
    remediation: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        return data
