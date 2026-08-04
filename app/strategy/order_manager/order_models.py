from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.strategy.portfolio_manager import AssetClass


_ZERO = Decimal("0")


class OrderSide(str, Enum):
    """Directional side of an enterprise order."""

    BUY = "BUY"
    SELL = "SELL"
    SELL_SHORT = "SELL_SHORT"
    BUY_TO_COVER = "BUY_TO_COVER"


class OrderType(str, Enum):
    """Supported enterprise order types."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class TimeInForce(str, Enum):
    """Order lifetime instruction."""

    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class OrderStatus(str, Enum):
    """Lifecycle status of an enterprise order."""

    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class ExecutionType(str, Enum):
    """Type of order lifecycle event."""

    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIAL_FILL = "PARTIAL_FILL"
    FILL = "FILL"
    REJECTED = "REJECTED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
    AMENDED = "AMENDED"


class OrderDecision(str, Enum):
    """Decision returned by the order manager."""

    APPROVE = "APPROVE"
    HOLD = "HOLD"
    REJECT = "REJECT"
    CANCEL = "CANCEL"
    NO_ACTION = "NO_ACTION"


_TERMINAL_ORDER_STATUSES = {
    OrderStatus.FILLED,
    OrderStatus.REJECTED,
    OrderStatus.CANCELLED,
    OrderStatus.EXPIRED,
    OrderStatus.FAILED,
}


class OrderModelSupport:
    """Shared validation helpers for order models."""

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
class OrderRequest:
    """Immutable request to create and submit an order."""

    order_id: str
    client_order_id: str
    portfolio_id: str
    symbol: str
    asset_class: AssetClass
    side: OrderSide
    order_type: OrderType
    time_in_force: TimeInForce
    quantity: Decimal
    created_at: datetime
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    expire_at: datetime | None = None
    strategy_id: str | None = None
    parent_order_id: str | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_order_id = (
            OrderModelSupport.required_text(
                self.order_id,
                "order_id",
            )
        )
        normalized_client_order_id = (
            OrderModelSupport.required_text(
                self.client_order_id,
                "client_order_id",
            )
        )
        normalized_portfolio_id = (
            OrderModelSupport.required_text(
                self.portfolio_id,
                "portfolio_id",
            )
        )
        normalized_symbol = (
            OrderModelSupport.required_text(
                self.symbol,
                "symbol",
            ).upper()
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

        OrderModelSupport.require_decimal(
            self.quantity,
            "quantity",
        )

        if self.quantity <= _ZERO:
            raise ValueError(
                "quantity must be greater than zero"
            )

        OrderModelSupport.validate_datetime(
            self.created_at,
            "created_at",
        )

        if self.limit_price is not None:
            OrderModelSupport.require_decimal(
                self.limit_price,
                "limit_price",
            )

            if self.limit_price <= _ZERO:
                raise ValueError(
                    "limit_price must be greater than zero"
                )

        if self.stop_price is not None:
            OrderModelSupport.require_decimal(
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

        if self.expire_at is not None:
            OrderModelSupport.validate_datetime(
                self.expire_at,
                "expire_at",
            )

            if self.expire_at <= self.created_at:
                raise ValueError(
                    "expire_at must be later than created_at"
                )

        if (
            self.time_in_force is TimeInForce.GTC
            and self.expire_at is not None
        ):
            raise ValueError(
                "GTC orders must not include expire_at"
            )

        if (
            self.time_in_force
            in {
                TimeInForce.IOC,
                TimeInForce.FOK,
            }
            and self.expire_at is not None
        ):
            raise ValueError(
                "IOC and FOK orders must not include expire_at"
            )

        normalized_strategy_id = (
            OrderModelSupport.optional_text(
                self.strategy_id,
                "strategy_id",
            )
        )
        normalized_parent_order_id = (
            OrderModelSupport.optional_text(
                self.parent_order_id,
                "parent_order_id",
            )
        )

        if normalized_parent_order_id == normalized_order_id:
            raise ValueError(
                "parent_order_id must differ from order_id"
            )

        normalized_metadata = (
            OrderModelSupport.normalize_pairs(
                self.metadata,
                "metadata",
            )
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
            "portfolio_id",
            normalized_portfolio_id,
        )
        object.__setattr__(
            self,
            "symbol",
            normalized_symbol,
        )
        object.__setattr__(
            self,
            "strategy_id",
            normalized_strategy_id,
        )
        object.__setattr__(
            self,
            "parent_order_id",
            normalized_parent_order_id,
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )


@dataclass(frozen=True, slots=True)
class OrderFill:
    """Immutable execution fill received from a broker."""

    fill_id: str
    order_id: str
    quantity: Decimal
    price: Decimal
    commission: Decimal
    executed_at: datetime
    venue: str
    broker_execution_id: str | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_fill_id = (
            OrderModelSupport.required_text(
                self.fill_id,
                "fill_id",
            )
        )
        normalized_order_id = (
            OrderModelSupport.required_text(
                self.order_id,
                "order_id",
            )
        )
        normalized_venue = (
            OrderModelSupport.required_text(
                self.venue,
                "venue",
            ).upper()
        )

        for field_name in (
            "quantity",
            "price",
            "commission",
        ):
            OrderModelSupport.require_decimal(
                getattr(self, field_name),
                field_name,
            )

        if self.quantity <= _ZERO:
            raise ValueError(
                "fill quantity must be greater than zero"
            )

        if self.price <= _ZERO:
            raise ValueError(
                "fill price must be greater than zero"
            )

        if self.commission < _ZERO:
            raise ValueError(
                "commission must not be negative"
            )

        OrderModelSupport.validate_datetime(
            self.executed_at,
            "executed_at",
        )

        normalized_broker_execution_id = (
            OrderModelSupport.optional_text(
                self.broker_execution_id,
                "broker_execution_id",
            )
        )
        normalized_metadata = (
            OrderModelSupport.normalize_pairs(
                self.metadata,
                "metadata",
            )
        )

        object.__setattr__(
            self,
            "fill_id",
            normalized_fill_id,
        )
        object.__setattr__(
            self,
            "order_id",
            normalized_order_id,
        )
        object.__setattr__(
            self,
            "venue",
            normalized_venue,
        )
        object.__setattr__(
            self,
            "broker_execution_id",
            normalized_broker_execution_id,
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )

    @property
    def gross_value(self) -> Decimal:
        return self.quantity * self.price

    @property
    def net_value(self) -> Decimal:
        return self.gross_value - self.commission


@dataclass(frozen=True, slots=True)
class OrderAllocation:
    """Immutable allocation of a broker fill."""

    allocation_id: str
    fill_id: str
    order_id: str
    portfolio_id: str
    quantity: Decimal
    allocated_at: datetime
    account_id: str | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_allocation_id = (
            OrderModelSupport.required_text(
                self.allocation_id,
                "allocation_id",
            )
        )
        normalized_fill_id = (
            OrderModelSupport.required_text(
                self.fill_id,
                "fill_id",
            )
        )
        normalized_order_id = (
            OrderModelSupport.required_text(
                self.order_id,
                "order_id",
            )
        )
        normalized_portfolio_id = (
            OrderModelSupport.required_text(
                self.portfolio_id,
                "portfolio_id",
            )
        )

        OrderModelSupport.require_decimal(
            self.quantity,
            "quantity",
        )

        if self.quantity <= _ZERO:
            raise ValueError(
                "allocation quantity must be greater than zero"
            )

        OrderModelSupport.validate_datetime(
            self.allocated_at,
            "allocated_at",
        )

        normalized_account_id = (
            OrderModelSupport.optional_text(
                self.account_id,
                "account_id",
            )
        )
        normalized_metadata = (
            OrderModelSupport.normalize_pairs(
                self.metadata,
                "metadata",
            )
        )

        object.__setattr__(
            self,
            "allocation_id",
            normalized_allocation_id,
        )
        object.__setattr__(
            self,
            "fill_id",
            normalized_fill_id,
        )
        object.__setattr__(
            self,
            "order_id",
            normalized_order_id,
        )
        object.__setattr__(
            self,
            "portfolio_id",
            normalized_portfolio_id,
        )
        object.__setattr__(
            self,
            "account_id",
            normalized_account_id,
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )


@dataclass(frozen=True, slots=True)
class OrderExecution:
    """Immutable aggregate order execution state."""

    execution_id: str
    order_id: str
    execution_type: ExecutionType
    status: OrderStatus
    requested_quantity: Decimal
    filled_quantity: Decimal
    remaining_quantity: Decimal
    occurred_at: datetime
    message: str
    fills: tuple[OrderFill, ...] = field(
        default_factory=tuple
    )
    allocations: tuple[OrderAllocation, ...] = field(
        default_factory=tuple
    )
    average_fill_price: Decimal | None = None
    broker_order_id: str | None = None
    error: str | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_execution_id = (
            OrderModelSupport.required_text(
                self.execution_id,
                "execution_id",
            )
        )
        normalized_order_id = (
            OrderModelSupport.required_text(
                self.order_id,
                "order_id",
            )
        )
        normalized_message = (
            OrderModelSupport.required_text(
                self.message,
                "message",
            )
        )

        if not isinstance(
            self.execution_type,
            ExecutionType,
        ):
            raise TypeError(
                "execution_type must be an ExecutionType"
            )

        if not isinstance(self.status, OrderStatus):
            raise TypeError(
                "status must be an OrderStatus"
            )

        for field_name in (
            "requested_quantity",
            "filled_quantity",
            "remaining_quantity",
        ):
            OrderModelSupport.require_decimal(
                getattr(self, field_name),
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

        if (
            self.filled_quantity
            + self.remaining_quantity
            != self.requested_quantity
        ):
            raise ValueError(
                "filled_quantity plus remaining_quantity "
                "must equal requested_quantity"
            )

        OrderModelSupport.validate_datetime(
            self.occurred_at,
            "occurred_at",
        )

        normalized_fills = tuple(self.fills)
        normalized_allocations = tuple(self.allocations)

        for fill in normalized_fills:
            if not isinstance(fill, OrderFill):
                raise TypeError(
                    "every fill must be an OrderFill"
                )

            if fill.order_id != normalized_order_id:
                raise ValueError(
                    "fill order_id must match execution order_id"
                )

            if fill.executed_at > self.occurred_at:
                raise ValueError(
                    "fill executed_at must not be later "
                    "than occurred_at"
                )

        fill_ids = [
            fill.fill_id
            for fill in normalized_fills
        ]

        if len(set(fill_ids)) != len(fill_ids):
            raise ValueError(
                "fill_id values must be unique"
            )

        total_fill_quantity = sum(
            (
                fill.quantity
                for fill in normalized_fills
            ),
            _ZERO,
        )

        if total_fill_quantity != self.filled_quantity:
            raise ValueError(
                "filled_quantity must equal total fill quantity"
            )

        for allocation in normalized_allocations:
            if not isinstance(
                allocation,
                OrderAllocation,
            ):
                raise TypeError(
                    "every allocation must be an "
                    "OrderAllocation"
                )

            if allocation.order_id != normalized_order_id:
                raise ValueError(
                    "allocation order_id must match "
                    "execution order_id"
                )

            if allocation.fill_id not in set(fill_ids):
                raise ValueError(
                    "allocation fill_id must reference "
                    "an execution fill"
                )

            if allocation.allocated_at > self.occurred_at:
                raise ValueError(
                    "allocation allocated_at must not be later "
                    "than occurred_at"
                )

        allocation_ids = [
            allocation.allocation_id
            for allocation in normalized_allocations
        ]

        if len(set(allocation_ids)) != len(
            allocation_ids
        ):
            raise ValueError(
                "allocation_id values must be unique"
            )

        allocation_quantity_by_fill: dict[
            str,
            Decimal,
        ] = {}

        for allocation in normalized_allocations:
            allocation_quantity_by_fill[
                allocation.fill_id
            ] = (
                allocation_quantity_by_fill.get(
                    allocation.fill_id,
                    _ZERO,
                )
                + allocation.quantity
            )

        for fill in normalized_fills:
            allocated_quantity = (
                allocation_quantity_by_fill.get(
                    fill.fill_id,
                    _ZERO,
                )
            )

            if allocated_quantity > fill.quantity:
                raise ValueError(
                    "allocated quantity must not exceed "
                    "fill quantity"
                )

        normalized_average_fill_price = (
            self.average_fill_price
        )

        if self.filled_quantity == _ZERO:
            if normalized_average_fill_price is not None:
                raise ValueError(
                    "unfilled executions must not include "
                    "average_fill_price"
                )
        else:
            if normalized_average_fill_price is None:
                raise ValueError(
                    "filled executions must include "
                    "average_fill_price"
                )

            OrderModelSupport.require_decimal(
                normalized_average_fill_price,
                "average_fill_price",
            )

            weighted_value = sum(
                (
                    fill.quantity * fill.price
                    for fill in normalized_fills
                ),
                _ZERO,
            )

            expected_average = (
                weighted_value / self.filled_quantity
            )

            if (
                normalized_average_fill_price
                != expected_average
            ):
                raise ValueError(
                    "average_fill_price must match fills"
                )

        if self.status is OrderStatus.PARTIALLY_FILLED:
            if not (
                _ZERO
                < self.filled_quantity
                < self.requested_quantity
            ):
                raise ValueError(
                    "partially filled orders require a "
                    "partial filled quantity"
                )

        if self.status is OrderStatus.FILLED:
            if (
                self.filled_quantity
                != self.requested_quantity
            ):
                raise ValueError(
                    "filled orders require the full quantity"
                )

            if self.remaining_quantity != _ZERO:
                raise ValueError(
                    "filled orders must have zero "
                    "remaining_quantity"
                )

        if (
            self.status
            in {
                OrderStatus.CREATED,
                OrderStatus.VALIDATED,
                OrderStatus.SUBMITTED,
                OrderStatus.ACKNOWLEDGED,
                OrderStatus.CANCEL_PENDING,
            }
            and self.filled_quantity != _ZERO
        ):
            raise ValueError(
                "non-fill lifecycle statuses must have "
                "zero filled_quantity"
            )

        normalized_error = (
            OrderModelSupport.optional_text(
                self.error,
                "error",
            )
        )

        if self.status in {
            OrderStatus.REJECTED,
            OrderStatus.FAILED,
        }:
            if normalized_error is None:
                raise ValueError(
                    "rejected and failed executions "
                    "must include an error"
                )
        elif normalized_error is not None:
            raise ValueError(
                "only rejected or failed executions "
                "may include an error"
            )

        normalized_broker_order_id = (
            OrderModelSupport.optional_text(
                self.broker_order_id,
                "broker_order_id",
            )
        )

        if (
            self.status
            in {
                OrderStatus.ACKNOWLEDGED,
                OrderStatus.PARTIALLY_FILLED,
                OrderStatus.FILLED,
                OrderStatus.CANCEL_PENDING,
                OrderStatus.CANCELLED,
            }
            and normalized_broker_order_id is None
        ):
            raise ValueError(
                "broker-managed executions must include "
                "broker_order_id"
            )

        normalized_warnings = (
            OrderModelSupport.normalize_warnings(
                self.warnings
            )
        )

        object.__setattr__(
            self,
            "execution_id",
            normalized_execution_id,
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
            "fills",
            normalized_fills,
        )
        object.__setattr__(
            self,
            "allocations",
            normalized_allocations,
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
            "warnings",
            normalized_warnings,
        )

    @property
    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_ORDER_STATUSES

    @property
    def total_commission(self) -> Decimal:
        return sum(
            (
                fill.commission
                for fill in self.fills
            ),
            _ZERO,
        )


@dataclass(frozen=True, slots=True)
class OrderReport:
    """Unified report returned by the order manager."""

    status: OrderStatus
    decision: OrderDecision
    request: OrderRequest
    execution: OrderExecution | None
    recommendation: str
    reported_at: datetime
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, OrderStatus):
            raise TypeError(
                "status must be an OrderStatus"
            )

        if not isinstance(
            self.decision,
            OrderDecision,
        ):
            raise TypeError(
                "decision must be an OrderDecision"
            )

        if not isinstance(self.request, OrderRequest):
            raise TypeError(
                "request must be an OrderRequest"
            )

        if (
            self.execution is not None
            and not isinstance(
                self.execution,
                OrderExecution,
            )
        ):
            raise TypeError(
                "execution must be an OrderExecution or None"
            )

        normalized_recommendation = (
            OrderModelSupport.required_text(
                self.recommendation,
                "recommendation",
            )
        )

        OrderModelSupport.validate_datetime(
            self.reported_at,
            "reported_at",
        )

        if self.reported_at < self.request.created_at:
            raise ValueError(
                "reported_at must not be earlier than "
                "request created_at"
            )

        if self.execution is not None:
            if (
                self.execution.order_id
                != self.request.order_id
            ):
                raise ValueError(
                    "execution order_id must match request"
                )

            if self.execution.status is not self.status:
                raise ValueError(
                    "report status must match execution status"
                )

            if (
                self.execution.occurred_at
                > self.reported_at
            ):
                raise ValueError(
                    "execution occurred_at must not be later "
                    "than reported_at"
                )

        normalized_error = (
            OrderModelSupport.optional_text(
                self.error,
                "error",
            )
        )

        if self.status in {
            OrderStatus.REJECTED,
            OrderStatus.FAILED,
        }:
            if normalized_error is None:
                raise ValueError(
                    "rejected and failed reports "
                    "must include an error"
                )
        elif normalized_error is not None:
            raise ValueError(
                "only rejected or failed reports "
                "may include an error"
            )

        if (
            self.status
            not in {
                OrderStatus.CREATED,
                OrderStatus.REJECTED,
                OrderStatus.FAILED,
            }
            and self.execution is None
        ):
            raise ValueError(
                "managed order reports must include "
                "an execution"
            )

        if self.decision is OrderDecision.APPROVE:
            if self.status in {
                OrderStatus.REJECTED,
                OrderStatus.FAILED,
                OrderStatus.CANCELLED,
                OrderStatus.EXPIRED,
            }:
                raise ValueError(
                    "approve decisions require an "
                    "eligible order status"
                )

        if self.decision is OrderDecision.REJECT:
            if self.status not in {
                OrderStatus.REJECTED,
                OrderStatus.FAILED,
            }:
                raise ValueError(
                    "reject decisions require rejected "
                    "or failed status"
                )

        if self.decision is OrderDecision.CANCEL:
            if self.status not in {
                OrderStatus.CANCEL_PENDING,
                OrderStatus.CANCELLED,
            }:
                raise ValueError(
                    "cancel decisions require cancellation status"
                )

        normalized_warnings = (
            OrderModelSupport.normalize_warnings(
                self.warnings
            )
        )

        object.__setattr__(
            self,
            "recommendation",
            normalized_recommendation,
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