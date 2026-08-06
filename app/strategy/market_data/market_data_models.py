from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class MarketDataType(str, Enum):
    QUOTE = "QUOTE"
    TRADE = "TRADE"
    BAR = "BAR"
    SNAPSHOT = "SNAPSHOT"


class SubscriptionStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class FeedStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    DEGRADED = "DEGRADED"


class BarInterval(str, Enum):
    ONE_SECOND = "1s"
    FIVE_SECONDS = "5s"
    FIFTEEN_SECONDS = "15s"
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"


class MarketDataModelSupport:
    @staticmethod
    def required_text(
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

    @staticmethod
    def decimal_value(
        value: Decimal,
        field_name: str,
    ) -> Decimal:
        if not isinstance(value, Decimal):
            raise TypeError(
                f"{field_name} must be a Decimal"
            )

        if not value.is_finite():
            raise ValueError(
                f"{field_name} must be finite"
            )

        return value

    @classmethod
    def positive_decimal(
        cls,
        value: Decimal,
        field_name: str,
    ) -> Decimal:
        normalized = cls.decimal_value(
            value,
            field_name,
        )

        if normalized <= Decimal("0"):
            raise ValueError(
                f"{field_name} must be positive"
            )

        return normalized

    @classmethod
    def nonnegative_decimal(
        cls,
        value: Decimal,
        field_name: str,
    ) -> Decimal:
        normalized = cls.decimal_value(
            value,
            field_name,
        )

        if normalized < Decimal("0"):
            raise ValueError(
                f"{field_name} must not be negative"
            )

        return normalized

    @staticmethod
    def aware_datetime(
        value: datetime,
        field_name: str,
    ) -> datetime:
        if not isinstance(value, datetime):
            raise TypeError(
                f"{field_name} must be a datetime"
            )

        if value.tzinfo is None:
            raise ValueError(
                f"{field_name} must be timezone-aware"
            )

        return value

    @staticmethod
    def normalize_metadata(
        values: (
            tuple[tuple[str, str], ...]
            | list[tuple[str, str]]
        ),
    ) -> tuple[tuple[str, str], ...]:
        normalized: list[tuple[str, str]] = []
        seen_keys: set[str] = set()

        for item in values:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
            ):
                raise TypeError(
                    "each metadata item must be "
                    "a two-item tuple"
                )

            raw_key, raw_value = item

            key = str(raw_key).strip()
            value = str(raw_value).strip()

            if not key:
                raise ValueError(
                    "metadata keys must not be empty"
                )

            if key in seen_keys:
                raise ValueError(
                    "metadata keys must be unique"
                )

            seen_keys.add(key)
            normalized.append((key, value))

        return tuple(normalized)


@dataclass(frozen=True, slots=True)
class MarketDataSubscription:
    subscription_id: str
    symbol: str
    market: str
    data_type: MarketDataType
    status: SubscriptionStatus
    subscribed_at: datetime
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        subscription_id = (
            MarketDataModelSupport.required_text(
                self.subscription_id,
                "subscription_id",
            )
        )
        symbol = MarketDataModelSupport.required_text(
            self.symbol,
            "symbol",
        ).upper()
        market = MarketDataModelSupport.required_text(
            self.market,
            "market",
        ).upper()

        if not isinstance(
            self.data_type,
            MarketDataType,
        ):
            raise TypeError(
                "data_type must be a MarketDataType"
            )

        if not isinstance(
            self.status,
            SubscriptionStatus,
        ):
            raise TypeError(
                "status must be a SubscriptionStatus"
            )

        MarketDataModelSupport.aware_datetime(
            self.subscribed_at,
            "subscribed_at",
        )

        metadata = (
            MarketDataModelSupport.normalize_metadata(
                self.metadata
            )
        )

        object.__setattr__(
            self,
            "subscription_id",
            subscription_id,
        )
        object.__setattr__(
            self,
            "symbol",
            symbol,
        )
        object.__setattr__(
            self,
            "market",
            market,
        )
        object.__setattr__(
            self,
            "metadata",
            metadata,
        )


@dataclass(frozen=True, slots=True)
class MarketQuote:
    symbol: str
    bid: Decimal
    ask: Decimal
    bid_size: Decimal
    ask_size: Decimal
    timestamp: datetime

    def __post_init__(self) -> None:
        symbol = MarketDataModelSupport.required_text(
            self.symbol,
            "symbol",
        ).upper()

        bid = MarketDataModelSupport.positive_decimal(
            self.bid,
            "bid",
        )
        ask = MarketDataModelSupport.positive_decimal(
            self.ask,
            "ask",
        )
        bid_size = (
            MarketDataModelSupport.nonnegative_decimal(
                self.bid_size,
                "bid_size",
            )
        )
        ask_size = (
            MarketDataModelSupport.nonnegative_decimal(
                self.ask_size,
                "ask_size",
            )
        )

        MarketDataModelSupport.aware_datetime(
            self.timestamp,
            "timestamp",
        )

        if bid > ask:
            raise ValueError(
                "bid must not exceed ask"
            )

        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "bid", bid)
        object.__setattr__(self, "ask", ask)
        object.__setattr__(
            self,
            "bid_size",
            bid_size,
        )
        object.__setattr__(
            self,
            "ask_size",
            ask_size,
        )

    @property
    def midpoint(self) -> Decimal:
        return (
            self.bid + self.ask
        ) / Decimal("2")

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid


@dataclass(frozen=True, slots=True)
class MarketTrade:
    symbol: str
    price: Decimal
    quantity: Decimal
    timestamp: datetime

    def __post_init__(self) -> None:
        symbol = MarketDataModelSupport.required_text(
            self.symbol,
            "symbol",
        ).upper()
        price = MarketDataModelSupport.positive_decimal(
            self.price,
            "price",
        )
        quantity = (
            MarketDataModelSupport.positive_decimal(
                self.quantity,
                "quantity",
            )
        )

        MarketDataModelSupport.aware_datetime(
            self.timestamp,
            "timestamp",
        )

        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "price", price)
        object.__setattr__(
            self,
            "quantity",
            quantity,
        )

    @property
    def notional(self) -> Decimal:
        return self.price * self.quantity


@dataclass(frozen=True, slots=True)
class MarketBar:
    symbol: str
    interval: BarInterval
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    start_time: datetime
    end_time: datetime

    def __post_init__(self) -> None:
        symbol = MarketDataModelSupport.required_text(
            self.symbol,
            "symbol",
        ).upper()

        if not isinstance(
            self.interval,
            BarInterval,
        ):
            raise TypeError(
                "interval must be a BarInterval"
            )

        open_price = (
            MarketDataModelSupport.positive_decimal(
                self.open,
                "open",
            )
        )
        high_price = (
            MarketDataModelSupport.positive_decimal(
                self.high,
                "high",
            )
        )
        low_price = (
            MarketDataModelSupport.positive_decimal(
                self.low,
                "low",
            )
        )
        close_price = (
            MarketDataModelSupport.positive_decimal(
                self.close,
                "close",
            )
        )
        volume = (
            MarketDataModelSupport.nonnegative_decimal(
                self.volume,
                "volume",
            )
        )

        MarketDataModelSupport.aware_datetime(
            self.start_time,
            "start_time",
        )
        MarketDataModelSupport.aware_datetime(
            self.end_time,
            "end_time",
        )

        if self.end_time <= self.start_time:
            raise ValueError(
                "end_time must be later than start_time"
            )

        if high_price < max(
            open_price,
            low_price,
            close_price,
        ):
            raise ValueError(
                "high must be greater than or equal "
                "to open, low, and close"
            )

        if low_price > min(
            open_price,
            high_price,
            close_price,
        ):
            raise ValueError(
                "low must be less than or equal "
                "to open, high, and close"
            )

        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(
            self,
            "open",
            open_price,
        )
        object.__setattr__(
            self,
            "high",
            high_price,
        )
        object.__setattr__(
            self,
            "low",
            low_price,
        )
        object.__setattr__(
            self,
            "close",
            close_price,
        )
        object.__setattr__(
            self,
            "volume",
            volume,
        )


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    symbol: str
    last_price: Decimal
    bid: Decimal
    ask: Decimal
    volume: Decimal
    timestamp: datetime

    def __post_init__(self) -> None:
        symbol = MarketDataModelSupport.required_text(
            self.symbol,
            "symbol",
        ).upper()

        last_price = (
            MarketDataModelSupport.positive_decimal(
                self.last_price,
                "last_price",
            )
        )
        bid = MarketDataModelSupport.positive_decimal(
            self.bid,
            "bid",
        )
        ask = MarketDataModelSupport.positive_decimal(
            self.ask,
            "ask",
        )
        volume = (
            MarketDataModelSupport.nonnegative_decimal(
                self.volume,
                "volume",
            )
        )

        MarketDataModelSupport.aware_datetime(
            self.timestamp,
            "timestamp",
        )

        if bid > ask:
            raise ValueError(
                "bid must not exceed ask"
            )

        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(
            self,
            "last_price",
            last_price,
        )
        object.__setattr__(self, "bid", bid)
        object.__setattr__(self, "ask", ask)
        object.__setattr__(
            self,
            "volume",
            volume,
        )

    @property
    def midpoint(self) -> Decimal:
        return (
            self.bid + self.ask
        ) / Decimal("2")

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid


@dataclass(frozen=True, slots=True)
class MarketDataHealthReport:
    feed_name: str
    status: FeedStatus
    evaluated_at: datetime
    latency_ms: Decimal
    active_subscriptions: int
    message: str

    def __post_init__(self) -> None:
        feed_name = (
            MarketDataModelSupport.required_text(
                self.feed_name,
                "feed_name",
            )
        )
        message = MarketDataModelSupport.required_text(
            self.message,
            "message",
        )

        if not isinstance(
            self.status,
            FeedStatus,
        ):
            raise TypeError(
                "status must be a FeedStatus"
            )

        MarketDataModelSupport.aware_datetime(
            self.evaluated_at,
            "evaluated_at",
        )

        latency_ms = (
            MarketDataModelSupport.nonnegative_decimal(
                self.latency_ms,
                "latency_ms",
            )
        )

        if not isinstance(
            self.active_subscriptions,
            int,
        ):
            raise TypeError(
                "active_subscriptions must be an integer"
            )

        if self.active_subscriptions < 0:
            raise ValueError(
                "active_subscriptions must not be negative"
            )

        object.__setattr__(
            self,
            "feed_name",
            feed_name,
        )
        object.__setattr__(
            self,
            "latency_ms",
            latency_ms,
        )
        object.__setattr__(
            self,
            "message",
            message,
        )