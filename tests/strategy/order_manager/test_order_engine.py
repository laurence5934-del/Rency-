from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.order_manager import (
    EnterpriseOrderManager,
    OrderDecision,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from app.strategy.portfolio_manager import AssetClass


NOW = datetime(
    2026,
    8,
    4,
    19,
    0,
    tzinfo=timezone.utc,
)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def engine(
    current_time: datetime = NOW,
) -> EnterpriseOrderManager:
    return EnterpriseOrderManager(
        clock=FixedClock(current_time)
    )


def request(
    *,
    order_id: str = "order-001",
    client_order_id: str = "client-order-001",
    portfolio_id: str = "portfolio-001",
    symbol: str = "NVDA",
    quantity: str = "10",
    side: OrderSide = OrderSide.BUY,
) -> OrderRequest:
    return OrderRequest(
        order_id=order_id,
        client_order_id=client_order_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        asset_class=AssetClass.EQUITY,
        side=side,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal(quantity),
        created_at=NOW,
        strategy_id="momentum-001",
    )


def registered_manager() -> EnterpriseOrderManager:
    value = engine()
    value.register_order(request())
    return value


def validated_manager() -> EnterpriseOrderManager:
    value = registered_manager()
    value.validate_order("order-001")
    return value


def submitted_manager() -> EnterpriseOrderManager:
    value = validated_manager()
    value.submit_order("order-001")
    return value


def acknowledged_manager() -> EnterpriseOrderManager:
    value = submitted_manager()
    value.acknowledge_order(
        "order-001",
        broker_order_id="broker-order-001",
    )
    return value


def test_register_order() -> None:
    value = engine()
    order_request = request()

    report = value.register_order(order_request)

    assert report.status is OrderStatus.CREATED
    assert report.decision is OrderDecision.APPROVE
    assert report.request == order_request
    assert report.execution is None
    assert value.order_ids == ("order-001",)


def test_register_order_requires_request_model() -> None:
    with pytest.raises(
        TypeError,
        match="request must be an OrderRequest",
    ):
        engine().register_order(object())


def test_duplicate_order_id_is_rejected() -> None:
    value = registered_manager()

    with pytest.raises(
        ValueError,
        match="order_id is already registered",
    ):
        value.register_order(
            request(
                client_order_id="client-order-002",
            )
        )


def test_duplicate_client_order_id_is_rejected() -> None:
    value = registered_manager()

    with pytest.raises(
        ValueError,
        match=(
            "client_order_id is already registered"
        ),
    ):
        value.register_order(
            request(
                order_id="order-002",
            )
        )


def test_register_multiple_orders() -> None:
    value = engine()

    value.register_order(request())

    value.register_order(
        request(
            order_id="order-002",
            client_order_id="client-order-002",
            symbol="AAPL",
        )
    )

    assert value.order_ids == (
        "order-001",
        "order-002",
    )


def test_get_request() -> None:
    value = registered_manager()

    result = value.get_request("order-001")

    assert result.order_id == "order-001"
    assert result.symbol == "NVDA"


def test_get_request_normalizes_identifier() -> None:
    value = registered_manager()

    result = value.get_request(
        "  order-001  "
    )

    assert result.order_id == "order-001"


def test_get_unknown_request_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="order not found",
    ):
        engine().get_request("missing")


def test_get_execution_before_validation_is_rejected() -> None:
    value = registered_manager()

    with pytest.raises(
        KeyError,
        match="order has no execution state",
    ):
        value.get_execution("order-001")


def test_validate_order() -> None:
    value = registered_manager()

    report = value.validate_order("order-001")

    assert report.status is OrderStatus.VALIDATED
    assert report.decision is OrderDecision.APPROVE
    assert report.execution is not None
    assert (
        report.execution.status
        is OrderStatus.VALIDATED
    )
    assert (
        report.execution.filled_quantity
        == Decimal("0")
    )
    assert (
        report.execution.remaining_quantity
        == Decimal("10")
    )


def test_validate_requires_created_status() -> None:
    value = validated_manager()

    with pytest.raises(
        RuntimeError,
        match=(
            "order transition is not permitted "
            "from VALIDATED"
        ),
    ):
        value.validate_order("order-001")


def test_submit_order() -> None:
    value = validated_manager()

    report = value.submit_order("order-001")

    assert report.status is OrderStatus.SUBMITTED
    assert report.execution is not None
    assert (
        report.execution.status
        is OrderStatus.SUBMITTED
    )
    assert (
        report.execution.remaining_quantity
        == Decimal("10")
    )


def test_submit_requires_validated_status() -> None:
    value = registered_manager()

    with pytest.raises(
        RuntimeError,
        match=(
            "order transition is not permitted "
            "from CREATED"
        ),
    ):
        value.submit_order("order-001")


def test_acknowledge_order() -> None:
    value = submitted_manager()

    report = value.acknowledge_order(
        "order-001",
        broker_order_id="broker-order-001",
    )

    assert report.status is OrderStatus.ACKNOWLEDGED
    assert report.execution is not None
    assert (
        report.execution.broker_order_id
        == "broker-order-001"
    )


def test_acknowledge_normalizes_broker_order_id() -> None:
    value = submitted_manager()

    report = value.acknowledge_order(
        "order-001",
        broker_order_id="  broker-order-001  ",
    )

    assert report.execution is not None
    assert (
        report.execution.broker_order_id
        == "broker-order-001"
    )


def test_acknowledge_requires_submitted_status() -> None:
    value = validated_manager()

    with pytest.raises(
        RuntimeError,
        match=(
            "order transition is not permitted "
            "from VALIDATED"
        ),
    ):
        value.acknowledge_order(
            "order-001",
            broker_order_id="broker-order-001",
        )


def test_duplicate_broker_order_id_is_rejected() -> None:
    value = engine()

    value.register_order(request())
    value.validate_order("order-001")
    value.submit_order("order-001")
    value.acknowledge_order(
        "order-001",
        broker_order_id="broker-order-001",
    )

    value.register_order(
        request(
            order_id="order-002",
            client_order_id="client-order-002",
            symbol="AAPL",
        )
    )
    value.validate_order("order-002")
    value.submit_order("order-002")

    with pytest.raises(
        ValueError,
        match=(
            "broker_order_id is already registered"
        ),
    ):
        value.acknowledge_order(
            "order-002",
            broker_order_id="broker-order-001",
        )


def test_get_current_execution() -> None:
    value = acknowledged_manager()

    execution = value.get_execution(
        "order-001"
    )

    assert execution.status is OrderStatus.ACKNOWLEDGED
    assert execution.execution_id == (
        "execution-000003"
    )


def test_get_latest_report() -> None:
    value = acknowledged_manager()

    report = value.get_report("order-001")

    assert report.status is OrderStatus.ACKNOWLEDGED
    assert report.execution is not None
    assert (
        report.execution.execution_id
        == "execution-000003"
    )


def test_get_report_for_unknown_order_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="order not found",
    ):
        engine().get_report("missing")


def test_execution_history() -> None:
    value = acknowledged_manager()

    executions = value.executions_for_order(
        "order-001"
    )

    assert len(executions) == 3
    assert tuple(
        execution.status
        for execution in executions
    ) == (
        OrderStatus.VALIDATED,
        OrderStatus.SUBMITTED,
        OrderStatus.ACKNOWLEDGED,
    )


def test_report_history_for_order() -> None:
    value = acknowledged_manager()

    reports = value.reports_for_order(
        "order-001"
    )

    assert len(reports) == 4
    assert tuple(
        report.status
        for report in reports
    ) == (
        OrderStatus.CREATED,
        OrderStatus.VALIDATED,
        OrderStatus.SUBMITTED,
        OrderStatus.ACKNOWLEDGED,
    )


def test_global_report_history() -> None:
    value = acknowledged_manager()

    assert len(value.report_history) == 4


def test_execution_ids_are_deterministic() -> None:
    value = acknowledged_manager()

    executions = value.executions_for_order(
        "order-001"
    )

    assert tuple(
        execution.execution_id
        for execution in executions
    ) == (
        "execution-000001",
        "execution-000002",
        "execution-000003",
    )


def test_execution_ids_continue_across_orders() -> None:
    value = acknowledged_manager()

    value.register_order(
        request(
            order_id="order-002",
            client_order_id="client-order-002",
            symbol="AAPL",
        )
    )
    value.validate_order("order-002")

    executions = value.executions_for_order(
        "order-002"
    )

    assert len(executions) == 1
    assert executions[0].execution_id == (
        "execution-000004"
    )


def test_registered_report_uses_engine_clock() -> None:
    current_time = NOW + timedelta(minutes=5)
    value = engine(current_time)

    report = value.register_order(request())

    assert report.reported_at == current_time


def test_validate_uses_engine_clock() -> None:
    current_time = NOW + timedelta(minutes=5)
    value = engine(current_time)
    value.register_order(request())

    report = value.validate_order("order-001")

    assert report.execution is not None
    assert (
        report.execution.occurred_at
        == current_time
    )
    assert report.reported_at == current_time


def test_order_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="order_id must not be empty",
    ):
        engine().get_request("   ")


def test_order_identifier_must_be_string() -> None:
    with pytest.raises(
        TypeError,
        match="order_id must be a string",
    ):
        engine().get_request(123)


def test_broker_order_id_must_not_be_empty() -> None:
    value = submitted_manager()

    with pytest.raises(
        ValueError,
        match=(
            "broker_order_id must not be empty"
        ),
    ):
        value.acknowledge_order(
            "order-001",
            broker_order_id="   ",
        )


def test_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterpriseOrderManager(clock=NOW)


def test_clock_must_return_datetime() -> None:
    value = EnterpriseOrderManager(
        clock=lambda: "now"
    )

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        value.register_order(request())


def test_clock_must_return_timezone_aware_datetime() -> None:
    value = EnterpriseOrderManager(
        clock=lambda: datetime(
            2026,
            8,
            4,
            19,
            0,
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        value.register_order(request())