from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .market_data_models import (
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


Clock = Callable[[], datetime]


class EnterpriseMarketDataService:
    """
    Maintains normalized enterprise market-data state.

    Responsibilities:
    - manage market-data subscriptions
    - ingest quotes, trades, bars, and snapshots
    - reject stale or out-of-order updates
    - expose latest market-data values
    - maintain immutable audit histories
    - track feed-health reports
    """

    def __init__(
        self,
        *,
        feed_name: str,
        clock: Clock | None = None,
    ) -> None:
        self._feed_name = self._normalize_identifier(
            feed_name,
            "feed_name",
        )

        if clock is not None and not callable(clock):
            raise TypeError(
                "clock must be callable"
            )

        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

        self._subscriptions: dict[
            str,
            MarketDataSubscription,
        ] = {}

        self._subscription_by_key: dict[
            tuple[str, str, MarketDataType],
            str,
        ] = {}

        self._quotes: dict[
            str,
            MarketQuote,
        ] = {}

        self._trades: dict[
            str,
            MarketTrade,
        ] = {}

        self._bars: dict[
            tuple[str, BarInterval],
            MarketBar,
        ] = {}

        self._snapshots: dict[
            str,
            MarketSnapshot,
        ] = {}

        self._quote_history: dict[
            str,
            list[MarketQuote],
        ] = {}

        self._trade_history: dict[
            str,
            list[MarketTrade],
        ] = {}

        self._bar_history: dict[
            tuple[str, BarInterval],
            list[MarketBar],
        ] = {}

        self._snapshot_history: dict[
            str,
            list[MarketSnapshot],
        ] = {}

        self._health_history: list[
            MarketDataHealthReport
        ] = []

        self._latest_health: (
            MarketDataHealthReport | None
        ) = None

    @property
    def feed_name(self) -> str:
        return self._feed_name

    @property
    def subscription_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(self._subscriptions)
        )

    @property
    def symbols(
        self,
    ) -> tuple[str, ...]:
        values = (
            set(self._quotes)
            | set(self._trades)
            | set(self._snapshots)
            | {
                symbol
                for symbol, _ in self._bars
            }
        )

        return tuple(sorted(values))

    @property
    def active_subscription_count(self) -> int:
        return sum(
            1
            for subscription
            in self._subscriptions.values()
            if subscription.status
            is SubscriptionStatus.ACTIVE
        )

    @property
    def health_history(
        self,
    ) -> tuple[MarketDataHealthReport, ...]:
        return tuple(self._health_history)

    def register_subscription(
        self,
        subscription: MarketDataSubscription,
    ) -> MarketDataSubscription:
        if not isinstance(
            subscription,
            MarketDataSubscription,
        ):
            raise TypeError(
                "subscription must be a "
                "MarketDataSubscription"
            )

        if (
            subscription.subscription_id
            in self._subscriptions
        ):
            raise ValueError(
                "subscription_id is already registered"
            )

        key = self._subscription_key(
            symbol=subscription.symbol,
            market=subscription.market,
            data_type=subscription.data_type,
        )

        if key in self._subscription_by_key:
            raise ValueError(
                "market-data subscription is already "
                "registered for symbol, market, "
                "and data_type"
            )

        self._subscriptions[
            subscription.subscription_id
        ] = subscription

        self._subscription_by_key[
            key
        ] = subscription.subscription_id

        return subscription

    def update_subscription(
        self,
        subscription: MarketDataSubscription,
    ) -> MarketDataSubscription:
        if not isinstance(
            subscription,
            MarketDataSubscription,
        ):
            raise TypeError(
                "subscription must be a "
                "MarketDataSubscription"
            )

        current = self.get_subscription(
            subscription.subscription_id
        )

        if subscription.symbol != current.symbol:
            raise ValueError(
                "subscription symbol cannot change"
            )

        if subscription.market != current.market:
            raise ValueError(
                "subscription market cannot change"
            )

        if (
            subscription.data_type
            is not current.data_type
        ):
            raise ValueError(
                "subscription data_type cannot change"
            )

        if (
            subscription.subscribed_at
            != current.subscribed_at
        ):
            raise ValueError(
                "subscription subscribed_at cannot change"
            )

        self._subscriptions[
            subscription.subscription_id
        ] = subscription

        return subscription

    def unregister_subscription(
        self,
        subscription_id: str,
    ) -> MarketDataSubscription:
        subscription = self.get_subscription(
            subscription_id
        )

        self._subscriptions.pop(
            subscription.subscription_id
        )

        self._subscription_by_key.pop(
            self._subscription_key(
                symbol=subscription.symbol,
                market=subscription.market,
                data_type=subscription.data_type,
            ),
            None,
        )

        return subscription

    def get_subscription(
        self,
        subscription_id: str,
    ) -> MarketDataSubscription:
        normalized_subscription_id = (
            self._normalize_identifier(
                subscription_id,
                "subscription_id",
            )
        )

        try:
            return self._subscriptions[
                normalized_subscription_id
            ]
        except KeyError as exc:
            raise KeyError(
                "market-data subscription not found: "
                f"{normalized_subscription_id}"
            ) from exc

    def subscription_for(
        self,
        *,
        symbol: str,
        market: str,
        data_type: MarketDataType,
    ) -> MarketDataSubscription:
        if not isinstance(
            data_type,
            MarketDataType,
        ):
            raise TypeError(
                "data_type must be a MarketDataType"
            )

        key = self._subscription_key(
            symbol=symbol,
            market=market,
            data_type=data_type,
        )

        try:
            subscription_id = (
                self._subscription_by_key[key]
            )
        except KeyError as exc:
            raise KeyError(
                "market-data subscription not found "
                "for symbol, market, and data_type"
            ) from exc

        return self._subscriptions[
            subscription_id
        ]

    def ingest_quote(
        self,
        quote: MarketQuote,
    ) -> MarketQuote:
        if not isinstance(
            quote,
            MarketQuote,
        ):
            raise TypeError(
                "quote must be a MarketQuote"
            )

        current = self._quotes.get(
            quote.symbol
        )

        if (
            current is not None
            and quote.timestamp < current.timestamp
        ):
            raise ValueError(
                "quote timestamp must not be earlier "
                "than the latest quote"
            )

        self._quotes[quote.symbol] = quote

        self._quote_history.setdefault(
            quote.symbol,
            [],
        ).append(quote)

        return quote

    def ingest_trade(
        self,
        trade: MarketTrade,
    ) -> MarketTrade:
        if not isinstance(
            trade,
            MarketTrade,
        ):
            raise TypeError(
                "trade must be a MarketTrade"
            )

        current = self._trades.get(
            trade.symbol
        )

        if (
            current is not None
            and trade.timestamp < current.timestamp
        ):
            raise ValueError(
                "trade timestamp must not be earlier "
                "than the latest trade"
            )

        self._trades[trade.symbol] = trade

        self._trade_history.setdefault(
            trade.symbol,
            [],
        ).append(trade)

        return trade

    def ingest_bar(
        self,
        bar: MarketBar,
    ) -> MarketBar:
        if not isinstance(
            bar,
            MarketBar,
        ):
            raise TypeError(
                "bar must be a MarketBar"
            )

        key = (
            bar.symbol,
            bar.interval,
        )

        current = self._bars.get(key)

        if (
            current is not None
            and bar.start_time < current.start_time
        ):
            raise ValueError(
                "bar start_time must not be earlier "
                "than the latest bar"
            )

        if (
            current is not None
            and bar.start_time == current.start_time
            and bar.end_time < current.end_time
        ):
            raise ValueError(
                "bar end_time must not move backward"
            )

        self._bars[key] = bar

        self._bar_history.setdefault(
            key,
            [],
        ).append(bar)

        return bar

    def ingest_snapshot(
        self,
        snapshot: MarketSnapshot,
    ) -> MarketSnapshot:
        if not isinstance(
            snapshot,
            MarketSnapshot,
        ):
            raise TypeError(
                "snapshot must be a MarketSnapshot"
            )

        current = self._snapshots.get(
            snapshot.symbol
        )

        if (
            current is not None
            and snapshot.timestamp < current.timestamp
        ):
            raise ValueError(
                "snapshot timestamp must not be earlier "
                "than the latest snapshot"
            )

        self._snapshots[
            snapshot.symbol
        ] = snapshot

        self._snapshot_history.setdefault(
            snapshot.symbol,
            [],
        ).append(snapshot)

        return snapshot

    def get_quote(
        self,
        symbol: str,
    ) -> MarketQuote:
        normalized_symbol = (
            self._normalize_symbol(symbol)
        )

        try:
            return self._quotes[
                normalized_symbol
            ]
        except KeyError as exc:
            raise KeyError(
                "market quote not found: "
                f"{normalized_symbol}"
            ) from exc

    def get_trade(
        self,
        symbol: str,
    ) -> MarketTrade:
        normalized_symbol = (
            self._normalize_symbol(symbol)
        )

        try:
            return self._trades[
                normalized_symbol
            ]
        except KeyError as exc:
            raise KeyError(
                "market trade not found: "
                f"{normalized_symbol}"
            ) from exc

    def get_bar(
        self,
        symbol: str,
        interval: BarInterval,
    ) -> MarketBar:
        normalized_symbol = (
            self._normalize_symbol(symbol)
        )

        if not isinstance(
            interval,
            BarInterval,
        ):
            raise TypeError(
                "interval must be a BarInterval"
            )

        key = (
            normalized_symbol,
            interval,
        )

        try:
            return self._bars[key]
        except KeyError as exc:
            raise KeyError(
                "market bar not found for symbol "
                "and interval"
            ) from exc

    def get_snapshot(
        self,
        symbol: str,
    ) -> MarketSnapshot:
        normalized_symbol = (
            self._normalize_symbol(symbol)
        )

        try:
            return self._snapshots[
                normalized_symbol
            ]
        except KeyError as exc:
            raise KeyError(
                "market snapshot not found: "
                f"{normalized_symbol}"
            ) from exc

    def quote_history(
        self,
        symbol: str,
    ) -> tuple[MarketQuote, ...]:
        normalized_symbol = (
            self._normalize_symbol(symbol)
        )

        return tuple(
            self._quote_history.get(
                normalized_symbol,
                (),
            )
        )

    def trade_history(
        self,
        symbol: str,
    ) -> tuple[MarketTrade, ...]:
        normalized_symbol = (
            self._normalize_symbol(symbol)
        )

        return tuple(
            self._trade_history.get(
                normalized_symbol,
                (),
            )
        )

    def bar_history(
        self,
        symbol: str,
        interval: BarInterval,
    ) -> tuple[MarketBar, ...]:
        normalized_symbol = (
            self._normalize_symbol(symbol)
        )

        if not isinstance(
            interval,
            BarInterval,
        ):
            raise TypeError(
                "interval must be a BarInterval"
            )

        return tuple(
            self._bar_history.get(
                (
                    normalized_symbol,
                    interval,
                ),
                (),
            )
        )

    def snapshot_history(
        self,
        symbol: str,
    ) -> tuple[MarketSnapshot, ...]:
        normalized_symbol = (
            self._normalize_symbol(symbol)
        )

        return tuple(
            self._snapshot_history.get(
                normalized_symbol,
                (),
            )
        )

    def latest_price(
        self,
        symbol: str,
    ):
        normalized_symbol = (
            self._normalize_symbol(symbol)
        )

        snapshot = self._snapshots.get(
            normalized_symbol
        )

        if snapshot is not None:
            return snapshot.last_price

        trade = self._trades.get(
            normalized_symbol
        )

        if trade is not None:
            return trade.price

        quote = self._quotes.get(
            normalized_symbol
        )

        if quote is not None:
            return quote.midpoint

        raise KeyError(
            "latest market price not found: "
            f"{normalized_symbol}"
        )

    def record_health(
        self,
        report: MarketDataHealthReport,
    ) -> MarketDataHealthReport:
        if not isinstance(
            report,
            MarketDataHealthReport,
        ):
            raise TypeError(
                "report must be a "
                "MarketDataHealthReport"
            )

        if report.feed_name != self._feed_name:
            raise ValueError(
                "health report feed_name must match "
                "service feed_name"
            )

        if (
            self._latest_health is not None
            and report.evaluated_at
            < self._latest_health.evaluated_at
        ):
            raise ValueError(
                "health report evaluated_at must not be "
                "earlier than the latest health report"
            )

        if (
            report.active_subscriptions
            != self.active_subscription_count
        ):
            raise ValueError(
                "health report active_subscriptions "
                "must match the service"
            )

        self._latest_health = report
        self._health_history.append(report)

        return report

    def get_health(
        self,
    ) -> MarketDataHealthReport:
        if self._latest_health is None:
            raise KeyError(
                "market-data health report not found"
            )

        return self._latest_health

    def evaluate_health(
        self,
        *,
        status: FeedStatus,
        latency_ms,
        message: str,
    ) -> MarketDataHealthReport:
        if not isinstance(
            status,
            FeedStatus,
        ):
            raise TypeError(
                "status must be a FeedStatus"
            )

        report = MarketDataHealthReport(
            feed_name=self._feed_name,
            status=status,
            evaluated_at=self._current_time(),
            latency_ms=latency_ms,
            active_subscriptions=(
                self.active_subscription_count
            ),
            message=message,
        )

        return self.record_health(report)

    def is_stale(
        self,
        symbol: str,
        *,
        maximum_age_seconds: int,
    ) -> bool:
        normalized_symbol = (
            self._normalize_symbol(symbol)
        )

        if not isinstance(
            maximum_age_seconds,
            int,
        ):
            raise TypeError(
                "maximum_age_seconds must be an integer"
            )

        if maximum_age_seconds < 0:
            raise ValueError(
                "maximum_age_seconds must not be negative"
            )

        timestamps: list[datetime] = []

        quote = self._quotes.get(
            normalized_symbol
        )
        if quote is not None:
            timestamps.append(quote.timestamp)

        trade = self._trades.get(
            normalized_symbol
        )
        if trade is not None:
            timestamps.append(trade.timestamp)

        snapshot = self._snapshots.get(
            normalized_symbol
        )
        if snapshot is not None:
            timestamps.append(snapshot.timestamp)

        if not timestamps:
            raise KeyError(
                "market data not found for symbol: "
                f"{normalized_symbol}"
            )

        latest_timestamp = max(timestamps)

        age_seconds = (
            self._current_time()
            - latest_timestamp
        ).total_seconds()

        return age_seconds > maximum_age_seconds

    def clear_symbol(
        self,
        symbol: str,
    ) -> None:
        normalized_symbol = (
            self._normalize_symbol(symbol)
        )

        self._quotes.pop(
            normalized_symbol,
            None,
        )
        self._trades.pop(
            normalized_symbol,
            None,
        )
        self._snapshots.pop(
            normalized_symbol,
            None,
        )

        for key in tuple(self._bars):
            if key[0] == normalized_symbol:
                self._bars.pop(key)

    def _current_time(self) -> datetime:
        value = self._clock()

        if not isinstance(
            value,
            datetime,
        ):
            raise TypeError(
                "clock must return a datetime"
            )

        if value.tzinfo is None:
            raise ValueError(
                "clock must return a timezone-aware datetime"
            )

        return value

    @classmethod
    def _subscription_key(
        cls,
        *,
        symbol: str,
        market: str,
        data_type: MarketDataType,
    ) -> tuple[str, str, MarketDataType]:
        if not isinstance(
            data_type,
            MarketDataType,
        ):
            raise TypeError(
                "data_type must be a MarketDataType"
            )

        return (
            cls._normalize_symbol(symbol),
            cls._normalize_identifier(
                market,
                "market",
            ).upper(),
            data_type,
        )

    @classmethod
    def _normalize_symbol(
        cls,
        value: str,
    ) -> str:
        return cls._normalize_identifier(
            value,
            "symbol",
        ).upper()

    @staticmethod
    def _normalize_identifier(
        value: str,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return normalized