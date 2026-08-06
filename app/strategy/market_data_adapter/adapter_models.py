from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.strategy.market_data import (
    MarketDataType,
)


class ProviderType(str, Enum):
    INTERACTIVE_BROKERS = "INTERACTIVE_BROKERS"
    POLYGON = "POLYGON"
    ALPACA = "ALPACA"
    REPLAY = "REPLAY"
    SIMULATED = "SIMULATED"
    CUSTOM = "CUSTOM"


class ConnectionStatus(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class SubscriptionAction(str, Enum):
    SUBSCRIBE = "SUBSCRIBE"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    PAUSE = "PAUSE"
    RESUME = "RESUME"


class ProviderCapability(str, Enum):
    REAL_TIME_QUOTES = "REAL_TIME_QUOTES"
    DELAYED_QUOTES = "DELAYED_QUOTES"
    TRADES = "TRADES"
    HISTORICAL_BARS = "HISTORICAL_BARS"
    REAL_TIME_BARS = "REAL_TIME_BARS"
    SNAPSHOTS = "SNAPSHOTS"
    MARKET_DEPTH = "MARKET_DEPTH"
    HEARTBEAT = "HEARTBEAT"


class AdapterModelSupport:
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
    def optional_text(
        value: str | None,
        field_name: str,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string or None"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty"
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

    @staticmethod
    def normalize_capabilities(
        capabilities: (
            tuple[ProviderCapability, ...]
            | list[ProviderCapability]
        ),
    ) -> tuple[ProviderCapability, ...]:
        normalized = tuple(capabilities)

        for capability in normalized:
            if not isinstance(
                capability,
                ProviderCapability,
            ):
                raise TypeError(
                    "every capability must be a "
                    "ProviderCapability"
                )

        if len(normalized) != len(set(normalized)):
            raise ValueError(
                "capabilities must be unique"
            )

        return normalized


@dataclass(frozen=True, slots=True)
class MarketDataConnectionRequest:
    connection_id: str
    provider_name: str
    provider_type: ProviderType
    requested_at: datetime
    requested_by: str
    host: str | None = None
    port: int | None = None
    client_id: int | None = None
    use_paper_environment: bool = True
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        connection_id = AdapterModelSupport.required_text(
            self.connection_id,
            "connection_id",
        )
        provider_name = AdapterModelSupport.required_text(
            self.provider_name,
            "provider_name",
        )
        requested_by = AdapterModelSupport.required_text(
            self.requested_by,
            "requested_by",
        )
        host = AdapterModelSupport.optional_text(
            self.host,
            "host",
        )

        if not isinstance(
            self.provider_type,
            ProviderType,
        ):
            raise TypeError(
                "provider_type must be a ProviderType"
            )

        AdapterModelSupport.aware_datetime(
            self.requested_at,
            "requested_at",
        )

        if not isinstance(
            self.use_paper_environment,
            bool,
        ):
            raise TypeError(
                "use_paper_environment must be a bool"
            )

        if self.port is not None:
            if not isinstance(self.port, int):
                raise TypeError(
                    "port must be an integer or None"
                )

            if self.port <= 0 or self.port > 65535:
                raise ValueError(
                    "port must be between 1 and 65535"
                )

        if self.client_id is not None:
            if not isinstance(self.client_id, int):
                raise TypeError(
                    "client_id must be an integer or None"
                )

            if self.client_id < 0:
                raise ValueError(
                    "client_id must not be negative"
                )

        metadata = AdapterModelSupport.normalize_metadata(
            self.metadata
        )

        object.__setattr__(
            self,
            "connection_id",
            connection_id,
        )
        object.__setattr__(
            self,
            "provider_name",
            provider_name,
        )
        object.__setattr__(
            self,
            "requested_by",
            requested_by,
        )
        object.__setattr__(
            self,
            "host",
            host,
        )
        object.__setattr__(
            self,
            "metadata",
            metadata,
        )


@dataclass(frozen=True, slots=True)
class MarketDataConnectionResult:
    connection_id: str
    provider_name: str
    provider_type: ProviderType
    status: ConnectionStatus
    connected_at: datetime | None
    evaluated_at: datetime
    capabilities: tuple[ProviderCapability, ...] = field(
        default_factory=tuple
    )
    provider_session_id: str | None = None
    message: str = "Connection evaluated."
    error: str | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        connection_id = AdapterModelSupport.required_text(
            self.connection_id,
            "connection_id",
        )
        provider_name = AdapterModelSupport.required_text(
            self.provider_name,
            "provider_name",
        )
        message = AdapterModelSupport.required_text(
            self.message,
            "message",
        )
        provider_session_id = (
            AdapterModelSupport.optional_text(
                self.provider_session_id,
                "provider_session_id",
            )
        )
        error = AdapterModelSupport.optional_text(
            self.error,
            "error",
        )

        if not isinstance(
            self.provider_type,
            ProviderType,
        ):
            raise TypeError(
                "provider_type must be a ProviderType"
            )

        if not isinstance(
            self.status,
            ConnectionStatus,
        ):
            raise TypeError(
                "status must be a ConnectionStatus"
            )

        if self.connected_at is not None:
            AdapterModelSupport.aware_datetime(
                self.connected_at,
                "connected_at",
            )

        AdapterModelSupport.aware_datetime(
            self.evaluated_at,
            "evaluated_at",
        )

        if (
            self.connected_at is not None
            and self.connected_at > self.evaluated_at
        ):
            raise ValueError(
                "connected_at must not be later "
                "than evaluated_at"
            )

        capabilities = (
            AdapterModelSupport.normalize_capabilities(
                self.capabilities
            )
        )

        connected_statuses = {
            ConnectionStatus.CONNECTED,
            ConnectionStatus.DEGRADED,
        }

        if self.status in connected_statuses:
            if self.connected_at is None:
                raise ValueError(
                    "connected and degraded results "
                    "require connected_at"
                )

            if provider_session_id is None:
                raise ValueError(
                    "connected and degraded results "
                    "require provider_session_id"
                )

            if error is not None:
                raise ValueError(
                    "connected and degraded results "
                    "must not include an error"
                )

        if self.status is ConnectionStatus.FAILED:
            if error is None:
                raise ValueError(
                    "failed connection results "
                    "require an error"
                )

            if self.connected_at is not None:
                raise ValueError(
                    "failed connection results must not "
                    "include connected_at"
                )

        if self.status in {
            ConnectionStatus.DISCONNECTED,
            ConnectionStatus.CONNECTING,
        }:
            if self.connected_at is not None:
                raise ValueError(
                    "disconnected and connecting results "
                    "must not include connected_at"
                )

            if provider_session_id is not None:
                raise ValueError(
                    "disconnected and connecting results "
                    "must not include provider_session_id"
                )

        if (
            self.status is not ConnectionStatus.FAILED
            and error is not None
        ):
            raise ValueError(
                "only failed connection results "
                "may include an error"
            )

        metadata = AdapterModelSupport.normalize_metadata(
            self.metadata
        )

        object.__setattr__(
            self,
            "connection_id",
            connection_id,
        )
        object.__setattr__(
            self,
            "provider_name",
            provider_name,
        )
        object.__setattr__(
            self,
            "provider_session_id",
            provider_session_id,
        )
        object.__setattr__(
            self,
            "message",
            message,
        )
        object.__setattr__(
            self,
            "capabilities",
            capabilities,
        )
        object.__setattr__(
            self,
            "error",
            error,
        )
        object.__setattr__(
            self,
            "metadata",
            metadata,
        )

    @property
    def is_connected(self) -> bool:
        return self.status in {
            ConnectionStatus.CONNECTED,
            ConnectionStatus.DEGRADED,
        }

    def supports(
        self,
        capability: ProviderCapability,
    ) -> bool:
        if not isinstance(
            capability,
            ProviderCapability,
        ):
            raise TypeError(
                "capability must be a "
                "ProviderCapability"
            )

        return capability in self.capabilities


@dataclass(frozen=True, slots=True)
class MarketDataConnectionReport:
    report_id: str
    request: MarketDataConnectionRequest
    result: MarketDataConnectionResult
    reported_at: datetime
    message: str
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        report_id = AdapterModelSupport.required_text(
            self.report_id,
            "report_id",
        )

        if not isinstance(
            self.request,
            MarketDataConnectionRequest,
        ):
            raise TypeError(
                "request must be a "
                "MarketDataConnectionRequest"
            )

        if not isinstance(
            self.result,
            MarketDataConnectionResult,
        ):
            raise TypeError(
                "result must be a "
                "MarketDataConnectionResult"
            )

        message = AdapterModelSupport.required_text(
            self.message,
            "message",
        )

        AdapterModelSupport.aware_datetime(
            self.reported_at,
            "reported_at",
        )

        if (
            self.request.connection_id
            != self.result.connection_id
        ):
            raise ValueError(
                "request and result connection_id "
                "values must match"
            )

        if (
            self.request.provider_name
            != self.result.provider_name
        ):
            raise ValueError(
                "request and result provider_name "
                "values must match"
            )

        if (
            self.request.provider_type
            is not self.result.provider_type
        ):
            raise ValueError(
                "request and result provider_type "
                "values must match"
            )

        if (
            self.result.evaluated_at
            < self.request.requested_at
        ):
            raise ValueError(
                "result evaluated_at must not be earlier "
                "than request requested_at"
            )

        if self.reported_at < self.result.evaluated_at:
            raise ValueError(
                "reported_at must not be earlier "
                "than result evaluated_at"
            )

        metadata = AdapterModelSupport.normalize_metadata(
            self.metadata
        )

        object.__setattr__(
            self,
            "report_id",
            report_id,
        )
        object.__setattr__(
            self,
            "message",
            message,
        )
        object.__setattr__(
            self,
            "metadata",
            metadata,
        )


@dataclass(frozen=True, slots=True)
class SubscriptionRequest:
    request_id: str
    connection_id: str
    subscription_id: str
    action: SubscriptionAction
    symbol: str
    market: str
    data_type: MarketDataType
    requested_at: datetime
    requested_by: str
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        request_id = AdapterModelSupport.required_text(
            self.request_id,
            "request_id",
        )
        connection_id = AdapterModelSupport.required_text(
            self.connection_id,
            "connection_id",
        )
        subscription_id = (
            AdapterModelSupport.required_text(
                self.subscription_id,
                "subscription_id",
            )
        )
        symbol = AdapterModelSupport.required_text(
            self.symbol,
            "symbol",
        ).upper()
        market = AdapterModelSupport.required_text(
            self.market,
            "market",
        ).upper()
        requested_by = AdapterModelSupport.required_text(
            self.requested_by,
            "requested_by",
        )

        if not isinstance(
            self.action,
            SubscriptionAction,
        ):
            raise TypeError(
                "action must be a SubscriptionAction"
            )

        if not isinstance(
            self.data_type,
            MarketDataType,
        ):
            raise TypeError(
                "data_type must be a MarketDataType"
            )

        AdapterModelSupport.aware_datetime(
            self.requested_at,
            "requested_at",
        )

        metadata = AdapterModelSupport.normalize_metadata(
            self.metadata
        )

        object.__setattr__(
            self,
            "request_id",
            request_id,
        )
        object.__setattr__(
            self,
            "connection_id",
            connection_id,
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
            "requested_by",
            requested_by,
        )
        object.__setattr__(
            self,
            "metadata",
            metadata,
        )


@dataclass(frozen=True, slots=True)
class SubscriptionResult:
    request_id: str
    connection_id: str
    subscription_id: str
    action: SubscriptionAction
    symbol: str
    market: str
    data_type: MarketDataType
    successful: bool
    evaluated_at: datetime
    provider_subscription_id: str | None = None
    message: str = "Subscription request evaluated."
    error: str | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        request_id = AdapterModelSupport.required_text(
            self.request_id,
            "request_id",
        )
        connection_id = AdapterModelSupport.required_text(
            self.connection_id,
            "connection_id",
        )
        subscription_id = (
            AdapterModelSupport.required_text(
                self.subscription_id,
                "subscription_id",
            )
        )
        symbol = AdapterModelSupport.required_text(
            self.symbol,
            "symbol",
        ).upper()
        market = AdapterModelSupport.required_text(
            self.market,
            "market",
        ).upper()
        message = AdapterModelSupport.required_text(
            self.message,
            "message",
        )
        provider_subscription_id = (
            AdapterModelSupport.optional_text(
                self.provider_subscription_id,
                "provider_subscription_id",
            )
        )
        error = AdapterModelSupport.optional_text(
            self.error,
            "error",
        )

        if not isinstance(
            self.action,
            SubscriptionAction,
        ):
            raise TypeError(
                "action must be a SubscriptionAction"
            )

        if not isinstance(
            self.data_type,
            MarketDataType,
        ):
            raise TypeError(
                "data_type must be a MarketDataType"
            )

        if not isinstance(self.successful, bool):
            raise TypeError(
                "successful must be a bool"
            )

        AdapterModelSupport.aware_datetime(
            self.evaluated_at,
            "evaluated_at",
        )

        if self.successful:
            if error is not None:
                raise ValueError(
                    "successful subscription results "
                    "must not include an error"
                )

            if (
                self.action
                in {
                    SubscriptionAction.SUBSCRIBE,
                    SubscriptionAction.RESUME,
                }
                and provider_subscription_id is None
            ):
                raise ValueError(
                    "successful subscribe and resume "
                    "results require provider_subscription_id"
                )
        else:
            if error is None:
                raise ValueError(
                    "unsuccessful subscription results "
                    "require an error"
                )

        metadata = AdapterModelSupport.normalize_metadata(
            self.metadata
        )

        object.__setattr__(
            self,
            "request_id",
            request_id,
        )
        object.__setattr__(
            self,
            "connection_id",
            connection_id,
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
            "provider_subscription_id",
            provider_subscription_id,
        )
        object.__setattr__(
            self,
            "message",
            message,
        )
        object.__setattr__(
            self,
            "error",
            error,
        )
        object.__setattr__(
            self,
            "metadata",
            metadata,
        )