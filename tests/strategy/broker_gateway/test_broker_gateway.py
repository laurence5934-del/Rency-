from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.broker_gateway import (
    BrokerAccount,
    BrokerCapability,
    BrokerConnectionState,
    BrokerDecision,
    BrokerEnvironment,
    BrokerOrderRequest,
    BrokerOrderResponse,
    BrokerOrderStatus,
    BrokerStatus,
    EnterpriseBrokerGateway,
)
from app.strategy.order_manager import (
    OrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)
from app.strategy.portfolio_manager import AssetClass


NOW = datetime(
    2026,
    8,
    4,
    21,
    0,
    tzinfo=timezone.utc,
)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


class RecordingSubmitter:
    def __init__(self) -> None:
        self.requests: list[BrokerOrderRequest] = []

    def __call__(
        self,
        request: BrokerOrderRequest,
    ) -> BrokerOrderResponse:
        self.requests.append(request)

        return BrokerOrderResponse(
            response_id="response-from-broker",
            gateway_order_id=request.gateway_order_id,
            order_id=request.order_id,
            status=BrokerOrderStatus.ACKNOWLEDGED,
            received_at=request.submitted_at,
            message="Broker acknowledged the order.",
            broker_order_id=(
                f"broker-{request.gateway_order_id}"
            ),
        )


def engine(
    current_time: datetime = NOW,
) -> EnterpriseBrokerGateway:
    return EnterpriseBrokerGateway(
        clock=FixedClock(current_time)
    )


def paper_account(
    *,
    account_id: str = "account-paper-001",
    broker_name: str = "Interactive Brokers",
    connection_state: BrokerConnectionState = (
        BrokerConnectionState.CONNECTED
    ),
    updated_at: datetime = NOW,
    capabilities: tuple[
        BrokerCapability,
        ...,
    ] | None = None,
) -> BrokerAccount:
    return BrokerAccount(
        account_id=account_id,
        broker_name=broker_name,
        environment=BrokerEnvironment.PAPER,
        connection_state=connection_state,
        currency="USD",
        cash_balance=Decimal("100000"),
        settled_cash=Decimal("90000"),
        buying_power=Decimal("180000"),
        equity=Decimal("120000"),
        margin_used=Decimal("20000"),
        updated_at=updated_at,
        capabilities=(
            capabilities
            if capabilities is not None
            else (
                BrokerCapability.MARKET_ORDERS,
                BrokerCapability.LIMIT_ORDERS,
                BrokerCapability.STOP_ORDERS,
                BrokerCapability.STOP_LIMIT_ORDERS,
                BrokerCapability.SHORT_SELLING,
                BrokerCapability.EXTENDED_HOURS,
                BrokerCapability.PAPER_TRADING,
            )
        ),
    )


def live_account(
    *,
    account_id: str = "account-live-001",
    broker_name: str = "Interactive Brokers Live",
) -> BrokerAccount:
    return BrokerAccount(
        account_id=account_id,
        broker_name=broker_name,
        environment=BrokerEnvironment.LIVE,
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
            BrokerCapability.LIVE_TRADING,
        ),
    )


def market_order(
    *,
    order_id: str = "order-001",
    client_order_id: str = "client-order-001",
    symbol: str = "NVDA",
    side: OrderSide = OrderSide.BUY,
) -> OrderRequest:
    return OrderRequest(
        order_id=order_id,
        client_order_id=client_order_id,
        portfolio_id="portfolio-001",
        symbol=symbol,
        asset_class=AssetClass.EQUITY,
        side=side,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal("10"),
        created_at=NOW,
        strategy_id="momentum-001",
    )


def limit_order(
    *,
    order_id: str = "order-002",
    client_order_id: str = "client-order-002",
) -> OrderRequest:
    return OrderRequest(
        order_id=order_id,
        client_order_id=client_order_id,
        portfolio_id="portfolio-001",
        symbol="AAPL",
        asset_class=AssetClass.EQUITY,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal("5"),
        created_at=NOW,
        limit_price=Decimal("200"),
    )


def registered_gateway(
    *,
    account: BrokerAccount | None = None,
    submitter: RecordingSubmitter | None = None,
) -> tuple[
    EnterpriseBrokerGateway,
    BrokerAccount,
    RecordingSubmitter,
]:
    value = engine()
    account_value = account or paper_account()
    submitter_value = submitter or RecordingSubmitter()

    value.register_broker(
        account=account_value,
        submitter=submitter_value,
    )

    return value, account_value, submitter_value


def test_register_broker() -> None:
    value = engine()
    account = paper_account()
    submitter = RecordingSubmitter()

    result = value.register_broker(
        account=account,
        submitter=submitter,
    )

    assert result == account
    assert value.account_ids == (
        "account-paper-001",
    )


def test_register_requires_account_model() -> None:
    with pytest.raises(
        TypeError,
        match="account must be a BrokerAccount",
    ):
        engine().register_broker(
            account=object(),
            submitter=RecordingSubmitter(),
        )


def test_register_requires_callable_submitter() -> None:
    with pytest.raises(
        TypeError,
        match="submitter must be callable",
    ):
        engine().register_broker(
            account=paper_account(),
            submitter=object(),
        )


def test_duplicate_account_id_is_rejected() -> None:
    value, account, _ = registered_gateway()

    with pytest.raises(
        ValueError,
        match="account_id is already registered",
    ):
        value.register_broker(
            account=account,
            submitter=RecordingSubmitter(),
        )


def test_duplicate_broker_name_is_rejected() -> None:
    value, _, _ = registered_gateway()

    duplicate_name = paper_account(
        account_id="account-paper-002",
    )

    with pytest.raises(
        ValueError,
        match="broker_name is already registered",
    ):
        value.register_broker(
            account=duplicate_name,
            submitter=RecordingSubmitter(),
        )


def test_register_multiple_brokers() -> None:
    value, _, _ = registered_gateway()

    second = paper_account(
        account_id="account-paper-002",
        broker_name="Paper Broker Two",
    )

    value.register_broker(
        account=second,
        submitter=RecordingSubmitter(),
    )

    assert value.account_ids == (
        "account-paper-001",
        "account-paper-002",
    )


def test_get_account() -> None:
    value, account, _ = registered_gateway()

    result = value.get_account(
        "account-paper-001"
    )

    assert result == account


def test_get_account_normalizes_identifier() -> None:
    value, _, _ = registered_gateway()

    result = value.get_account(
        "  account-paper-001  "
    )

    assert result.account_id == (
        "account-paper-001"
    )


def test_get_unknown_account_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="broker account not found",
    ):
        engine().get_account("missing")


def test_unregister_broker() -> None:
    value, account, _ = registered_gateway()

    removed = value.unregister_broker(
        account.account_id
    )

    assert removed == account
    assert value.account_ids == ()


def test_unregister_unknown_broker_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="broker account not found",
    ):
        engine().unregister_broker("missing")


def test_update_account() -> None:
    value, account, _ = registered_gateway()

    updated = replace(
        account,
        cash_balance=Decimal("110000"),
        settled_cash=Decimal("95000"),
        buying_power=Decimal("190000"),
        equity=Decimal("130000"),
        updated_at=NOW + timedelta(minutes=1),
    )

    result = value.update_account(updated)

    assert result.cash_balance == Decimal("110000")
    assert value.get_account(
        account.account_id
    ) == updated


def test_update_requires_account_model() -> None:
    with pytest.raises(
        TypeError,
        match="account must be a BrokerAccount",
    ):
        engine().update_account(object())


def test_update_rejects_broker_name_change() -> None:
    value, account, _ = registered_gateway()

    changed = replace(
        account,
        broker_name="Different Broker",
        updated_at=NOW + timedelta(minutes=1),
    )

    with pytest.raises(
        ValueError,
        match="broker_name must not change",
    ):
        value.update_account(changed)


def test_update_rejects_environment_change() -> None:
    value, account, _ = registered_gateway()

    changed = replace(
        account,
        environment=BrokerEnvironment.LIVE,
        capabilities=(
            BrokerCapability.MARKET_ORDERS,
            BrokerCapability.LIVE_TRADING,
        ),
        updated_at=NOW + timedelta(minutes=1),
    )

    with pytest.raises(
        ValueError,
        match="broker environment must not change",
    ):
        value.update_account(changed)


def test_update_rejects_stale_snapshot() -> None:
    value, account, _ = registered_gateway()

    stale = replace(
        account,
        updated_at=NOW - timedelta(seconds=1),
    )

    with pytest.raises(
        ValueError,
        match=(
            "account update must not be older "
            "than the current snapshot"
        ),
    ):
        value.update_account(stale)


def test_paper_account_does_not_need_live_authorization() -> None:
    value, account, _ = registered_gateway()

    assert value.is_live_authorized(
        account.account_id
    ) is False


def test_authorize_live_trading() -> None:
    account = live_account()
    value, _, _ = registered_gateway(
        account=account
    )

    result = value.authorize_live_trading(
        account.account_id,
        confirmation="AUTHORIZE LIVE TRADING",
    )

    assert result == account
    assert value.is_live_authorized(
        account.account_id
    ) is True


def test_live_authorization_normalizes_confirmation() -> None:
    account = live_account()
    value, _, _ = registered_gateway(
        account=account
    )

    value.authorize_live_trading(
        account.account_id,
        confirmation="  authorize live trading  ",
    )

    assert value.is_live_authorized(
        account.account_id
    ) is True


def test_paper_account_rejects_live_authorization() -> None:
    value, account, _ = registered_gateway()

    with pytest.raises(
        ValueError,
        match=(
            "only live accounts require "
            "live-trading authorization"
        ),
    ):
        value.authorize_live_trading(
            account.account_id,
            confirmation="AUTHORIZE LIVE TRADING",
        )


def test_invalid_live_confirmation_is_rejected() -> None:
    account = live_account()
    value, _, _ = registered_gateway(
        account=account
    )

    with pytest.raises(
        ValueError,
        match="invalid live-trading confirmation",
    ):
        value.authorize_live_trading(
            account.account_id,
            confirmation="yes",
        )


def test_revoke_live_trading() -> None:
    account = live_account()
    value, _, _ = registered_gateway(
        account=account
    )

    value.authorize_live_trading(
        account.account_id,
        confirmation="AUTHORIZE LIVE TRADING",
    )

    value.revoke_live_trading(
        account.account_id
    )

    assert value.is_live_authorized(
        account.account_id
    ) is False


def test_translate_market_order() -> None:
    value, account, _ = registered_gateway()

    translated = value.translate_order(
        market_order(),
        account_id=account.account_id,
    )

    assert translated.gateway_order_id == (
        "gateway-order-000001"
    )
    assert translated.order_id == "order-001"
    assert translated.symbol == "NVDA"
    assert translated.account_id == account.account_id
    assert translated.environment is (
        BrokerEnvironment.PAPER
    )
    assert translated.order_type is OrderType.MARKET


def test_translate_limit_order() -> None:
    value, account, _ = registered_gateway()

    translated = value.translate_order(
        limit_order(),
        account_id=account.account_id,
    )

    assert translated.order_type is OrderType.LIMIT
    assert translated.limit_price == Decimal("200")


def test_translation_records_portfolio_metadata() -> None:
    value, account, _ = registered_gateway()

    translated = value.translate_order(
        market_order(),
        account_id=account.account_id,
    )

    assert translated.metadata == (
        ("portfolio_id", "portfolio-001"),
        ("strategy_id", "momentum-001"),
    )


def test_translate_requires_order_request() -> None:
    value, account, _ = registered_gateway()

    with pytest.raises(
        TypeError,
        match="request must be an OrderRequest",
    ):
        value.translate_order(
            object(),
            account_id=account.account_id,
        )


def test_extended_hours_flag_must_be_bool() -> None:
    value, account, _ = registered_gateway()

    with pytest.raises(
        TypeError,
        match=(
            "allow_extended_hours must be a bool"
        ),
    ):
        value.translate_order(
            limit_order(),
            account_id=account.account_id,
            allow_extended_hours="yes",
        )


def test_translation_is_idempotent() -> None:
    value, account, _ = registered_gateway()
    order = market_order()

    first = value.translate_order(
        order,
        account_id=account.account_id,
    )

    second = value.translate_order(
        order,
        account_id=account.account_id,
    )

    assert first == second
    assert value.gateway_order_ids == (
        "gateway-order-000001",
    )


def test_gateway_ids_are_deterministic() -> None:
    value, account, _ = registered_gateway()

    first = value.translate_order(
        market_order(),
        account_id=account.account_id,
    )

    second = value.translate_order(
        limit_order(),
        account_id=account.account_id,
    )

    assert first.gateway_order_id == (
        "gateway-order-000001"
    )
    assert second.gateway_order_id == (
        "gateway-order-000002"
    )


def test_same_order_id_with_different_client_id_is_rejected() -> None:
    value, account, _ = registered_gateway()

    value.translate_order(
        market_order(),
        account_id=account.account_id,
    )

    conflicting = market_order(
        client_order_id="different-client"
    )

    with pytest.raises(
        ValueError,
        match=(
            "order_id is already associated "
            "with another client_order_id"
        ),
    ):
        value.translate_order(
            conflicting,
            account_id=account.account_id,
        )


def test_same_client_id_with_different_order_id_is_rejected() -> None:
    value, account, _ = registered_gateway()

    value.translate_order(
        market_order(),
        account_id=account.account_id,
    )

    conflicting = market_order(
        order_id="different-order"
    )

    with pytest.raises(
        ValueError,
        match=(
            "client_order_id is already associated "
            "with another order_id"
        ),
    ):
        value.translate_order(
            conflicting,
            account_id=account.account_id,
        )


def test_disconnected_account_cannot_translate() -> None:
    account = paper_account(
        connection_state=(
            BrokerConnectionState.DISCONNECTED
        )
    )
    value, _, _ = registered_gateway(
        account=account
    )

    with pytest.raises(
        RuntimeError,
        match="broker account must be connected",
    ):
        value.translate_order(
            market_order(),
            account_id=account.account_id,
        )


def test_unsupported_order_type_is_rejected() -> None:
    account = paper_account(
        capabilities=(
            BrokerCapability.MARKET_ORDERS,
            BrokerCapability.PAPER_TRADING,
        )
    )
    value, _, _ = registered_gateway(
        account=account
    )

    with pytest.raises(
        ValueError,
        match=(
            "broker account does not support LIMIT orders"
        ),
    ):
        value.translate_order(
            limit_order(),
            account_id=account.account_id,
        )


def test_short_selling_requires_capability() -> None:
    account = paper_account(
        capabilities=(
            BrokerCapability.MARKET_ORDERS,
            BrokerCapability.PAPER_TRADING,
        )
    )
    value, _, _ = registered_gateway(
        account=account
    )

    short_order = market_order(
        side=OrderSide.SELL_SHORT
    )

    with pytest.raises(
        ValueError,
        match=(
            "broker account does not support short selling"
        ),
    ):
        value.translate_order(
            short_order,
            account_id=account.account_id,
        )


def test_extended_hours_requires_capability() -> None:
    account = paper_account(
        capabilities=(
            BrokerCapability.LIMIT_ORDERS,
            BrokerCapability.PAPER_TRADING,
        )
    )
    value, _, _ = registered_gateway(
        account=account
    )

    with pytest.raises(
        ValueError,
        match=(
            "broker account does not support "
            "extended-hours trading"
        ),
    ):
        value.translate_order(
            limit_order(),
            account_id=account.account_id,
            allow_extended_hours=True,
        )


def test_live_order_requires_explicit_authorization() -> None:
    account = live_account()
    value, _, _ = registered_gateway(
        account=account
    )

    with pytest.raises(
        PermissionError,
        match=(
            "live trading is not explicitly authorized"
        ),
    ):
        value.translate_order(
            market_order(),
            account_id=account.account_id,
        )


def test_authorized_live_order_can_translate() -> None:
    account = live_account()
    value, _, _ = registered_gateway(
        account=account
    )

    value.authorize_live_trading(
        account.account_id,
        confirmation="AUTHORIZE LIVE TRADING",
    )

    translated = value.translate_order(
        market_order(),
        account_id=account.account_id,
    )

    assert translated.environment is (
        BrokerEnvironment.LIVE
    )


def test_submit_order() -> None:
    value, account, submitter = registered_gateway()

    response = value.submit_order(
        market_order(),
        account_id=account.account_id,
    )

    assert response.status is (
        BrokerOrderStatus.ACKNOWLEDGED
    )
    assert response.broker_order_id == (
        "broker-gateway-order-000001"
    )
    assert len(submitter.requests) == 1
    assert len(value.response_history) == 1


def test_submit_is_idempotent() -> None:
    value, account, submitter = registered_gateway()
    order = market_order()

    first = value.submit_order(
        order,
        account_id=account.account_id,
    )

    second = value.submit_order(
        order,
        account_id=account.account_id,
    )

    assert first == second
    assert len(submitter.requests) == 1
    assert len(value.response_history) == 1


def test_submitter_must_return_broker_response() -> None:
    account = paper_account()
    value = engine()

    value.register_broker(
        account=account,
        submitter=lambda request: object(),
    )

    with pytest.raises(
        TypeError,
        match=(
            "submitter must return a "
            "BrokerOrderResponse"
        ),
    ):
        value.submit_order(
            market_order(),
            account_id=account.account_id,
        )


def test_get_gateway_order() -> None:
    value, account, _ = registered_gateway()

    translated = value.translate_order(
        market_order(),
        account_id=account.account_id,
    )

    result = value.get_gateway_order(
        translated.gateway_order_id
    )

    assert result == translated


def test_gateway_order_for_order() -> None:
    value, account, _ = registered_gateway()

    translated = value.translate_order(
        market_order(),
        account_id=account.account_id,
    )

    result = value.gateway_order_for_order(
        "order-001"
    )

    assert result == translated


def test_get_unknown_gateway_order_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="gateway order not found",
    ):
        engine().get_gateway_order("missing")


def test_get_response() -> None:
    value, account, _ = registered_gateway()

    response = value.submit_order(
        market_order(),
        account_id=account.account_id,
    )

    result = value.get_response(
        response.gateway_order_id
    )

    assert result == response


def test_get_response_before_submission_is_rejected() -> None:
    value, account, _ = registered_gateway()

    translated = value.translate_order(
        market_order(),
        account_id=account.account_id,
    )

    with pytest.raises(
        KeyError,
        match=(
            "gateway order has no broker response"
        ),
    ):
        value.get_response(
            translated.gateway_order_id
        )