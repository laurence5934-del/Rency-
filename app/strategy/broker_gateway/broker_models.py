from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.strategy.order_manager import (
    OrderSide,
    OrderType,
    TimeInForce,
)
from app.strategy.portfolio_manager import AssetClass


_ZERO = Decimal("0")


class BrokerEnvironment(str, Enum):
    """Execution environment used by a broker connection."""

    PAPER = "PAPER"
    LIVE = "LIVE"


class BrokerConnectionState(str, Enum):
    """Current connectivity state of a broker adapter."""

    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class BrokerStatus(str, Enum):
    """Overall result status of a broker-gateway operation."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class BrokerDecision(str, Enum):
    """Decision returned by the broker gateway."""

    APPROVE = "APPROVE"
    HOLD = "HOLD"
    REJECT = "REJECT"
    RETRY = "RETRY"
    NO_ACTION = "NO_ACTION"


class BrokerOrderStatus(str, Enum):
    """Broker-facing order lifecycle status."""

    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class BrokerCapability(str, Enum):
    """Capability exposed by a broker adapter."""

    MARKET_ORDERS = "MARKET_ORDERS"
    LIMIT_ORDERS = "LIMIT_ORDERS"
    STOP_ORDERS = "STOP_ORDERS"
    STOP_LIMIT_ORDERS = "STOP_LIMIT_ORDERS"
    SHORT_SELLING = "SHORT_SELLING"
    FRACTIONAL_SHARES = "FRACTIONAL_SHARES"
    EXTENDED_HOURS = "EXTENDED_HOURS"
    OPTIONS = "OPTIONS"
    PAPER_TRADING = "PAPER_TRADING"
    LIVE_TRADING = "LIVE_TRADING"


_TERMINAL_BROKER_ORDER_STATUSES = {
    BrokerOrderStatus.FILLED,
    BrokerOrderStatus.CANCELLED,
    BrokerOrderStatus.REJECTED,
    BrokerOrderStatus.EXPIRED,
    BrokerOrderStatus.FAILED,
}


class BrokerModelSupport:
    """Shared validation helpers for broker-gateway models."""

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
    def require_decimal(
        value: Decimal,
        field_name: str,
    ) -> None:
        if not isinstance(value, Decimal):
            raise TypeError(
                f"{field_name} must be a Decimal"
            )

    @staticmethod
    def validate_datetime(
        value: datetime,
        field_name: str,
    ) -> None:
        if not isinstance(value, datetime):
            raise TypeError(
                f"{field_name} must be a datetime"
            )

        if value.tzinfo is None:
            raise ValueError(
                f"{field_name} must be timezone-aware"
            )

    @staticmethod
    def normalize_pairs(
        values: tuple[tuple[str, str], ...]
        | list[tuple[str, str]],
        collection_name: str,
    ) -> tuple[tuple[str, str], ...]:
        normalized: list[tuple[str, str]] = []
        seen_keys: set[str] = set()

        for item in values:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
            ):
                raise TypeError(
                    f"each {collection_name} item must be "
                    "a two-item tuple"
                )

            raw_key, raw_value = item
            key = str(raw_key).strip()
            value = str(raw_value).strip()

            if not key:
                raise ValueError(
                    f"{collection_name} keys must not be empty"
                )

            if key in seen_keys:
                raise ValueError(
                    f"{collection_name} keys must be unique"
                )

            seen_keys.add(key)
            normalized.append((key, value))

        return tuple(normalized)

    @staticmethod
    def normalize_warnings(
        warnings: tuple[str, ...] | list[str],
    ) -> tuple[str, ...]:
        normalized: list[str] = []

        for warning in warnings:
            if not isinstance(warning, str):
                raise TypeError(
                    "every warning must be a string"
                )

            value = warning.strip()

            if not value:
                raise ValueError(
                    "warnings must not contain empty values"
                )

            normalized.append(value)

        return tuple(normalized)


@dataclass(frozen=True, slots=True)
class BrokerAccount:
    """Immutable broker account and buying-power snapshot."""

    account_id: str
    broker_name: str
    environment: BrokerEnvironment
    connection_state: BrokerConnectionState
    currency: str
    cash_balance: Decimal
    settled_cash: Decimal
    buying_power: Decimal
    equity: Decimal
    margin_used: Decimal
    updated_at: datetime
    capabilities: tuple[BrokerCapability, ...] = field(
        default_factory=tuple
    )
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_account_id = (
            BrokerModelSupport.required_text(
                self.account_id,
                "account_id",
            )
        )
        normalized_broker_name = (
            BrokerModelSupport.required_text(
                self.broker_name,
                "broker_name",
            )
        )
        normalized_currency = (
            BrokerModelSupport.required_text(
                self.currency,
                "currency",
            ).upper()
        )

        if not isinstance(
            self.environment,
            BrokerEnvironment,
        ):
            raise TypeError(
                "environment must be a BrokerEnvironment"
            )

        if not isinstance(
            self.connection_state,
            BrokerConnectionState,
        ):
            raise TypeError(
                "connection_state must be a "
                "BrokerConnectionState"
            )

        for field_name in (
            "cash_balance",
            "settled_cash",
            "buying_power",
            "equity",
            "margin_used",
        ):
            value = getattr(self, field_name)

            BrokerModelSupport.require_decimal(
                value,
                field_name,
            )

            if value < _ZERO:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        if self.settled_cash > self.cash_balance:
            raise ValueError(
                "settled_cash must not exceed cash_balance"
            )

        if self.margin_used > self.equity:
            raise ValueError(
                "margin_used must not exceed equity"
            )

        BrokerModelSupport.validate_datetime(
            self.updated_at,
            "updated_at",
        )

        normalized_capabilities = tuple(
            self.capabilities
        )

        for capability in normalized_capabilities:
            if not isinstance(
                capability,
                BrokerCapability,
            ):
                raise TypeError(
                    "every capability must be a "
                    "BrokerCapability"
                )

        if len(set(normalized_capabilities)) != len(
            normalized_capabilities
        ):
            raise ValueError(
                "capabilities must be unique"
            )

        if (
            self.environment is BrokerEnvironment.PAPER
            and BrokerCapability.LIVE_TRADING
            in normalized_capabilities
        ):
            raise ValueError(
                "paper accounts must not advertise "
                "LIVE_TRADING capability"
            )

        if (
            self.environment is BrokerEnvironment.LIVE
            and BrokerCapability.PAPER_TRADING
            in normalized_capabilities
        ):
            raise ValueError(
                "live accounts must not advertise "
                "PAPER_TRADING capability"
            )

        normalized_metadata = (
            BrokerModelSupport.normalize_pairs(
                self.metadata,
                "metadata",
            )
        )
        normalized_warnings = (
            BrokerModelSupport.normalize_warnings(
                self.warnings
            )
        )

        object.__setattr__(
            self,
            "account_id",
            normalized_account_id,
        )
        object.__setattr__(
            self,
            "broker_name",
            normalized_broker_name,
        )
        object.__setattr__(
            self,
            "currency",
            normalized_currency,
        )
        object.__setattr__(
            self,
            "capabilities",
            normalized_capabilities,
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )
        object.__setattr__(
            self,
            "warnings",
            normalized_warnings,
        )

    @property
    def is_connected(self) -> bool:
        return (
            self.connection_state
            is BrokerConnectionState.CONNECTED
        )

    @property
    def available_equity(self) -> Decimal:
        return self.equity - self.margin_used


@dataclass(frozen=True, slots=True)
class BrokerOrderRequest:
    """Immutable order translated for broker submission."""

    gateway_order_id: str
    order_id: str
    client_order_id: str
    broker_name: str
    account_id: str
    environment: BrokerEnvironment
    symbol: str
    asset_class: AssetClass
    side: OrderSide
    order_type: OrderType
    time_in_force: TimeInForce
    quantity: Decimal
    submitted_at: datetime
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    allow_extended_hours: bool = False
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_gateway_order_id = (
            BrokerModelSupport.required_text(
                self.gateway_order_id,
                "gateway_order_id",
            )
        )
        normalized_order_id = (
            BrokerModelSupport.required_text(
                self.order_id,
                "order_id",
            )
        )
        normalized_client_order_id = (
            BrokerModelSupport.required_text(
                self.client_order_id,
                "client_order_id",
            )
        )
        normalized_broker_name = (
            BrokerModelSupport.required_text(
                self.broker_name,
                "broker_name",
            )
        )
        normalized_account_id = (
            BrokerModelSupport.required_text(
                self.account_id,
                "account_id",
            )
        )
        normalized_symbol = (
            BrokerModelSupport.required_text(
                self.symbol,
                "symbol",
            ).upper()
        )

        if not isinstance(
            self.environment,
            BrokerEnvironment,
        ):
            raise TypeError(
                "environment must be a BrokerEnvironment"
            )

        if not isinstance(self.asset_class, AssetClass):
            raise TypeError(
                "asset_class must be an AssetClass"
            )

        if not isinstance(self.side, OrderSide):
            raise TypeError(
                "side must be an OrderSide"
            )

        if not isinstance(self.order_type, OrderType):
            raise TypeError(
                "order_type must be an OrderType"
            )

        if not isinstance(
            self.time_in_force,
            TimeInForce,
        ):
            raise TypeError(
                "time_in_force must be a TimeInForce"
            )

        BrokerModelSupport.require_decimal(
            self.quantity,
            "quantity",
        )

        if self.quantity <= _ZERO:
            raise ValueError(
                "quantity must be greater than zero"
            )

        BrokerModelSupport.validate_datetime(
            self.submitted_at,
            "submitted_at",
        )

        if not isinstance(
            self.allow_extended_hours,
            bool,
        ):
            raise TypeError(
                "allow_extended_hours must be a bool"
            )

        if self.limit_price is not None:
            BrokerModelSupport.require_decimal(
                self.limit_price,
                "limit_price",
            )

            if self.limit_price <= _ZERO:
                raise ValueError(
                    "limit_price must be greater than zero"
                )

        if self.stop_price is not None:
            BrokerModelSupport.require_decimal(
                self.stop_price,
                "stop_price",
            )

            if self.stop_price <= _ZERO:
                raise ValueError(
                    "stop_price must be greater than zero"
                )

        if self.order_type is OrderType.MARKET:
            if self.limit_price is not None:
                raise ValueError(
                    "market orders must not include limit_price"
                )

            if self.stop_price is not None:
                raise ValueError(
                    "market orders must not include stop_price"
                )

        if self.order_type is OrderType.LIMIT:
            if self.limit_price is None:
                raise ValueError(
                    "limit orders must include limit_price"
                )

            if self.stop_price is not None:
                raise ValueError(
                    "limit orders must not include stop_price"
                )

        if self.order_type is OrderType.STOP:
            if self.stop_price is None:
                raise ValueError(
                    "stop orders must include stop_price"
                )

            if self.limit_price is not None:
                raise ValueError(
                    "stop orders must not include limit_price"
                )

        if self.order_type is OrderType.STOP_LIMIT:
            if self.stop_price is None:
                raise ValueError(
                    "stop-limit orders must include stop_price"
                )

            if self.limit_price is None:
                raise ValueError(
                    "stop-limit orders must include limit_price"
                )

        if (
            self.allow_extended_hours
            and self.order_type is OrderType.MARKET
        ):
            raise ValueError(
                "extended-hours orders must not use "
                "MARKET order type"
            )

        normalized_metadata = (
            BrokerModelSupport.normalize_pairs(
                self.metadata,
                "metadata",
            )
        )

        object.__setattr__(
            self,
            "gateway_order_id",
            normalized_gateway_order_id,
        )
        object.__setattr__(
            self,
            "order_id",
            normalized_order_id,
        )
        object.__setattr__(
            self,
            "client_order_id",
            normalized_client_order_id,
        )
        object.__setattr__(
            self,
            "broker_name",
            normalized_broker_name,
        )
        object.__setattr__(
            self,
            "account_id",
            normalized_account_id,
        )
        object.__setattr__(
            self,
            "symbol",
            normalized_symbol,
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )


@dataclass(frozen=True, slots=True)
class BrokerOrderResponse:
    """Immutable acknowledgement or rejection from a broker."""

    response_id: str
    gateway_order_id: str
    order_id: str
    status: BrokerOrderStatus
    received_at: datetime
    message: str
    broker_order_id: str | None = None
    error: str | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_response_id = (
            BrokerModelSupport.required_text(
                self.response_id,
                "response_id",
            )
        )
        normalized_gateway_order_id = (
            BrokerModelSupport.required_text(
                self.gateway_order_id,
                "gateway_order_id",
            )
        )
        normalized_order_id = (
            BrokerModelSupport.required_text(
                self.order_id,
                "order_id",
            )
        )
        normalized_message = (
            BrokerModelSupport.required_text(
                self.message,
                "message",
            )
        )

        if not isinstance(
            self.status,
            BrokerOrderStatus,
        ):
            raise TypeError(
                "status must be a BrokerOrderStatus"
            )

        BrokerModelSupport.validate_datetime(
            self.received_at,
            "received_at",
        )

        normalized_broker_order_id = (
            BrokerModelSupport.optional_text(
                self.broker_order_id,
                "broker_order_id",
            )
        )
        normalized_error = (
            BrokerModelSupport.optional_text(
                self.error,
                "error",
            )
        )

        if self.status in {
            BrokerOrderStatus.ACKNOWLEDGED,
            BrokerOrderStatus.PARTIALLY_FILLED,
            BrokerOrderStatus.FILLED,
            BrokerOrderStatus.CANCEL_PENDING,
            BrokerOrderStatus.CANCELLED,
        }:
            if normalized_broker_order_id is None:
                raise ValueError(
                    "broker-managed responses must include "
                    "broker_order_id"
                )

        if self.status in {
            BrokerOrderStatus.REJECTED,
            BrokerOrderStatus.FAILED,
        }:
            if normalized_error is None:
                raise ValueError(
                    "rejected and failed responses must "
                    "include an error"
                )
        elif normalized_error is not None:
            raise ValueError(
                "only rejected or failed responses may "
                "include an error"
            )

        normalized_metadata = (
            BrokerModelSupport.normalize_pairs(
                self.metadata,
                "metadata",
            )
        )
        normalized_warnings = (
            BrokerModelSupport.normalize_warnings(
                self.warnings
            )
        )

        object.__setattr__(
            self,
            "response_id",
            normalized_response_id,
        )
        object.__setattr__(
            self,
            "gateway_order_id",
            normalized_gateway_order_id,
        )
        object.__setattr__(
            self,
            "order_id",
            normalized_order_id,
        )
        object.__setattr__(
            self,
            "message",
            normalized_message,
        )
        object.__setattr__(
            self,
            "broker_order_id",
            normalized_broker_order_id,
        )
        object.__setattr__(
            self,
            "error",
            normalized_error,
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )
        object.__setattr__(
            self,
            "warnings",
            normalized_warnings,
        )

    @property
    def is_terminal(self) -> bool:
        return (
            self.status
            in _TERMINAL_BROKER_ORDER_STATUSES
        )


@dataclass(frozen=True, slots=True)
class BrokerExecutionReport:
    """Immutable broker execution-state snapshot."""

    report_id: str
    gateway_order_id: str
    order_id: str
    broker_order_id: str
    status: BrokerOrderStatus
    requested_quantity: Decimal
    filled_quantity: Decimal
    remaining_quantity: Decimal
    commission: Decimal
    occurred_at: datetime
    venue: str
    average_fill_price: Decimal | None = None
    error: str | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_report_id = (
            BrokerModelSupport.required_text(
                self.report_id,
                "report_id",
            )
        )
        normalized_gateway_order_id = (
            BrokerModelSupport.required_text(
                self.gateway_order_id,
                "gateway_order_id",
            )
        )
        normalized_order_id = (
            BrokerModelSupport.required_text(
                self.order_id,
                "order_id",
            )
        )
        normalized_broker_order_id = (
            BrokerModelSupport.required_text(
                self.broker_order_id,
                "broker_order_id",
            )
        )
        normalized_venue = (
            BrokerModelSupport.required_text(
                self.venue,
                "venue",
            ).upper()
        )

        if not isinstance(
            self.status,
            BrokerOrderStatus,
        ):
            raise TypeError(
                "status must be a BrokerOrderStatus"
            )

        for field_name in (
            "requested_quantity",
            "filled_quantity",
            "remaining_quantity",
            "commission",
        ):
            value = getattr(self, field_name)

            BrokerModelSupport.require_decimal(
                value,
                field_name,
            )

        if self.requested_quantity <= _ZERO:
            raise ValueError(
                "requested_quantity must be greater than zero"
            )

        if self.filled_quantity < _ZERO:
            raise ValueError(
                "filled_quantity must not be negative"
            )

        if self.remaining_quantity < _ZERO:
            raise ValueError(
                "remaining_quantity must not be negative"
            )

        if self.commission < _ZERO:
            raise ValueError(
                "commission must not be negative"
            )

        if (
            self.filled_quantity
            + self.remaining_quantity
            != self.requested_quantity
        ):
            raise ValueError(
                "filled_quantity plus remaining_quantity "
                "must equal requested_quantity"
            )

        BrokerModelSupport.validate_datetime(
            self.occurred_at,
            "occurred_at",
        )

        if self.filled_quantity == _ZERO:
            if self.average_fill_price is not None:
                raise ValueError(
                    "unfilled reports must not include "
                    "average_fill_price"
                )
        else:
            if self.average_fill_price is None:
                raise ValueError(
                    "filled reports must include "
                    "average_fill_price"
                )

            BrokerModelSupport.require_decimal(
                self.average_fill_price,
                "average_fill_price",
            )

            if self.average_fill_price <= _ZERO:
                raise ValueError(
                    "average_fill_price must be greater than zero"
                )

        if (
            self.status
            is BrokerOrderStatus.PARTIALLY_FILLED
            and not (
                _ZERO
                < self.filled_quantity
                < self.requested_quantity
            )
        ):
            raise ValueError(
                "partially filled reports require a "
                "partial filled quantity"
            )

        if self.status is BrokerOrderStatus.FILLED:
            if self.filled_quantity != self.requested_quantity:
                raise ValueError(
                    "filled reports require the full quantity"
                )

            if self.remaining_quantity != _ZERO:
                raise ValueError(
                    "filled reports must have zero "
                    "remaining_quantity"
                )

        normalized_error = (
            BrokerModelSupport.optional_text(
                self.error,
                "error",
            )
        )

        if self.status in {
            BrokerOrderStatus.REJECTED,
            BrokerOrderStatus.FAILED,
        }:
            if normalized_error is None:
                raise ValueError(
                    "rejected and failed reports must "
                    "include an error"
                )
        elif normalized_error is not None:
            raise ValueError(
                "only rejected or failed reports may "
                "include an error"
            )

        normalized_metadata = (
            BrokerModelSupport.normalize_pairs(
                self.metadata,
                "metadata",
            )
        )
        normalized_warnings = (
            BrokerModelSupport.normalize_warnings(
                self.warnings
            )
        )

        object.__setattr__(
            self,
            "report_id",
            normalized_report_id,
        )
        object.__setattr__(
            self,
            "gateway_order_id",
            normalized_gateway_order_id,
        )
        object.__setattr__(
            self,
            "order_id",
            normalized_order_id,
        )
        object.__setattr__(
            self,
            "broker_order_id",
            normalized_broker_order_id,
        )
        object.__setattr__(
            self,
            "venue",
            normalized_venue,
        )
        object.__setattr__(
            self,
            "error",
            normalized_error,
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )
        object.__setattr__(
            self,
            "warnings",
            normalized_warnings,
        )

    @property
    def is_terminal(self) -> bool:
        return (
            self.status
            in _TERMINAL_BROKER_ORDER_STATUSES
        )


@dataclass(frozen=True, slots=True)
class BrokerHealthReport:
    """Immutable health snapshot for a broker adapter."""

    health_id: str
    broker_name: str
    environment: BrokerEnvironment
    connection_state: BrokerConnectionState
    status: BrokerStatus
    decision: BrokerDecision
    checked_at: datetime
    latency_ms: int
    account_accessible: bool
    order_submission_available: bool
    message: str
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        normalized_health_id = (
            BrokerModelSupport.required_text(
                self.health_id,
                "health_id",
            )
        )
        normalized_broker_name = (
            BrokerModelSupport.required_text(
                self.broker_name,
                "broker_name",
            )
        )
        normalized_message = (
            BrokerModelSupport.required_text(
                self.message,
                "message",
            )
        )

        if not isinstance(
            self.environment,
            BrokerEnvironment,
        ):
            raise TypeError(
                "environment must be a BrokerEnvironment"
            )

        if not isinstance(
            self.connection_state,
            BrokerConnectionState,
        ):
            raise TypeError(
                "connection_state must be a "
                "BrokerConnectionState"
            )

        if not isinstance(self.status, BrokerStatus):
            raise TypeError(
                "status must be a BrokerStatus"
            )

        if not isinstance(
            self.decision,
            BrokerDecision,
        ):
            raise TypeError(
                "decision must be a BrokerDecision"
            )

        BrokerModelSupport.validate_datetime(
            self.checked_at,
            "checked_at",
        )

        if not isinstance(self.latency_ms, int):
            raise TypeError(
                "latency_ms must be an integer"
            )

        if self.latency_ms < 0:
            raise ValueError(
                "latency_ms must not be negative"
            )

        if not isinstance(
            self.account_accessible,
            bool,
        ):
            raise TypeError(
                "account_accessible must be a bool"
            )

        if not isinstance(
            self.order_submission_available,
            bool,
        ):
            raise TypeError(
                "order_submission_available must be a bool"
            )

        if (
            self.connection_state
            is not BrokerConnectionState.CONNECTED
            and self.order_submission_available
        ):
            raise ValueError(
                "order submission requires a connected broker"
            )

        if (
            self.order_submission_available
            and not self.account_accessible
        ):
            raise ValueError(
                "order submission requires account access"
            )

        normalized_error = (
            BrokerModelSupport.optional_text(
                self.error,
                "error",
            )
        )

        if self.status is BrokerStatus.FAILED:
            if normalized_error is None:
                raise ValueError(
                    "failed health reports must include an error"
                )
        elif normalized_error is not None:
            raise ValueError(
                "only failed health reports may include an error"
            )

        if self.decision is BrokerDecision.APPROVE:
            if not self.order_submission_available:
                raise ValueError(
                    "approve decisions require order submission "
                    "availability"
                )

        if self.decision is BrokerDecision.REJECT:
            if self.order_submission_available:
                raise ValueError(
                    "reject decisions require order submission "
                    "to be unavailable"
                )

        normalized_warnings = (
            BrokerModelSupport.normalize_warnings(
                self.warnings
            )
        )

        object.__setattr__(
            self,
            "health_id",
            normalized_health_id,
        )
        object.__setattr__(
            self,
            "broker_name",
            normalized_broker_name,
        )
        object.__setattr__(
            self,
            "message",
            normalized_message,
        )
        object.__setattr__(
            self,
            "warnings",
            normalized_warnings,
        )
        object.__setattr__(
            self,
            "error",
            normalized_error,
        )