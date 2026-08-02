from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.audit.audit_models import (
    AuditEventType,
    AuditSeverity,
    AuditTrailStatus,
)
from app.strategy.audit.audit_trail import (
    ExecutionAuditTrail,
)


NOW = datetime(
    2026,
    8,
    2,
    18,
    0,
    tzinfo=timezone.utc,
)


class IncrementingClock:
    def __init__(self) -> None:
        self.current = NOW

    def __call__(self) -> datetime:
        value = self.current
        self.current += timedelta(seconds=1)
        return value


def trail(
    *,
    execution_id: str | None = "execution-001",
) -> ExecutionAuditTrail:
    return ExecutionAuditTrail(
        audit_id="audit-001",
        request_id="paper-001",
        execution_id=execution_id,
        clock=IncrementingClock(),
    )


def append_default_event(
    value: ExecutionAuditTrail,
):
    return value.append_event(
        event_type=(
            AuditEventType.COORDINATION_STARTED
        ),
        severity=AuditSeverity.INFO,
        message="Coordination started.",
        source="agent-coordinator",
    )


def test_creates_audit_trail() -> None:
    value = trail()

    assert value.audit_id == "audit-001"
    assert value.request_id == "paper-001"
    assert value.execution_id == "execution-001"
    assert value.events == ()
    assert value.finalized is False


def test_constructor_normalizes_identifiers() -> None:
    value = ExecutionAuditTrail(
        audit_id="  audit-001  ",
        request_id="  paper-001  ",
        execution_id="  execution-001  ",
        clock=IncrementingClock(),
    )

    assert value.audit_id == "audit-001"
    assert value.request_id == "paper-001"
    assert value.execution_id == "execution-001"


def test_audit_id_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="audit_id must not be empty",
    ):
        ExecutionAuditTrail(
            audit_id="   ",
            request_id="paper-001",
        )


def test_request_id_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="request_id must not be empty",
    ):
        ExecutionAuditTrail(
            audit_id="audit-001",
            request_id="   ",
        )


def test_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        ExecutionAuditTrail(
            audit_id="audit-001",
            request_id="paper-001",
            clock=NOW,
        )


def test_append_event() -> None:
    value = trail()

    result = append_default_event(value)

    assert result.sequence_number == 1
    assert result.event_id == "audit-001-000001"
    assert result.request_id == "paper-001"
    assert result.execution_id == "execution-001"
    assert value.events == (result,)


def test_event_sequence_increments() -> None:
    value = trail()

    first = append_default_event(value)
    second = value.append_event(
        event_type=(
            AuditEventType.COORDINATION_COMPLETED
        ),
        severity=AuditSeverity.INFO,
        message="Coordination completed.",
    )

    assert first.sequence_number == 1
    assert second.sequence_number == 2
    assert second.event_id == "audit-001-000002"


def test_events_property_returns_tuple() -> None:
    value = trail()
    append_default_event(value)

    assert isinstance(value.events, tuple)


def test_event_type_must_be_valid() -> None:
    with pytest.raises(
        TypeError,
        match="event_type must be an AuditEventType",
    ):
        trail().append_event(
            event_type="TRADE_APPROVED",
            severity=AuditSeverity.INFO,
            message="Approved.",
        )


def test_event_severity_must_be_valid() -> None:
    with pytest.raises(
        TypeError,
        match="severity must be an AuditSeverity",
    ):
        trail().append_event(
            event_type=AuditEventType.TRADE_APPROVED,
            severity="INFO",
            message="Approved.",
        )


def test_event_request_id_must_match() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "event request_id must match the audit trail"
        ),
    ):
        trail().append_event(
            event_type=AuditEventType.TRADE_APPROVED,
            severity=AuditSeverity.INFO,
            message="Approved.",
            request_id="different",
        )


def test_event_execution_id_must_match() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "event execution_id must match the audit trail"
        ),
    ):
        trail().append_event(
            event_type=AuditEventType.TRADE_APPROVED,
            severity=AuditSeverity.INFO,
            message="Approved.",
            execution_id="different",
        )


def test_event_timestamps_must_be_chronological() -> None:
    value = trail()

    value.append_event(
        event_type=AuditEventType.TRADE_APPROVED,
        severity=AuditSeverity.INFO,
        message="Approved.",
        occurred_at=NOW + timedelta(seconds=10),
    )

    with pytest.raises(
        ValueError,
        match="event timestamps must be chronological",
    ):
        value.append_event(
            event_type=(
                AuditEventType.EXECUTION_COMPLETED
            ),
            severity=AuditSeverity.INFO,
            message="Completed.",
            occurred_at=NOW + timedelta(seconds=5),
        )


def test_attach_execution_id() -> None:
    value = trail(execution_id=None)

    value.attach_execution_id(" execution-001 ")

    assert value.execution_id == "execution-001"


def test_execution_id_cannot_be_reassigned() -> None:
    value = trail()

    with pytest.raises(
        ValueError,
        match="execution_id is already assigned",
    ):
        value.attach_execution_id("different")


def test_attach_order_id() -> None:
    value = trail()

    value.attach_order_id(" SIM-000001 ")

    assert value.order_id == "SIM-000001"


def test_order_id_cannot_be_reassigned() -> None:
    value = trail()
    value.attach_order_id("SIM-000001")

    with pytest.raises(
        ValueError,
        match="order_id is already assigned",
    ):
        value.attach_order_id("SIM-000002")


def test_find_event() -> None:
    value = trail()
    created = append_default_event(value)

    found = value.find_event(created.event_id)

    assert found == created


def test_find_event_returns_none() -> None:
    assert trail().find_event("missing") is None


def test_find_event_id_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="event_id must not be empty",
    ):
        trail().find_event("   ")


def test_filters_events_by_type() -> None:
    value = trail()

    append_default_event(value)
    completed = value.append_event(
        event_type=(
            AuditEventType.COORDINATION_COMPLETED
        ),
        severity=AuditSeverity.INFO,
        message="Completed.",
    )

    assert value.events_by_type(
        AuditEventType.COORDINATION_COMPLETED
    ) == (completed,)


def test_filters_events_by_severity() -> None:
    value = trail()

    append_default_event(value)
    failed = value.append_event(
        event_type=AuditEventType.EXECUTION_FAILED,
        severity=AuditSeverity.ERROR,
        message="Execution failed.",
    )

    assert value.events_by_severity(
        AuditSeverity.ERROR
    ) == (failed,)


def test_snapshot_of_open_trail_is_pending() -> None:
    value = trail()
    append_default_event(value)

    report = value.snapshot()

    assert report.status is AuditTrailStatus.PENDING
    assert report.event_count == 1
    assert report.record is not None
    assert report.record.successful is False


def test_successful_finalization() -> None:
    value = trail()
    append_default_event(value)

    report = value.finalize_success()

    assert report.status is AuditTrailStatus.COMPLETED
    assert report.record is not None
    assert report.record.successful is True
    assert value.finalized is True


def test_successful_finalization_requires_events() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "cannot finalize a successful audit trail "
            "without events"
        ),
    ):
        trail().finalize_success()


def test_failure_finalization() -> None:
    value = trail()

    value.append_event(
        event_type=AuditEventType.EXECUTION_FAILED,
        severity=AuditSeverity.ERROR,
        message="Execution failed.",
    )

    report = value.finalize_failure(
        error="broker unavailable"
    )

    assert report.status is AuditTrailStatus.FAILED
    assert report.error == "broker unavailable"
    assert report.record is not None
    assert report.record.successful is False


def test_failure_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="error must not be empty",
    ):
        trail().finalize_failure(error="   ")


def test_finalization_preserves_warnings() -> None:
    value = trail()
    append_default_event(value)

    report = value.finalize_success(
        warnings=("Audit warning.",)
    )

    assert report.warnings == ("Audit warning.",)
    assert report.record is not None
    assert report.record.warnings == (
        "Audit warning.",
    )


def test_report_counts_error_and_critical_events() -> None:
    value = trail()

    value.append_event(
        event_type=AuditEventType.EXECUTION_FAILED,
        severity=AuditSeverity.ERROR,
        message="Execution failed.",
    )
    value.append_event(
        event_type=AuditEventType.RISK_GATE_BLOCKED,
        severity=AuditSeverity.CRITICAL,
        message="Risk blocked execution.",
    )

    report = value.finalize_failure(
        error="execution blocked"
    )

    assert report.error_event_count == 1
    assert report.critical_event_count == 1


def test_completed_at_cannot_precede_last_event() -> None:
    value = trail()

    value.append_event(
        event_type=AuditEventType.TRADE_APPROVED,
        severity=AuditSeverity.INFO,
        message="Approved.",
        occurred_at=NOW + timedelta(seconds=10),
    )

    with pytest.raises(
        ValueError,
        match=(
            "completed_at must not be earlier than "
            "the last event"
        ),
    ):
        value.finalize_success(
            completed_at=NOW + timedelta(seconds=5)
        )


def test_cannot_append_after_finalization() -> None:
    value = trail()
    append_default_event(value)
    value.finalize_success()

    with pytest.raises(
        RuntimeError,
        match="audit trail is already finalized",
    ):
        append_default_event(value)


def test_cannot_finalize_twice() -> None:
    value = trail()
    append_default_event(value)
    value.finalize_success()

    with pytest.raises(
        RuntimeError,
        match="audit trail is already finalized",
    ):
        value.finalize_failure(
            error="late failure"
        )


def test_clock_must_return_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        ExecutionAuditTrail(
            audit_id="audit-001",
            request_id="paper-001",
            clock=lambda: "now",
        )


def test_clock_must_return_timezone_aware_datetime() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        ExecutionAuditTrail(
            audit_id="audit-001",
            request_id="paper-001",
            clock=lambda: datetime(2026, 8, 2),
        )