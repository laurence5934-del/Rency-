from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.market_data import (
    BarInterval,
    EnterpriseMarketDataService,
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
    20,
    0,
    tzinfo=timezone.utc,
)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def service(
    *,
    current_time: datetime = NOW,
) -> EnterpriseMarketDataService:
    return EnterpriseMarketDataService(
        feed_name="IBKR Market Data",
        clock=FixedClock(current_time),
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
            ("source", "market-data-test"),
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


def registered_service(
) -> EnterpriseMarketDataService:
    value = service()
    value.register_subscription(
        subscription()
    )
    return value


def test_create_market_data_service() -> None:
    value = service()

    assert value.feed_name == "IBKR Market Data"
    assert value.subscription_ids == ()
    assert value.symbols == ()
    assert value.active_subscription_count == 0
    assert value.health_history == ()


def test_feed_name_is_normalized() -> None:
    value = EnterpriseMarketDataService(
        feed_name="  IBKR Market Data  ",
        clock=FixedClock(NOW),
    )

    assert value.feed_name == "IBKR Market Data"


def test_feed_name_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="feed_name must not be empty",
    ):
        EnterpriseMarketDataService(
            feed_name="   "
        )


def test_feed_name_must_be_string() -> None:
    with pytest.raises(
        TypeError,
        match="feed_name must be a string",
    ):
        EnterpriseMarketDataService(
            feed_name=123
        )


def test_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterpriseMarketDataService(
            feed_name="IBKR Market Data",
            clock=NOW,
        )


def test_register_subscription() -> None:
    value = service()
    request = subscription()

    result = value.register_subscription(
        request
    )

    assert result == request
    assert value.subscription_ids == (
        "subscription-001",
    )
    assert value.active_subscription_count == 1


def test_register_subscription_requires_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "subscription must be a "
            "MarketDataSubscription"
        ),
    ):
        service().register_subscription(
            object()
        )


def test_duplicate_subscription_id_is_rejected() -> None:
    value = registered_service()

    with pytest.raises(
        ValueError,
        match=(
            "subscription_id is already registered"
        ),
    ):
        value.register_subscription(
            subscription(
                symbol="AAPL",
                market="NASDAQ",
            )
        )


def test_duplicate_subscription_key_is_rejected() -> None:
    value = registered_service()

    with pytest.raises(
        ValueError,
        match=(
            "market-data subscription is already "
            "registered for symbol, market, "
            "and data_type"
        ),
    ):
        value.register_subscription(
            subscription(
                subscription_id="subscription-002",
            )
        )


def test_register_multiple_subscriptions() -> None:
    value = service()

    value.register_subscription(
        subscription()
    )

    value.register_subscription(
        subscription(
            subscription_id="subscription-002",
            symbol="AAPL",
            data_type=MarketDataType.TRADE,
        )
    )

    assert value.subscription_ids == (
        "subscription-001",
        "subscription-002",
    )
    assert value.active_subscription_count == 2


def test_get_subscription() -> None:
    value = registered_service()

    result = value.get_subscription(
        "subscription-001"
    )

    assert result.symbol == "NVDA"
    assert result.market == "NASDAQ"


def test_get_subscription_normalizes_identifier() -> None:
    value = registered_service()

    result = value.get_subscription(
        "  subscription-001  "
    )

    assert result.subscription_id == (
        "subscription-001"
    )


def test_get_unknown_subscription_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market-data subscription not found"
        ),
    ):
        service().get_subscription(
            "missing"
        )


def test_subscription_for() -> None:
    value = registered_service()

    result = value.subscription_for(
        symbol="nvda",
        market="nasdaq",
        data_type=MarketDataType.QUOTE,
    )

    assert result.subscription_id == (
        "subscription-001"
    )


def test_subscription_for_requires_data_type() -> None:
    value = registered_service()

    with pytest.raises(
        TypeError,
        match="data_type must be a MarketDataType",
    ):
        value.subscription_for(
            symbol="NVDA",
            market="NASDAQ",
            data_type="QUOTE",
        )


def test_unknown_subscription_key_is_rejected() -> None:
    value = registered_service()

    with pytest.raises(
        KeyError,
        match=(
            "market-data subscription not found "
            "for symbol, market, and data_type"
        ),
    ):
        value.subscription_for(
            symbol="AAPL",
            market="NASDAQ",
            data_type=MarketDataType.QUOTE,
        )


def test_update_subscription() -> None:
    value = registered_service()

    updated = subscription(
        status=SubscriptionStatus.PAUSED,
    )

    result = value.update_subscription(updated)

    assert result.status is (
        SubscriptionStatus.PAUSED
    )
    assert value.active_subscription_count == 0


def test_update_subscription_requires_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "subscription must be a "
            "MarketDataSubscription"
        ),
    ):
        registered_service().update_subscription(
            object()
        )


def test_update_unknown_subscription_is_rejected() -> None:
    value = registered_service()

    with pytest.raises(
        KeyError,
        match=(
            "market-data subscription not found"
        ),
    ):
        value.update_subscription(
            subscription(
                subscription_id="missing",
            )
        )


def test_update_rejects_symbol_change() -> None:
    value = registered_service()

    with pytest.raises(
        ValueError,
        match=(
            "subscription symbol cannot change"
        ),
    ):
        value.update_subscription(
            subscription(symbol="AAPL")
        )


def test_update_rejects_market_change() -> None:
    value = registered_service()

    with pytest.raises(
        ValueError,
        match=(
            "subscription market cannot change"
        ),
    ):
        value.update_subscription(
            subscription(market="NYSE")
        )


def test_update_rejects_data_type_change() -> None:
    value = registered_service()

    with pytest.raises(
        ValueError,
        match=(
            "subscription data_type cannot change"
        ),
    ):
        value.update_subscription(
            subscription(
                data_type=MarketDataType.TRADE
            )
        )


def test_update_rejects_subscribed_at_change() -> None:
    value = registered_service()

    with pytest.raises(
        ValueError,
        match=(
            "subscription subscribed_at "
            "cannot change"
        ),
    ):
        value.update_subscription(
            subscription(
                subscribed_at=(
                    NOW + timedelta(seconds=1)
                )
            )
        )


def test_unregister_subscription() -> None:
    value = registered_service()

    removed = value.unregister_subscription(
        "subscription-001"
    )

    assert removed.subscription_id == (
        "subscription-001"
    )
    assert value.subscription_ids == ()
    assert value.active_subscription_count == 0


def test_unregister_allows_same_key_to_be_reused() -> None:
    value = registered_service()

    value.unregister_subscription(
        "subscription-001"
    )

    replacement = value.register_subscription(
        subscription(
            subscription_id="subscription-002",
        )
    )

    assert replacement.subscription_id == (
        "subscription-002"
    )


def test_ingest_quote() -> None:
    value = service()
    market_quote = quote()

    result = value.ingest_quote(
        market_quote
    )

    assert result == market_quote
    assert value.get_quote("NVDA") == market_quote
    assert value.symbols == ("NVDA",)


def test_ingest_quote_requires_model() -> None:
    with pytest.raises(
        TypeError,
        match="quote must be a MarketQuote",
    ):
        service().ingest_quote(object())


def test_quote_lookup_normalizes_symbol() -> None:
    value = service()
    value.ingest_quote(quote())

    assert value.get_quote(
        "  nvda  "
    ).symbol == "NVDA"


def test_unknown_quote_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="market quote not found",
    ):
        service().get_quote("NVDA")


def test_stale_quote_is_rejected() -> None:
    value = service()

    value.ingest_quote(
        quote(timestamp=NOW)
    )

    with pytest.raises(
        ValueError,
        match=(
            "quote timestamp must not be earlier "
            "than the latest quote"
        ),
    ):
        value.ingest_quote(
            quote(
                timestamp=(
                    NOW - timedelta(seconds=1)
                )
            )
        )


def test_quote_with_same_timestamp_is_allowed() -> None:
    value = service()

    value.ingest_quote(
        quote(
            bid="125.10",
            ask="125.20",
        )
    )

    latest = value.ingest_quote(
        quote(
            bid="125.20",
            ask="125.30",
        )
    )

    assert value.get_quote("NVDA") == latest
    assert len(value.quote_history("NVDA")) == 2


def test_quote_history() -> None:
    value = service()

    first = quote(
        timestamp=NOW
    )
    second = quote(
        bid="125.20",
        ask="125.30",
        timestamp=(
            NOW + timedelta(seconds=1)
        ),
    )

    value.ingest_quote(first)
    value.ingest_quote(second)

    assert value.quote_history("NVDA") == (
        first,
        second,
    )


def test_unknown_quote_history_returns_empty() -> None:
    assert service().quote_history(
        "NVDA"
    ) == ()


def test_ingest_trade() -> None:
    value = service()
    market_trade = trade()

    result = value.ingest_trade(
        market_trade
    )

    assert result == market_trade
    assert value.get_trade("NVDA") == market_trade
    assert value.symbols == ("NVDA",)


def test_ingest_trade_requires_model() -> None:
    with pytest.raises(
        TypeError,
        match="trade must be a MarketTrade",
    ):
        service().ingest_trade(object())


def test_unknown_trade_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="market trade not found",
    ):
        service().get_trade("NVDA")


def test_stale_trade_is_rejected() -> None:
    value = service()

    value.ingest_trade(
        trade(timestamp=NOW)
    )

    with pytest.raises(
        ValueError,
        match=(
            "trade timestamp must not be earlier "
            "than the latest trade"
        ),
    ):
        value.ingest_trade(
            trade(
                timestamp=(
                    NOW - timedelta(seconds=1)
                )
            )
        )


def test_trade_history() -> None:
    value = service()

    first = trade(
        timestamp=NOW
    )
    second = trade(
        price="125.25",
        timestamp=(
            NOW + timedelta(seconds=1)
        ),
    )

    value.ingest_trade(first)
    value.ingest_trade(second)

    assert value.trade_history("NVDA") == (
        first,
        second,
    )


def test_ingest_bar() -> None:
    value = service()
    market_bar = bar()

    result = value.ingest_bar(
        market_bar
    )

    assert result == market_bar
    assert value.get_bar(
        "NVDA",
        BarInterval.ONE_MINUTE,
    ) == market_bar


def test_ingest_bar_requires_model() -> None:
    with pytest.raises(
        TypeError,
        match="bar must be a MarketBar",
    ):
        service().ingest_bar(object())


def test_get_bar_requires_interval_enum() -> None:
    value = service()
    value.ingest_bar(bar())

    with pytest.raises(
        TypeError,
        match="interval must be a BarInterval",
    ):
        value.get_bar(
            "NVDA",
            "1m",
        )


def test_unknown_bar_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market bar not found for symbol "
            "and interval"
        ),
    ):
        service().get_bar(
            "NVDA",
            BarInterval.ONE_MINUTE,
        )


def test_stale_bar_is_rejected() -> None:
    value = service()

    value.ingest_bar(
        bar(
            start_time=NOW,
            end_time=(
                NOW + timedelta(minutes=1)
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "bar start_time must not be earlier "
            "than the latest bar"
        ),
    ):
        value.ingest_bar(
            bar(
                start_time=(
                    NOW - timedelta(minutes=1)
                ),
                end_time=NOW,
            )
        )


def test_bar_end_time_cannot_move_backward() -> None:
    value = service()

    value.ingest_bar(
        bar(
            start_time=NOW,
            end_time=(
                NOW + timedelta(minutes=2)
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "bar end_time must not move backward"
        ),
    ):
        value.ingest_bar(
            bar(
                start_time=NOW,
                end_time=(
                    NOW + timedelta(minutes=1)
                ),
            )
        )


def test_bar_history() -> None:
    value = service()

    first = bar(
        start_time=NOW,
        end_time=(
            NOW + timedelta(minutes=1)
        ),
    )
    second = bar(
        open_price="125.50",
        high="126.50",
        low="125.00",
        close="126.00",
        start_time=(
            NOW + timedelta(minutes=1)
        ),
        end_time=(
            NOW + timedelta(minutes=2)
        ),
    )

    value.ingest_bar(first)
    value.ingest_bar(second)

    assert value.bar_history(
        "NVDA",
        BarInterval.ONE_MINUTE,
    ) == (
        first,
        second,
    )


def test_bar_history_requires_interval_enum() -> None:
    with pytest.raises(
        TypeError,
        match="interval must be a BarInterval",
    ):
        service().bar_history(
            "NVDA",
            "1m",
        )


def test_ingest_snapshot() -> None:
    value = service()
    market_snapshot = snapshot()

    result = value.ingest_snapshot(
        market_snapshot
    )

    assert result == market_snapshot
    assert value.get_snapshot(
        "NVDA"
    ) == market_snapshot


def test_ingest_snapshot_requires_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "snapshot must be a MarketSnapshot"
        ),
    ):
        service().ingest_snapshot(
            object()
        )


def test_unknown_snapshot_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="market snapshot not found",
    ):
        service().get_snapshot("NVDA")


def test_stale_snapshot_is_rejected() -> None:
    value = service()

    value.ingest_snapshot(
        snapshot(timestamp=NOW)
    )

    with pytest.raises(
        ValueError,
        match=(
            "snapshot timestamp must not be earlier "
            "than the latest snapshot"
        ),
    ):
        value.ingest_snapshot(
            snapshot(
                timestamp=(
                    NOW - timedelta(seconds=1)
                )
            )
        )


def test_snapshot_history() -> None:
    value = service()

    first = snapshot(
        timestamp=NOW
    )
    second = snapshot(
        last_price="125.25",
        bid="125.20",
        ask="125.30",
        timestamp=(
            NOW + timedelta(seconds=1)
        ),
    )

    value.ingest_snapshot(first)
    value.ingest_snapshot(second)

    assert value.snapshot_history(
        "NVDA"
    ) == (
        first,
        second,
    )


def test_symbols_include_all_ingested_types() -> None:
    value = service()

    value.ingest_quote(
        quote(symbol="NVDA")
    )
    value.ingest_trade(
        trade(symbol="AAPL")
    )
    value.ingest_bar(
        bar(symbol="MSFT")
    )
    value.ingest_snapshot(
        snapshot(symbol="TSLA")
    )

    assert value.symbols == (
        "AAPL",
        "MSFT",
        "NVDA",
        "TSLA",
    )


@pytest.mark.parametrize(
    ("method_name", "field_name"),
    [
        ("get_quote", "symbol"),
        ("get_trade", "symbol"),
        ("get_snapshot", "symbol"),
        ("quote_history", "symbol"),
        ("trade_history", "symbol"),
        ("snapshot_history", "symbol"),
    ],
)
def test_symbol_must_not_be_empty(
    method_name: str,
    field_name: str,
) -> None:
    value = service()
    method = getattr(value, method_name)

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        method("   ")


def test_subscription_identifier_must_not_be_empty(
) -> None:
    with pytest.raises(
        ValueError,
        match="subscription_id must not be empty",
    ):
        service().get_subscription("   ")


def test_subscription_identifier_must_be_string(
) -> None:
    with pytest.raises(
        TypeError,
        match="subscription_id must be a string",
    ):
        service().get_subscription(123)

def health_report(
    *,
    feed_name: str = "IBKR Market Data",
    status: FeedStatus = FeedStatus.CONNECTED,
    evaluated_at: datetime = NOW,
    latency_ms: str = "12.5",
    active_subscriptions: int = 0,
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


def test_latest_price_uses_quote_midpoint() -> None:
    value = service()

    value.ingest_quote(
        quote(
            bid="125.10",
            ask="125.30",
        )
    )

    assert value.latest_price(
        "NVDA"
    ) == Decimal("125.20")


def test_latest_price_prefers_trade_over_quote() -> None:
    value = service()

    value.ingest_quote(
        quote(
            bid="125.10",
            ask="125.30",
        )
    )
    value.ingest_trade(
        trade(price="125.25")
    )

    assert value.latest_price(
        "NVDA"
    ) == Decimal("125.25")


def test_latest_price_prefers_snapshot_over_trade(
) -> None:
    value = service()

    value.ingest_quote(
        quote(
            bid="125.10",
            ask="125.30",
        )
    )
    value.ingest_trade(
        trade(price="125.25")
    )
    value.ingest_snapshot(
        snapshot(last_price="125.40")
    )

    assert value.latest_price(
        "NVDA"
    ) == Decimal("125.40")


def test_latest_price_normalizes_symbol() -> None:
    value = service()
    value.ingest_trade(
        trade(price="125.25")
    )

    assert value.latest_price(
        "  nvda  "
    ) == Decimal("125.25")


def test_latest_price_without_market_data_is_rejected(
) -> None:
    with pytest.raises(
        KeyError,
        match="latest market price not found",
    ):
        service().latest_price("NVDA")


def test_record_health() -> None:
    value = service()
    report = health_report()

    result = value.record_health(report)

    assert result == report
    assert value.get_health() == report
    assert value.health_history == (report,)


def test_record_health_requires_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "report must be a "
            "MarketDataHealthReport"
        ),
    ):
        service().record_health(object())


def test_health_report_feed_name_must_match() -> None:
    value = service()

    with pytest.raises(
        ValueError,
        match=(
            "health report feed_name must match "
            "service feed_name"
        ),
    ):
        value.record_health(
            health_report(
                feed_name="Different Feed"
            )
        )


def test_health_report_active_count_must_match_service(
) -> None:
    value = registered_service()

    with pytest.raises(
        ValueError,
        match=(
            "health report active_subscriptions "
            "must match the service"
        ),
    ):
        value.record_health(
            health_report(
                active_subscriptions=0
            )
        )


def test_health_report_accepts_matching_active_count(
) -> None:
    value = registered_service()

    report = health_report(
        active_subscriptions=1
    )

    assert value.record_health(report) == report


def test_paused_subscription_is_not_counted_as_active(
) -> None:
    value = registered_service()

    value.update_subscription(
        subscription(
            status=SubscriptionStatus.PAUSED
        )
    )

    report = health_report(
        active_subscriptions=0
    )

    assert value.record_health(report) == report


def test_cancelled_subscription_is_not_counted_as_active(
) -> None:
    value = registered_service()

    value.update_subscription(
        subscription(
            status=SubscriptionStatus.CANCELLED
        )
    )

    assert value.active_subscription_count == 0


def test_pending_subscription_is_not_counted_as_active(
) -> None:
    value = service()

    value.register_subscription(
        subscription(
            status=SubscriptionStatus.PENDING
        )
    )

    assert value.active_subscription_count == 0


def test_health_reports_must_be_chronological() -> None:
    value = service()

    value.record_health(
        health_report(
            evaluated_at=NOW
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "health report evaluated_at must not be "
            "earlier than the latest health report"
        ),
    ):
        value.record_health(
            health_report(
                evaluated_at=(
                    NOW - timedelta(seconds=1)
                )
            )
        )


def test_health_reports_allow_same_timestamp() -> None:
    value = service()

    first = health_report(
        evaluated_at=NOW,
        status=FeedStatus.CONNECTED,
    )
    second = health_report(
        evaluated_at=NOW,
        status=FeedStatus.DEGRADED,
        message="Feed latency is elevated.",
    )

    value.record_health(first)
    value.record_health(second)

    assert value.health_history == (
        first,
        second,
    )
    assert value.get_health() == second


def test_get_health_before_recording_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market-data health report not found"
        ),
    ):
        service().get_health()


def test_evaluate_health() -> None:
    value = registered_service()

    report = value.evaluate_health(
        status=FeedStatus.CONNECTED,
        latency_ms=Decimal("8.5"),
        message="Feed is operating normally.",
    )

    assert report.feed_name == "IBKR Market Data"
    assert report.status is FeedStatus.CONNECTED
    assert report.evaluated_at == NOW
    assert report.latency_ms == Decimal("8.5")
    assert report.active_subscriptions == 1
    assert value.get_health() == report


def test_evaluate_health_requires_status_enum() -> None:
    with pytest.raises(
        TypeError,
        match="status must be a FeedStatus",
    ):
        service().evaluate_health(
            status="CONNECTED",
            latency_ms=Decimal("8.5"),
            message="Feed is operating normally.",
        )


def test_evaluate_health_requires_decimal_latency(
) -> None:
    with pytest.raises(
        TypeError,
        match="latency_ms must be a Decimal",
    ):
        service().evaluate_health(
            status=FeedStatus.CONNECTED,
            latency_ms=8.5,
            message="Feed is operating normally.",
        )


def test_evaluate_health_uses_current_active_count(
) -> None:
    value = service()

    value.register_subscription(
        subscription()
    )
    value.register_subscription(
        subscription(
            subscription_id="subscription-002",
            symbol="AAPL",
            data_type=MarketDataType.TRADE,
        )
    )

    report = value.evaluate_health(
        status=FeedStatus.CONNECTED,
        latency_ms=Decimal("5"),
        message="Two subscriptions are active.",
    )

    assert report.active_subscriptions == 2


def test_market_data_is_not_stale_at_boundary() -> None:
    value = service(
        current_time=NOW
    )

    value.ingest_quote(
        quote(
            timestamp=(
                NOW - timedelta(seconds=30)
            )
        )
    )

    assert value.is_stale(
        "NVDA",
        maximum_age_seconds=30,
    ) is False


def test_market_data_is_stale_beyond_boundary() -> None:
    value = service(
        current_time=NOW
    )

    value.ingest_quote(
        quote(
            timestamp=(
                NOW - timedelta(seconds=31)
            )
        )
    )

    assert value.is_stale(
        "NVDA",
        maximum_age_seconds=30,
    ) is True


def test_staleness_uses_latest_available_timestamp(
) -> None:
    value = service(
        current_time=NOW
    )

    value.ingest_quote(
        quote(
            timestamp=(
                NOW - timedelta(seconds=60)
            )
        )
    )
    value.ingest_trade(
        trade(
            timestamp=(
                NOW - timedelta(seconds=10)
            )
        )
    )

    assert value.is_stale(
        "NVDA",
        maximum_age_seconds=30,
    ) is False


def test_staleness_includes_snapshot_timestamp() -> None:
    value = service(
        current_time=NOW
    )

    value.ingest_quote(
        quote(
            timestamp=(
                NOW - timedelta(seconds=60)
            )
        )
    )
    value.ingest_snapshot(
        snapshot(
            timestamp=(
                NOW - timedelta(seconds=5)
            )
        )
    )

    assert value.is_stale(
        "NVDA",
        maximum_age_seconds=30,
    ) is False


def test_staleness_requires_integer_maximum_age(
) -> None:
    value = service()
    value.ingest_quote(quote())

    with pytest.raises(
        TypeError,
        match=(
            "maximum_age_seconds must be an integer"
        ),
    ):
        value.is_stale(
            "NVDA",
            maximum_age_seconds=Decimal("30"),
        )


def test_staleness_rejects_negative_maximum_age(
) -> None:
    value = service()
    value.ingest_quote(quote())

    with pytest.raises(
        ValueError,
        match=(
            "maximum_age_seconds must not be negative"
        ),
    ):
        value.is_stale(
            "NVDA",
            maximum_age_seconds=-1,
        )


def test_staleness_without_data_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market data not found for symbol"
        ),
    ):
        service().is_stale(
            "NVDA",
            maximum_age_seconds=30,
        )


def test_staleness_normalizes_symbol() -> None:
    value = service()
    value.ingest_quote(quote())

    assert value.is_stale(
        "  nvda  ",
        maximum_age_seconds=0,
    ) is False


def test_clear_symbol_removes_current_market_data(
) -> None:
    value = service()

    value.ingest_quote(quote())
    value.ingest_trade(trade())
    value.ingest_bar(bar())
    value.ingest_snapshot(snapshot())

    value.clear_symbol("NVDA")

    assert value.symbols == ()

    with pytest.raises(KeyError):
        value.get_quote("NVDA")

    with pytest.raises(KeyError):
        value.get_trade("NVDA")

    with pytest.raises(KeyError):
        value.get_bar(
            "NVDA",
            BarInterval.ONE_MINUTE,
        )

    with pytest.raises(KeyError):
        value.get_snapshot("NVDA")


def test_clear_symbol_preserves_histories() -> None:
    value = service()

    market_quote = quote()
    market_trade = trade()
    market_bar = bar()
    market_snapshot = snapshot()

    value.ingest_quote(market_quote)
    value.ingest_trade(market_trade)
    value.ingest_bar(market_bar)
    value.ingest_snapshot(market_snapshot)

    value.clear_symbol("NVDA")

    assert value.quote_history(
        "NVDA"
    ) == (market_quote,)

    assert value.trade_history(
        "NVDA"
    ) == (market_trade,)

    assert value.bar_history(
        "NVDA",
        BarInterval.ONE_MINUTE,
    ) == (market_bar,)

    assert value.snapshot_history(
        "NVDA"
    ) == (market_snapshot,)


def test_clear_symbol_does_not_remove_subscription(
) -> None:
    value = registered_service()
    value.ingest_quote(quote())

    value.clear_symbol("NVDA")

    assert value.subscription_ids == (
        "subscription-001",
    )
    assert value.active_subscription_count == 1


def test_clear_unknown_symbol_is_safe() -> None:
    value = service()

    assert value.clear_symbol(
        "UNKNOWN"
    ) is None


def test_clear_symbol_normalizes_identifier() -> None:
    value = service()
    value.ingest_quote(quote())

    value.clear_symbol("  nvda  ")

    assert value.symbols == ()


def test_clear_symbol_rejects_empty_identifier() -> None:
    with pytest.raises(
        ValueError,
        match="symbol must not be empty",
    ):
        service().clear_symbol("   ")


def test_latest_price_rejects_empty_symbol() -> None:
    with pytest.raises(
        ValueError,
        match="symbol must not be empty",
    ):
        service().latest_price("   ")


def test_is_stale_rejects_empty_symbol() -> None:
    with pytest.raises(
        ValueError,
        match="symbol must not be empty",
    ):
        service().is_stale(
            "   ",
            maximum_age_seconds=30,
        )


def test_clock_must_return_datetime() -> None:
    value = EnterpriseMarketDataService(
        feed_name="IBKR Market Data",
        clock=lambda: "now",
    )

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        value.evaluate_health(
            status=FeedStatus.CONNECTED,
            latency_ms=Decimal("5"),
            message="Feed is healthy.",
        )


def test_clock_must_return_timezone_aware_datetime(
) -> None:
    value = EnterpriseMarketDataService(
        feed_name="IBKR Market Data",
        clock=lambda: datetime(
            2026,
            8,
            6,
            20,
            0,
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        value.evaluate_health(
            status=FeedStatus.CONNECTED,
            latency_ms=Decimal("5"),
            message="Feed is healthy.",
        )


def test_staleness_clock_must_return_datetime() -> None:
    value = EnterpriseMarketDataService(
        feed_name="IBKR Market Data",
        clock=lambda: "now",
    )
    value.ingest_quote(quote())

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        value.is_stale(
            "NVDA",
            maximum_age_seconds=30,
        )


def test_health_history_tracks_all_reports() -> None:
    value = service()

    first = value.evaluate_health(
        status=FeedStatus.CONNECTED,
        latency_ms=Decimal("5"),
        message="Feed connected.",
    )

    second = value.evaluate_health(
        status=FeedStatus.DEGRADED,
        latency_ms=Decimal("50"),
        message="Feed latency increased.",
    )

    assert value.health_history == (
        first,
        second,
    )