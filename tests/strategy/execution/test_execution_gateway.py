from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.strategy.execution.execution_gateway import (
    AlpacaAdapter,
    ExecutionGateway,
    InteractiveBrokersAdapter,
    SimulatorBrokerAdapter,
    TradierAdapter,
)
from app.strategy.execution.execution_models import (
    ExecutionOrderType,
    ExecutionReceipt,
    ExecutionRequest,
    ExecutionSide,
    ExecutionStatus,
)


NOW = datetime(
    2026,
    8,
    2,
    17,
    0,
    tzinfo=timezone.utc,
)


def request(
    *,
    side: ExecutionSide = ExecutionSide.BUY,
    order_type: ExecutionOrderType = (
        ExecutionOrderType.MARKET
    ),
    quantity: str = "10",
    limit_price: str | None = None,
) -> ExecutionRequest:
    return ExecutionRequest(
        execution_id="execution-001",
        symbol="AAPL",
        side=side,
        quantity=Decimal(quantity),
        order_type=order_type,
        submitted_at=NOW,
        limit_price=(
            Decimal(limit_price)
            if limit_price is not None
            else None
        ),
    )


def simulator(
    *,
    price: str = "200",
    commission: str = "1",
) -> SimulatorBrokerAdapter:
    return SimulatorBrokerAdapter(
        price_provider=lambda symbol: Decimal(price),
        commission_per_order=Decimal(commission),
        clock=lambda: NOW,
    )


def test_market_order_executes() -> None:
    report = ExecutionGateway(
        adapter=simulator()
    ).submit(request())

    assert report.status is ExecutionStatus.COMPLETED
    assert report.receipt is not None
    assert report.receipt.average_price == Decimal("200")
    assert report.receipt.filled_quantity == Decimal("10")
    assert report.receipt.commission == Decimal("1")


def test_simulator_generates_sequential_order_ids() -> None:
    adapter = simulator()
    gateway = ExecutionGateway(adapter=adapter)

    first = gateway.submit(request())
    second_request = ExecutionRequest(
        execution_id="execution-002",
        symbol="MSFT",
        side=ExecutionSide.BUY,
        quantity=Decimal("5"),
        order_type=ExecutionOrderType.MARKET,
        submitted_at=NOW,
    )
    second = gateway.submit(second_request)

    assert first.receipt is not None
    assert second.receipt is not None
    assert first.receipt.order_id == "SIM-000001"
    assert second.receipt.order_id == "SIM-000002"


def test_buy_limit_executes_when_market_is_below_limit() -> None:
    report = ExecutionGateway(
        adapter=simulator(price="195")
    ).submit(
        request(
            order_type=ExecutionOrderType.LIMIT,
            limit_price="200",
        )
    )

    assert report.status is ExecutionStatus.COMPLETED
    assert report.receipt is not None
    assert report.receipt.average_price == Decimal("195")


def test_buy_limit_fails_when_market_is_above_limit() -> None:
    report = ExecutionGateway(
        adapter=simulator(price="205")
    ).submit(
        request(
            order_type=ExecutionOrderType.LIMIT,
            limit_price="200",
        )
    )

    assert report.status is ExecutionStatus.FAILED
    assert (
        report.error
        == "buy limit price has not been reached"
    )


def test_sell_limit_executes_when_market_is_above_limit() -> None:
    report = ExecutionGateway(
        adapter=simulator(price="205")
    ).submit(
        request(
            side=ExecutionSide.SELL,
            order_type=ExecutionOrderType.LIMIT,
            limit_price="200",
        )
    )

    assert report.status is ExecutionStatus.COMPLETED


def test_sell_limit_fails_when_market_is_below_limit() -> None:
    report = ExecutionGateway(
        adapter=simulator(price="195")
    ).submit(
        request(
            side=ExecutionSide.SELL,
            order_type=ExecutionOrderType.LIMIT,
            limit_price="200",
        )
    )

    assert report.status is ExecutionStatus.FAILED
    assert (
        report.error
        == "sell limit price has not been reached"
    )


def test_invalid_adapter_receipt_returns_failed_report() -> None:
    class InvalidAdapter:
        name = "INVALID"

        def execute(self, value):
            del value
            return object()

    report = ExecutionGateway(
        adapter=InvalidAdapter()
    ).submit(request())

    assert report.status is ExecutionStatus.FAILED
    assert (
        report.error
        == "adapter execute must return ExecutionReceipt"
    )


def test_overfill_returns_failed_report() -> None:
    class OverfillAdapter:
        name = "OVERFILL"

        def execute(self, value):
            return ExecutionReceipt(
                execution_id=value.execution_id,
                broker_name=self.name,
                order_id="OVERFILL-001",
                filled_quantity=(
                    value.quantity + Decimal("1")
                ),
                average_price=Decimal("200"),
                commission=Decimal("0"),
                executed_at=NOW,
            )

    report = ExecutionGateway(
        adapter=OverfillAdapter()
    ).submit(request())

    assert report.status is ExecutionStatus.FAILED
    assert "must not exceed" in report.error


def test_partial_fill_adds_warning() -> None:
    class PartialFillAdapter:
        name = "PARTIAL"

        def execute(self, value):
            return ExecutionReceipt(
                execution_id=value.execution_id,
                broker_name=self.name,
                order_id="PARTIAL-001",
                filled_quantity=Decimal("5"),
                average_price=Decimal("200"),
                commission=Decimal("0"),
                executed_at=NOW,
            )

    report = ExecutionGateway(
        adapter=PartialFillAdapter()
    ).submit(request(quantity="10"))

    assert report.status is ExecutionStatus.COMPLETED
    assert report.warnings == (
        "The execution was partially filled.",
    )


@pytest.mark.parametrize(
    "adapter",
    [
        InteractiveBrokersAdapter(),
        AlpacaAdapter(),
        TradierAdapter(),
    ],
)
def test_unconfigured_live_adapter_fails_safely(
    adapter,
) -> None:
    report = ExecutionGateway(
        adapter=adapter
    ).submit(request())

    assert report.status is ExecutionStatus.FAILED
    assert "is not configured" in report.error


def test_request_type_is_validated() -> None:
    with pytest.raises(
        TypeError,
        match="request must be an ExecutionRequest",
    ):
        ExecutionGateway(
            adapter=simulator()
        ).submit(object())


def test_adapter_requires_execute() -> None:
    with pytest.raises(
        TypeError,
        match="adapter must provide an execute method",
    ):
        ExecutionGateway(
            adapter=object()
        )


def test_price_provider_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="price_provider must be callable",
    ):
        SimulatorBrokerAdapter(
            price_provider=Decimal("200")
        )


def test_commission_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="commission_per_order must not be negative",
    ):
        SimulatorBrokerAdapter(
            price_provider=lambda symbol: Decimal(
                "200"
            ),
            commission_per_order=Decimal("-1"),
        )


def test_price_provider_must_return_decimal() -> None:
    report = ExecutionGateway(
        adapter=SimulatorBrokerAdapter(
            price_provider=lambda symbol: 200,
            clock=lambda: NOW,
        )
    ).submit(request())

    assert report.status is ExecutionStatus.FAILED
    assert (
        report.error
        == "price_provider must return a Decimal"
    )


def test_clock_must_return_timezone_aware_datetime() -> None:
    report = ExecutionGateway(
        adapter=SimulatorBrokerAdapter(
            price_provider=lambda symbol: Decimal(
                "200"
            ),
            clock=lambda: datetime(2026, 8, 2),
        )
    ).submit(request())

    assert report.status is ExecutionStatus.FAILED
    assert (
        report.error
        == "clock must return a timezone-aware datetime"
    )