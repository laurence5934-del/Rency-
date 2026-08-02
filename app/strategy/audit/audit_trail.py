from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from typing import Callable, Iterable

from .audit_models import (
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    AuditTrailReport,
    AuditTrailStatus,
    ExecutionAuditRecord,
)


Clock = Callable[[], datetime]


class ExecutionAuditTrail:
    """Append-only audit trail for one trading workflow."""

    def __init__(
        self,
        *,
        audit_id: str,
        request_id: str,
        execution_id: str | None = None,
        clock: Clock | None = None,
    ) -> None:
        normalized_audit_id = audit_id.strip()
        normalized_request_id = request_id.strip()

        if not normalized_audit_id:
            raise ValueError(
                "audit_id must not be empty"
            )

        if not normalized_request_id:
            raise ValueError(
                "request_id must not be empty"
            )

        normalized_execution_id = (
            self._normalize_optional_identifier(
                execution_id,
                "execution_id",
            )
        )

        if clock is not None and not callable(clock):
            raise TypeError(
                "clock must be callable"
            )

        self._audit_id = normalized_audit_id
        self._request_id = normalized_request_id
        self._execution_id = normalized_execution_id
        self._order_id: str | None = None
        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

        self._created_at = self._current_time()
        self._events: list[AuditEvent] = []
        self._event_sequence = count(1)
        self._finalized = False
        self._record: ExecutionAuditRecord | None = None

    @property
    def audit_id(self) -> str:
        return self._audit_id

    @property
    def request_id(self) -> str:
        return self._request_id

    @property
    def execution_id(self) -> str | None:
        return self._execution_id

    @property
    def order_id(self) -> str | None:
        return self._order_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def finalized(self) -> bool:
        return self._finalized

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)

    def append_event(
        self,
        *,
        event_type: AuditEventType,
        severity: AuditSeverity,
        message: str,
        source: str = "",
        request_id: str | None = None,
        execution_id: str | None = None,
        order_id: str | None = None,
        attributes: Iterable[tuple[str, str]] = (),
        occurred_at: datetime | None = None,
    ) -> AuditEvent:
        self._ensure_open()

        if not isinstance(event_type, AuditEventType):
            raise TypeError(
                "event_type must be an AuditEventType"
            )

        if not isinstance(severity, AuditSeverity):
            raise TypeError(
                "severity must be an AuditSeverity"
            )

        effective_request_id = (
            self._request_id
            if request_id is None
            else request_id
        )

        effective_execution_id = (
            self._execution_id
            if execution_id is None
            else execution_id
        )

        effective_order_id = (
            self._order_id
            if order_id is None
            else order_id
        )

        if (
            effective_request_id
            != self._request_id
        ):
            raise ValueError(
                "event request_id must match the audit trail"
            )

        if (
            self._execution_id is not None
            and effective_execution_id is not None
            and effective_execution_id
            != self._execution_id
        ):
            raise ValueError(
                "event execution_id must match the audit trail"
            )

        if (
            self._order_id is not None
            and effective_order_id is not None
            and effective_order_id != self._order_id
        ):
            raise ValueError(
                "event order_id must match the audit trail"
            )

        event_time = (
            occurred_at
            if occurred_at is not None
            else self._current_time()
        )

        self._validate_timestamp(event_time)

        if (
            self._events
            and event_time
            < self._events[-1].occurred_at
        ):
            raise ValueError(
                "event timestamps must be chronological"
            )

        sequence_number = next(
            self._event_sequence
        )

        event = AuditEvent(
            sequence_number=sequence_number,
            event_id=(
                f"{self._audit_id}-"
                f"{sequence_number:06d}"
            ),
            event_type=event_type,
            severity=severity,
            occurred_at=event_time,
            message=message,
            request_id=effective_request_id,
            execution_id=effective_execution_id,
            order_id=effective_order_id,
            source=source,
            attributes=tuple(attributes),
        )

        self._events.append(event)

        return event

    def attach_execution_id(
        self,
        execution_id: str,
    ) -> None:
        self._ensure_open()

        normalized_execution_id = (
            self._normalize_optional_identifier(
                execution_id,
                "execution_id",
            )
        )

        if normalized_execution_id is None:
            raise ValueError(
                "execution_id must not be empty"
            )

        if (
            self._execution_id is not None
            and self._execution_id
            != normalized_execution_id
        ):
            raise ValueError(
                "execution_id is already assigned"
            )

        for event in self._events:
            if (
                event.execution_id is not None
                and event.execution_id
                != normalized_execution_id
            ):
                raise ValueError(
                    "existing event execution_id does not match"
                )

        self._execution_id = normalized_execution_id

    def attach_order_id(
        self,
        order_id: str,
    ) -> None:
        self._ensure_open()

        normalized_order_id = (
            self._normalize_optional_identifier(
                order_id,
                "order_id",
            )
        )

        if normalized_order_id is None:
            raise ValueError(
                "order_id must not be empty"
            )

        if (
            self._order_id is not None
            and self._order_id != normalized_order_id
        ):
            raise ValueError(
                "order_id is already assigned"
            )

        for event in self._events:
            if (
                event.order_id is not None
                and event.order_id
                != normalized_order_id
            ):
                raise ValueError(
                    "existing event order_id does not match"
                )

        self._order_id = normalized_order_id

    def find_event(
        self,
        event_id: str,
    ) -> AuditEvent | None:
        normalized_event_id = event_id.strip()

        if not normalized_event_id:
            raise ValueError(
                "event_id must not be empty"
            )

        return next(
            (
                event
                for event in self._events
                if event.event_id
                == normalized_event_id
            ),
            None,
        )

    def events_by_type(
        self,
        event_type: AuditEventType,
    ) -> tuple[AuditEvent, ...]:
        if not isinstance(event_type, AuditEventType):
            raise TypeError(
                "event_type must be an AuditEventType"
            )

        return tuple(
            event
            for event in self._events
            if event.event_type is event_type
        )

    def events_by_severity(
        self,
        severity: AuditSeverity,
    ) -> tuple[AuditEvent, ...]:
        if not isinstance(severity, AuditSeverity):
            raise TypeError(
                "severity must be an AuditSeverity"
            )

        return tuple(
            event
            for event in self._events
            if event.severity is severity
        )

    def finalize_success(
        self,
        *,
        completed_at: datetime | None = None,
        warnings: Iterable[str] = (),
    ) -> AuditTrailReport:
        self._ensure_open()

        if not self._events:
            raise ValueError(
                "cannot finalize a successful audit trail "
                "without events"
            )

        final_time = (
            completed_at
            if completed_at is not None
            else self._current_time()
        )

        self._validate_final_time(final_time)

        record = ExecutionAuditRecord(
            audit_id=self._audit_id,
            request_id=self._request_id,
            execution_id=self._execution_id,
            order_id=self._order_id,
            created_at=self._created_at,
            events=tuple(self._events),
            completed_at=final_time,
            successful=True,
            warnings=tuple(warnings),
        )

        self._finalized = True
        self._record = record

        return self._report(
            status=AuditTrailStatus.COMPLETED,
            record=record,
            warnings=tuple(warnings),
        )

    def finalize_failure(
        self,
        *,
        error: str,
        completed_at: datetime | None = None,
        warnings: Iterable[str] = (),
    ) -> AuditTrailReport:
        self._ensure_open()

        normalized_error = error.strip()

        if not normalized_error:
            raise ValueError(
                "error must not be empty"
            )

        final_time = (
            completed_at
            if completed_at is not None
            else self._current_time()
        )

        self._validate_final_time(final_time)

        record = ExecutionAuditRecord(
            audit_id=self._audit_id,
            request_id=self._request_id,
            execution_id=self._execution_id,
            order_id=self._order_id,
            created_at=self._created_at,
            events=tuple(self._events),
            completed_at=final_time,
            successful=False,
            warnings=tuple(warnings),
        )

        self._finalized = True
        self._record = record

        return self._report(
            status=AuditTrailStatus.FAILED,
            record=record,
            warnings=tuple(warnings),
            error=normalized_error,
        )

    def snapshot(self) -> AuditTrailReport:
        record = ExecutionAuditRecord(
            audit_id=self._audit_id,
            request_id=self._request_id,
            execution_id=self._execution_id,
            order_id=self._order_id,
            created_at=self._created_at,
            events=tuple(self._events),
            completed_at=(
                self._record.completed_at
                if self._record is not None
                else None
            ),
            successful=(
                self._record.successful
                if self._record is not None
                else False
            ),
            warnings=(
                self._record.warnings
                if self._record is not None
                else ()
            ),
        )

        return self._report(
            status=(
                AuditTrailStatus.COMPLETED
                if self._finalized
                else AuditTrailStatus.PENDING
            ),
            record=record,
            warnings=record.warnings,
        )

    @staticmethod
    def _report(
        *,
        status: AuditTrailStatus,
        record: ExecutionAuditRecord,
        warnings: tuple[str, ...] = (),
        error: str | None = None,
    ) -> AuditTrailReport:
        events = record.events

        return AuditTrailReport(
            status=status,
            record=record,
            event_count=len(events),
            first_event_at=(
                events[0].occurred_at
                if events
                else None
            ),
            last_event_at=(
                events[-1].occurred_at
                if events
                else None
            ),
            critical_event_count=sum(
                1
                for event in events
                if event.severity
                is AuditSeverity.CRITICAL
            ),
            error_event_count=sum(
                1
                for event in events
                if event.severity
                is AuditSeverity.ERROR
            ),
            warnings=warnings,
            error=error,
        )

    def _validate_final_time(
        self,
        completed_at: datetime,
    ) -> None:
        self._validate_timestamp(completed_at)

        if completed_at < self._created_at:
            raise ValueError(
                "completed_at must not be earlier than created_at"
            )

        if (
            self._events
            and completed_at
            < self._events[-1].occurred_at
        ):
            raise ValueError(
                "completed_at must not be earlier than "
                "the last event"
            )

    def _current_time(self) -> datetime:
        value = self._clock()

        self._validate_timestamp(value)

        return value

    @staticmethod
    def _validate_timestamp(
        value: datetime,
    ) -> None:
        if not isinstance(value, datetime):
            raise TypeError(
                "clock must return a datetime"
            )

        if value.tzinfo is None:
            raise ValueError(
                "clock must return a timezone-aware datetime"
            )

    def _ensure_open(self) -> None:
        if self._finalized:
            raise RuntimeError(
                "audit trail is already finalized"
            )

    @staticmethod
    def _normalize_optional_identifier(
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