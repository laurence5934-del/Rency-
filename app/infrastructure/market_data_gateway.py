from __future__ import annotations

import time
import uuid
from collections import OrderedDict, defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence


class ProviderStatus(str, Enum):
    REGISTERED = "REGISTERED"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    DISABLED = "DISABLED"


class BarInterval(str, Enum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"


@dataclass(frozen=True, slots=True)
class MarketQuote:
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    timestamp_utc: str
    provider: str
    sequence: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        provider = self.provider.strip()
        if not symbol or not provider:
            raise ValueError("symbol and provider cannot be empty")
        if self.bid < 0 or self.ask < 0:
            raise ValueError("bid and ask cannot be negative")
        if self.bid > 0 and self.ask > 0 and self.ask < self.bid:
            raise ValueError("ask cannot be below bid")
        if self.bid_size < 0 or self.ask_size < 0:
            raise ValueError("quote sizes cannot be negative")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "provider", provider)

    @property
    def midpoint(self) -> float | None:
        return None if self.bid <= 0 or self.ask <= 0 else (self.bid + self.ask) / 2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MarketTrade:
    symbol: str
    price: float
    size: float
    timestamp_utc: str
    provider: str
    trade_id: str | None = None
    sequence: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        provider = self.provider.strip()
        if not symbol or not provider:
            raise ValueError("symbol and provider cannot be empty")
        if self.price <= 0:
            raise ValueError("price must be positive")
        if self.size < 0:
            raise ValueError("size cannot be negative")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "provider", provider)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MarketBar:
    symbol: str
    interval: BarInterval
    open: float
    high: float
    low: float
    close: float
    volume: float
    start_time_utc: str
    end_time_utc: str
    provider: str
    trade_count: int | None = None
    vwap: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        provider = self.provider.strip()
        if not symbol or not provider:
            raise ValueError("symbol and provider cannot be empty")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("OHLC values must be positive")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("invalid high")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("invalid low")
        if self.volume < 0:
            raise ValueError("volume cannot be negative")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "provider", provider)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["interval"] = self.interval.value
        return data


class MarketDataProvider(Protocol):
    name: str

    def get_quote(self, symbol: str) -> MarketQuote: ...

    def get_recent_trades(self, symbol: str, limit: int = 100) -> Sequence[MarketTrade]: ...

    def get_historical_bars(
        self,
        symbol: str,
        interval: BarInterval,
        start_time_utc: str,
        end_time_utc: str,
        limit: int | None = None,
    ) -> Sequence[MarketBar]: ...

    def health_check(self) -> Mapping[str, Any]: ...


class EventPublisher(Protocol):
    def publish_event(
        self,
        event_type: str,
        payload: Any = None,
        *,
        source: str = "unknown",
        **kwargs: Any,
    ) -> Any: ...


@dataclass(slots=True)
class ProviderHealth:
    name: str
    enabled: bool = True
    status: ProviderStatus = ProviderStatus.REGISTERED
    consecutive_failures: int = 0
    average_latency_ms: float = 0.0
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_success_utc: str | None = None
    last_failure_utc: str | None = None
    last_error: str | None = None

    def success(self, latency_ms: float) -> None:
        self.request_count += 1
        self.success_count += 1
        self.consecutive_failures = 0
        self.last_success_utc = datetime.now(timezone.utc).isoformat()
        self.average_latency_ms += (latency_ms - self.average_latency_ms) / self.request_count
        self.status = ProviderStatus.HEALTHY if self.enabled else ProviderStatus.DISABLED

    def failure(self, error: str, threshold: int) -> None:
        self.request_count += 1
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_failure_utc = datetime.now(timezone.utc).isoformat()
        self.last_error = error
        self.status = (
            ProviderStatus.DISABLED
            if not self.enabled
            else ProviderStatus.UNHEALTHY
            if self.consecutive_failures >= threshold
            else ProviderStatus.DEGRADED
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(slots=True)
class MarketDataGatewayConfig:
    quote_cache_ttl_seconds: float = 1.0
    trade_cache_ttl_seconds: float = 2.0
    bar_cache_ttl_seconds: float = 30.0
    cache_capacity: int = 10_000
    provider_failure_threshold: int = 3
    max_future_timestamp_seconds: float = 5.0
    duplicate_history_capacity: int = 50_000
    publish_events: bool = True

    def __post_init__(self) -> None:
        if min(
            self.quote_cache_ttl_seconds,
            self.trade_cache_ttl_seconds,
            self.bar_cache_ttl_seconds,
        ) < 0:
            raise ValueError("cache TTL values cannot be negative")
        if self.cache_capacity < 1 or self.provider_failure_threshold < 1:
            raise ValueError("capacity and threshold must be positive")


@dataclass(frozen=True, slots=True)
class CacheEntry:
    value: Any
    created: float
    ttl: float

    def expired(self) -> bool:
        return time.monotonic() - self.created > self.ttl


class MarketDataGateway:
    """Version 10.0.3 - normalized, validated, cached multi-provider market data."""

    def __init__(
        self,
        config: MarketDataGatewayConfig | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self.config = config or MarketDataGatewayConfig()
        self.event_publisher = event_publisher
        self._lock = RLock()
        self._providers: dict[str, MarketDataProvider] = {}
        self._priority: list[str] = []
        self._health: dict[str, ProviderHealth] = {}
        self._symbol_map: dict[tuple[str, str], str] = {}
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._seen: deque[str] = deque(maxlen=self.config.duplicate_history_capacity)
        self._seen_set: set[str] = set()
        self._metrics: defaultdict[str, int] = defaultdict(int)

    def register_provider(
        self,
        provider: MarketDataProvider,
        *,
        priority: int | None = None,
        enabled: bool = True,
    ) -> None:
        name = provider.name.strip()
        if not name:
            raise ValueError("provider name cannot be empty")
        with self._lock:
            if name in self._providers:
                raise ValueError(f"provider already registered: {name}")
            self._providers[name] = provider
            self._health[name] = ProviderHealth(
                name=name,
                enabled=enabled,
                status=ProviderStatus.REGISTERED if enabled else ProviderStatus.DISABLED,
            )
            if priority is None or priority >= len(self._priority):
                self._priority.append(name)
            else:
                self._priority.insert(max(0, priority), name)

    def enable_provider(self, name: str, enabled: bool = True) -> None:
        with self._lock:
            health = self._health.get(name)
            if health is None:
                raise KeyError(f"unknown provider: {name}")
            health.enabled = enabled
            health.status = ProviderStatus.REGISTERED if enabled else ProviderStatus.DISABLED

    def map_symbol(self, canonical: str, provider: str, provider_symbol: str) -> None:
        key = (canonical.strip().upper(), provider.strip())
        if not all((*key, provider_symbol.strip())):
            raise ValueError("mapping values cannot be empty")
        with self._lock:
            self._symbol_map[key] = provider_symbol.strip()

    def get_quote(
        self,
        symbol: str,
        *,
        provider_name: str | None = None,
        use_cache: bool = True,
    ) -> MarketQuote:
        canonical = self._symbol(symbol)
        key = f"quote:{canonical}:{provider_name or '*'}"
        if use_cache and (cached := self._cache_get(key)) is not None:
            self._metrics["cache_hits"] += 1
            return cached
        self._metrics["cache_misses"] += 1

        quote = self._execute(
            canonical,
            provider_name,
            lambda p, s: p.get_quote(s),
            self._validate_quote,
        )
        self._cache_put(key, quote, self.config.quote_cache_ttl_seconds)
        self._publish("market.quote.received", quote.to_dict())
        return quote

    def get_recent_trades(
        self,
        symbol: str,
        *,
        limit: int = 100,
        provider_name: str | None = None,
        use_cache: bool = True,
    ) -> tuple[MarketTrade, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        canonical = self._symbol(symbol)
        key = f"trades:{canonical}:{provider_name or '*'}:{limit}"
        if use_cache and (cached := self._cache_get(key)) is not None:
            self._metrics["cache_hits"] += 1
            return cached
        self._metrics["cache_misses"] += 1

        trades = self._execute(
            canonical,
            provider_name,
            lambda p, s: tuple(p.get_recent_trades(s, limit=limit)),
            self._validate_trades,
        )
        self._cache_put(key, trades, self.config.trade_cache_ttl_seconds)
        for trade in trades:
            self._publish("market.trade.received", trade.to_dict())
        return trades

    def get_historical_bars(
        self,
        symbol: str,
        interval: BarInterval,
        start_time_utc: str,
        end_time_utc: str,
        *,
        limit: int | None = None,
        provider_name: str | None = None,
        use_cache: bool = True,
    ) -> tuple[MarketBar, ...]:
        canonical = self._symbol(symbol)
        start = self._parse_timestamp(start_time_utc)
        end = self._parse_timestamp(end_time_utc)
        if start >= end:
            raise ValueError("start_time_utc must precede end_time_utc")
        if limit is not None and limit < 1:
            raise ValueError("limit must be positive")

        key = f"bars:{canonical}:{interval.value}:{start_time_utc}:{end_time_utc}:{limit}:{provider_name or '*'}"
        if use_cache and (cached := self._cache_get(key)) is not None:
            self._metrics["cache_hits"] += 1
            return cached
        self._metrics["cache_misses"] += 1

        bars = self._execute(
            canonical,
            provider_name,
            lambda p, s: tuple(
                p.get_historical_bars(
                    s, interval, start_time_utc, end_time_utc, limit
                )
            ),
            self._validate_bars,
        )
        self._cache_put(key, bars, self.config.bar_cache_ttl_seconds)
        self._publish(
            "market.bars.received",
            {"symbol": canonical, "interval": interval.value, "bars": [b.to_dict() for b in bars]},
        )
        return bars

    def health_check(self) -> dict[str, Any]:
        with self._lock:
            providers = {name: item.to_dict() for name, item in self._health.items()}
        available = [
            item for item in providers.values()
            if item["enabled"] and item["status"] != ProviderStatus.UNHEALTHY.value
        ]
        return {
            "healthy": bool(available),
            "registered_providers": len(providers),
            "available_providers": len(available),
            "cache_entries": len(self._cache),
            "providers": providers,
        }

    def metrics(self) -> dict[str, int]:
        with self._lock:
            return dict(self._metrics)

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    def _execute(
        self,
        canonical: str,
        provider_name: str | None,
        action: Callable[[MarketDataProvider, str], Any],
        validator: Callable[[Any, str], Any],
    ) -> Any:
        names = self._provider_names(provider_name)
        if not names:
            raise RuntimeError("no enabled market-data provider is available")
        last_error: Exception | None = None

        for index, name in enumerate(names):
            provider = self._providers[name]
            provider_symbol = self._symbol_map.get((canonical, name), canonical)
            started = time.perf_counter()
            self._metrics["requests"] += 1
            try:
                result = validator(action(provider, provider_symbol), canonical)
                latency = (time.perf_counter() - started) * 1000
                self._health[name].success(latency)
                self._metrics["successes"] += 1
                if index:
                    self._metrics["failovers"] += 1
                return result
            except Exception as exc:
                last_error = exc
                self._health[name].failure(
                    str(exc), self.config.provider_failure_threshold
                )
                self._metrics["failures"] += 1

        raise RuntimeError(
            f"all providers failed for {canonical}: {last_error}"
        ) from last_error

    def _provider_names(self, requested: str | None) -> list[str]:
        with self._lock:
            if requested is not None:
                if requested not in self._providers:
                    raise KeyError(f"unknown provider: {requested}")
                return [requested] if self._health[requested].enabled else []
            return [
                name for name in self._priority
                if self._health[name].enabled
                and self._health[name].status != ProviderStatus.UNHEALTHY
            ]

    def _validate_quote(self, quote: MarketQuote, canonical: str) -> MarketQuote:
        self._validate_timestamp(quote.timestamp_utc)
        self._ensure_symbol(quote.symbol, canonical)
        self._deduplicate(
            f"q:{canonical}:{quote.provider}:{quote.sequence}:{quote.timestamp_utc}:{quote.bid}:{quote.ask}"
        )
        return MarketQuote(
            canonical, quote.bid, quote.ask, quote.bid_size, quote.ask_size,
            quote.timestamp_utc, quote.provider, quote.sequence, quote.metadata
        )

    def _validate_trades(
        self, trades: Iterable[MarketTrade], canonical: str
    ) -> tuple[MarketTrade, ...]:
        output: list[MarketTrade] = []
        for trade in trades:
            self._validate_timestamp(trade.timestamp_utc)
            self._ensure_symbol(trade.symbol, canonical)
            identity = trade.trade_id or (
                f"{trade.provider}:{trade.sequence}:{trade.timestamp_utc}:{trade.price}:{trade.size}"
            )
            self._deduplicate(f"t:{canonical}:{identity}")
            output.append(
                MarketTrade(
                    canonical, trade.price, trade.size, trade.timestamp_utc,
                    trade.provider, trade.trade_id, trade.sequence, trade.metadata
                )
            )
        return tuple(sorted(output, key=lambda item: item.timestamp_utc))

    def _validate_bars(
        self, bars: Iterable[MarketBar], canonical: str
    ) -> tuple[MarketBar, ...]:
        output: list[MarketBar] = []
        for bar in bars:
            self._validate_timestamp(bar.start_time_utc)
            self._validate_timestamp(bar.end_time_utc)
            self._ensure_symbol(bar.symbol, canonical)
            self._deduplicate(
                f"b:{canonical}:{bar.provider}:{bar.interval.value}:{bar.start_time_utc}:{bar.end_time_utc}"
            )
            output.append(
                MarketBar(
                    canonical, bar.interval, bar.open, bar.high, bar.low, bar.close,
                    bar.volume, bar.start_time_utc, bar.end_time_utc, bar.provider,
                    bar.trade_count, bar.vwap, bar.metadata
                )
            )
        return tuple(sorted(output, key=lambda item: item.start_time_utc))

    def _deduplicate(self, identity: str) -> None:
        with self._lock:
            if identity in self._seen_set:
                self._metrics["duplicates_rejected"] += 1
                raise ValueError(f"duplicate market-data record: {identity}")
            if len(self._seen) == self._seen.maxlen:
                self._seen_set.discard(self._seen.popleft())
            self._seen.append(identity)
            self._seen_set.add(identity)

    def _cache_get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.expired():
                self._cache.pop(key, None)
                return None
            self._cache.move_to_end(key)
            return entry.value

    def _cache_put(self, key: str, value: Any, ttl: float) -> None:
        if ttl <= 0:
            return
        with self._lock:
            self._cache[key] = CacheEntry(value, time.monotonic(), ttl)
            self._cache.move_to_end(key)
            while len(self._cache) > self.config.cache_capacity:
                self._cache.popitem(last=False)

    def _publish(self, event_type: str, payload: Any) -> None:
        if self.config.publish_events and self.event_publisher is not None:
            self.event_publisher.publish_event(
                event_type, payload, source="market_data_gateway"
            )

    @staticmethod
    def _symbol(value: str) -> str:
        symbol = value.strip().upper()
        if not symbol:
            raise ValueError("symbol cannot be empty")
        return symbol

    @staticmethod
    def _ensure_symbol(actual: str, expected: str) -> None:
        if actual.strip().upper() != expected:
            raise ValueError(f"provider returned {actual!r}; expected {expected!r}")

    def _validate_timestamp(self, value: str) -> None:
        parsed = self._parse_timestamp(value)
        future_limit = datetime.now(timezone.utc).timestamp() + self.config.max_future_timestamp_seconds
        if parsed.timestamp() > future_limit:
            raise ValueError(f"timestamp is too far in the future: {value}")

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"invalid ISO-8601 timestamp: {value}") from exc
        if parsed.tzinfo is None:
            raise ValueError("timestamp must include timezone information")
        return parsed.astimezone(timezone.utc)
