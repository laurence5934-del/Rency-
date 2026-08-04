from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.order_manager.order_models import (
    ExecutionType,
    OrderAllocation,
    OrderDecision,
    OrderExecution,
    OrderFill,
    OrderReport,
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
    18,
    0,
    tzinfo=timezone.utc,
)


def market_request(
    *,
    order_id: str = "order-001",
    client_order_id: str = "client-order-001",
    portfolio_id: str = "portfolio-001",
    symbol: str = "NVDA",
    quantity: str = "10",
    side: OrderSide = OrderSide.BUY,
    time_in_force: TimeInForce = TimeInForce.DAY,
) -> OrderRequest:
    return OrderRequest(
        order_id=order_id,
        client_order_id=client_order_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        asset_class=AssetClass.EQUITY,
        side=side,
        order_type=OrderType.MARKET,
        time_in_force=time_in_force,
        quantity=Decimal(quantity),
        created_at=NOW,
        strategy_id="momentum-001",
    )


def limit_request(
    *,
    order_id: str = "order-001",
    limit_price: str = "125.50",
) -> OrderRequest:
    return OrderRequest(
        order_id=order_id,
        client_order_id="client-order-001",
        portfolio_id="portfolio-001",
        symbol="NVDA",
        asset_class=AssetClass.EQUITY,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal("10"),
        created_at=NOW,
        limit_price=Decimal(limit_price),
    )


def stop_request() -> OrderRequest:
    return OrderRequest(
        order_id="order-001",
        client_order_id="client-order-001",
        portfolio_id="portfolio-001",
        symbol="NVDA",
        asset_class=AssetClass.EQUITY,
        side=OrderSide.SELL,
        order_type=OrderType.STOP,
        time_in_force=TimeInForce.GTC,
        quantity=Decimal("10"),
        created_at=NOW,
        stop_price=Decimal("110"),
    )


def stop_limit_request() -> OrderRequest:
    return OrderRequest(
        order_id="order-001",
        client_order_id="client-order-001",
        portfolio_id="portfolio-001",
        symbol="NVDA",
        asset_class=AssetClass.EQUITY,
        side=OrderSide.SELL,
        order_type=OrderType.STOP_LIMIT,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal("10"),
        created_at=NOW,
        limit_price=Decimal("109"),
        stop_price=Decimal("110"),
    )


def fill(
    *,
    fill_id: str = "fill-001",
    order_id: str = "order-001",
    quantity: str = "4",
    price: str = "125",
    commission: str = "1",
    executed_at: datetime = NOW + timedelta(seconds=1),
) -> OrderFill:
    return OrderFill(
        fill_id=fill_id,
        order_id=order_id,
        quantity=Decimal(quantity),
        price=Decimal(price),
        commission=Decimal(commission),
        executed_at=executed_at,
        venue="NASDAQ",
        broker_execution_id="broker-execution-001",
    )


def allocation(
    *,
    allocation_id: str = "allocation-001",
    fill_id: str = "fill-001",
    order_id: str = "order-001",
    quantity: str = "4",
) -> OrderAllocation:
    return OrderAllocation(
        allocation_id=allocation_id,
        fill_id=fill_id,
        order_id=order_id,
        portfolio_id="portfolio-001",
        quantity=Decimal(quantity),
        allocated_at=NOW + timedelta(seconds=2),
        account_id="account-001",
    )


def acknowledged_execution() -> OrderExecution:
    return OrderExecution(
        execution_id="execution-001",
        order_id="order-001",
        execution_type=ExecutionType.ACKNOWLEDGED,
        status=OrderStatus.ACKNOWLEDGED,
        requested_quantity=Decimal("10"),
        filled_quantity=Decimal("0"),
        remaining_quantity=Decimal("10"),
        occurred_at=NOW + timedelta(seconds=1),
        message="Broker acknowledged the order.",
        broker_order_id="broker-order-001",
    )


def partial_execution() -> OrderExecution:
    first_fill = fill()

    return OrderExecution(
        execution_id="execution-001",
        order_id="order-001",
        execution_type=ExecutionType.PARTIAL_FILL,
        status=OrderStatus.PARTIALLY_FILLED,
        requested_quantity=Decimal("10"),
        filled_quantity=Decimal("4"),
        remaining_quantity=Decimal("6"),
        occurred_at=NOW + timedelta(seconds=3),
        message="Order partially filled.",
        fills=(first_fill,),
        allocations=(allocation(),),
        average_fill_price=Decimal("125"),
        broker_order_id="broker-order-001",
    )


def filled_execution() -> OrderExecution:
    first_fill = fill(
        fill_id="fill-001",
        quantity="4",
        price="125",
    )
    second_fill = fill(
        fill_id="fill-002",
        quantity="6",
        price="127",
        commission="1.50",
        executed_at=NOW + timedelta(seconds=2),
    )

    return OrderExecution(
        execution_id="execution-002",
        order_id="order-001",
        execution_type=ExecutionType.FILL,
        status=OrderStatus.FILLED,
        requested_quantity=Decimal("10"),
        filled_quantity=Decimal("10"),
        remaining_quantity=Decimal("0"),
        occurred_at=NOW + timedelta(seconds=3),
        message="Order completely filled.",
        fills=(first_fill, second_fill),
        allocations=(
            allocation(
                allocation_id="allocation-001",
                fill_id="fill-001",
                quantity="4",
            ),
            allocation(
                allocation_id="allocation-002",
                fill_id="fill-002",
                quantity="6",
            ),
        ),
        average_fill_price=Decimal("126.2"),
        broker_order_id="broker-order-001",
    )


def test_market_order_request() -> None:
    value = market_request()

    assert value.symbol == "NVDA"
    assert value.order_type is OrderType.MARKET
    assert value.quantity == Decimal("10")
    assert value.limit_price is None
    assert value.stop_price is None


def test_limit_order_request() -> None:
    value = limit_request()

    assert value.order_type is OrderType.LIMIT
    assert value.limit_price == Decimal("125.50")
    assert value.stop_price is None


def test_stop_order_request() -> None:
    value = stop_request()

    assert value.order_type is OrderType.STOP
    assert value.stop_price == Decimal("110")
    assert value.limit_price is None


def test_stop_limit_order_request() -> None:
    value = stop_limit_request()

    assert value.order_type is OrderType.STOP_LIMIT
    assert value.stop_price == Decimal("110")
    assert value.limit_price == Decimal("109")


def test_request_text_is_normalized() -> None:
    value = OrderRequest(
        order_id="  order-001  ",
        client_order_id="  client-order-001  ",
        portfolio_id="  portfolio-001  ",
        symbol="  nvda  ",
        asset_class=AssetClass.EQUITY,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal("10"),
        created_at=NOW,
        strategy_id="  momentum-001  ",
        metadata=[
            ("  source  ", "  strategy  "),
        ],
    )

    assert value.order_id == "order-001"
    assert value.client_order_id == "client-order-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.symbol == "NVDA"
    assert value.strategy_id == "momentum-001"
    assert value.metadata == (
        ("source", "strategy"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "order_id",
        "client_order_id",
        "portfolio_id",
        "symbol",
    ],
)
def test_request_identifiers_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "order_id": "order-001",
        "client_order_id": "client-order-001",
        "portfolio_id": "portfolio-001",
        "symbol": "NVDA",
        "asset_class": AssetClass.EQUITY,
        "side": OrderSide.BUY,
        "order_type": OrderType.MARKET,
        "time_in_force": TimeInForce.DAY,
        "quantity": Decimal("10"),
        "created_at": NOW,
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        OrderRequest(**arguments)


def test_quantity_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="quantity must be a Decimal",
    ):
        OrderRequest(
            order_id="order-001",
            client_order_id="client-order-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            quantity=10,
            created_at=NOW,
        )


@pytest.mark.parametrize(
    "quantity",
    [
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_quantity_must_be_positive(
    quantity: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="quantity must be greater than zero",
    ):
        OrderRequest(
            order_id="order-001",
            client_order_id="client-order-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            quantity=quantity,
            created_at=NOW,
        )


def test_created_at_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="created_at must be timezone-aware",
    ):
        OrderRequest(
            order_id="order-001",
            client_order_id="client-order-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            quantity=Decimal("10"),
            created_at=datetime(2026, 8, 4, 18, 0),
        )


def test_market_order_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="market orders must not include limit_price",
    ):
        OrderRequest(
            order_id="order-001",
            client_order_id="client-order-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            quantity=Decimal("10"),
            created_at=NOW,
            limit_price=Decimal("125"),
        )


def test_market_order_rejects_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="market orders must not include stop_price",
    ):
        OrderRequest(
            order_id="order-001",
            client_order_id="client-order-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            quantity=Decimal("10"),
            created_at=NOW,
            stop_price=Decimal("120"),
        )


def test_limit_order_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="limit orders must include limit_price",
    ):
        OrderRequest(
            order_id="order-001",
            client_order_id="client-order-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.DAY,
            quantity=Decimal("10"),
            created_at=NOW,
        )


def test_stop_order_requires_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="stop orders must include stop_price",
    ):
        OrderRequest(
            order_id="order-001",
            client_order_id="client-order-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            time_in_force=TimeInForce.DAY,
            quantity=Decimal("10"),
            created_at=NOW,
        )


def test_stop_limit_requires_both_prices() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "stop-limit orders must include limit_price"
        ),
    ):
        OrderRequest(
            order_id="order-001",
            client_order_id="client-order-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LIMIT,
            time_in_force=TimeInForce.DAY,
            quantity=Decimal("10"),
            created_at=NOW,
            stop_price=Decimal("110"),
        )


def test_expiration_must_follow_creation() -> None:
    with pytest.raises(
        ValueError,
        match="expire_at must be later than created_at",
    ):
        OrderRequest(
            order_id="order-001",
            client_order_id="client-order-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            quantity=Decimal("10"),
            created_at=NOW,
            expire_at=NOW,
        )


def test_gtc_order_rejects_expiration() -> None:
    with pytest.raises(
        ValueError,
        match="GTC orders must not include expire_at",
    ):
        OrderRequest(
            order_id="order-001",
            client_order_id="client-order-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.GTC,
            quantity=Decimal("10"),
            created_at=NOW,
            expire_at=NOW + timedelta(days=1),
        )


@pytest.mark.parametrize(
    "time_in_force",
    [
        TimeInForce.IOC,
        TimeInForce.FOK,
    ],
)
def test_immediate_orders_reject_expiration(
    time_in_force: TimeInForce,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "IOC and FOK orders must not include expire_at"
        ),
    ):
        OrderRequest(
            order_id="order-001",
            client_order_id="client-order-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force=time_in_force,
            quantity=Decimal("10"),
            created_at=NOW,
            expire_at=NOW + timedelta(minutes=1),
        )


def test_parent_order_must_differ() -> None:
    with pytest.raises(
        ValueError,
        match="parent_order_id must differ from order_id",
    ):
        OrderRequest(
            order_id="order-001",
            client_order_id="client-order-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            quantity=Decimal("10"),
            created_at=NOW,
            parent_order_id="order-001",
        )


def test_order_fill() -> None:
    value = fill()

    assert value.fill_id == "fill-001"
    assert value.venue == "NASDAQ"
    assert value.gross_value == Decimal("500")
    assert value.net_value == Decimal("499")


def test_fill_text_is_normalized() -> None:
    value = OrderFill(
        fill_id="  fill-001  ",
        order_id="  order-001  ",
        quantity=Decimal("2"),
        price=Decimal("100"),
        commission=Decimal("1"),
        executed_at=NOW,
        venue="  nasdaq  ",
        broker_execution_id="  execution-001  ",
    )

    assert value.fill_id == "fill-001"
    assert value.order_id == "order-001"
    assert value.venue == "NASDAQ"
    assert value.broker_execution_id == "execution-001"


@pytest.mark.parametrize(
    "quantity",
    [
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_fill_quantity_must_be_positive(
    quantity: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="fill quantity must be greater than zero",
    ):
        OrderFill(
            fill_id="fill-001",
            order_id="order-001",
            quantity=quantity,
            price=Decimal("100"),
            commission=Decimal("0"),
            executed_at=NOW,
            venue="NASDAQ",
        )


def test_fill_price_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="fill price must be greater than zero",
    ):
        OrderFill(
            fill_id="fill-001",
            order_id="order-001",
            quantity=Decimal("1"),
            price=Decimal("0"),
            commission=Decimal("0"),
            executed_at=NOW,
            venue="NASDAQ",
        )


def test_commission_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="commission must not be negative",
    ):
        OrderFill(
            fill_id="fill-001",
            order_id="order-001",
            quantity=Decimal("1"),
            price=Decimal("100"),
            commission=Decimal("-1"),
            executed_at=NOW,
            venue="NASDAQ",
        )


def test_order_allocation() -> None:
    value = allocation()

    assert value.allocation_id == "allocation-001"
    assert value.fill_id == "fill-001"
    assert value.quantity == Decimal("4")


def test_allocation_quantity_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "allocation quantity must be greater than zero"
        ),
    ):
        OrderAllocation(
            allocation_id="allocation-001",
            fill_id="fill-001",
            order_id="order-001",
            portfolio_id="portfolio-001",
            quantity=Decimal("0"),
            allocated_at=NOW,
        )


def test_acknowledged_execution() -> None:
    value = acknowledged_execution()

    assert value.status is OrderStatus.ACKNOWLEDGED
    assert value.filled_quantity == Decimal("0")
    assert value.remaining_quantity == Decimal("10")
    assert value.is_terminal is False


def test_partial_execution() -> None:
    value = partial_execution()

    assert value.status is OrderStatus.PARTIALLY_FILLED
    assert value.filled_quantity == Decimal("4")
    assert value.remaining_quantity == Decimal("6")
    assert value.average_fill_price == Decimal("125")
    assert value.total_commission == Decimal("1")


def test_complete_execution() -> None:
    value = filled_execution()

    assert value.status is OrderStatus.FILLED
    assert value.remaining_quantity == Decimal("0")
    assert value.average_fill_price == Decimal("126.2")
    assert value.total_commission == Decimal("2.50")
    assert value.is_terminal is True


def test_execution_quantities_must_reconcile() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "filled_quantity plus remaining_quantity "
            "must equal requested_quantity"
        ),
    ):
        OrderExecution(
            execution_id="execution-001",
            order_id="order-001",
            execution_type=ExecutionType.SUBMITTED,
            status=OrderStatus.SUBMITTED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("9"),
            occurred_at=NOW,
            message="Submitted.",
        )


def test_fill_order_id_must_match_execution() -> None:
    bad_fill = fill(
        order_id="different-order"
    )

    with pytest.raises(
        ValueError,
        match=(
            "fill order_id must match execution order_id"
        ),
    ):
        OrderExecution(
            execution_id="execution-001",
            order_id="order-001",
            execution_type=ExecutionType.PARTIAL_FILL,
            status=OrderStatus.PARTIALLY_FILLED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("4"),
            remaining_quantity=Decimal("6"),
            occurred_at=NOW + timedelta(seconds=3),
            message="Partial fill.",
            fills=(bad_fill,),
            average_fill_price=Decimal("125"),
            broker_order_id="broker-order-001",
        )


def test_fill_ids_must_be_unique() -> None:
    first_fill = fill()

    with pytest.raises(
        ValueError,
        match="fill_id values must be unique",
    ):
        OrderExecution(
            execution_id="execution-001",
            order_id="order-001",
            execution_type=ExecutionType.FILL,
            status=OrderStatus.FILLED,
            requested_quantity=Decimal("8"),
            filled_quantity=Decimal("8"),
            remaining_quantity=Decimal("0"),
            occurred_at=NOW + timedelta(seconds=3),
            message="Filled.",
            fills=(first_fill, first_fill),
            average_fill_price=Decimal("125"),
            broker_order_id="broker-order-001",
        )


def test_filled_quantity_must_match_fills() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "filled_quantity must equal total fill quantity"
        ),
    ):
        OrderExecution(
            execution_id="execution-001",
            order_id="order-001",
            execution_type=ExecutionType.PARTIAL_FILL,
            status=OrderStatus.PARTIALLY_FILLED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("5"),
            remaining_quantity=Decimal("5"),
            occurred_at=NOW + timedelta(seconds=3),
            message="Partial fill.",
            fills=(fill(quantity="4"),),
            average_fill_price=Decimal("125"),
            broker_order_id="broker-order-001",
        )


def test_allocation_must_reference_execution_fill() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "allocation fill_id must reference "
            "an execution fill"
        ),
    ):
        OrderExecution(
            execution_id="execution-001",
            order_id="order-001",
            execution_type=ExecutionType.PARTIAL_FILL,
            status=OrderStatus.PARTIALLY_FILLED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("4"),
            remaining_quantity=Decimal("6"),
            occurred_at=NOW + timedelta(seconds=3),
            message="Partial fill.",
            fills=(fill(),),
            allocations=(
                allocation(
                    fill_id="unknown-fill"
                ),
            ),
            average_fill_price=Decimal("125"),
            broker_order_id="broker-order-001",
        )


def test_allocation_cannot_exceed_fill() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "allocated quantity must not exceed "
            "fill quantity"
        ),
    ):
        OrderExecution(
            execution_id="execution-001",
            order_id="order-001",
            execution_type=ExecutionType.PARTIAL_FILL,
            status=OrderStatus.PARTIALLY_FILLED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("4"),
            remaining_quantity=Decimal("6"),
            occurred_at=NOW + timedelta(seconds=3),
            message="Partial fill.",
            fills=(fill(),),
            allocations=(
                allocation(quantity="5"),
            ),
            average_fill_price=Decimal("125"),
            broker_order_id="broker-order-001",
        )


def test_unfilled_execution_rejects_average_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "unfilled executions must not include "
            "average_fill_price"
        ),
    ):
        OrderExecution(
            execution_id="execution-001",
            order_id="order-001",
            execution_type=ExecutionType.SUBMITTED,
            status=OrderStatus.SUBMITTED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("10"),
            occurred_at=NOW,
            message="Submitted.",
            average_fill_price=Decimal("125"),
        )


def test_filled_execution_requires_average_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "filled executions must include "
            "average_fill_price"
        ),
    ):
        OrderExecution(
            execution_id="execution-001",
            order_id="order-001",
            execution_type=ExecutionType.PARTIAL_FILL,
            status=OrderStatus.PARTIALLY_FILLED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("4"),
            remaining_quantity=Decimal("6"),
            occurred_at=NOW + timedelta(seconds=3),
            message="Partial fill.",
            fills=(fill(),),
            broker_order_id="broker-order-001",
        )


def test_average_fill_price_must_reconcile() -> None:
    with pytest.raises(
        ValueError,
        match="average_fill_price must match fills",
    ):
        OrderExecution(
            execution_id="execution-001",
            order_id="order-001",
            execution_type=ExecutionType.PARTIAL_FILL,
            status=OrderStatus.PARTIALLY_FILLED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("4"),
            remaining_quantity=Decimal("6"),
            occurred_at=NOW + timedelta(seconds=3),
            message="Partial fill.",
            fills=(fill(),),
            average_fill_price=Decimal("124"),
            broker_order_id="broker-order-001",
        )


def test_rejected_execution_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "rejected and failed executions "
            "must include an error"
        ),
    ):
        OrderExecution(
            execution_id="execution-001",
            order_id="order-001",
            execution_type=ExecutionType.REJECTED,
            status=OrderStatus.REJECTED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("10"),
            occurred_at=NOW,
            message="Order rejected.",
        )


def test_broker_managed_execution_requires_broker_id() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "broker-managed executions must include "
            "broker_order_id"
        ),
    ):
        OrderExecution(
            execution_id="execution-001",
            order_id="order-001",
            execution_type=ExecutionType.ACKNOWLEDGED,
            status=OrderStatus.ACKNOWLEDGED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("10"),
            occurred_at=NOW,
            message="Acknowledged.",
        )


def test_order_report() -> None:
    request = market_request()
    execution = acknowledged_execution()

    report = OrderReport(
        status=OrderStatus.ACKNOWLEDGED,
        decision=OrderDecision.APPROVE,
        request=request,
        execution=execution,
        recommendation="Continue monitoring the order.",
        reported_at=NOW + timedelta(seconds=2),
    )

    assert report.request == request
    assert report.execution == execution
    assert report.error is None


def test_created_report_may_have_no_execution() -> None:
    report = OrderReport(
        status=OrderStatus.CREATED,
        decision=OrderDecision.APPROVE,
        request=market_request(),
        execution=None,
        recommendation="Validate the new order.",
        reported_at=NOW,
    )

    assert report.execution is None


def test_managed_report_requires_execution() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "managed order reports must include "
            "an execution"
        ),
    ):
        OrderReport(
            status=OrderStatus.SUBMITTED,
            decision=OrderDecision.APPROVE,
            request=market_request(),
            execution=None,
            recommendation="Order submitted.",
            reported_at=NOW,
        )


def test_report_execution_order_must_match_request() -> None:
    execution = OrderExecution(
        execution_id="execution-001",
        order_id="different-order",
        execution_type=ExecutionType.SUBMITTED,
        status=OrderStatus.SUBMITTED,
        requested_quantity=Decimal("10"),
        filled_quantity=Decimal("0"),
        remaining_quantity=Decimal("10"),
        occurred_at=NOW,
        message="Submitted.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "execution order_id must match request"
        ),
    ):
        OrderReport(
            status=OrderStatus.SUBMITTED,
            decision=OrderDecision.APPROVE,
            request=market_request(),
            execution=execution,
            recommendation="Monitor the order.",
            reported_at=NOW,
        )


def test_report_status_must_match_execution() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "report status must match execution status"
        ),
    ):
        OrderReport(
            status=OrderStatus.SUBMITTED,
            decision=OrderDecision.APPROVE,
            request=market_request(),
            execution=acknowledged_execution(),
            recommendation="Monitor the order.",
            reported_at=NOW + timedelta(seconds=2),
        )


def test_rejected_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "rejected and failed reports "
            "must include an error"
        ),
    ):
        OrderReport(
            status=OrderStatus.REJECTED,
            decision=OrderDecision.REJECT,
            request=market_request(),
            execution=None,
            recommendation="Correct the order.",
            reported_at=NOW,
        )


def test_reject_decision_requires_rejected_status() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "reject decisions require rejected "
            "or failed status"
        ),
    ):
        OrderReport(
            status=OrderStatus.CREATED,
            decision=OrderDecision.REJECT,
            request=market_request(),
            execution=None,
            recommendation="Invalid rejection.",
            reported_at=NOW,
        )


def test_models_are_immutable() -> None:
    value = market_request()

    with pytest.raises(FrozenInstanceError):
        value.quantity = Decimal("20")