from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.broker_gateway import (
    BrokerAccount,
    BrokerCapability,
    BrokerConnectionState,
    BrokerDecision,
    BrokerEnvironment,
    BrokerExecutionReport,
    BrokerHealthReport,
    BrokerOrderRequest,
    BrokerOrderResponse,
    BrokerOrderStatus,
    BrokerStatus,
)
from app.strategy.order_manager import (
    OrderSide,
    OrderType,
    TimeInForce,
)
from app.strategy.portfolio_manager import AssetClass


NOW = datetime(
    2026,
    8,
    4,
    20,
    0,
    tzinfo=timezone.utc,
)


def paper_account() -> BrokerAccount:
    return BrokerAccount(
        account_id="account-001",
        broker_name="Interactive Brokers",
        environment=BrokerEnvironment.PAPER,
        connection_state=BrokerConnectionState.CONNECTED,
        currency="USD",
        cash_balance=Decimal("100000"),
        settled_cash=Decimal("90000"),
        buying_power=Decimal("180000"),
        equity=Decimal("120000"),
        margin_used=Decimal("20000"),
        updated_at=NOW,
        capabilities=(
            BrokerCapability.MARKET_ORDERS,
            BrokerCapability.LIMIT_ORDERS,
            BrokerCapability.STOP_ORDERS,
            BrokerCapability.SHORT_SELLING,
            BrokerCapability.PAPER_TRADING,
        ),
    )


def market_order_request() -> BrokerOrderRequest:
    return BrokerOrderRequest(
        gateway_order_id="gateway-order-001",
        order_id="order-001",
        client_order_id="client-order-001",
        broker_name="Interactive Brokers",
        account_id="account-001",
        environment=BrokerEnvironment.PAPER,
        symbol="NVDA",
        asset_class=AssetClass.EQUITY,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal("10"),
        submitted_at=NOW,
    )


def limit_order_request() -> BrokerOrderRequest:
    return BrokerOrderRequest(
        gateway_order_id="gateway-order-002",
        order_id="order-002",
        client_order_id="client-order-002",
        broker_name="Interactive Brokers",
        account_id="account-001",
        environment=BrokerEnvironment.PAPER,
        symbol="AAPL",
        asset_class=AssetClass.EQUITY,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal("5"),
        submitted_at=NOW,
        limit_price=Decimal("200"),
    )


def acknowledged_response() -> BrokerOrderResponse:
    return BrokerOrderResponse(
        response_id="response-001",
        gateway_order_id="gateway-order-001",
        order_id="order-001",
        status=BrokerOrderStatus.ACKNOWLEDGED,
        received_at=NOW + timedelta(seconds=1),
        message="Broker acknowledged the order.",
        broker_order_id="broker-order-001",
    )


def partial_execution_report() -> BrokerExecutionReport:
    return BrokerExecutionReport(
        report_id="report-001",
        gateway_order_id="gateway-order-001",
        order_id="order-001",
        broker_order_id="broker-order-001",
        status=BrokerOrderStatus.PARTIALLY_FILLED,
        requested_quantity=Decimal("10"),
        filled_quantity=Decimal("4"),
        remaining_quantity=Decimal("6"),
        commission=Decimal("1.25"),
        occurred_at=NOW + timedelta(seconds=2),
        venue="NASDAQ",
        average_fill_price=Decimal("125"),
    )


def filled_execution_report() -> BrokerExecutionReport:
    return BrokerExecutionReport(
        report_id="report-002",
        gateway_order_id="gateway-order-001",
        order_id="order-001",
        broker_order_id="broker-order-001",
        status=BrokerOrderStatus.FILLED,
        requested_quantity=Decimal("10"),
        filled_quantity=Decimal("10"),
        remaining_quantity=Decimal("0"),
        commission=Decimal("2.50"),
        occurred_at=NOW + timedelta(seconds=3),
        venue="NASDAQ",
        average_fill_price=Decimal("126.20"),
    )


def healthy_report() -> BrokerHealthReport:
    return BrokerHealthReport(
        health_id="health-001",
        broker_name="Interactive Brokers",
        environment=BrokerEnvironment.PAPER,
        connection_state=BrokerConnectionState.CONNECTED,
        status=BrokerStatus.COMPLETED,
        decision=BrokerDecision.APPROVE,
        checked_at=NOW,
        latency_ms=25,
        account_accessible=True,
        order_submission_available=True,
        message="Broker connection is healthy.",
    )


def test_paper_account() -> None:
    value = paper_account()

    assert value.account_id == "account-001"
    assert value.environment is BrokerEnvironment.PAPER
    assert value.is_connected is True
    assert value.available_equity == Decimal("100000")


def test_account_text_is_normalized() -> None:
    value = BrokerAccount(
        account_id="  account-001  ",
        broker_name="  Interactive Brokers  ",
        environment=BrokerEnvironment.PAPER,
        connection_state=BrokerConnectionState.CONNECTED,
        currency="  usd  ",
        cash_balance=Decimal("1000"),
        settled_cash=Decimal("900"),
        buying_power=Decimal("1500"),
        equity=Decimal("1200"),
        margin_used=Decimal("200"),
        updated_at=NOW,
        capabilities=(BrokerCapability.PAPER_TRADING,),
        metadata=[("  source  ", "  broker  ")],
        warnings=["  Account warning.  "],
    )

    assert value.account_id == "account-001"
    assert value.broker_name == "Interactive Brokers"
    assert value.currency == "USD"
    assert value.metadata == (("source", "broker"),)
    assert value.warnings == ("Account warning.",)


@pytest.mark.parametrize(
    "field_name",
    [
        "cash_balance",
        "settled_cash",
        "buying_power",
        "equity",
        "margin_used",
    ],
)
def test_account_financial_fields_require_decimal(
    field_name: str,
) -> None:
    arguments = {
        "account_id": "account-001",
        "broker_name": "Broker",
        "environment": BrokerEnvironment.PAPER,
        "connection_state": BrokerConnectionState.CONNECTED,
        "currency": "USD",
        "cash_balance": Decimal("1000"),
        "settled_cash": Decimal("900"),
        "buying_power": Decimal("1500"),
        "equity": Decimal("1200"),
        "margin_used": Decimal("200"),
        "updated_at": NOW,
        "capabilities": (BrokerCapability.PAPER_TRADING,),
    }
    arguments[field_name] = 100

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a Decimal",
    ):
        BrokerAccount(**arguments)


def test_settled_cash_cannot_exceed_balance() -> None:
    with pytest.raises(
        ValueError,
        match="settled_cash must not exceed cash_balance",
    ):
        BrokerAccount(
            account_id="account-001",
            broker_name="Broker",
            environment=BrokerEnvironment.PAPER,
            connection_state=BrokerConnectionState.CONNECTED,
            currency="USD",
            cash_balance=Decimal("1000"),
            settled_cash=Decimal("1001"),
            buying_power=Decimal("1000"),
            equity=Decimal("1000"),
            margin_used=Decimal("0"),
            updated_at=NOW,
            capabilities=(BrokerCapability.PAPER_TRADING,),
        )


def test_margin_used_cannot_exceed_equity() -> None:
    with pytest.raises(
        ValueError,
        match="margin_used must not exceed equity",
    ):
        BrokerAccount(
            account_id="account-001",
            broker_name="Broker",
            environment=BrokerEnvironment.PAPER,
            connection_state=BrokerConnectionState.CONNECTED,
            currency="USD",
            cash_balance=Decimal("1000"),
            settled_cash=Decimal("1000"),
            buying_power=Decimal("1000"),
            equity=Decimal("500"),
            margin_used=Decimal("501"),
            updated_at=NOW,
            capabilities=(BrokerCapability.PAPER_TRADING,),
        )


def test_capabilities_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="capabilities must be unique",
    ):
        BrokerAccount(
            account_id="account-001",
            broker_name="Broker",
            environment=BrokerEnvironment.PAPER,
            connection_state=BrokerConnectionState.CONNECTED,
            currency="USD",
            cash_balance=Decimal("1000"),
            settled_cash=Decimal("1000"),
            buying_power=Decimal("1000"),
            equity=Decimal("1000"),
            margin_used=Decimal("0"),
            updated_at=NOW,
            capabilities=(
                BrokerCapability.PAPER_TRADING,
                BrokerCapability.PAPER_TRADING,
            ),
        )


def test_paper_account_rejects_live_capability() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "paper accounts must not advertise "
            "LIVE_TRADING capability"
        ),
    ):
        BrokerAccount(
            account_id="account-001",
            broker_name="Broker",
            environment=BrokerEnvironment.PAPER,
            connection_state=BrokerConnectionState.CONNECTED,
            currency="USD",
            cash_balance=Decimal("1000"),
            settled_cash=Decimal("1000"),
            buying_power=Decimal("1000"),
            equity=Decimal("1000"),
            margin_used=Decimal("0"),
            updated_at=NOW,
            capabilities=(BrokerCapability.LIVE_TRADING,),
        )


def test_live_account_rejects_paper_capability() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "live accounts must not advertise "
            "PAPER_TRADING capability"
        ),
    ):
        BrokerAccount(
            account_id="account-001",
            broker_name="Broker",
            environment=BrokerEnvironment.LIVE,
            connection_state=BrokerConnectionState.CONNECTED,
            currency="USD",
            cash_balance=Decimal("1000"),
            settled_cash=Decimal("1000"),
            buying_power=Decimal("1000"),
            equity=Decimal("1000"),
            margin_used=Decimal("0"),
            updated_at=NOW,
            capabilities=(BrokerCapability.PAPER_TRADING,),
        )


def test_market_broker_order_request() -> None:
    value = market_order_request()

    assert value.symbol == "NVDA"
    assert value.order_type is OrderType.MARKET
    assert value.quantity == Decimal("10")
    assert value.limit_price is None


def test_limit_broker_order_request() -> None:
    value = limit_order_request()

    assert value.symbol == "AAPL"
    assert value.order_type is OrderType.LIMIT
    assert value.limit_price == Decimal("200")


def test_broker_order_text_is_normalized() -> None:
    value = BrokerOrderRequest(
        gateway_order_id="  gateway-order-001  ",
        order_id="  order-001  ",
        client_order_id="  client-order-001  ",
        broker_name="  Interactive Brokers  ",
        account_id="  account-001  ",
        environment=BrokerEnvironment.PAPER,
        symbol="  nvda  ",
        asset_class=AssetClass.EQUITY,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal("10"),
        submitted_at=NOW,
    )

    assert value.gateway_order_id == "gateway-order-001"
    assert value.order_id == "order-001"
    assert value.symbol == "NVDA"


@pytest.mark.parametrize(
    "quantity",
    [
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_broker_order_quantity_must_be_positive(
    quantity: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="quantity must be greater than zero",
    ):
        BrokerOrderRequest(
            gateway_order_id="gateway-order-001",
            order_id="order-001",
            client_order_id="client-order-001",
            broker_name="Broker",
            account_id="account-001",
            environment=BrokerEnvironment.PAPER,
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            quantity=quantity,
            submitted_at=NOW,
        )


def test_limit_order_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="limit orders must include limit_price",
    ):
        BrokerOrderRequest(
            gateway_order_id="gateway-order-001",
            order_id="order-001",
            client_order_id="client-order-001",
            broker_name="Broker",
            account_id="account-001",
            environment=BrokerEnvironment.PAPER,
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.DAY,
            quantity=Decimal("10"),
            submitted_at=NOW,
        )


def test_stop_order_requires_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="stop orders must include stop_price",
    ):
        BrokerOrderRequest(
            gateway_order_id="gateway-order-001",
            order_id="order-001",
            client_order_id="client-order-001",
            broker_name="Broker",
            account_id="account-001",
            environment=BrokerEnvironment.PAPER,
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            time_in_force=TimeInForce.DAY,
            quantity=Decimal("10"),
            submitted_at=NOW,
        )


def test_stop_limit_requires_both_prices() -> None:
    with pytest.raises(
        ValueError,
        match="stop-limit orders must include limit_price",
    ):
        BrokerOrderRequest(
            gateway_order_id="gateway-order-001",
            order_id="order-001",
            client_order_id="client-order-001",
            broker_name="Broker",
            account_id="account-001",
            environment=BrokerEnvironment.PAPER,
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LIMIT,
            time_in_force=TimeInForce.DAY,
            quantity=Decimal("10"),
            submitted_at=NOW,
            stop_price=Decimal("110"),
        )


def test_extended_hours_rejects_market_order() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "extended-hours orders must not use "
            "MARKET order type"
        ),
    ):
        BrokerOrderRequest(
            gateway_order_id="gateway-order-001",
            order_id="order-001",
            client_order_id="client-order-001",
            broker_name="Broker",
            account_id="account-001",
            environment=BrokerEnvironment.PAPER,
            symbol="NVDA",
            asset_class=AssetClass.EQUITY,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            quantity=Decimal("10"),
            submitted_at=NOW,
            allow_extended_hours=True,
        )


def test_acknowledged_response() -> None:
    value = acknowledged_response()

    assert value.status is BrokerOrderStatus.ACKNOWLEDGED
    assert value.broker_order_id == "broker-order-001"
    assert value.is_terminal is False


def test_response_text_is_normalized() -> None:
    value = BrokerOrderResponse(
        response_id="  response-001  ",
        gateway_order_id="  gateway-order-001  ",
        order_id="  order-001  ",
        status=BrokerOrderStatus.SUBMITTED,
        received_at=NOW,
        message="  Order submitted.  ",
    )

    assert value.response_id == "response-001"
    assert value.gateway_order_id == "gateway-order-001"
    assert value.message == "Order submitted."


def test_acknowledged_response_requires_broker_id() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "broker-managed responses must include "
            "broker_order_id"
        ),
    ):
        BrokerOrderResponse(
            response_id="response-001",
            gateway_order_id="gateway-order-001",
            order_id="order-001",
            status=BrokerOrderStatus.ACKNOWLEDGED,
            received_at=NOW,
            message="Acknowledged.",
        )


def test_rejected_response_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "rejected and failed responses must "
            "include an error"
        ),
    ):
        BrokerOrderResponse(
            response_id="response-001",
            gateway_order_id="gateway-order-001",
            order_id="order-001",
            status=BrokerOrderStatus.REJECTED,
            received_at=NOW,
            message="Rejected.",
        )


def test_successful_response_rejects_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only rejected or failed responses may "
            "include an error"
        ),
    ):
        BrokerOrderResponse(
            response_id="response-001",
            gateway_order_id="gateway-order-001",
            order_id="order-001",
            status=BrokerOrderStatus.SUBMITTED,
            received_at=NOW,
            message="Submitted.",
            error="Unexpected error.",
        )


def test_partial_execution_report() -> None:
    value = partial_execution_report()

    assert value.status is BrokerOrderStatus.PARTIALLY_FILLED
    assert value.filled_quantity == Decimal("4")
    assert value.remaining_quantity == Decimal("6")
    assert value.average_fill_price == Decimal("125")
    assert value.is_terminal is False


def test_filled_execution_report() -> None:
    value = filled_execution_report()

    assert value.status is BrokerOrderStatus.FILLED
    assert value.filled_quantity == Decimal("10")
    assert value.remaining_quantity == Decimal("0")
    assert value.is_terminal is True


def test_execution_quantities_must_reconcile() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "filled_quantity plus remaining_quantity "
            "must equal requested_quantity"
        ),
    ):
        BrokerExecutionReport(
            report_id="report-001",
            gateway_order_id="gateway-order-001",
            order_id="order-001",
            broker_order_id="broker-order-001",
            status=BrokerOrderStatus.ACKNOWLEDGED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("9"),
            commission=Decimal("0"),
            occurred_at=NOW,
            venue="NASDAQ",
        )


def test_unfilled_report_rejects_average_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "unfilled reports must not include "
            "average_fill_price"
        ),
    ):
        BrokerExecutionReport(
            report_id="report-001",
            gateway_order_id="gateway-order-001",
            order_id="order-001",
            broker_order_id="broker-order-001",
            status=BrokerOrderStatus.ACKNOWLEDGED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("10"),
            commission=Decimal("0"),
            occurred_at=NOW,
            venue="NASDAQ",
            average_fill_price=Decimal("125"),
        )


def test_filled_report_requires_average_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "filled reports must include "
            "average_fill_price"
        ),
    ):
        BrokerExecutionReport(
            report_id="report-001",
            gateway_order_id="gateway-order-001",
            order_id="order-001",
            broker_order_id="broker-order-001",
            status=BrokerOrderStatus.PARTIALLY_FILLED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("4"),
            remaining_quantity=Decimal("6"),
            commission=Decimal("1"),
            occurred_at=NOW,
            venue="NASDAQ",
        )


def test_partial_status_requires_partial_quantity() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "partially filled reports require a "
            "partial filled quantity"
        ),
    ):
        BrokerExecutionReport(
            report_id="report-001",
            gateway_order_id="gateway-order-001",
            order_id="order-001",
            broker_order_id="broker-order-001",
            status=BrokerOrderStatus.PARTIALLY_FILLED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("10"),
            remaining_quantity=Decimal("0"),
            commission=Decimal("1"),
            occurred_at=NOW,
            venue="NASDAQ",
            average_fill_price=Decimal("125"),
        )


def test_filled_status_requires_full_quantity() -> None:
    with pytest.raises(
        ValueError,
        match="filled reports require the full quantity",
    ):
        BrokerExecutionReport(
            report_id="report-001",
            gateway_order_id="gateway-order-001",
            order_id="order-001",
            broker_order_id="broker-order-001",
            status=BrokerOrderStatus.FILLED,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("4"),
            remaining_quantity=Decimal("6"),
            commission=Decimal("1"),
            occurred_at=NOW,
            venue="NASDAQ",
            average_fill_price=Decimal("125"),
        )


def test_healthy_broker_report() -> None:
    value = healthy_report()

    assert value.status is BrokerStatus.COMPLETED
    assert value.decision is BrokerDecision.APPROVE
    assert value.account_accessible is True
    assert value.order_submission_available is True


def test_health_latency_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="latency_ms must not be negative",
    ):
        BrokerHealthReport(
            health_id="health-001",
            broker_name="Broker",
            environment=BrokerEnvironment.PAPER,
            connection_state=BrokerConnectionState.CONNECTED,
            status=BrokerStatus.COMPLETED,
            decision=BrokerDecision.APPROVE,
            checked_at=NOW,
            latency_ms=-1,
            account_accessible=True,
            order_submission_available=True,
            message="Healthy.",
        )


def test_disconnected_broker_cannot_submit_orders() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "order submission requires a connected broker"
        ),
    ):
        BrokerHealthReport(
            health_id="health-001",
            broker_name="Broker",
            environment=BrokerEnvironment.PAPER,
            connection_state=BrokerConnectionState.DISCONNECTED,
            status=BrokerStatus.COMPLETED,
            decision=BrokerDecision.APPROVE,
            checked_at=NOW,
            latency_ms=0,
            account_accessible=True,
            order_submission_available=True,
            message="Invalid health state.",
        )


def test_submission_requires_account_access() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "order submission requires account access"
        ),
    ):
        BrokerHealthReport(
            health_id="health-001",
            broker_name="Broker",
            environment=BrokerEnvironment.PAPER,
            connection_state=BrokerConnectionState.CONNECTED,
            status=BrokerStatus.COMPLETED,
            decision=BrokerDecision.APPROVE,
            checked_at=NOW,
            latency_ms=10,
            account_accessible=False,
            order_submission_available=True,
            message="Invalid health state.",
        )


def test_failed_health_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed health reports must include an error"
        ),
    ):
        BrokerHealthReport(
            health_id="health-001",
            broker_name="Broker",
            environment=BrokerEnvironment.PAPER,
            connection_state=BrokerConnectionState.FAILED,
            status=BrokerStatus.FAILED,
            decision=BrokerDecision.REJECT,
            checked_at=NOW,
            latency_ms=0,
            account_accessible=False,
            order_submission_available=False,
            message="Broker health check failed.",
        )


def test_approve_requires_submission_availability() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "approve decisions require order submission "
            "availability"
        ),
    ):
        BrokerHealthReport(
            health_id="health-001",
            broker_name="Broker",
            environment=BrokerEnvironment.PAPER,
            connection_state=BrokerConnectionState.CONNECTED,
            status=BrokerStatus.COMPLETED,
            decision=BrokerDecision.APPROVE,
            checked_at=NOW,
            latency_ms=10,
            account_accessible=True,
            order_submission_available=False,
            message="Unavailable.",
        )


def test_reject_requires_submission_unavailable() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "reject decisions require order submission "
            "to be unavailable"
        ),
    ):
        BrokerHealthReport(
            health_id="health-001",
            broker_name="Broker",
            environment=BrokerEnvironment.PAPER,
            connection_state=BrokerConnectionState.CONNECTED,
            status=BrokerStatus.COMPLETED,
            decision=BrokerDecision.REJECT,
            checked_at=NOW,
            latency_ms=10,
            account_accessible=True,
            order_submission_available=True,
            message="Invalid rejection.",
        )


def test_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="updated_at must be timezone-aware",
    ):
        BrokerAccount(
            account_id="account-001",
            broker_name="Broker",
            environment=BrokerEnvironment.PAPER,
            connection_state=BrokerConnectionState.CONNECTED,
            currency="USD",
            cash_balance=Decimal("1000"),
            settled_cash=Decimal("1000"),
            buying_power=Decimal("1000"),
            equity=Decimal("1000"),
            margin_used=Decimal("0"),
            updated_at=datetime(2026, 8, 4, 20, 0),
            capabilities=(BrokerCapability.PAPER_TRADING,),
        )


def test_models_are_immutable() -> None:
    value = paper_account()

    with pytest.raises(FrozenInstanceError):
        value.cash_balance = Decimal("200000")