from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.audit.audit_models import (
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    AuditTrailReport,
    AuditTrailStatus,
    ExecutionAuditRecord,
)


NOW = datetime(
    2026,
    8,
    2,
    18,
    0,
    tzinfo=timezone.utc,
)


def event(
    sequence_number: int = 1,
    *,
    event_id: str | None = None,
    event_type: AuditEventType = (
        AuditEventType.COORDINATION_STARTED
    ),
    severity: AuditSeverity = AuditSeverity.INFO,
    occurred_at: datetime | None = None,
    request_id: str = "paper-001",
    execution_id: str | None = None,
    order_id: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        sequence_number=sequence_number,
        event_id=(
            event_id
            if event_id is not None
            else f"event-{sequence_number:03d}"
        ),
        event_type=event_type,
        severity=severity,
        occurred_at=(
            occurred_at
            if occurred_at is not None
            else NOW + timedelta(
                seconds=sequence_number
            )
        ),
        message=f"Audit event {sequence_number}.",
        request_id=request_id,
        execution_id=execution_id,
        order_id=order_id,
        source="agent-coordinator",
    )


def record() -> ExecutionAuditRecord:
    return ExecutionAuditRecord(
        audit_id="audit-001",
        request_id="paper-001",
        execution_id="execution-001",
        order_id="SIM-000001",
        created_at=NOW,
        completed_at=NOW + timedelta(minutes=1),
        events=(
            event(
                1,
                execution_id="execution-001",
            ),
            event(
                2,
                event_type=(
                    AuditEventType.EXECUTION_COMPLETED
                ),
                execution_id="execution-001",
                order_id="SIM-000001",
            ),
        ),
        successful=True,
    )


def report() -> AuditTrailReport:
    value = record()

    return AuditTrailReport(
        status=AuditTrailStatus.COMPLETED,
        record=value,
        event_count=2,
        first_event_at=value.events[0].occurred_at,
        last_event_at=value.events[-1].occurred_at,
    )


def test_audit_event() -> None:
    value = event()

    assert value.sequence_number == 1
    assert value.event_id == "event-001"
    assert (
        value.event_type
        is AuditEventType.COORDINATION_STARTED
    )


def test_audit_event_text_is_normalized() -> None:
    value = AuditEvent(
        sequence_number=1,
        event_id="  event-001  ",
        event_type=AuditEventType.TRADE_APPROVED,
        severity=AuditSeverity.INFO,
        occurred_at=NOW,
        message="  Trade approved.  ",
        request_id="  paper-001  ",
        execution_id="  execution-001  ",
        order_id="  SIM-000001  ",
        source="  paper-orchestrator  ",
    )

    assert value.event_id == "event-001"
    assert value.message == "Trade approved."
    assert value.request_id == "paper-001"
    assert value.execution_id == "execution-001"
    assert value.order_id == "SIM-000001"
    assert value.source == "paper-orchestrator"


@pytest.mark.parametrize(
    "sequence_number",
    [0, -1],
)
def test_sequence_number_must_be_positive(
    sequence_number: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "sequence_number must be greater than zero"
        ),
    ):
        AuditEvent(
            sequence_number=sequence_number,
            event_id="event-001",
            event_type=AuditEventType.TRADE_APPROVED,
            severity=AuditSeverity.INFO,
            occurred_at=NOW,
            message="Trade approved.",
        )


def test_event_id_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="event_id must not be empty",
    ):
        AuditEvent(
            sequence_number=1,
            event_id="   ",
            event_type=AuditEventType.TRADE_APPROVED,
            severity=AuditSeverity.INFO,
            occurred_at=NOW,
            message="Trade approved.",
        )


def test_message_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="message must not be empty",
    ):
        AuditEvent(
            sequence_number=1,
            event_id="event-001",
            event_type=AuditEventType.TRADE_APPROVED,
            severity=AuditSeverity.INFO,
            occurred_at=NOW,
            message="   ",
        )


def test_occurred_at_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="occurred_at must be timezone-aware",
    ):
        AuditEvent(
            sequence_number=1,
            event_id="event-001",
            event_type=AuditEventType.TRADE_APPROVED,
            severity=AuditSeverity.INFO,
            occurred_at=datetime(2026, 8, 2),
            message="Trade approved.",
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "execution_id",
        "order_id",
    ],
)
def test_optional_identifier_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "sequence_number": 1,
        "event_id": "event-001",
        "event_type": AuditEventType.TRADE_APPROVED,
        "severity": AuditSeverity.INFO,
        "occurred_at": NOW,
        "message": "Trade approved.",
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        AuditEvent(**arguments)


def test_event_attributes_are_normalized() -> None:
    value = AuditEvent(
        sequence_number=1,
        event_id="event-001",
        event_type=AuditEventType.TRADE_APPROVED,
        severity=AuditSeverity.INFO,
        occurred_at=NOW,
        message="Trade approved.",
        attributes=[
            (
                "  confidence  ",
                "  0.90  ",
            ),
        ],
    )

    assert value.attributes == (
        (
            "confidence",
            "0.90",
        ),
    )


def test_attribute_must_have_two_items() -> None:
    with pytest.raises(
        TypeError,
        match="two-item tuple",
    ):
        AuditEvent(
            sequence_number=1,
            event_id="event-001",
            event_type=AuditEventType.TRADE_APPROVED,
            severity=AuditSeverity.INFO,
            occurred_at=NOW,
            message="Trade approved.",
            attributes=(
                ("invalid",),
            ),
        )


def test_execution_audit_record() -> None:
    value = record()

    assert value.audit_id == "audit-001"
    assert value.request_id == "paper-001"
    assert len(value.events) == 2
    assert value.successful is True


def test_record_text_is_normalized() -> None:
    value = ExecutionAuditRecord(
        audit_id="  audit-001  ",
        request_id="  paper-001  ",
        execution_id="  execution-001  ",
        order_id="  SIM-000001  ",
        created_at=NOW,
    )

    assert value.audit_id == "audit-001"
    assert value.request_id == "paper-001"
    assert value.execution_id == "execution-001"
    assert value.order_id == "SIM-000001"


def test_completed_at_must_not_precede_created_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed_at must not be earlier than created_at"
        ),
    ):
        ExecutionAuditRecord(
            audit_id="audit-001",
            request_id="paper-001",
            created_at=NOW,
            completed_at=NOW - timedelta(seconds=1),
        )


def test_duplicate_event_ids_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="duplicate event_id",
    ):
        ExecutionAuditRecord(
            audit_id="audit-001",
            request_id="paper-001",
            created_at=NOW,
            events=(
                event(
                    1,
                    event_id="duplicate",
                ),
                event(
                    2,
                    event_id="duplicate",
                ),
            ),
        )


def test_event_sequences_must_be_increasing() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "event sequence numbers must be strictly increasing"
        ),
    ):
        ExecutionAuditRecord(
            audit_id="audit-001",
            request_id="paper-001",
            created_at=NOW,
            events=(
                event(2),
                event(1),
            ),
        )


def test_event_timestamps_must_be_chronological() -> None:
    with pytest.raises(
        ValueError,
        match="event timestamps must be chronological",
    ):
        ExecutionAuditRecord(
            audit_id="audit-001",
            request_id="paper-001",
            created_at=NOW,
            events=(
                event(
                    1,
                    occurred_at=NOW
                    + timedelta(seconds=10),
                ),
                event(
                    2,
                    occurred_at=NOW
                    + timedelta(seconds=5),
                ),
            ),
        )


def test_event_request_id_must_match_record() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "event request_id must match the audit record"
        ),
    ):
        ExecutionAuditRecord(
            audit_id="audit-001",
            request_id="paper-001",
            created_at=NOW,
            events=(
                event(
                    1,
                    request_id="different",
                ),
            ),
        )


def test_event_execution_id_must_match_record() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "event execution_id must match the audit record"
        ),
    ):
        ExecutionAuditRecord(
            audit_id="audit-001",
            request_id="paper-001",
            execution_id="execution-001",
            created_at=NOW,
            events=(
                event(
                    1,
                    execution_id="different",
                ),
            ),
        )


def test_successful_record_requires_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "successful records must include completed_at"
        ),
    ):
        ExecutionAuditRecord(
            audit_id="audit-001",
            request_id="paper-001",
            created_at=NOW,
            events=(event(),),
            successful=True,
        )


def test_successful_record_requires_events() -> None:
    with pytest.raises(
        ValueError,
        match="successful records must include events",
    ):
        ExecutionAuditRecord(
            audit_id="audit-001",
            request_id="paper-001",
            created_at=NOW,
            completed_at=NOW,
            successful=True,
        )


def test_audit_trail_report() -> None:
    value = report()

    assert value.status is AuditTrailStatus.COMPLETED
    assert value.event_count == 2
    assert value.record == record()


def test_report_event_count_must_match_record() -> None:
    value = record()

    with pytest.raises(
        ValueError,
        match=(
            "event_count must match the record event count"
        ),
    ):
        AuditTrailReport(
            status=AuditTrailStatus.COMPLETED,
            record=value,
            event_count=1,
            first_event_at=value.events[0].occurred_at,
            last_event_at=value.events[-1].occurred_at,
        )


def test_report_first_event_time_must_match_record() -> None:
    value = record()

    with pytest.raises(
        ValueError,
        match=(
            "first_event_at must match the first record event"
        ),
    ):
        AuditTrailReport(
            status=AuditTrailStatus.COMPLETED,
            record=value,
            event_count=2,
            first_event_at=NOW,
            last_event_at=value.events[-1].occurred_at,
        )


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        AuditTrailReport(
            status=AuditTrailStatus.FAILED,
            record=None,
            event_count=0,
            first_event_at=None,
            last_event_at=None,
        )


def test_completed_report_cannot_include_error() -> None:
    with pytest.raises(
        ValueError,
        match="only failed reports may include an error",
    ):
        AuditTrailReport(
            status=AuditTrailStatus.COMPLETED,
            record=None,
            event_count=0,
            first_event_at=None,
            last_event_at=None,
            error="Unexpected error.",
        )


def test_report_warnings_are_tuples() -> None:
    value = AuditTrailReport(
        status=AuditTrailStatus.COMPLETED,
        record=None,
        event_count=0,
        first_event_at=None,
        last_event_at=None,
        warnings=["Audit warning."],
    )

    assert value.warnings == (
        "Audit warning.",
    )


def test_models_are_immutable() -> None:
    value = event()

    with pytest.raises(FrozenInstanceError):
        value.event_id = "changed"