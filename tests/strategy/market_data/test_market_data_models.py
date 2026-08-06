from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.market_data import (
    BarInterval,
    FeedStatus,
    MarketBar,
    MarketDataHealthReport,
    MarketDataSubscription,
    MarketDataType,
    MarketQuote,
    MarketSnapshot,
    MarketTrade,
    SubscriptionStatus,
)


NOW = datetime(
    2026,
    8,
    6,
    18,
    0,
    tzinfo=timezone.utc,
)


def subscription(
    *,
    subscription_id: str = "subscription-001",
    symbol: str = "NVDA",
    market: str = "NASDAQ",
    data_type: MarketDataType = MarketDataType.QUOTE,
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
    subscribed_at: datetime = NOW,
) -> MarketDataSubscription:
    return MarketDataSubscription(
        subscription_id=subscription_id,
        symbol=symbol,
        market=market,
        data_type=data_type,
        status=status,
        subscribed_at=subscribed_at,
        metadata=(
            ("source", "strategy"),
        ),
    )


def quote(
    *,
    symbol: str = "NVDA",
    bid: str = "125.10",
    ask: str = "125.20",
    bid_size: str = "100",
    ask_size: str = "120",
    timestamp: datetime = NOW,
) -> MarketQuote:
    return MarketQuote(
        symbol=symbol,
        bid=Decimal(bid),
        ask=Decimal(ask),
        bid_size=Decimal(bid_size),
        ask_size=Decimal(ask_size),
        timestamp=timestamp,
    )


def trade(
    *,
    symbol: str = "NVDA",
    price: str = "125.15",
    quantity: str = "50",
    timestamp: datetime = NOW,
) -> MarketTrade:
    return MarketTrade(
        symbol=symbol,
        price=Decimal(price),
        quantity=Decimal(quantity),
        timestamp=timestamp,
    )


def bar(
    *,
    symbol: str = "NVDA",
    interval: BarInterval = BarInterval.ONE_MINUTE,
    open_price: str = "125.00",
    high: str = "126.00",
    low: str = "124.50",
    close: str = "125.50",
    volume: str = "10000",
    start_time: datetime = NOW,
    end_time: datetime = NOW + timedelta(minutes=1),
) -> MarketBar:
    return MarketBar(
        symbol=symbol,
        interval=interval,
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal(volume),
        start_time=start_time,
        end_time=end_time,
    )


def test_market_data_subscription() -> None:
    value = subscription()

    assert value.subscription_id == "subscription-001"
    assert value.symbol == "NVDA"
    assert value.market == "NASDAQ"
    assert value.data_type is MarketDataType.QUOTE
    assert value.status is SubscriptionStatus.ACTIVE
    assert value.subscribed_at == NOW
    assert value.metadata == (
        ("source", "strategy"),
    )


def test_subscription_text_is_normalized() -> None:
    value = MarketDataSubscription(
        subscription_id="  subscription-001  ",
        symbol="  nvda  ",
        market="  nasdaq  ",
        data_type=MarketDataType.QUOTE,
        status=SubscriptionStatus.ACTIVE,
        subscribed_at=NOW,
        metadata=[
            ("  source  ", "  strategy  "),
        ],
    )

    assert value.subscription_id == "subscription-001"
    assert value.symbol == "NVDA"
    assert value.market == "NASDAQ"
    assert value.metadata == (
        ("source", "strategy"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "subscription_id",
        "symbol",
        "market",
    ],
)
def test_subscription_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "subscription_id": "subscription-001",
        "symbol": "NVDA",
        "market": "NASDAQ",
        "data_type": MarketDataType.QUOTE,
        "status": SubscriptionStatus.ACTIVE,
        "subscribed_at": NOW,
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        MarketDataSubscription(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "subscription_id",
        "symbol",
        "market",
    ],
)
def test_subscription_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "subscription_id": "subscription-001",
        "symbol": "NVDA",
        "market": "NASDAQ",
        "data_type": MarketDataType.QUOTE,
        "status": SubscriptionStatus.ACTIVE,
        "subscribed_at": NOW,
    }
    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        MarketDataSubscription(**arguments)


def test_subscription_requires_market_data_type() -> None:
    with pytest.raises(
        TypeError,
        match="data_type must be a MarketDataType",
    ):
        MarketDataSubscription(
            subscription_id="subscription-001",
            symbol="NVDA",
            market="NASDAQ",
            data_type="QUOTE",
            status=SubscriptionStatus.ACTIVE,
            subscribed_at=NOW,
        )


def test_subscription_requires_status_enum() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "status must be a SubscriptionStatus"
        ),
    ):
        MarketDataSubscription(
            subscription_id="subscription-001",
            symbol="NVDA",
            market="NASDAQ",
            data_type=MarketDataType.QUOTE,
            status="ACTIVE",
            subscribed_at=NOW,
        )


def test_subscription_timestamp_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="subscribed_at must be a datetime",
    ):
        MarketDataSubscription(
            subscription_id="subscription-001",
            symbol="NVDA",
            market="NASDAQ",
            data_type=MarketDataType.QUOTE,
            status=SubscriptionStatus.ACTIVE,
            subscribed_at="2026-08-06",
        )


def test_subscription_timestamp_must_be_timezone_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "subscribed_at must be timezone-aware"
        ),
    ):
        MarketDataSubscription(
            subscription_id="subscription-001",
            symbol="NVDA",
            market="NASDAQ",
            data_type=MarketDataType.QUOTE,
            status=SubscriptionStatus.ACTIVE,
            subscribed_at=datetime(
                2026,
                8,
                6,
                18,
                0,
            ),
        )


def test_subscription_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        MarketDataSubscription(
            subscription_id="subscription-001",
            symbol="NVDA",
            market="NASDAQ",
            data_type=MarketDataType.QUOTE,
            status=SubscriptionStatus.ACTIVE,
            subscribed_at=NOW,
            metadata=(
                ("source", "strategy"),
                ("source", "duplicate"),
            ),
        )


def test_subscription_metadata_items_must_be_pairs(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        MarketDataSubscription(
            subscription_id="subscription-001",
            symbol="NVDA",
            market="NASDAQ",
            data_type=MarketDataType.QUOTE,
            status=SubscriptionStatus.ACTIVE,
            subscribed_at=NOW,
            metadata=(
                ("source",),
            ),
        )


def test_market_quote() -> None:
    value = quote()

    assert value.symbol == "NVDA"
    assert value.bid == Decimal("125.10")
    assert value.ask == Decimal("125.20")
    assert value.bid_size == Decimal("100")
    assert value.ask_size == Decimal("120")
    assert value.midpoint == Decimal("125.15")
    assert value.spread == Decimal("0.10")


def test_quote_symbol_is_normalized() -> None:
    value = quote(symbol="  nvda  ")

    assert value.symbol == "NVDA"


@pytest.mark.parametrize(
    "field_name",
    [
        "bid",
        "ask",
        "bid_size",
        "ask_size",
    ],
)
def test_quote_decimal_fields_require_decimal(
    field_name: str,
) -> None:
    arguments = {
        "symbol": "NVDA",
        "bid": Decimal("125.10"),
        "ask": Decimal("125.20"),
        "bid_size": Decimal("100"),
        "ask_size": Decimal("120"),
        "timestamp": NOW,
    }
    arguments[field_name] = 125

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a Decimal",
    ):
        MarketQuote(**arguments)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("bid", Decimal("0")),
        ("bid", Decimal("-1")),
        ("ask", Decimal("0")),
        ("ask", Decimal("-1")),
    ],
)
def test_quote_prices_must_be_positive(
    field_name: str,
    value: Decimal,
) -> None:
    arguments = {
        "symbol": "NVDA",
        "bid": Decimal("125.10"),
        "ask": Decimal("125.20"),
        "bid_size": Decimal("100"),
        "ask_size": Decimal("120"),
        "timestamp": NOW,
    }
    arguments[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be positive",
    ):
        MarketQuote(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "bid_size",
        "ask_size",
    ],
)
def test_quote_sizes_must_not_be_negative(
    field_name: str,
) -> None:
    arguments = {
        "symbol": "NVDA",
        "bid": Decimal("125.10"),
        "ask": Decimal("125.20"),
        "bid_size": Decimal("100"),
        "ask_size": Decimal("120"),
        "timestamp": NOW,
    }
    arguments[field_name] = Decimal("-1")

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be negative",
    ):
        MarketQuote(**arguments)


def test_quote_allows_zero_sizes() -> None:
    value = quote(
        bid_size="0",
        ask_size="0",
    )

    assert value.bid_size == Decimal("0")
    assert value.ask_size == Decimal("0")


def test_quote_bid_must_not_exceed_ask() -> None:
    with pytest.raises(
        ValueError,
        match="bid must not exceed ask",
    ):
        quote(
            bid="126.00",
            ask="125.00",
        )


def test_quote_allows_locked_market() -> None:
    value = quote(
        bid="125.00",
        ask="125.00",
    )

    assert value.spread == Decimal("0")
    assert value.midpoint == Decimal("125.00")


def test_quote_timestamp_must_be_timezone_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="timestamp must be timezone-aware",
    ):
        quote(
            timestamp=datetime(
                2026,
                8,
                6,
                18,
                0,
            )
        )


def test_market_trade() -> None:
    value = trade()

    assert value.symbol == "NVDA"
    assert value.price == Decimal("125.15")
    assert value.quantity == Decimal("50")
    assert value.notional == Decimal("6257.50")


def test_trade_symbol_is_normalized() -> None:
    value = trade(symbol="  nvda  ")

    assert value.symbol == "NVDA"


@pytest.mark.parametrize(
    "field_name",
    [
        "price",
        "quantity",
    ],
)
def test_trade_decimal_fields_require_decimal(
    field_name: str,
) -> None:
    arguments = {
        "symbol": "NVDA",
        "price": Decimal("125.15"),
        "quantity": Decimal("50"),
        "timestamp": NOW,
    }
    arguments[field_name] = 10

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a Decimal",
    ):
        MarketTrade(**arguments)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("price", Decimal("0")),
        ("price", Decimal("-1")),
        ("quantity", Decimal("0")),
        ("quantity", Decimal("-1")),
    ],
)
def test_trade_values_must_be_positive(
    field_name: str,
    value: Decimal,
) -> None:
    arguments = {
        "symbol": "NVDA",
        "price": Decimal("125.15"),
        "quantity": Decimal("50"),
        "timestamp": NOW,
    }
    arguments[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be positive",
    ):
        MarketTrade(**arguments)


def test_trade_timestamp_must_be_timezone_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="timestamp must be timezone-aware",
    ):
        trade(
            timestamp=datetime(
                2026,
                8,
                6,
                18,
                0,
            )
        )


def test_market_bar() -> None:
    value = bar()

    assert value.symbol == "NVDA"
    assert value.interval is BarInterval.ONE_MINUTE
    assert value.open == Decimal("125.00")
    assert value.high == Decimal("126.00")
    assert value.low == Decimal("124.50")
    assert value.close == Decimal("125.50")
    assert value.volume == Decimal("10000")


def test_bar_symbol_is_normalized() -> None:
    value = bar(symbol="  nvda  ")

    assert value.symbol == "NVDA"


def test_bar_requires_interval_enum() -> None:
    with pytest.raises(
        TypeError,
        match="interval must be a BarInterval",
    ):
        MarketBar(
            symbol="NVDA",
            interval="1m",
            open=Decimal("125.00"),
            high=Decimal("126.00"),
            low=Decimal("124.50"),
            close=Decimal("125.50"),
            volume=Decimal("10000"),
            start_time=NOW,
            end_time=NOW + timedelta(minutes=1),
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ],
)
def test_bar_decimal_fields_require_decimal(
    field_name: str,
) -> None:
    arguments = {
        "symbol": "NVDA",
        "interval": BarInterval.ONE_MINUTE,
        "open": Decimal("125.00"),
        "high": Decimal("126.00"),
        "low": Decimal("124.50"),
        "close": Decimal("125.50"),
        "volume": Decimal("10000"),
        "start_time": NOW,
        "end_time": NOW + timedelta(minutes=1),
    }
    arguments[field_name] = 100

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a Decimal",
    ):
        MarketBar(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "open",
        "high",
        "low",
        "close",
    ],
)
def test_bar_prices_must_be_positive(
    field_name: str,
) -> None:
    arguments = {
        "symbol": "NVDA",
        "interval": BarInterval.ONE_MINUTE,
        "open": Decimal("125.00"),
        "high": Decimal("126.00"),
        "low": Decimal("124.50"),
        "close": Decimal("125.50"),
        "volume": Decimal("10000"),
        "start_time": NOW,
        "end_time": NOW + timedelta(minutes=1),
    }
    arguments[field_name] = Decimal("0")

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be positive",
    ):
        MarketBar(**arguments)


def test_bar_volume_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="volume must not be negative",
    ):
        bar(volume="-1")


def test_bar_allows_zero_volume() -> None:
    value = bar(volume="0")

    assert value.volume == Decimal("0")


def test_bar_end_time_must_follow_start_time() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "end_time must be later than start_time"
        ),
    ):
        bar(
            start_time=NOW,
            end_time=NOW,
        )


def test_bar_high_must_cover_all_prices() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "high must be greater than or equal "
            "to open, low, and close"
        ),
    ):
        bar(
            open_price="125.00",
            high="124.90",
            low="124.50",
            close="124.80",
        )


def test_bar_low_must_cover_all_prices() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "low must be less than or equal "
            "to open, high, and close"
        ),
    ):
        bar(
            open_price="125.00",
            high="126.00",
            low="125.10",
            close="125.50",
        )


def test_bar_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="start_time must be timezone-aware",
    ):
        bar(
            start_time=datetime(
                2026,
                8,
                6,
                18,
                0,
            ),
            end_time=NOW + timedelta(minutes=1),
        )


@pytest.mark.parametrize(
    "model",
    [
        subscription(),
        quote(),
        trade(),
        bar(),
    ],
)
def test_market_data_models_are_immutable(
    model: object,
) -> None:
    with pytest.raises(FrozenInstanceError):
        model.symbol = "AAPL"

def snapshot(
    *,
    symbol: str = "NVDA",
    last_price: str = "125.15",
    bid: str = "125.10",
    ask: str = "125.20",
    volume: str = "250000",
    timestamp: datetime = NOW,
) -> MarketSnapshot:
    return MarketSnapshot(
        symbol=symbol,
        last_price=Decimal(last_price),
        bid=Decimal(bid),
        ask=Decimal(ask),
        volume=Decimal(volume),
        timestamp=timestamp,
    )


def health_report(
    *,
    feed_name: str = "IBKR Market Data",
    status: FeedStatus = FeedStatus.CONNECTED,
    evaluated_at: datetime = NOW,
    latency_ms: str = "12.5",
    active_subscriptions: int = 25,
    message: str = "Market data feed is healthy.",
) -> MarketDataHealthReport:
    return MarketDataHealthReport(
        feed_name=feed_name,
        status=status,
        evaluated_at=evaluated_at,
        latency_ms=Decimal(latency_ms),
        active_subscriptions=active_subscriptions,
        message=message,
    )


def test_market_snapshot() -> None:
    value = snapshot()

    assert value.symbol == "NVDA"
    assert value.last_price == Decimal("125.15")
    assert value.bid == Decimal("125.10")
    assert value.ask == Decimal("125.20")
    assert value.volume == Decimal("250000")
    assert value.midpoint == Decimal("125.15")
    assert value.spread == Decimal("0.10")
    assert value.timestamp == NOW


def test_snapshot_symbol_is_normalized() -> None:
    value = snapshot(symbol="  nvda  ")

    assert value.symbol == "NVDA"


def test_snapshot_symbol_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="symbol must not be empty",
    ):
        snapshot(symbol="   ")


def test_snapshot_symbol_must_be_string() -> None:
    with pytest.raises(
        TypeError,
        match="symbol must be a string",
    ):
        MarketSnapshot(
            symbol=123,
            last_price=Decimal("125.15"),
            bid=Decimal("125.10"),
            ask=Decimal("125.20"),
            volume=Decimal("250000"),
            timestamp=NOW,
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "last_price",
        "bid",
        "ask",
        "volume",
    ],
)
def test_snapshot_decimal_fields_require_decimal(
    field_name: str,
) -> None:
    arguments = {
        "symbol": "NVDA",
        "last_price": Decimal("125.15"),
        "bid": Decimal("125.10"),
        "ask": Decimal("125.20"),
        "volume": Decimal("250000"),
        "timestamp": NOW,
    }
    arguments[field_name] = 125

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a Decimal",
    ):
        MarketSnapshot(**arguments)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("last_price", Decimal("0")),
        ("last_price", Decimal("-1")),
        ("bid", Decimal("0")),
        ("bid", Decimal("-1")),
        ("ask", Decimal("0")),
        ("ask", Decimal("-1")),
    ],
)
def test_snapshot_prices_must_be_positive(
    field_name: str,
    value: Decimal,
) -> None:
    arguments = {
        "symbol": "NVDA",
        "last_price": Decimal("125.15"),
        "bid": Decimal("125.10"),
        "ask": Decimal("125.20"),
        "volume": Decimal("250000"),
        "timestamp": NOW,
    }
    arguments[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be positive",
    ):
        MarketSnapshot(**arguments)


def test_snapshot_volume_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="volume must not be negative",
    ):
        snapshot(volume="-1")


def test_snapshot_allows_zero_volume() -> None:
    value = snapshot(volume="0")

    assert value.volume == Decimal("0")


def test_snapshot_bid_must_not_exceed_ask() -> None:
    with pytest.raises(
        ValueError,
        match="bid must not exceed ask",
    ):
        snapshot(
            bid="126.00",
            ask="125.00",
        )


def test_snapshot_allows_locked_market() -> None:
    value = snapshot(
        bid="125.00",
        ask="125.00",
        last_price="125.00",
    )

    assert value.midpoint == Decimal("125.00")
    assert value.spread == Decimal("0")


def test_snapshot_timestamp_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="timestamp must be a datetime",
    ):
        MarketSnapshot(
            symbol="NVDA",
            last_price=Decimal("125.15"),
            bid=Decimal("125.10"),
            ask=Decimal("125.20"),
            volume=Decimal("250000"),
            timestamp="2026-08-06",
        )


def test_snapshot_timestamp_must_be_timezone_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="timestamp must be timezone-aware",
    ):
        snapshot(
            timestamp=datetime(
                2026,
                8,
                6,
                18,
                0,
            )
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("last_price", Decimal("NaN")),
        ("bid", Decimal("Infinity")),
        ("ask", Decimal("-Infinity")),
        ("volume", Decimal("NaN")),
    ],
)
def test_snapshot_decimal_fields_must_be_finite(
    field_name: str,
    value: Decimal,
) -> None:
    arguments = {
        "symbol": "NVDA",
        "last_price": Decimal("125.15"),
        "bid": Decimal("125.10"),
        "ask": Decimal("125.20"),
        "volume": Decimal("250000"),
        "timestamp": NOW,
    }
    arguments[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be finite",
    ):
        MarketSnapshot(**arguments)


def test_market_data_health_report() -> None:
    value = health_report()

    assert value.feed_name == "IBKR Market Data"
    assert value.status is FeedStatus.CONNECTED
    assert value.evaluated_at == NOW
    assert value.latency_ms == Decimal("12.5")
    assert value.active_subscriptions == 25
    assert value.message == (
        "Market data feed is healthy."
    )


def test_health_report_text_is_normalized() -> None:
    value = health_report(
        feed_name="  IBKR Market Data  ",
        message="  Market data feed is healthy.  ",
    )

    assert value.feed_name == "IBKR Market Data"
    assert value.message == (
        "Market data feed is healthy."
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "feed_name",
        "message",
    ],
)
def test_health_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "feed_name": "IBKR Market Data",
        "status": FeedStatus.CONNECTED,
        "evaluated_at": NOW,
        "latency_ms": Decimal("12.5"),
        "active_subscriptions": 25,
        "message": "Market data feed is healthy.",
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        MarketDataHealthReport(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "feed_name",
        "message",
    ],
)
def test_health_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "feed_name": "IBKR Market Data",
        "status": FeedStatus.CONNECTED,
        "evaluated_at": NOW,
        "latency_ms": Decimal("12.5"),
        "active_subscriptions": 25,
        "message": "Market data feed is healthy.",
    }
    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        MarketDataHealthReport(**arguments)


def test_health_report_requires_feed_status() -> None:
    with pytest.raises(
        TypeError,
        match="status must be a FeedStatus",
    ):
        MarketDataHealthReport(
            feed_name="IBKR Market Data",
            status="CONNECTED",
            evaluated_at=NOW,
            latency_ms=Decimal("12.5"),
            active_subscriptions=25,
            message="Market data feed is healthy.",
        )


def test_health_evaluated_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="evaluated_at must be a datetime",
    ):
        MarketDataHealthReport(
            feed_name="IBKR Market Data",
            status=FeedStatus.CONNECTED,
            evaluated_at="2026-08-06",
            latency_ms=Decimal("12.5"),
            active_subscriptions=25,
            message="Market data feed is healthy.",
        )


def test_health_evaluated_at_must_be_timezone_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="evaluated_at must be timezone-aware",
    ):
        health_report(
            evaluated_at=datetime(
                2026,
                8,
                6,
                18,
                0,
            )
        )


def test_health_latency_requires_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="latency_ms must be a Decimal",
    ):
        MarketDataHealthReport(
            feed_name="IBKR Market Data",
            status=FeedStatus.CONNECTED,
            evaluated_at=NOW,
            latency_ms=12.5,
            active_subscriptions=25,
            message="Market data feed is healthy.",
        )


def test_health_latency_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="latency_ms must not be negative",
    ):
        health_report(latency_ms="-0.1")


def test_health_report_allows_zero_latency() -> None:
    value = health_report(latency_ms="0")

    assert value.latency_ms == Decimal("0")


@pytest.mark.parametrize(
    "latency",
    [
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_health_latency_must_be_finite(
    latency: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="latency_ms must be finite",
    ):
        MarketDataHealthReport(
            feed_name="IBKR Market Data",
            status=FeedStatus.CONNECTED,
            evaluated_at=NOW,
            latency_ms=latency,
            active_subscriptions=25,
            message="Market data feed is healthy.",
        )


def test_active_subscriptions_must_be_integer() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "active_subscriptions must be an integer"
        ),
    ):
        health_report(active_subscriptions=Decimal("25"))


def test_active_subscriptions_must_not_be_negative(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "active_subscriptions must not be negative"
        ),
    ):
        health_report(active_subscriptions=-1)


def test_health_report_allows_zero_subscriptions() -> None:
    value = health_report(
        status=FeedStatus.DISCONNECTED,
        active_subscriptions=0,
        message="Market data feed is disconnected.",
    )

    assert value.active_subscriptions == 0
    assert value.status is FeedStatus.DISCONNECTED


@pytest.mark.parametrize(
    "status",
    [
        FeedStatus.CONNECTED,
        FeedStatus.DISCONNECTED,
        FeedStatus.DEGRADED,
    ],
)
def test_health_report_supports_all_feed_statuses(
    status: FeedStatus,
) -> None:
    value = health_report(status=status)

    assert value.status is status


@pytest.mark.parametrize(
    "model",
    [
        snapshot(),
        health_report(),
    ],
)
def test_remaining_market_data_models_are_immutable(
    model: object,
) -> None:
    with pytest.raises(FrozenInstanceError):
        if isinstance(model, MarketSnapshot):
            model.symbol = "AAPL"
        else:
            model.message = "Changed."