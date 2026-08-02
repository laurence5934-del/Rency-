from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.trade_lifecycle.lifecycle_engine import (
    TradeLifecycleEngine,
)
from app.strategy.trade_lifecycle.lifecycle_models import (
    LifecycleEventType,
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


class IncrementingClock:
    def __init__(self) -> None:
        self.value = NOW

    def __call__(self) -> datetime:
        current = self.value
        self.value += timedelta(seconds=1)
        return current


def engine(
    *,
    quantity: str = "10",
) -> TradeLifecycleEngine:
    return TradeLifecycleEngine(
        lifecycle_id="lifecycle-001",
        execution_id="execution-001",
        order_id="SIM-000001",
        original_quantity=Decimal(quantity),
        clock=IncrementingClock(),
    )


def acknowledged_engine() -> TradeLifecycleEngine:
    value = engine()
    value.submit()
    value.acknowledge()
    return value


def test_creates_lifecycle() -> None:
    value = engine()

    assert value.current_stage is TradeLifecycleStage.CREATED
    assert value.original_quantity == Decimal("10")
    assert value.remaining_quantity == Decimal("10")
    assert len(value.events) == 1


def test_created_event_is_recorded() -> None:
    value = engine()

    first = value.events[0]

    assert first.sequence_number == 1
    assert first.event_id == "lifecycle-001-000001"
    assert first.event_type is LifecycleEventType.ORDER_CREATED


def test_submit_order() -> None:
    report = engine().submit()

    assert report.status is TradeLifecycleStatus.PENDING
    assert report.current_stage is TradeLifecycleStage.SUBMITTED
    assert report.event_count == 2


def test_acknowledge_order() -> None:
    value = engine()
    value.submit()

    report = value.acknowledge()

    assert report.current_stage is TradeLifecycleStage.ACKNOWLEDGED


def test_cannot_acknowledge_created_order() -> None:
    with pytest.raises(
        ValueError,
        match="CREATED -> ACKNOWLEDGED",
    ):
        engine().acknowledge()


def test_partial_fill() -> None:
    report = acknowledged_engine().record_fill(
        filled_quantity=Decimal("4"),
        fill_price=Decimal("200"),
    )

    assert (
        report.current_stage
        is TradeLifecycleStage.PARTIALLY_FILLED
    )
    assert report.record is not None
    assert (
        report.record.cumulative_filled_quantity
        == Decimal("4")
    )
    assert report.record.remaining_quantity == Decimal("6")
    assert report.record.average_fill_price == Decimal("200")


def test_multiple_partial_fills_accumulate() -> None:
    value = acknowledged_engine()

    value.record_fill(
        filled_quantity=Decimal("3"),
        fill_price=Decimal("200"),
    )
    report = value.record_fill(
        filled_quantity=Decimal("2"),
        fill_price=Decimal("210"),
    )

    assert report.record is not None
    assert (
        report.record.cumulative_filled_quantity
        == Decimal("5")
    )
    assert report.record.remaining_quantity == Decimal("5")


def test_weighted_average_fill_price() -> None:
    value = acknowledged_engine()

    value.record_fill(
        filled_quantity=Decimal("4"),
        fill_price=Decimal("100"),
    )
    report = value.record_fill(
        filled_quantity=Decimal("6"),
        fill_price=Decimal("200"),
    )

    assert report.record is not None
    assert (
        report.record.average_fill_price
        == Decimal("160")
    )


def test_full_fill_is_terminal() -> None:
    report = acknowledged_engine().record_fill(
        filled_quantity=Decimal("10"),
        fill_price=Decimal("200"),
    )

    assert report.status is TradeLifecycleStatus.COMPLETED
    assert report.current_stage is TradeLifecycleStage.FILLED
    assert report.terminal is True
    assert report.record is not None
    assert report.record.remaining_quantity == Decimal("0")


def test_fill_cannot_exceed_remaining_quantity() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "filled_quantity must not exceed "
            "remaining_quantity"
        ),
    ):
        acknowledged_engine().record_fill(
            filled_quantity=Decimal("11"),
            fill_price=Decimal("200"),
        )


def test_fill_quantity_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="filled_quantity must be greater than zero",
    ):
        acknowledged_engine().record_fill(
            filled_quantity=Decimal("0"),
            fill_price=Decimal("200"),
        )


def test_fill_price_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="fill_price must be greater than zero",
    ):
        acknowledged_engine().record_fill(
            filled_quantity=Decimal("1"),
            fill_price=Decimal("0"),
        )


def test_request_modification() -> None:
    report = acknowledged_engine().request_modification()

    assert (
        report.current_stage
        is TradeLifecycleStage.MODIFICATION_REQUESTED
    )


def test_confirm_modification() -> None:
    value = acknowledged_engine()
    value.request_modification()

    report = value.confirm_modified(
        attributes=(
            ("new_limit_price", "195"),
        )
    )

    assert report.current_stage is TradeLifecycleStage.MODIFIED


def test_cannot_confirm_unrequested_modification() -> None:
    with pytest.raises(
        ValueError,
        match="ACKNOWLEDGED -> MODIFIED",
    ):
        acknowledged_engine().confirm_modified()


def test_request_cancellation() -> None:
    report = acknowledged_engine().request_cancellation()

    assert (
        report.current_stage
        is TradeLifecycleStage.CANCELLATION_REQUESTED
    )


def test_cancel_order() -> None:
    value = acknowledged_engine()
    value.request_cancellation()

    report = value.cancel()

    assert report.current_stage is TradeLifecycleStage.CANCELLED
    assert report.terminal is True
    assert report.status is TradeLifecycleStatus.COMPLETED


def test_cannot_cancel_without_request() -> None:
    with pytest.raises(
        ValueError,
        match="ACKNOWLEDGED -> CANCELLED",
    ):
        acknowledged_engine().cancel()


def test_reject_submitted_order() -> None:
    value = engine()
    value.submit()

    report = value.reject(
        reason="Broker rejected the order."
    )

    assert report.current_stage is TradeLifecycleStage.REJECTED
    assert report.terminal is True


def test_rejection_reason_must_not_be_empty() -> None:
    value = engine()
    value.submit()

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        value.reject(reason="   ")


def test_expire_acknowledged_order() -> None:
    report = acknowledged_engine().expire()

    assert report.current_stage is TradeLifecycleStage.EXPIRED
    assert report.terminal is True


def test_fail_lifecycle() -> None:
    report = acknowledged_engine().fail(
        error="Broker connection failed."
    )

    assert report.current_stage is TradeLifecycleStage.FAILED
    assert report.terminal is True
    assert (
        "Order lifecycle ended in failure."
        in report.warnings
    )


def test_schedule_retry() -> None:
    value = acknowledged_engine()

    report = value.schedule_retry(
        reason="Retry broker reconciliation."
    )

    assert report.record is not None
    assert report.record.retry_count == 1
    assert (
        report.current_stage
        is TradeLifecycleStage.ACKNOWLEDGED
    )


def test_multiple_retries_increment_count() -> None:
    value = acknowledged_engine()

    value.schedule_retry(reason="Retry one.")
    report = value.schedule_retry(reason="Retry two.")

    assert report.record is not None
    assert report.record.retry_count == 2


def test_reconciliation_preserves_stage() -> None:
    value = acknowledged_engine()

    report = value.reconcile(
        broker_status="WORKING"
    )

    assert (
        report.current_stage
        is TradeLifecycleStage.ACKNOWLEDGED
    )
    assert (
        value.events[-1].event_type
        is LifecycleEventType.BROKER_RECONCILED
    )


def test_events_by_type() -> None:
    value = acknowledged_engine()

    events = value.events_by_type(
        LifecycleEventType.ORDER_ACKNOWLEDGED
    )

    assert len(events) == 1


def test_events_by_stage() -> None:
    value = acknowledged_engine()

    events = value.events_by_stage(
        TradeLifecycleStage.SUBMITTED
    )

    assert len(events) == 1


def test_find_event() -> None:
    value = engine()
    event_id = value.events[0].event_id

    assert value.find_event(event_id) == value.events[0]


def test_find_event_returns_none() -> None:
    assert engine().find_event("missing") is None


def test_event_ids_are_sequential() -> None:
    value = acknowledged_engine()

    assert tuple(
        event.event_id
        for event in value.events
    ) == (
        "lifecycle-001-000001",
        "lifecycle-001-000002",
        "lifecycle-001-000003",
    )


def test_cannot_change_terminal_lifecycle() -> None:
    value = acknowledged_engine()
    value.record_fill(
        filled_quantity=Decimal("10"),
        fill_price=Decimal("200"),
    )

    with pytest.raises(
        RuntimeError,
        match="trade lifecycle is already terminal",
    ):
        value.schedule_retry(
            reason="Late retry."
        )


def test_snapshot_is_immutable_record() -> None:
    value = acknowledged_engine()

    report = value.snapshot()

    assert report.record is not None
    assert isinstance(report.record.events, tuple)


def test_original_quantity_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="original_quantity must be a Decimal",
    ):
        TradeLifecycleEngine(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=10,
        )


def test_original_quantity_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "original_quantity must be greater than zero"
        ),
    ):
        TradeLifecycleEngine(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("0"),
        )


def test_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        TradeLifecycleEngine(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("10"),
            clock=NOW,
        )


def test_clock_must_return_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        TradeLifecycleEngine(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("10"),
            clock=lambda: "now",
        )


def test_clock_must_return_timezone_aware_datetime() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        TradeLifecycleEngine(
            lifecycle_id="lifecycle-001",
            execution_id="execution-001",
            order_id="SIM-000001",
            original_quantity=Decimal("10"),
            clock=lambda: datetime(2026, 8, 2),
        )