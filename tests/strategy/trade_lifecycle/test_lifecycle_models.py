from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.trade_lifecycle.lifecycle_models import (
    LifecycleEventSeverity,
    LifecycleEventType,
    OrderLifecycleEvent,
    TradeLifecycleRecord,
    TradeLifecycleReport,
    TradeLifecycleStage,
    TradeLifecycleStatus,
)


NOW = datetime(
    2026,
    8,
    2,
    20,
    0,
    tzinfo=timezone.utc,
)


def event(
    sequence_number: int = 1,
    *,
    event_id: str | None = None,
    event_type: LifecycleEventType = (
        LifecycleEventType.ORDER_CREATED
    ),
    stage: TradeLifecycleStage = (
        TradeLifecycleStage.CREATED
    ),
    severity: LifecycleEventSeverity = (
        LifecycleEventSeverity.INFO
    ),
    occurred_at: datetime | None = None,
    filled_quantity: str = "0",
    remaining_quantity: str = "10",
    average_price: str | None = None,
) -> OrderLifecycleEvent:
    return OrderLifecycleEvent(
        sequence_number=sequence_number,
        event_id=(
            event_id
            if event_id is not None
            else f"event-{sequence_number:03d}"
        ),
        event_type=event_type,
        stage=stage,
        severity=severity,
        occurred_at=(
            occurred_at
            if occurred_at is not None
            else NOW + timedelta(
                seconds=sequence_number
            )
        ),
        message=f"Lifecycle event {sequence_number}.",
        execution_id="execution-001",
        order_id="SIM-000001",
        filled_quantity=Decimal(filled_quantity),
        remaining_quantity=Decimal(
            remaining_quantity
        ),
        average_price=(
            Decimal(average_price)
            if average_price is not None
            else None
        ),
    )


def active_record() -> TradeLifecycleRecord:
    return TradeLifecycleRecord(
        lifecycle_id="lifecycle-001",
        execution_id="execution-001",
        order_id="SIM-000001",
        original_quantity=Decimal("10"),
        current_stage=TradeLifecycleStage.SUBMITTED,
        created_at=NOW,
        events=(
            event(
                1,
                event_type=(
                    LifecycleEventType.ORDER_SUBMITTED
                ),
                stage=TradeLifecycleStage.SUBMITTED,
            ),
        ),
        cumulative_filled_quantity=Decimal("0"),
        remaining_quantity=Decimal("10"),
    )


def filled_record() -> TradeLifecycleRecord:
    return TradeLifecycleRecord(
        lifecycle_id="lifecycle-001",
        execution_id="execution-001",
        order_id="SIM-000001",
        original_quantity=Decimal("10"),
        current_stage=TradeLifecycleStage.FILLED,
        created_at=NOW,
        events=(
            event(
                1,
                event_type=(
                    LifecycleEventType.ORDER_SUBMITTED
                ),
                stage=TradeLifecycleStage.SUBMITTED,
            ),
            event(
                2,
                event_type=(
                    LifecycleEventType.ORDER_FILLED
                ),
                stage=TradeLifecycleStage.FILLED,
                filled_quantity="10",
                remaining_quantity="0",
                average_price="200",
            ),
        ),
        cumulative_filled_quantity=Decimal("10"),
        remaining_quantity=Decimal("0"),
        average_fill_price=Decimal("200"),
        terminal=True,
        completed_at=NOW + timedelta(minutes=1),
    )


def test_order_lifecycle_event() -> None:
    value = event()

    assert value.sequence_number == 1
    assert value.event_id == "event-001"
    assert (
        value.event_type
        is LifecycleEventType.ORDER_CREATED
    )


def test_event_text_is_normalized() -> None:
    value = OrderLifecycleEvent(
        sequence_number=1,
        event_id="  event-001  ",
        event_type=LifecycleEventType.ORDER_SUBMITTED,
        stage=TradeLifecycleStage.SUBMITTED,
        severity=LifecycleEventSeverity.INFO,
        occurred_at=NOW,
        message="  Order submitted.  ",
        execution_id="  execution-001  ",
        order_id="  SIM-000001  ",
        broker_status="  submitted  ",
    )

    assert value.event_id == "event-001"
    assert value.execution_id == "execution-001"
    assert value.order_id == "SIM-000001"
    assert value.message == "Order submitted."
    assert value.broker_status == "submitted"


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
        OrderLifecycleEvent(
            sequence_number=sequence_number,
            event_id="event-001",
            event_type=(
                LifecycleEventType.ORDER_CREATED
            ),
            stage=TradeLifecycleStage.CREATED,
            severity=LifecycleEventSeverity.INFO,
            occurred_at=NOW,
            message="Created.",
            execution_id="execution-001",
            order_id="SIM-000001",
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "event_id",
        "execution_id",
        "order_id",
        "message",
    ],
)
def test_event_text_fields_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "sequence_number": 1,
        "event_id": "event-001",
        "event_type": (
            LifecycleEventType.ORDER_CREATED
        ),
        "stage": TradeLifecycleStage.CREATED,
        "severity": LifecycleEventSeverity.INFO,
        "occurred_at": NOW,
        "message": "Created.",
        "execution_id": "execution-001",
        "order_id": "SIM-000001",
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        OrderLifecycleEvent(**arguments)


def test_event_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="occurred_at must be timezone-aware",
    ):
        OrderLifecycleEvent(
            sequence_number=1,
            event_id="event-001",
            event_type=(
                LifecycleEventType.ORDER_CREATED
            ),
            stage=TradeLifecycleStage.CREATED,
            severity=LifecycleEventSeverity.INFO,
            occurred_at=datetime(2026, 8, 2),
            message="Created.",
            execution_id="execution-001",
            order_id="SIM-000001",
        )


def test_event_quantities_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="filled_quantity must not be negative",
    ):
        event(
            filled_quantity="-1"
        )


def test_filled_event_requires_average_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "filled events must include average_price"
        ),
    ):
        event(
            filled_quantity="5",
            remaining_quantity="5",
        )


def test_event_attributes_are_normalized() -> None:
    value = OrderLifecycleEvent(
        sequence_number=1,
        event_id="event-001",
        event_type=LifecycleEventType.ORDER_SUBMITTED,
        stage=TradeLifecycleStage.SUBMITTED,
        severity=LifecycleEventSeverity.INFO,
        occurred_at=NOW,
        message="Submitted.",
        execution_id="execution-001",
        order_id="SIM-000001",
        attributes=[
            (
                "  broker  ",
                "  SIMULATOR  ",
            ),
        ],
    )

    assert value.attributes == (
        (
            "broker",
            "SIMULATOR",
        ),
    )


def test_active_lifecycle_record() -> None:
    value = active_record()

    assert value.current_stage is TradeLifecycleStage.SUBMITTED
    assert value.terminal is False
    assert value.remaining_quantity == Decimal("10")


def test_filled_lifecycle_record() -> None:
    value = filled_record()

    assert value.current_stage is TradeLifecycleStage.FILLED
    assert value.terminal is True
    assert value.remaining_quantity == Decimal("0")
    assert value.average_fill_price == Decimal("200")


def test_record_identifiers_are_normalized() -> None:
    value = TradeLifecycleRecord(
        lifecycle_id="  lifecycle-001  ",
        execution_id="  execution-001  ",
        order_id="  SIM-000001  ",
        original_quantity=Decimal("10"),
        current_stage=TradeLifecycleStage.CREATED,
        created_at=NOW,
        cumulative_filled_quantity=Decimal("0"),
        remaining_quantity=Decimal("10"),
    )

    assert value.lifecycle_id == "lifecycle-001"
    assert value.execution_id == "execution-001"
    assert value.order_id == "SIM-000001"


def test_original_quantity_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "original_quantity must be greater than zero"
        ),
    ):
        TradeLifecycleRecord(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("0"),
            current_stage=TradeLifecycleStage.CREATED,
            created_at=NOW,
            cumulative_filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("0"),
        )


def test_cumulative_fill_cannot_exceed_original() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "cumulative_filled_quantity must not exceed "
            "original_quantity"
        ),
    ):
        TradeLifecycleRecord(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("10"),
            current_stage=(
                TradeLifecycleStage.PARTIALLY_FILLED
            ),
            created_at=NOW,
            cumulative_filled_quantity=Decimal("11"),
            remaining_quantity=Decimal("0"),
            average_fill_price=Decimal("200"),
        )


def test_remaining_quantity_must_match_fill() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "remaining_quantity must equal original_quantity "
            "minus cumulative_filled_quantity"
        ),
    ):
        TradeLifecycleRecord(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("10"),
            current_stage=(
                TradeLifecycleStage.PARTIALLY_FILLED
            ),
            created_at=NOW,
            cumulative_filled_quantity=Decimal("5"),
            remaining_quantity=Decimal("4"),
            average_fill_price=Decimal("200"),
        )


def test_filled_record_requires_average_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "filled records must include average_fill_price"
        ),
    ):
        TradeLifecycleRecord(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("10"),
            current_stage=(
                TradeLifecycleStage.PARTIALLY_FILLED
            ),
            created_at=NOW,
            cumulative_filled_quantity=Decimal("5"),
            remaining_quantity=Decimal("5"),
        )


def test_retry_count_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="retry_count must not be negative",
    ):
        TradeLifecycleRecord(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("10"),
            current_stage=TradeLifecycleStage.CREATED,
            created_at=NOW,
            cumulative_filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("10"),
            retry_count=-1,
        )


def test_terminal_record_requires_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "terminal records must include completed_at"
        ),
    ):
        TradeLifecycleRecord(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("10"),
            current_stage=TradeLifecycleStage.CANCELLED,
            created_at=NOW,
            cumulative_filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("10"),
            terminal=True,
        )


def test_terminal_stage_requires_terminal_true() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "terminal lifecycle stages require terminal=True"
        ),
    ):
        TradeLifecycleRecord(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("10"),
            current_stage=TradeLifecycleStage.CANCELLED,
            created_at=NOW,
            cumulative_filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("10"),
        )


def test_filled_record_requires_zero_remaining() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "filled records must have zero remaining_quantity"
        ),
    ):
        TradeLifecycleRecord(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("10"),
            current_stage=TradeLifecycleStage.FILLED,
            created_at=NOW,
            cumulative_filled_quantity=Decimal("5"),
            remaining_quantity=Decimal("5"),
            average_fill_price=Decimal("200"),
            terminal=True,
            completed_at=NOW + timedelta(minutes=1),
        )


def test_duplicate_event_ids_are_rejected() -> None:
    duplicate = event(
        1,
        event_id="duplicate",
        event_type=LifecycleEventType.ORDER_SUBMITTED,
        stage=TradeLifecycleStage.SUBMITTED,
    )

    with pytest.raises(
        ValueError,
        match="duplicate event_id",
    ):
        TradeLifecycleRecord(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("10"),
            current_stage=TradeLifecycleStage.SUBMITTED,
            created_at=NOW,
            events=(duplicate, duplicate),
            cumulative_filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("10"),
        )


def test_event_sequences_must_be_increasing() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "event sequence numbers must be strictly increasing"
        ),
    ):
        TradeLifecycleRecord(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("10"),
            current_stage=TradeLifecycleStage.SUBMITTED,
            created_at=NOW,
            events=(
                event(
                    2,
                    event_type=(
                        LifecycleEventType.ORDER_SUBMITTED
                    ),
                    stage=TradeLifecycleStage.SUBMITTED,
                ),
                event(
                    1,
                    event_type=(
                        LifecycleEventType.ORDER_SUBMITTED
                    ),
                    stage=TradeLifecycleStage.SUBMITTED,
                ),
            ),
            cumulative_filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("10"),
        )


def test_event_execution_id_must_match_record() -> None:
    bad_event = OrderLifecycleEvent(
        sequence_number=1,
        event_id="event-001",
        event_type=LifecycleEventType.ORDER_SUBMITTED,
        stage=TradeLifecycleStage.SUBMITTED,
        severity=LifecycleEventSeverity.INFO,
        occurred_at=NOW,
        message="Submitted.",
        execution_id="different",
        order_id="SIM-000001",
    )

    with pytest.raises(
        ValueError,
        match=(
            "event execution_id must match "
            "the lifecycle record"
        ),
    ):
        TradeLifecycleRecord(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("10"),
            current_stage=TradeLifecycleStage.SUBMITTED,
            created_at=NOW,
            events=(bad_event,),
            cumulative_filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("10"),
        )


def test_current_stage_matches_last_event() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "current_stage must match the final event stage"
        ),
    ):
        TradeLifecycleRecord(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("10"),
            current_stage=TradeLifecycleStage.ACKNOWLEDGED,
            created_at=NOW,
            events=(
                event(
                    1,
                    event_type=(
                        LifecycleEventType.ORDER_SUBMITTED
                    ),
                    stage=TradeLifecycleStage.SUBMITTED,
                ),
            ),
            cumulative_filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("10"),
        )


def test_trade_lifecycle_report() -> None:
    record = active_record()

    report = TradeLifecycleReport(
        status=TradeLifecycleStatus.PENDING,
        record=record,
        event_count=1,
        terminal=False,
        current_stage=TradeLifecycleStage.SUBMITTED,
    )

    assert report.record == record
    assert report.event_count == 1
    assert report.terminal is False


def test_report_event_count_must_match_record() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "event_count must match the record event count"
        ),
    ):
        TradeLifecycleReport(
            status=TradeLifecycleStatus.PENDING,
            record=active_record(),
            event_count=0,
            terminal=False,
            current_stage=TradeLifecycleStage.SUBMITTED,
        )


def test_report_terminal_must_match_record() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "terminal must match the lifecycle record"
        ),
    ):
        TradeLifecycleReport(
            status=TradeLifecycleStatus.COMPLETED,
            record=filled_record(),
            event_count=2,
            terminal=False,
            current_stage=TradeLifecycleStage.FILLED,
        )


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        TradeLifecycleReport(
            status=TradeLifecycleStatus.FAILED,
            record=None,
            event_count=0,
            terminal=False,
            current_stage=None,
        )


def test_completed_report_cannot_include_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only failed reports may include an error"
        ),
    ):
        TradeLifecycleReport(
            status=TradeLifecycleStatus.COMPLETED,
            record=filled_record(),
            event_count=2,
            terminal=True,
            current_stage=TradeLifecycleStage.FILLED,
            error="Unexpected error.",
        )


def test_report_warnings_are_tuples() -> None:
    value = TradeLifecycleReport(
        status=TradeLifecycleStatus.PENDING,
        record=active_record(),
        event_count=1,
        terminal=False,
        current_stage=TradeLifecycleStage.SUBMITTED,
        warnings=["Lifecycle warning."],
    )

    assert value.warnings == (
        "Lifecycle warning.",
    )


def test_models_are_immutable() -> None:
    value = active_record()

    with pytest.raises(FrozenInstanceError):
        value.order_id = "changed"