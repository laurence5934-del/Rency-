from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AuditTrailStatus(str, Enum):
    """Lifecycle status of an audit-trail operation."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AuditSeverity(str, Enum):
    """Severity assigned to an audit event."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditEventType(str, Enum):
    """Supported enterprise trading audit events."""

    COORDINATION_STARTED = "COORDINATION_STARTED"
    AGENT_OPINION_RECORDED = "AGENT_OPINION_RECORDED"
    COORDINATION_COMPLETED = "COORDINATION_COMPLETED"

    TRADE_APPROVED = "TRADE_APPROVED"
    TRADE_REVIEW_REQUIRED = "TRADE_REVIEW_REQUIRED"
    TRADE_REJECTED = "TRADE_REJECTED"

    RISK_GATE_APPROVED = "RISK_GATE_APPROVED"
    RISK_GATE_BLOCKED = "RISK_GATE_BLOCKED"

    REGIME_GATE_APPROVED = "REGIME_GATE_APPROVED"
    REGIME_GATE_BLOCKED = "REGIME_GATE_BLOCKED"

    BROKER_SUBMISSION_STARTED = "BROKER_SUBMISSION_STARTED"
    BROKER_SUBMISSION_COMPLETED = "BROKER_SUBMISSION_COMPLETED"
    BROKER_SUBMISSION_FAILED = "BROKER_SUBMISSION_FAILED"

    EXECUTION_COMPLETED = "EXECUTION_COMPLETED"
    EXECUTION_FAILED = "EXECUTION_FAILED"

    CUSTOM = "CUSTOM"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """One immutable event in an enterprise execution audit trail."""

    sequence_number: int
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    occurred_at: datetime
    message: str
    request_id: str | None = None
    execution_id: str | None = None
    order_id: str | None = None
    source: str = ""
    attributes: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_event_id = self.event_id.strip()
        normalized_message = self.message.strip()
        normalized_source = self.source.strip()

        if self.sequence_number < 1:
            raise ValueError(
                "sequence_number must be greater than zero"
            )

        if not normalized_event_id:
            raise ValueError(
                "event_id must not be empty"
            )

        if not isinstance(
            self.event_type,
            AuditEventType,
        ):
            raise TypeError(
                "event_type must be an AuditEventType"
            )

        if not isinstance(
            self.severity,
            AuditSeverity,
        ):
            raise TypeError(
                "severity must be an AuditSeverity"
            )

        if not isinstance(self.occurred_at, datetime):
            raise TypeError(
                "occurred_at must be a datetime"
            )

        if self.occurred_at.tzinfo is None:
            raise ValueError(
                "occurred_at must be timezone-aware"
            )

        if not normalized_message:
            raise ValueError(
                "message must not be empty"
            )

        normalized_request_id = self._normalize_optional_text(
            self.request_id,
            "request_id",
        )
        normalized_execution_id = self._normalize_optional_text(
            self.execution_id,
            "execution_id",
        )
        normalized_order_id = self._normalize_optional_text(
            self.order_id,
            "order_id",
        )

        normalized_attributes: list[
            tuple[str, str]
        ] = []

        for item in self.attributes:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
            ):
                raise TypeError(
                    "each attribute must be a two-item tuple"
                )

            name, value = item
            normalized_name = str(name).strip()
            normalized_value = str(value).strip()

            if not normalized_name:
                raise ValueError(
                    "attribute names must not be empty"
                )

            normalized_attributes.append(
                (
                    normalized_name,
                    normalized_value,
                )
            )

        object.__setattr__(
            self,
            "event_id",
            normalized_event_id,
        )
        object.__setattr__(
            self,
            "message",
            normalized_message,
        )
        object.__setattr__(
            self,
            "request_id",
            normalized_request_id,
        )
        object.__setattr__(
            self,
            "execution_id",
            normalized_execution_id,
        )
        object.__setattr__(
            self,
            "order_id",
            normalized_order_id,
        )
        object.__setattr__(
            self,
            "source",
            normalized_source,
        )
        object.__setattr__(
            self,
            "attributes",
            tuple(normalized_attributes),
        )

    @staticmethod
    def _normalize_optional_text(
        value: str | None,
        field_name: str,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string or None"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return normalized


@dataclass(frozen=True, slots=True)
class ExecutionAuditRecord:
    """Immutable correlated audit record for one trading workflow."""

    audit_id: str
    request_id: str
    created_at: datetime
    events: tuple[AuditEvent, ...] = field(
        default_factory=tuple
    )
    execution_id: str | None = None
    order_id: str | None = None
    completed_at: datetime | None = None
    successful: bool = False
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_audit_id = self.audit_id.strip()
        normalized_request_id = self.request_id.strip()

        if not normalized_audit_id:
            raise ValueError(
                "audit_id must not be empty"
            )

        if not normalized_request_id:
            raise ValueError(
                "request_id must not be empty"
            )

        self._validate_datetime(
            self.created_at,
            "created_at",
        )

        if self.completed_at is not None:
            self._validate_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.created_at:
                raise ValueError(
                    "completed_at must not be earlier than created_at"
                )

        normalized_execution_id = (
            AuditEvent._normalize_optional_text(
                self.execution_id,
                "execution_id",
            )
        )
        normalized_order_id = (
            AuditEvent._normalize_optional_text(
                self.order_id,
                "order_id",
            )
        )

        normalized_events = tuple(self.events)

        self._validate_events(
            events=normalized_events,
            request_id=normalized_request_id,
            execution_id=normalized_execution_id,
            order_id=normalized_order_id,
        )

        if self.successful and self.completed_at is None:
            raise ValueError(
                "successful records must include completed_at"
            )

        if self.successful and not normalized_events:
            raise ValueError(
                "successful records must include events"
            )

        object.__setattr__(
            self,
            "audit_id",
            normalized_audit_id,
        )
        object.__setattr__(
            self,
            "request_id",
            normalized_request_id,
        )
        object.__setattr__(
            self,
            "execution_id",
            normalized_execution_id,
        )
        object.__setattr__(
            self,
            "order_id",
            normalized_order_id,
        )
        object.__setattr__(
            self,
            "events",
            normalized_events,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )

    @staticmethod
    def _validate_datetime(
        value: datetime,
        field_name: str,
    ) -> None:
        if not isinstance(value, datetime):
            raise TypeError(
                f"{field_name} must be a datetime"
            )

        if value.tzinfo is None:
            raise ValueError(
                f"{field_name} must be timezone-aware"
            )

    @staticmethod
    def _validate_events(
        *,
        events: tuple[AuditEvent, ...],
        request_id: str,
        execution_id: str | None,
        order_id: str | None,
    ) -> None:
        seen_event_ids: set[str] = set()
        previous_sequence = 0
        previous_time: datetime | None = None

        for event in events:
            if not isinstance(event, AuditEvent):
                raise TypeError(
                    "every event must be an AuditEvent"
                )

            if event.event_id in seen_event_ids:
                raise ValueError(
                    f"duplicate event_id: {event.event_id}"
                )

            if event.sequence_number <= previous_sequence:
                raise ValueError(
                    "event sequence numbers must be strictly increasing"
                )

            if (
                previous_time is not None
                and event.occurred_at < previous_time
            ):
                raise ValueError(
                    "event timestamps must be chronological"
                )

            if (
                event.request_id is not None
                and event.request_id != request_id
            ):
                raise ValueError(
                    "event request_id must match the audit record"
                )

            if (
                execution_id is not None
                and event.execution_id is not None
                and event.execution_id != execution_id
            ):
                raise ValueError(
                    "event execution_id must match the audit record"
                )

            if (
                order_id is not None
                and event.order_id is not None
                and event.order_id != order_id
            ):
                raise ValueError(
                    "event order_id must match the audit record"
                )

            seen_event_ids.add(event.event_id)
            previous_sequence = event.sequence_number
            previous_time = event.occurred_at


@dataclass(frozen=True, slots=True)
class AuditTrailReport:
    """Summary produced when an audit trail is inspected or finalized."""

    status: AuditTrailStatus
    record: ExecutionAuditRecord | None
    event_count: int
    first_event_at: datetime | None
    last_event_at: datetime | None
    critical_event_count: int = 0
    error_event_count: int = 0
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.status,
            AuditTrailStatus,
        ):
            raise TypeError(
                "status must be an AuditTrailStatus"
            )

        if (
            self.record is not None
            and not isinstance(
                self.record,
                ExecutionAuditRecord,
            )
        ):
            raise TypeError(
                "record must be an ExecutionAuditRecord or None"
            )

        for field_name in (
            "event_count",
            "critical_event_count",
            "error_event_count",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, int):
                raise TypeError(
                    f"{field_name} must be an integer"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        if (
            self.critical_event_count
            + self.error_event_count
            > self.event_count
        ):
            raise ValueError(
                "severity event counts must not exceed event_count"
            )

        for field_name in (
            "first_event_at",
            "last_event_at",
        ):
            value = getattr(self, field_name)

            if value is not None:
                ExecutionAuditRecord._validate_datetime(
                    value,
                    field_name,
                )

        if (
            self.first_event_at is not None
            and self.last_event_at is not None
            and self.last_event_at < self.first_event_at
        ):
            raise ValueError(
                "last_event_at must not be earlier than first_event_at"
            )

        if self.record is not None:
            if self.event_count != len(self.record.events):
                raise ValueError(
                    "event_count must match the record event count"
                )

            if self.record.events:
                expected_first = (
                    self.record.events[0].occurred_at
                )
                expected_last = (
                    self.record.events[-1].occurred_at
                )

                if self.first_event_at != expected_first:
                    raise ValueError(
                        "first_event_at must match the first record event"
                    )

                if self.last_event_at != expected_last:
                    raise ValueError(
                        "last_event_at must match the last record event"
                    )
            elif (
                self.first_event_at is not None
                or self.last_event_at is not None
            ):
                raise ValueError(
                    "empty records must not include event timestamps"
                )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if self.status is AuditTrailStatus.FAILED:
            if not normalized_error:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error:
            raise ValueError(
                "only failed reports may include an error"
            )

        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )
        object.__setattr__(
            self,
            "error",
            normalized_error,
        )