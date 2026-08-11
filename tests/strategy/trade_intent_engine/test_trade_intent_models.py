from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest
from app.strategy.trade_intent_engine import (
    TradeIntent,
    TradeIntentAction,
    TradeIntentDecision,
    TradeIntentReport,
    TradeIntentRequest,
    TradeIntentResult,
    TradeIntentStatus,
    TradeOrderType,
    TradeSide,
    TradeTimeInForce,
)


NOW = datetime(
    2026,
    8,
    11,
    4,
    0,
    tzinfo=timezone.utc,
)


def trade_intent_request(
    *,
    request_id: str = "request-001",
    correlation_id: str = "correlation-001",
    strategy_id: str = "strategy-001",
    portfolio_id: str = "portfolio-001",
    allocation_id: str = "allocation-001",
    signal_id: str = "signal-001",
    symbol: str = "NVDA",
    action: TradeIntentAction = TradeIntentAction.OPEN,
    side: TradeSide = TradeSide.BUY,
    order_type: TradeOrderType = TradeOrderType.MARKET,
    time_in_force: TradeTimeInForce = TradeTimeInForce.DAY,
    quantity: int = 10,
    confidence: int = 85,
    created_at: datetime = NOW,
    sequence_number: int = 1,
    requested_by: str = "portfolio-allocation-engine",
    limit_price: float | None = None,
    stop_price: float | None = None,
    is_replay: bool = False,
) -> TradeIntentRequest:
    return TradeIntentRequest(
        request_id=request_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        allocation_id=allocation_id,
        signal_id=signal_id,
        symbol=symbol,
        action=action,
        side=side,
        order_type=order_type,
        time_in_force=time_in_force,
        quantity=quantity,
        confidence=confidence,
        created_at=created_at,
        sequence_number=sequence_number,
        requested_by=requested_by,
        limit_price=limit_price,
        stop_price=stop_price,
        is_replay=is_replay,
        metadata=(
            ("environment", "paper"),
        ),
    )


def test_trade_intent_request() -> None:
    value = trade_intent_request()

    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.allocation_id == "allocation-001"
    assert value.signal_id == "signal-001"
    assert value.symbol == "NVDA"
    assert value.action is TradeIntentAction.OPEN
    assert value.side is TradeSide.BUY
    assert value.order_type is TradeOrderType.MARKET
    assert value.time_in_force is TradeTimeInForce.DAY
    assert value.quantity == 10
    assert value.confidence == 85
    assert value.created_at == NOW
    assert value.sequence_number == 1
    assert value.requested_by == "portfolio-allocation-engine"
    assert value.limit_price is None
    assert value.stop_price is None
    assert value.is_replay is False
    assert value.metadata == (
        ("environment", "paper"),
    )


def test_trade_intent_request_text_is_normalized() -> None:
    value = TradeIntentRequest(
        request_id="  request-001  ",
        correlation_id="  correlation-001  ",
        strategy_id="  strategy-001  ",
        portfolio_id="  portfolio-001  ",
        allocation_id="  allocation-001  ",
        signal_id="  signal-001  ",
        symbol="  nvda  ",
        action=TradeIntentAction.OPEN,
        side=TradeSide.BUY,
        order_type=TradeOrderType.MARKET,
        time_in_force=TradeTimeInForce.DAY,
        quantity=10,
        confidence=85,
        created_at=NOW,
        sequence_number=1,
        requested_by="  portfolio-allocation-engine  ",
        metadata=[
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.allocation_id == "allocation-001"
    assert value.signal_id == "signal-001"
    assert value.symbol == "NVDA"
    assert value.requested_by == "portfolio-allocation-engine"
    assert value.metadata == (
        ("environment", "paper"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "allocation_id",
        "signal_id",
        "symbol",
        "requested_by",
    ],
)
def test_trade_intent_request_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "allocation_id": "allocation-001",
        "signal_id": "signal-001",
        "symbol": "NVDA",
        "action": TradeIntentAction.OPEN,
        "side": TradeSide.BUY,
        "order_type": TradeOrderType.MARKET,
        "time_in_force": TradeTimeInForce.DAY,
        "quantity": 10,
        "confidence": 85,
        "created_at": NOW,
        "sequence_number": 1,
        "requested_by": "portfolio-allocation-engine",
    }

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        TradeIntentRequest(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "allocation_id",
        "signal_id",
        "symbol",
        "requested_by",
    ],
)
def test_trade_intent_request_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "allocation_id": "allocation-001",
        "signal_id": "signal-001",
        "symbol": "NVDA",
        "action": TradeIntentAction.OPEN,
        "side": TradeSide.BUY,
        "order_type": TradeOrderType.MARKET,
        "time_in_force": TradeTimeInForce.DAY,
        "quantity": 10,
        "confidence": 85,
        "created_at": NOW,
        "sequence_number": 1,
        "requested_by": "portfolio-allocation-engine",
    }

    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        TradeIntentRequest(**arguments)


def test_trade_intent_request_requires_action_enum() -> None:
    with pytest.raises(
        TypeError,
        match="action must be a TradeIntentAction",
    ):
        trade_intent_request(
            action="OPEN"
        )


def test_trade_intent_request_requires_side_enum() -> None:
    with pytest.raises(
        TypeError,
        match="side must be a TradeSide",
    ):
        trade_intent_request(
            side="BUY"
        )


def test_trade_intent_request_requires_order_type_enum() -> None:
    with pytest.raises(
        TypeError,
        match="order_type must be a TradeOrderType",
    ):
        trade_intent_request(
            order_type="MARKET"
        )


def test_trade_intent_request_requires_time_in_force_enum() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "time_in_force must be a TradeTimeInForce"
        ),
    ):
        trade_intent_request(
            time_in_force="DAY"
        )


def test_trade_intent_request_quantity_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="quantity must be an integer",
    ):
        trade_intent_request(
            quantity="10"
        )


def test_trade_intent_request_quantity_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="quantity must be an integer",
    ):
        trade_intent_request(
            quantity=True
        )


@pytest.mark.parametrize(
    "quantity",
    [
        0,
        -1,
    ],
)
def test_trade_intent_request_quantity_must_be_positive(
    quantity: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="quantity must be positive",
    ):
        trade_intent_request(
            quantity=quantity
        )


@pytest.mark.parametrize(
    "confidence",
    [
        -1,
        101,
    ],
)
def test_trade_intent_request_confidence_bounds(
    confidence: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="confidence must be between 0 and 100",
    ):
        trade_intent_request(
            confidence=confidence
        )


def test_trade_intent_request_confidence_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        trade_intent_request(
            confidence="85"
        )


def test_trade_intent_request_confidence_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        trade_intent_request(
            confidence=True
        )


@pytest.mark.parametrize(
    "confidence",
    [
        0,
        100,
    ],
)
def test_trade_intent_request_confidence_boundaries_allowed(
    confidence: int,
) -> None:
    value = trade_intent_request(
        confidence=confidence
    )

    assert value.confidence == confidence


def test_trade_intent_request_created_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="created_at must be a datetime",
    ):
        TradeIntentRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            allocation_id="allocation-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=TradeIntentAction.OPEN,
            side=TradeSide.BUY,
            order_type=TradeOrderType.MARKET,
            time_in_force=TradeTimeInForce.DAY,
            quantity=10,
            confidence=85,
            created_at="2026-08-11",
            sequence_number=1,
            requested_by="portfolio-allocation-engine",
        )


def test_trade_intent_request_created_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="created_at must be timezone-aware",
    ):
        trade_intent_request(
            created_at=datetime(
                2026,
                8,
                11,
                4,
                0,
            )
        )


def test_trade_intent_request_sequence_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="sequence_number must be an integer",
    ):
        trade_intent_request(
            sequence_number="1"
        )


def test_trade_intent_request_sequence_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="sequence_number must be an integer",
    ):
        trade_intent_request(
            sequence_number=True
        )


def test_trade_intent_request_sequence_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="sequence_number must not be negative",
    ):
        trade_intent_request(
            sequence_number=-1
        )


def test_zero_sequence_number_is_allowed() -> None:
    value = trade_intent_request(
        sequence_number=0
    )

    assert value.sequence_number == 0


def test_trade_intent_request_replay_requires_bool() -> None:
    with pytest.raises(
        TypeError,
        match="is_replay must be a bool",
    ):
        trade_intent_request(
            is_replay="yes"
        )


def test_replay_trade_intent_request() -> None:
    value = trade_intent_request(
        is_replay=True
    )

    assert value.is_replay is True


def test_hold_trade_intent_requires_none_side() -> None:
    with pytest.raises(
        ValueError,
        match="HOLD trade intents require NONE side",
    ):
        trade_intent_request(
            action=TradeIntentAction.HOLD,
            side=TradeSide.BUY,
        )


def test_hold_trade_intent_with_none_side() -> None:
    value = trade_intent_request(
        action=TradeIntentAction.HOLD,
        side=TradeSide.NONE,
    )

    assert value.is_actionable is False


def test_actionable_trade_intent_rejects_none_side() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "actionable trade intents require a trade side"
        ),
    ):
        trade_intent_request(
            action=TradeIntentAction.OPEN,
            side=TradeSide.NONE,
        )


def test_market_order_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "MARKET orders must not include "
            "limit_price or stop_price"
        ),
    ):
        trade_intent_request(
            limit_price=100.0
        )


def test_market_order_rejects_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "MARKET orders must not include "
            "limit_price or stop_price"
        ),
    ):
        trade_intent_request(
            stop_price=95.0
        )


def test_limit_order_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="LIMIT orders require limit_price",
    ):
        trade_intent_request(
            order_type=TradeOrderType.LIMIT,
        )


def test_limit_order_rejects_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="LIMIT orders must not include stop_price",
    ):
        trade_intent_request(
            order_type=TradeOrderType.LIMIT,
            limit_price=100.0,
            stop_price=95.0,
        )


def test_limit_order() -> None:
    value = trade_intent_request(
        order_type=TradeOrderType.LIMIT,
        limit_price=100.0,
    )

    assert value.limit_price == 100.0
    assert value.stop_price is None
    assert value.is_limit_order is True
    assert value.is_market_order is False


def test_stop_order_requires_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="STOP orders require stop_price",
    ):
        trade_intent_request(
            order_type=TradeOrderType.STOP,
        )


def test_stop_order_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="STOP orders must not include limit_price",
    ):
        trade_intent_request(
            order_type=TradeOrderType.STOP,
            stop_price=95.0,
            limit_price=100.0,
        )


def test_stop_order() -> None:
    value = trade_intent_request(
        order_type=TradeOrderType.STOP,
        stop_price=95.0,
    )

    assert value.stop_price == 95.0
    assert value.limit_price is None
    assert value.is_stop_order is True


def test_stop_limit_order_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "STOP_LIMIT orders require limit_price"
        ),
    ):
        trade_intent_request(
            order_type=TradeOrderType.STOP_LIMIT,
            stop_price=95.0,
        )


def test_stop_limit_order_requires_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="STOP_LIMIT orders require stop_price",
    ):
        trade_intent_request(
            order_type=TradeOrderType.STOP_LIMIT,
            limit_price=100.0,
        )


def test_stop_limit_order() -> None:
    value = trade_intent_request(
        order_type=TradeOrderType.STOP_LIMIT,
        limit_price=100.0,
        stop_price=95.0,
    )

    assert value.limit_price == 100.0
    assert value.stop_price == 95.0
    assert value.is_stop_order is True


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("limit_price", 0),
        ("limit_price", -1),
        ("stop_price", 0),
        ("stop_price", -1),
    ],
)
def test_trade_intent_request_prices_must_be_positive(
    field_name: str,
    value: int,
) -> None:
    kwargs = {
        "order_type": TradeOrderType.STOP_LIMIT,
        "limit_price": 100.0,
        "stop_price": 95.0,
    }

    kwargs[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be positive",
    ):
        trade_intent_request(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("limit_price", "100"),
        ("limit_price", True),
        ("stop_price", "95"),
        ("stop_price", True),
    ],
)
def test_trade_intent_request_prices_require_numbers(
    field_name: str,
    value: object,
) -> None:
    kwargs = {
        "order_type": TradeOrderType.STOP_LIMIT,
        "limit_price": 100.0,
        "stop_price": 95.0,
    }

    kwargs[field_name] = value

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a number",
    ):
        trade_intent_request(**kwargs)


def test_trade_intent_request_is_actionable() -> None:
    value = trade_intent_request()

    assert value.is_actionable is True


def test_market_order_property() -> None:
    value = trade_intent_request()

    assert value.is_market_order is True
    assert value.is_limit_order is False
    assert value.is_stop_order is False


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (79, False),
        (80, True),
        (100, True),
    ],
)
def test_trade_intent_request_high_confidence_property(
    confidence: int,
    expected: bool,
) -> None:
    value = trade_intent_request(
        confidence=confidence
    )

    assert value.is_high_confidence is expected


def test_trade_intent_request_metadata_is_normalized() -> None:
    value = TradeIntentRequest(
        request_id="request-001",
        correlation_id="correlation-001",
        strategy_id="strategy-001",
        portfolio_id="portfolio-001",
        allocation_id="allocation-001",
        signal_id="signal-001",
        symbol="NVDA",
        action=TradeIntentAction.OPEN,
        side=TradeSide.BUY,
        order_type=TradeOrderType.MARKET,
        time_in_force=TradeTimeInForce.DAY,
        quantity=10,
        confidence=85,
        created_at=NOW,
        sequence_number=1,
        requested_by="portfolio-allocation-engine",
        metadata=[
            ("  environment  ", "  paper  "),
            ("  source  ", "  allocation  "),
        ],
    )

    assert value.metadata == (
        ("environment", "paper"),
        ("source", "allocation"),
    )


def test_trade_intent_request_metadata_keys_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        TradeIntentRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            allocation_id="allocation-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=TradeIntentAction.OPEN,
            side=TradeSide.BUY,
            order_type=TradeOrderType.MARKET,
            time_in_force=TradeTimeInForce.DAY,
            quantity=10,
            confidence=85,
            created_at=NOW,
            sequence_number=1,
            requested_by="portfolio-allocation-engine",
            metadata=(
                ("source", "one"),
                ("source", "two"),
            ),
        )


def test_trade_intent_request_metadata_items_must_be_pairs() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        TradeIntentRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            allocation_id="allocation-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=TradeIntentAction.OPEN,
            side=TradeSide.BUY,
            order_type=TradeOrderType.MARKET,
            time_in_force=TradeTimeInForce.DAY,
            quantity=10,
            confidence=85,
            created_at=NOW,
            sequence_number=1,
            requested_by="portfolio-allocation-engine",
            metadata=(
                ("source",),
            ),
        )


def test_trade_intent_request_metadata_keys_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        TradeIntentRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            allocation_id="allocation-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=TradeIntentAction.OPEN,
            side=TradeSide.BUY,
            order_type=TradeOrderType.MARKET,
            time_in_force=TradeTimeInForce.DAY,
            quantity=10,
            confidence=85,
            created_at=NOW,
            sequence_number=1,
            requested_by="portfolio-allocation-engine",
            metadata=(
                (123, "allocation"),
            ),
        )


def test_trade_intent_request_metadata_values_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        TradeIntentRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            allocation_id="allocation-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=TradeIntentAction.OPEN,
            side=TradeSide.BUY,
            order_type=TradeOrderType.MARKET,
            time_in_force=TradeTimeInForce.DAY,
            quantity=10,
            confidence=85,
            created_at=NOW,
            sequence_number=1,
            requested_by="portfolio-allocation-engine",
            metadata=(
                ("source", 123),
            ),
        )


def test_trade_intent_request_is_immutable() -> None:
    value = trade_intent_request()

    with pytest.raises(FrozenInstanceError):
        value.request_id = "changed"

def trade_intent(
    *,
    intent_id: str = "intent-001",
    request_id: str = "request-001",
    correlation_id: str = "correlation-001",
    strategy_id: str = "strategy-001",
    portfolio_id: str = "portfolio-001",
    allocation_id: str = "allocation-001",
    signal_id: str = "signal-001",
    symbol: str = "NVDA",
    action: TradeIntentAction = TradeIntentAction.OPEN,
    side: TradeSide = TradeSide.BUY,
    order_type: TradeOrderType = TradeOrderType.MARKET,
    time_in_force: TradeTimeInForce = TradeTimeInForce.DAY,
    quantity: int = 10,
    confidence: int = 85,
    generated_at: datetime = NOW,
    expires_at: datetime | None = None,
    rationale: str = "Approved allocation supports trade construction.",
    limit_price: float | None = None,
    stop_price: float | None = None,
    warnings: tuple[str, ...] = (),
) -> TradeIntent:
    return TradeIntent(
        intent_id=intent_id,
        request_id=request_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        allocation_id=allocation_id,
        signal_id=signal_id,
        symbol=symbol,
        action=action,
        side=side,
        order_type=order_type,
        time_in_force=time_in_force,
        quantity=quantity,
        confidence=confidence,
        generated_at=generated_at,
        expires_at=expires_at,
        rationale=rationale,
        limit_price=limit_price,
        stop_price=stop_price,
        warnings=warnings,
        metadata=(
            ("environment", "paper"),
        ),
    )


def test_trade_intent() -> None:
    value = trade_intent()

    assert value.intent_id == "intent-001"
    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.allocation_id == "allocation-001"
    assert value.signal_id == "signal-001"
    assert value.symbol == "NVDA"
    assert value.action is TradeIntentAction.OPEN
    assert value.side is TradeSide.BUY
    assert value.order_type is TradeOrderType.MARKET
    assert value.time_in_force is TradeTimeInForce.DAY
    assert value.quantity == 10
    assert value.confidence == 85
    assert value.generated_at == NOW
    assert value.expires_at is None
    assert value.rationale == (
        "Approved allocation supports trade construction."
    )
    assert value.is_actionable is True
    assert value.is_market_order is True
    assert value.is_high_confidence is True
    assert value.has_expiration is False


def test_trade_intent_text_is_normalized() -> None:
    value = TradeIntent(
        intent_id="  intent-001  ",
        request_id="  request-001  ",
        correlation_id="  correlation-001  ",
        strategy_id="  strategy-001  ",
        portfolio_id="  portfolio-001  ",
        allocation_id="  allocation-001  ",
        signal_id="  signal-001  ",
        symbol="  nvda  ",
        action=TradeIntentAction.OPEN,
        side=TradeSide.BUY,
        order_type=TradeOrderType.MARKET,
        time_in_force=TradeTimeInForce.DAY,
        quantity=10,
        confidence=85,
        generated_at=NOW,
        expires_at=None,
        rationale="  Approved allocation supports trade construction.  ",
        metadata=[
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.intent_id == "intent-001"
    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.allocation_id == "allocation-001"
    assert value.signal_id == "signal-001"
    assert value.symbol == "NVDA"
    assert value.rationale == (
        "Approved allocation supports trade construction."
    )
    assert value.metadata == (
        ("environment", "paper"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "intent_id",
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "allocation_id",
        "signal_id",
        "symbol",
        "rationale",
    ],
)
def test_trade_intent_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "intent_id": "intent-001",
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "allocation_id": "allocation-001",
        "signal_id": "signal-001",
        "symbol": "NVDA",
        "action": TradeIntentAction.OPEN,
        "side": TradeSide.BUY,
        "order_type": TradeOrderType.MARKET,
        "time_in_force": TradeTimeInForce.DAY,
        "quantity": 10,
        "confidence": 85,
        "generated_at": NOW,
        "expires_at": None,
        "rationale": "Approved allocation supports trade construction.",
    }

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        TradeIntent(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "intent_id",
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "allocation_id",
        "signal_id",
        "symbol",
        "rationale",
    ],
)
def test_trade_intent_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "intent_id": "intent-001",
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "allocation_id": "allocation-001",
        "signal_id": "signal-001",
        "symbol": "NVDA",
        "action": TradeIntentAction.OPEN,
        "side": TradeSide.BUY,
        "order_type": TradeOrderType.MARKET,
        "time_in_force": TradeTimeInForce.DAY,
        "quantity": 10,
        "confidence": 85,
        "generated_at": NOW,
        "expires_at": None,
        "rationale": "Approved allocation supports trade construction.",
    }

    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        TradeIntent(**arguments)


def test_trade_intent_requires_action_enum() -> None:
    with pytest.raises(
        TypeError,
        match="action must be a TradeIntentAction",
    ):
        trade_intent(
            action="OPEN"
        )


def test_trade_intent_requires_side_enum() -> None:
    with pytest.raises(
        TypeError,
        match="side must be a TradeSide",
    ):
        trade_intent(
            side="BUY"
        )


def test_trade_intent_requires_order_type_enum() -> None:
    with pytest.raises(
        TypeError,
        match="order_type must be a TradeOrderType",
    ):
        trade_intent(
            order_type="MARKET"
        )


def test_trade_intent_requires_time_in_force_enum() -> None:
    with pytest.raises(
        TypeError,
        match="time_in_force must be a TradeTimeInForce",
    ):
        trade_intent(
            time_in_force="DAY"
        )


def test_trade_intent_quantity_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="quantity must be an integer",
    ):
        trade_intent(
            quantity="10"
        )


def test_trade_intent_quantity_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="quantity must be an integer",
    ):
        trade_intent(
            quantity=True
        )


@pytest.mark.parametrize(
    "quantity",
    [
        0,
        -1,
    ],
)
def test_trade_intent_quantity_must_be_positive(
    quantity: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="quantity must be positive",
    ):
        trade_intent(
            quantity=quantity
        )


@pytest.mark.parametrize(
    "confidence",
    [
        -1,
        101,
    ],
)
def test_trade_intent_confidence_bounds(
    confidence: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="confidence must be between 0 and 100",
    ):
        trade_intent(
            confidence=confidence
        )


def test_trade_intent_confidence_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        trade_intent(
            confidence="85"
        )


def test_trade_intent_confidence_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        trade_intent(
            confidence=True
        )


@pytest.mark.parametrize(
    "confidence",
    [
        0,
        100,
    ],
)
def test_trade_intent_confidence_boundaries_allowed(
    confidence: int,
) -> None:
    value = trade_intent(
        confidence=confidence
    )

    assert value.confidence == confidence


def test_trade_intent_generated_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="generated_at must be a datetime",
    ):
        TradeIntent(
            intent_id="intent-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            allocation_id="allocation-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=TradeIntentAction.OPEN,
            side=TradeSide.BUY,
            order_type=TradeOrderType.MARKET,
            time_in_force=TradeTimeInForce.DAY,
            quantity=10,
            confidence=85,
            generated_at="2026-08-11",
            expires_at=None,
            rationale="Approved allocation supports trade construction.",
        )


def test_trade_intent_generated_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="generated_at must be timezone-aware",
    ):
        trade_intent(
            generated_at=datetime(
                2026,
                8,
                11,
                4,
                0,
            )
        )


def test_trade_intent_expires_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="expires_at must be a datetime",
    ):
        trade_intent(
            expires_at="2026-08-11"
        )


def test_trade_intent_expires_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="expires_at must be timezone-aware",
    ):
        trade_intent(
            expires_at=datetime(
                2026,
                8,
                11,
                4,
                5,
            )
        )


def test_trade_intent_expiration_must_follow_generation() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "expires_at must not be earlier "
            "than generated_at"
        ),
    ):
        trade_intent(
            expires_at=(
                NOW - timedelta(seconds=1)
            )
        )


def test_trade_intent_expiration_may_equal_generation() -> None:
    value = trade_intent(
        expires_at=NOW
    )

    assert value.expires_at == NOW
    assert value.has_expiration is True


def test_trade_intent_has_expiration() -> None:
    value = trade_intent(
        expires_at=(
            NOW + timedelta(minutes=5)
        )
    )

    assert value.has_expiration is True


def test_trade_intent_without_expiration_never_expires() -> None:
    value = trade_intent()

    assert value.is_expired_at(
        NOW + timedelta(days=1)
    ) is False


def test_trade_intent_not_expired_at_boundary() -> None:
    expires_at = (
        NOW + timedelta(minutes=5)
    )

    value = trade_intent(
        expires_at=expires_at
    )

    assert value.is_expired_at(
        expires_at
    ) is False


def test_trade_intent_expires_after_boundary() -> None:
    expires_at = (
        NOW + timedelta(minutes=5)
    )

    value = trade_intent(
        expires_at=expires_at
    )

    assert value.is_expired_at(
        expires_at + timedelta(microseconds=1)
    ) is True


def test_trade_intent_expiry_check_requires_datetime() -> None:
    value = trade_intent(
        expires_at=(
            NOW + timedelta(minutes=5)
        )
    )

    with pytest.raises(
        TypeError,
        match="value must be a datetime",
    ):
        value.is_expired_at(
            "2026-08-11"
        )


def test_trade_intent_expiry_check_requires_aware_datetime() -> None:
    value = trade_intent(
        expires_at=(
            NOW + timedelta(minutes=5)
        )
    )

    with pytest.raises(
        ValueError,
        match="value must be timezone-aware",
    ):
        value.is_expired_at(
            datetime(
                2026,
                8,
                11,
                4,
                10,
            )
        )


def test_trade_intent_hold_requires_none_side() -> None:
    with pytest.raises(
        ValueError,
        match="HOLD trade intents require NONE side",
    ):
        trade_intent(
            action=TradeIntentAction.HOLD,
            side=TradeSide.BUY,
        )


def test_trade_intent_hold_with_none_side() -> None:
    value = trade_intent(
        action=TradeIntentAction.HOLD,
        side=TradeSide.NONE,
    )

    assert value.is_actionable is False


def test_trade_intent_actionable_rejects_none_side() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "actionable trade intents require a trade side"
        ),
    ):
        trade_intent(
            action=TradeIntentAction.OPEN,
            side=TradeSide.NONE,
        )


def test_trade_intent_market_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "MARKET orders must not include "
            "limit_price or stop_price"
        ),
    ):
        trade_intent(
            limit_price=100.0
        )


def test_trade_intent_market_rejects_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "MARKET orders must not include "
            "limit_price or stop_price"
        ),
    ):
        trade_intent(
            stop_price=95.0
        )


def test_trade_intent_limit_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="LIMIT orders require limit_price",
    ):
        trade_intent(
            order_type=TradeOrderType.LIMIT,
        )


def test_trade_intent_limit_rejects_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="LIMIT orders must not include stop_price",
    ):
        trade_intent(
            order_type=TradeOrderType.LIMIT,
            limit_price=100.0,
            stop_price=95.0,
        )


def test_trade_intent_limit_order() -> None:
    value = trade_intent(
        order_type=TradeOrderType.LIMIT,
        limit_price=100.0,
    )

    assert value.limit_price == 100.0
    assert value.stop_price is None
    assert value.is_limit_order is True
    assert value.is_market_order is False


def test_trade_intent_stop_requires_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="STOP orders require stop_price",
    ):
        trade_intent(
            order_type=TradeOrderType.STOP,
        )


def test_trade_intent_stop_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="STOP orders must not include limit_price",
    ):
        trade_intent(
            order_type=TradeOrderType.STOP,
            stop_price=95.0,
            limit_price=100.0,
        )


def test_trade_intent_stop_order() -> None:
    value = trade_intent(
        order_type=TradeOrderType.STOP,
        stop_price=95.0,
    )

    assert value.stop_price == 95.0
    assert value.limit_price is None
    assert value.is_stop_order is True


def test_trade_intent_stop_limit_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="STOP_LIMIT orders require limit_price",
    ):
        trade_intent(
            order_type=TradeOrderType.STOP_LIMIT,
            stop_price=95.0,
        )


def test_trade_intent_stop_limit_requires_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="STOP_LIMIT orders require stop_price",
    ):
        trade_intent(
            order_type=TradeOrderType.STOP_LIMIT,
            limit_price=100.0,
        )


def test_trade_intent_stop_limit_order() -> None:
    value = trade_intent(
        order_type=TradeOrderType.STOP_LIMIT,
        limit_price=100.0,
        stop_price=95.0,
    )

    assert value.limit_price == 100.0
    assert value.stop_price == 95.0
    assert value.is_stop_order is True


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("limit_price", 0),
        ("limit_price", -1),
        ("stop_price", 0),
        ("stop_price", -1),
    ],
)
def test_trade_intent_prices_must_be_positive(
    field_name: str,
    value: int,
) -> None:
    kwargs = {
        "order_type": TradeOrderType.STOP_LIMIT,
        "limit_price": 100.0,
        "stop_price": 95.0,
    }

    kwargs[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be positive",
    ):
        trade_intent(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("limit_price", "100"),
        ("limit_price", True),
        ("stop_price", "95"),
        ("stop_price", True),
    ],
)
def test_trade_intent_prices_require_numbers(
    field_name: str,
    value: object,
) -> None:
    kwargs = {
        "order_type": TradeOrderType.STOP_LIMIT,
        "limit_price": 100.0,
        "stop_price": 95.0,
    }

    kwargs[field_name] = value

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a number",
    ):
        trade_intent(**kwargs)


def test_trade_intent_is_actionable() -> None:
    value = trade_intent()

    assert value.is_actionable is True


def test_trade_intent_market_order_property() -> None:
    value = trade_intent()

    assert value.is_market_order is True
    assert value.is_limit_order is False
    assert value.is_stop_order is False


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (79, False),
        (80, True),
        (100, True),
    ],
)
def test_trade_intent_high_confidence_property(
    confidence: int,
    expected: bool,
) -> None:
    value = trade_intent(
        confidence=confidence
    )

    assert value.is_high_confidence is expected


def test_trade_intent_warnings_are_normalized() -> None:
    value = trade_intent(
        warnings=(
            " spread elevated ",
            "spread elevated",
            " liquidity constrained ",
        )
    )

    assert value.warnings == (
        "spread elevated",
        "liquidity constrained",
    )


def test_trade_intent_warnings_reject_empty_values() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        trade_intent(
            warnings=(
                "valid",
                "   ",
            )
        )


def test_trade_intent_warnings_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        trade_intent(
            warnings=(
                "valid",
                123,
            )
        )


def test_trade_intent_metadata_is_normalized() -> None:
    value = TradeIntent(
        intent_id="intent-001",
        request_id="request-001",
        correlation_id="correlation-001",
        strategy_id="strategy-001",
        portfolio_id="portfolio-001",
        allocation_id="allocation-001",
        signal_id="signal-001",
        symbol="NVDA",
        action=TradeIntentAction.OPEN,
        side=TradeSide.BUY,
        order_type=TradeOrderType.MARKET,
        time_in_force=TradeTimeInForce.DAY,
        quantity=10,
        confidence=85,
        generated_at=NOW,
        expires_at=None,
        rationale="Approved allocation supports trade construction.",
        metadata=[
            ("  source  ", "  allocation  "),
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.metadata == (
        ("source", "allocation"),
        ("environment", "paper"),
    )


def test_trade_intent_metadata_keys_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        TradeIntent(
            intent_id="intent-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            allocation_id="allocation-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=TradeIntentAction.OPEN,
            side=TradeSide.BUY,
            order_type=TradeOrderType.MARKET,
            time_in_force=TradeTimeInForce.DAY,
            quantity=10,
            confidence=85,
            generated_at=NOW,
            expires_at=None,
            rationale="Approved allocation supports trade construction.",
            metadata=(
                ("source", "one"),
                ("source", "two"),
            ),
        )


def test_trade_intent_metadata_items_must_be_pairs() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        TradeIntent(
            intent_id="intent-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            allocation_id="allocation-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=TradeIntentAction.OPEN,
            side=TradeSide.BUY,
            order_type=TradeOrderType.MARKET,
            time_in_force=TradeTimeInForce.DAY,
            quantity=10,
            confidence=85,
            generated_at=NOW,
            expires_at=None,
            rationale="Approved allocation supports trade construction.",
            metadata=(
                ("source",),
            ),
        )


def test_trade_intent_metadata_keys_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        TradeIntent(
            intent_id="intent-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            allocation_id="allocation-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=TradeIntentAction.OPEN,
            side=TradeSide.BUY,
            order_type=TradeOrderType.MARKET,
            time_in_force=TradeTimeInForce.DAY,
            quantity=10,
            confidence=85,
            generated_at=NOW,
            expires_at=None,
            rationale="Approved allocation supports trade construction.",
            metadata=(
                (123, "allocation"),
            ),
        )


def test_trade_intent_metadata_values_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        TradeIntent(
            intent_id="intent-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            allocation_id="allocation-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=TradeIntentAction.OPEN,
            side=TradeSide.BUY,
            order_type=TradeOrderType.MARKET,
            time_in_force=TradeTimeInForce.DAY,
            quantity=10,
            confidence=85,
            generated_at=NOW,
            expires_at=None,
            rationale="Approved allocation supports trade construction.",
            metadata=(
                ("source", 123),
            ),
        )


def test_trade_intent_is_immutable() -> None:
    value = trade_intent()

    with pytest.raises(FrozenInstanceError):
        value.intent_id = "changed"

def trade_intent_result(
    *,
    request_id: str = "request-001",
    correlation_id: str = "correlation-001",
    status: TradeIntentStatus = TradeIntentStatus.ACTIVE,
    decision: TradeIntentDecision = TradeIntentDecision.PROCEED,
    started_at: datetime = NOW,
    updated_at: datetime = NOW,
    completed_at: datetime | None = None,
    intent: TradeIntent | None = None,
    warnings: tuple[str, ...] = (),
    error: str | None = None,
) -> TradeIntentResult:
    return TradeIntentResult(
        request_id=request_id,
        correlation_id=correlation_id,
        status=status,
        decision=decision,
        started_at=started_at,
        updated_at=updated_at,
        completed_at=completed_at,
        intent=intent,
        warnings=warnings,
        error=error,
        metadata=(
            ("environment", "paper"),
        ),
    )


def approved_trade_intent_result() -> TradeIntentResult:
    return trade_intent_result(
        status=TradeIntentStatus.APPROVED,
        decision=TradeIntentDecision.APPROVE,
        completed_at=NOW,
        intent=trade_intent(),
    )


def failed_trade_intent_result(
    *,
    retryable: bool = True,
) -> TradeIntentResult:
    return trade_intent_result(
        status=TradeIntentStatus.FAILED,
        decision=(
            TradeIntentDecision.RETRY
            if retryable
            else TradeIntentDecision.NO_ACTION
        ),
        completed_at=NOW,
        error="Trade intent evaluation failed.",
    )


def test_active_trade_intent_result() -> None:
    value = trade_intent_result()

    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.status is TradeIntentStatus.ACTIVE
    assert value.decision is TradeIntentDecision.PROCEED
    assert value.started_at == NOW
    assert value.updated_at == NOW
    assert value.completed_at is None
    assert value.intent is None
    assert value.is_terminal is False
    assert value.is_successful is False
    assert value.has_intent is False


def test_pending_trade_intent_result() -> None:
    value = trade_intent_result(
        status=TradeIntentStatus.PENDING,
        decision=TradeIntentDecision.NO_ACTION,
    )

    assert value.status is TradeIntentStatus.PENDING
    assert value.is_terminal is False


def test_approved_trade_intent_result() -> None:
    value = approved_trade_intent_result()

    assert value.status is TradeIntentStatus.APPROVED
    assert value.decision is TradeIntentDecision.APPROVE
    assert value.is_terminal is True
    assert value.is_successful is True
    assert value.has_intent is True


def test_rejected_trade_intent_result() -> None:
    value = trade_intent_result(
        status=TradeIntentStatus.REJECTED,
        decision=TradeIntentDecision.REJECT,
        completed_at=NOW,
    )

    assert value.status is TradeIntentStatus.REJECTED
    assert value.is_terminal is True
    assert value.is_successful is False


def test_cancelled_trade_intent_result() -> None:
    value = trade_intent_result(
        status=TradeIntentStatus.CANCELLED,
        decision=TradeIntentDecision.CANCEL,
        completed_at=NOW,
    )

    assert value.status is TradeIntentStatus.CANCELLED
    assert value.is_terminal is True


def test_failed_trade_intent_result_retryable() -> None:
    value = failed_trade_intent_result(
        retryable=True
    )

    assert value.status is TradeIntentStatus.FAILED
    assert value.decision is TradeIntentDecision.RETRY
    assert value.error == "Trade intent evaluation failed."
    assert value.is_terminal is True


def test_failed_trade_intent_result_non_retryable() -> None:
    value = failed_trade_intent_result(
        retryable=False
    )

    assert value.decision is TradeIntentDecision.NO_ACTION


def test_trade_intent_result_text_is_normalized() -> None:
    value = TradeIntentResult(
        request_id="  request-001  ",
        correlation_id="  correlation-001  ",
        status=TradeIntentStatus.ACTIVE,
        decision=TradeIntentDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW,
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        ),
        metadata=[
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.warnings == (
        "warning one",
        "warning two",
    )
    assert value.metadata == (
        ("environment", "paper"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
    ],
)
def test_trade_intent_result_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "status": TradeIntentStatus.ACTIVE,
        "decision": TradeIntentDecision.PROCEED,
        "started_at": NOW,
        "updated_at": NOW,
    }

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        TradeIntentResult(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
    ],
)
def test_trade_intent_result_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "status": TradeIntentStatus.ACTIVE,
        "decision": TradeIntentDecision.PROCEED,
        "started_at": NOW,
        "updated_at": NOW,
    }

    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        TradeIntentResult(**arguments)


def test_trade_intent_result_requires_status_enum() -> None:
    with pytest.raises(
        TypeError,
        match="status must be a TradeIntentStatus",
    ):
        trade_intent_result(
            status="ACTIVE"
        )


def test_trade_intent_result_requires_decision_enum() -> None:
    with pytest.raises(
        TypeError,
        match="decision must be a TradeIntentDecision",
    ):
        trade_intent_result(
            decision="PROCEED"
        )


def test_trade_intent_result_started_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="started_at must be a datetime",
    ):
        TradeIntentResult(
            request_id="request-001",
            correlation_id="correlation-001",
            status=TradeIntentStatus.ACTIVE,
            decision=TradeIntentDecision.PROCEED,
            started_at="2026-08-11",
            updated_at=NOW,
        )


def test_trade_intent_result_started_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="started_at must be timezone-aware",
    ):
        trade_intent_result(
            started_at=datetime(
                2026,
                8,
                11,
                4,
                0,
            )
        )


def test_trade_intent_result_updated_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="updated_at must be a datetime",
    ):
        TradeIntentResult(
            request_id="request-001",
            correlation_id="correlation-001",
            status=TradeIntentStatus.ACTIVE,
            decision=TradeIntentDecision.PROCEED,
            started_at=NOW,
            updated_at="2026-08-11",
        )


def test_trade_intent_result_updated_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="updated_at must be timezone-aware",
    ):
        trade_intent_result(
            updated_at=datetime(
                2026,
                8,
                11,
                4,
                0,
            )
        )


def test_trade_intent_result_updated_at_must_follow_start() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "updated_at must not be earlier "
            "than started_at"
        ),
    ):
        trade_intent_result(
            updated_at=(
                NOW - timedelta(seconds=1)
            ),
        )


def test_trade_intent_result_completed_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="completed_at must be a datetime",
    ):
        TradeIntentResult(
            request_id="request-001",
            correlation_id="correlation-001",
            status=TradeIntentStatus.REJECTED,
            decision=TradeIntentDecision.REJECT,
            started_at=NOW,
            updated_at=NOW,
            completed_at="2026-08-11",
        )


def test_trade_intent_result_completed_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="completed_at must be timezone-aware",
    ):
        trade_intent_result(
            status=TradeIntentStatus.REJECTED,
            decision=TradeIntentDecision.REJECT,
            completed_at=datetime(
                2026,
                8,
                11,
                4,
                0,
            ),
        )


def test_trade_intent_result_completed_at_must_follow_update() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed_at must not be earlier "
            "than updated_at"
        ),
    ):
        trade_intent_result(
            status=TradeIntentStatus.REJECTED,
            decision=TradeIntentDecision.REJECT,
            completed_at=(
                NOW - timedelta(seconds=1)
            ),
        )


def test_trade_intent_result_requires_intent_model() -> None:
    with pytest.raises(
        TypeError,
        match="intent must be a TradeIntent or None",
    ):
        trade_intent_result(
            intent=object()
        )


def test_intent_request_id_must_match_result() -> None:
    value = trade_intent(
        request_id="different-request"
    )

    with pytest.raises(
        ValueError,
        match=(
            "intent request_id must match "
            "result request_id"
        ),
    ):
        trade_intent_result(
            intent=value
        )


def test_intent_correlation_id_must_match_result() -> None:
    value = trade_intent(
        correlation_id="different-correlation"
    )

    with pytest.raises(
        ValueError,
        match=(
            "intent correlation_id must match "
            "result correlation_id"
        ),
    ):
        trade_intent_result(
            intent=value
        )


def test_intent_generation_must_not_precede_result_start() -> None:
    value = trade_intent(
        generated_at=(
            NOW - timedelta(seconds=1)
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "intent generated_at must not be "
            "earlier than result started_at"
        ),
    ):
        trade_intent_result(
            intent=value
        )


def test_intent_generation_must_not_follow_result_update() -> None:
    value = trade_intent(
        generated_at=(
            NOW + timedelta(seconds=1)
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "intent generated_at must not be "
            "later than result updated_at"
        ),
    ):
        trade_intent_result(
            intent=value
        )


@pytest.mark.parametrize(
    "status",
    [
        TradeIntentStatus.APPROVED,
        TradeIntentStatus.REJECTED,
        TradeIntentStatus.CANCELLED,
        TradeIntentStatus.FAILED,
    ],
)
def test_terminal_trade_intent_result_requires_completed_at(
    status: TradeIntentStatus,
) -> None:
    if status is TradeIntentStatus.APPROVED:
        decision = TradeIntentDecision.APPROVE
        intent = trade_intent()
        error = None
    elif status is TradeIntentStatus.REJECTED:
        decision = TradeIntentDecision.REJECT
        intent = None
        error = None
    elif status is TradeIntentStatus.CANCELLED:
        decision = TradeIntentDecision.CANCEL
        intent = None
        error = None
    else:
        decision = TradeIntentDecision.RETRY
        intent = None
        error = "Trade intent evaluation failed."

    with pytest.raises(
        ValueError,
        match=(
            "terminal trade intent results require "
            "completed_at"
        ),
    ):
        trade_intent_result(
            status=status,
            decision=decision,
            intent=intent,
            error=error,
        )


@pytest.mark.parametrize(
    ("status", "decision"),
    [
        (
            TradeIntentStatus.PENDING,
            TradeIntentDecision.NO_ACTION,
        ),
        (
            TradeIntentStatus.ACTIVE,
            TradeIntentDecision.PROCEED,
        ),
    ],
)
def test_non_terminal_trade_intent_result_rejects_completed_at(
    status: TradeIntentStatus,
    decision: TradeIntentDecision,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-terminal trade intent results must not "
            "include completed_at"
        ),
    ):
        trade_intent_result(
            status=status,
            decision=decision,
            completed_at=NOW,
        )


def test_pending_trade_intent_result_requires_no_action() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "pending trade intent results require "
            "NO_ACTION decision"
        ),
    ):
        trade_intent_result(
            status=TradeIntentStatus.PENDING,
            decision=TradeIntentDecision.PROCEED,
        )


def test_pending_trade_intent_result_rejects_intent() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "pending trade intent results must not "
            "include an intent"
        ),
    ):
        trade_intent_result(
            status=TradeIntentStatus.PENDING,
            decision=TradeIntentDecision.NO_ACTION,
            intent=trade_intent(),
        )


def test_active_trade_intent_result_requires_proceed() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "active trade intent results require "
            "PROCEED decision"
        ),
    ):
        trade_intent_result(
            status=TradeIntentStatus.ACTIVE,
            decision=TradeIntentDecision.HOLD,
        )


def test_approved_trade_intent_result_requires_approve() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "approved trade intent results require "
            "APPROVE decision"
        ),
    ):
        trade_intent_result(
            status=TradeIntentStatus.APPROVED,
            decision=TradeIntentDecision.PROCEED,
            completed_at=NOW,
            intent=trade_intent(),
        )


def test_approved_trade_intent_result_requires_intent() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "approved trade intent results require "
            "an intent"
        ),
    ):
        trade_intent_result(
            status=TradeIntentStatus.APPROVED,
            decision=TradeIntentDecision.APPROVE,
            completed_at=NOW,
            intent=None,
        )


def test_rejected_trade_intent_result_requires_reject() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "rejected trade intent results require "
            "REJECT decision"
        ),
    ):
        trade_intent_result(
            status=TradeIntentStatus.REJECTED,
            decision=TradeIntentDecision.NO_ACTION,
            completed_at=NOW,
        )


def test_cancelled_trade_intent_result_requires_cancel() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "cancelled trade intent results require "
            "CANCEL decision"
        ),
    ):
        trade_intent_result(
            status=TradeIntentStatus.CANCELLED,
            decision=TradeIntentDecision.NO_ACTION,
            completed_at=NOW,
        )


@pytest.mark.parametrize(
    "decision",
    [
        TradeIntentDecision.RETRY,
        TradeIntentDecision.NO_ACTION,
    ],
)
def test_failed_trade_intent_result_allows_retry_or_no_action(
    decision: TradeIntentDecision,
) -> None:
    value = trade_intent_result(
        status=TradeIntentStatus.FAILED,
        decision=decision,
        completed_at=NOW,
        error="Trade intent evaluation failed.",
    )

    assert value.decision is decision


def test_failed_trade_intent_result_rejects_success_decision() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed trade intent results require "
            "RETRY or NO_ACTION decision"
        ),
    ):
        trade_intent_result(
            status=TradeIntentStatus.FAILED,
            decision=TradeIntentDecision.APPROVE,
            completed_at=NOW,
            error="Trade intent evaluation failed.",
        )


def test_failed_trade_intent_result_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed trade intent results require "
            "an error"
        ),
    ):
        trade_intent_result(
            status=TradeIntentStatus.FAILED,
            decision=TradeIntentDecision.RETRY,
            completed_at=NOW,
            error=None,
        )


def test_only_failed_trade_intent_result_may_include_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only failed trade intent results may "
            "include an error"
        ),
    ):
        trade_intent_result(
            status=TradeIntentStatus.REJECTED,
            decision=TradeIntentDecision.REJECT,
            completed_at=NOW,
            error="Unexpected error.",
        )


def test_trade_intent_result_error_is_normalized() -> None:
    value = trade_intent_result(
        status=TradeIntentStatus.FAILED,
        decision=TradeIntentDecision.RETRY,
        completed_at=NOW,
        error="  Trade intent evaluation failed.  ",
    )

    assert value.error == "Trade intent evaluation failed."


def test_trade_intent_result_error_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="error must not be empty",
    ):
        trade_intent_result(
            status=TradeIntentStatus.FAILED,
            decision=TradeIntentDecision.RETRY,
            completed_at=NOW,
            error="   ",
        )


def test_trade_intent_result_warnings_are_normalized() -> None:
    value = trade_intent_result(
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        ),
    )

    assert value.warnings == (
        "warning one",
        "warning two",
    )


def test_trade_intent_result_warnings_reject_empty_values() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        trade_intent_result(
            warnings=(
                "valid",
                "   ",
            )
        )


def test_trade_intent_result_warnings_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        trade_intent_result(
            warnings=(
                "valid",
                123,
            )
        )


def test_trade_intent_result_metadata_is_normalized() -> None:
    value = TradeIntentResult(
        request_id="request-001",
        correlation_id="correlation-001",
        status=TradeIntentStatus.ACTIVE,
        decision=TradeIntentDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW,
        metadata=[
            ("  engine  ", "  trade-intent  "),
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.metadata == (
        ("engine", "trade-intent"),
        ("environment", "paper"),
    )


def test_trade_intent_result_metadata_keys_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        TradeIntentResult(
            request_id="request-001",
            correlation_id="correlation-001",
            status=TradeIntentStatus.ACTIVE,
            decision=TradeIntentDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            metadata=(
                ("engine", "one"),
                ("engine", "two"),
            ),
        )


def test_trade_intent_result_is_immutable() -> None:
    value = approved_trade_intent_result()

    with pytest.raises(FrozenInstanceError):
        value.status = TradeIntentStatus.FAILED

def trade_intent_report(
    *,
    report_id: str = "report-001",
    request: TradeIntentRequest | None = None,
    result: TradeIntentResult | None = None,
    reported_at: datetime = NOW,
    message: str = "Trade intent evaluation updated.",
    warnings: tuple[str, ...] = (),
) -> TradeIntentReport:
    return TradeIntentReport(
        report_id=report_id,
        request=request or trade_intent_request(),
        result=result or trade_intent_result(),
        reported_at=reported_at,
        message=message,
        warnings=warnings,
        metadata=(
            ("source", "trade-intent-engine"),
        ),
    )


def test_trade_intent_report() -> None:
    value = trade_intent_report()

    assert value.report_id == "report-001"
    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.allocation_id == "allocation-001"
    assert value.signal_id == "signal-001"
    assert value.symbol == "NVDA"
    assert value.status is TradeIntentStatus.ACTIVE
    assert value.decision is TradeIntentDecision.PROCEED
    assert value.intent is None
    assert value.is_terminal is False
    assert value.reported_at == NOW
    assert value.message == (
        "Trade intent evaluation updated."
    )
    assert value.metadata == (
        ("source", "trade-intent-engine"),
    )


def test_approved_trade_intent_report() -> None:
    value = trade_intent_report(
        result=approved_trade_intent_result(),
    )

    assert value.status is TradeIntentStatus.APPROVED
    assert value.decision is TradeIntentDecision.APPROVE
    assert value.intent is not None
    assert value.is_terminal is True


def test_trade_intent_report_text_is_normalized() -> None:
    value = TradeIntentReport(
        report_id="  report-001  ",
        request=trade_intent_request(),
        result=trade_intent_result(),
        reported_at=NOW,
        message="  Trade intent updated.  ",
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        ),
        metadata=[
            ("  source  ", "  trade-intent-engine  "),
        ],
    )

    assert value.report_id == "report-001"
    assert value.message == "Trade intent updated."
    assert value.warnings == (
        "warning one",
        "warning two",
    )
    assert value.metadata == (
        ("source", "trade-intent-engine"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_trade_intent_report_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "report_id": "report-001",
        "request": trade_intent_request(),
        "result": trade_intent_result(),
        "reported_at": NOW,
        "message": "Trade intent updated.",
    }

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        TradeIntentReport(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_trade_intent_report_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "report_id": "report-001",
        "request": trade_intent_request(),
        "result": trade_intent_result(),
        "reported_at": NOW,
        "message": "Trade intent updated.",
    }

    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        TradeIntentReport(**arguments)


def test_trade_intent_report_requires_request_model() -> None:
    with pytest.raises(
        TypeError,
        match="request must be a TradeIntentRequest",
    ):
        TradeIntentReport(
            report_id="report-001",
            request=object(),
            result=trade_intent_result(),
            reported_at=NOW,
            message="Trade intent updated.",
        )


def test_trade_intent_report_requires_result_model() -> None:
    with pytest.raises(
        TypeError,
        match="result must be a TradeIntentResult",
    ):
        TradeIntentReport(
            report_id="report-001",
            request=trade_intent_request(),
            result=object(),
            reported_at=NOW,
            message="Trade intent updated.",
        )


def test_trade_intent_reported_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="reported_at must be a datetime",
    ):
        TradeIntentReport(
            report_id="report-001",
            request=trade_intent_request(),
            result=trade_intent_result(),
            reported_at="2026-08-11",
            message="Trade intent updated.",
        )


def test_trade_intent_reported_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="reported_at must be timezone-aware",
    ):
        trade_intent_report(
            reported_at=datetime(
                2026,
                8,
                11,
                4,
                0,
            )
        )


def test_trade_intent_report_request_id_must_match_result() -> None:
    result = trade_intent_result(
        request_id="different-request",
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result request_id values "
            "must match"
        ),
    ):
        trade_intent_report(
            result=result,
        )


def test_trade_intent_report_correlation_id_must_match_result() -> None:
    result = trade_intent_result(
        correlation_id="different-correlation",
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result correlation_id values "
            "must match"
        ),
    ):
        trade_intent_report(
            result=result,
        )


def test_trade_intent_report_result_must_not_start_before_request() -> None:
    request = trade_intent_request(
        created_at=NOW,
    )

    result = trade_intent_result(
        started_at=(
            NOW - timedelta(seconds=1)
        ),
        updated_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match=(
            "result started_at must not be earlier "
            "than request created_at"
        ),
    ):
        trade_intent_report(
            request=request,
            result=result,
        )


def test_trade_intent_reported_at_must_follow_result_update() -> None:
    result = trade_intent_result(
        started_at=NOW,
        updated_at=(
            NOW + timedelta(seconds=1)
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier "
            "than result updated_at"
        ),
    ):
        trade_intent_report(
            result=result,
            reported_at=NOW,
        )


def test_trade_intent_reported_at_must_follow_result_completion() -> None:
    intent = trade_intent(
        generated_at=NOW,
    )

    result = trade_intent_result(
        status=TradeIntentStatus.APPROVED,
        decision=TradeIntentDecision.APPROVE,
        started_at=NOW,
        updated_at=NOW,
        completed_at=(
            NOW + timedelta(seconds=1)
        ),
        intent=intent,
    )

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier "
            "than result completed_at"
        ),
    ):
        trade_intent_report(
            result=result,
            reported_at=NOW,
        )


def test_report_intent_strategy_id_must_match_request() -> None:
    intent = trade_intent(
        strategy_id="different-strategy",
    )

    result = trade_intent_result(
        status=TradeIntentStatus.APPROVED,
        decision=TradeIntentDecision.APPROVE,
        completed_at=NOW,
        intent=intent,
    )

    with pytest.raises(
        ValueError,
        match="intent strategy_id must match request",
    ):
        trade_intent_report(
            result=result,
        )


def test_report_intent_portfolio_id_must_match_request() -> None:
    intent = trade_intent(
        portfolio_id="different-portfolio",
    )

    result = trade_intent_result(
        status=TradeIntentStatus.APPROVED,
        decision=TradeIntentDecision.APPROVE,
        completed_at=NOW,
        intent=intent,
    )

    with pytest.raises(
        ValueError,
        match="intent portfolio_id must match request",
    ):
        trade_intent_report(
            result=result,
        )


def test_report_intent_allocation_id_must_match_request() -> None:
    intent = trade_intent(
        allocation_id="different-allocation",
    )

    result = trade_intent_result(
        status=TradeIntentStatus.APPROVED,
        decision=TradeIntentDecision.APPROVE,
        completed_at=NOW,
        intent=intent,
    )

    with pytest.raises(
        ValueError,
        match="intent allocation_id must match request",
    ):
        trade_intent_report(
            result=result,
        )


def test_report_intent_signal_id_must_match_request() -> None:
    intent = trade_intent(
        signal_id="different-signal",
    )

    result = trade_intent_result(
        status=TradeIntentStatus.APPROVED,
        decision=TradeIntentDecision.APPROVE,
        completed_at=NOW,
        intent=intent,
    )

    with pytest.raises(
        ValueError,
        match="intent signal_id must match request",
    ):
        trade_intent_report(
            result=result,
        )


def test_report_intent_symbol_must_match_request() -> None:
    intent = trade_intent(
        symbol="AAPL",
    )

    result = trade_intent_result(
        status=TradeIntentStatus.APPROVED,
        decision=TradeIntentDecision.APPROVE,
        completed_at=NOW,
        intent=intent,
    )

    with pytest.raises(
        ValueError,
        match="intent symbol must match request",
    ):
        trade_intent_report(
            result=result,
        )


def test_report_intent_action_must_match_request() -> None:
    intent = trade_intent(
        action=TradeIntentAction.INCREASE,
    )

    result = trade_intent_result(
        status=TradeIntentStatus.APPROVED,
        decision=TradeIntentDecision.APPROVE,
        completed_at=NOW,
        intent=intent,
    )

    with pytest.raises(
        ValueError,
        match="intent action must match request",
    ):
        trade_intent_report(
            result=result,
        )


def test_report_intent_side_must_match_request() -> None:
    intent = trade_intent(
        side=TradeSide.SELL,
    )

    result = trade_intent_result(
        status=TradeIntentStatus.APPROVED,
        decision=TradeIntentDecision.APPROVE,
        completed_at=NOW,
        intent=intent,
    )

    with pytest.raises(
        ValueError,
        match="intent side must match request",
    ):
        trade_intent_report(
            result=result,
        )


def test_report_intent_order_type_must_match_request() -> None:
    intent = trade_intent(
        order_type=TradeOrderType.LIMIT,
        limit_price=100.0,
    )

    result = trade_intent_result(
        status=TradeIntentStatus.APPROVED,
        decision=TradeIntentDecision.APPROVE,
        completed_at=NOW,
        intent=intent,
    )

    with pytest.raises(
        ValueError,
        match="intent order_type must match request",
    ):
        trade_intent_report(
            result=result,
        )


def test_report_intent_time_in_force_must_match_request() -> None:
    intent = trade_intent(
        time_in_force=TradeTimeInForce.GTC,
    )

    result = trade_intent_result(
        status=TradeIntentStatus.APPROVED,
        decision=TradeIntentDecision.APPROVE,
        completed_at=NOW,
        intent=intent,
    )

    with pytest.raises(
        ValueError,
        match="intent time_in_force must match request",
    ):
        trade_intent_report(
            result=result,
        )


def test_trade_intent_report_warnings_are_normalized() -> None:
    value = trade_intent_report(
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        )
    )

    assert value.warnings == (
        "warning one",
        "warning two",
    )


def test_trade_intent_report_warnings_reject_empty_values() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        trade_intent_report(
            warnings=(
                "valid",
                "   ",
            )
        )


def test_trade_intent_report_warnings_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        trade_intent_report(
            warnings=(
                "valid",
                123,
            )
        )


def test_trade_intent_report_metadata_is_normalized() -> None:
    value = TradeIntentReport(
        report_id="report-001",
        request=trade_intent_request(),
        result=trade_intent_result(),
        reported_at=NOW,
        message="Trade intent updated.",
        metadata=[
            ("  source  ", "  engine  "),
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.metadata == (
        ("source", "engine"),
        ("environment", "paper"),
    )


def test_trade_intent_report_metadata_keys_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        TradeIntentReport(
            report_id="report-001",
            request=trade_intent_request(),
            result=trade_intent_result(),
            reported_at=NOW,
            message="Trade intent updated.",
            metadata=(
                ("source", "engine"),
                ("source", "duplicate"),
            ),
        )


def test_trade_intent_report_metadata_items_must_be_pairs() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        TradeIntentReport(
            report_id="report-001",
            request=trade_intent_request(),
            result=trade_intent_result(),
            reported_at=NOW,
            message="Trade intent updated.",
            metadata=(
                ("source",),
            ),
        )


def test_trade_intent_report_metadata_keys_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        TradeIntentReport(
            report_id="report-001",
            request=trade_intent_request(),
            result=trade_intent_result(),
            reported_at=NOW,
            message="Trade intent updated.",
            metadata=(
                (123, "engine"),
            ),
        )


def test_trade_intent_report_metadata_values_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        TradeIntentReport(
            report_id="report-001",
            request=trade_intent_request(),
            result=trade_intent_result(),
            reported_at=NOW,
            message="Trade intent updated.",
            metadata=(
                ("source", 123),
            ),
        )


def test_trade_intent_report_is_immutable() -> None:
    value = trade_intent_report()

    with pytest.raises(FrozenInstanceError):
        value.report_id = "changed"