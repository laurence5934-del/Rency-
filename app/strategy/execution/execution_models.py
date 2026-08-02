from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")


class ExecutionStatus(str, Enum):
    """Lifecycle state of an execution workflow."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExecutionSide(str, Enum):
    """Supported broker-order directions."""

    BUY = "BUY"
    SELL = "SELL"


class ExecutionOrderType(str, Enum):
    """Supported execution-order types."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    """Broker-neutral order submitted to an execution gateway."""

    execution_id: str
    symbol: str
    side: ExecutionSide
    quantity: Decimal
    order_type: ExecutionOrderType
    submitted_at: datetime
    limit_price: Decimal | None = None
    strategy_id: str | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_execution_id = self.execution_id.strip()
        normalized_symbol = self.symbol.strip().upper()

        if not normalized_execution_id:
            raise ValueError(
                "execution_id must not be empty"
            )

        if not normalized_symbol:
            raise ValueError(
                "symbol must not be empty"
            )

        if not isinstance(self.side, ExecutionSide):
            raise TypeError(
                "side must be an ExecutionSide"
            )

        if not isinstance(
            self.order_type,
            ExecutionOrderType,
        ):
            raise TypeError(
                "order_type must be an ExecutionOrderType"
            )

        if not isinstance(self.quantity, Decimal):
            raise TypeError(
                "quantity must be a Decimal"
            )

        if self.quantity <= _ZERO:
            raise ValueError(
                "quantity must be greater than zero"
            )

        if not isinstance(self.submitted_at, datetime):
            raise TypeError(
                "submitted_at must be a datetime"
            )

        if self.submitted_at.tzinfo is None:
            raise ValueError(
                "submitted_at must be timezone-aware"
            )

        if self.limit_price is not None:
            if not isinstance(self.limit_price, Decimal):
                raise TypeError(
                    "limit_price must be a Decimal or None"
                )

            if self.limit_price <= _ZERO:
                raise ValueError(
                    "limit_price must be greater than zero"
                )

        if (
            self.order_type is ExecutionOrderType.LIMIT
            and self.limit_price is None
        ):
            raise ValueError(
                "limit orders must include a limit_price"
            )

        if (
            self.order_type is ExecutionOrderType.MARKET
            and self.limit_price is not None
        ):
            raise ValueError(
                "market orders must not include a limit_price"
            )

        normalized_strategy_id = (
            self.strategy_id.strip()
            if self.strategy_id is not None
            else None
        )

        if (
            self.strategy_id is not None
            and not normalized_strategy_id
        ):
            raise ValueError(
                "strategy_id must not be empty"
            )

        normalized_metadata: list[
            tuple[str, str]
        ] = []

        for item in self.metadata:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
            ):
                raise TypeError(
                    "each metadata item must be a two-item tuple"
                )

            name, value = item
            normalized_name = str(name).strip()
            normalized_value = str(value).strip()

            if not normalized_name:
                raise ValueError(
                    "metadata names must not be empty"
                )

            normalized_metadata.append(
                (
                    normalized_name,
                    normalized_value,
                )
            )

        object.__setattr__(
            self,
            "execution_id",
            normalized_execution_id,
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
            "metadata",
            tuple(normalized_metadata),
        )


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    """Successful broker acknowledgement or fill."""

    execution_id: str
    broker_name: str
    order_id: str
    filled_quantity: Decimal
    average_price: Decimal
    commission: Decimal
    executed_at: datetime

    def __post_init__(self) -> None:
        normalized_execution_id = self.execution_id.strip()
        normalized_broker_name = self.broker_name.strip()
        normalized_order_id = self.order_id.strip()

        if not normalized_execution_id:
            raise ValueError(
                "execution_id must not be empty"
            )

        if not normalized_broker_name:
            raise ValueError(
                "broker_name must not be empty"
            )

        if not normalized_order_id:
            raise ValueError(
                "order_id must not be empty"
            )

        for field_name in (
            "filled_quantity",
            "average_price",
            "commission",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if self.filled_quantity <= _ZERO:
            raise ValueError(
                "filled_quantity must be greater than zero"
            )

        if self.average_price <= _ZERO:
            raise ValueError(
                "average_price must be greater than zero"
            )

        if self.commission < _ZERO:
            raise ValueError(
                "commission must not be negative"
            )

        if not isinstance(self.executed_at, datetime):
            raise TypeError(
                "executed_at must be a datetime"
            )

        if self.executed_at.tzinfo is None:
            raise ValueError(
                "executed_at must be timezone-aware"
            )

        object.__setattr__(
            self,
            "execution_id",
            normalized_execution_id,
        )
        object.__setattr__(
            self,
            "broker_name",
            normalized_broker_name,
        )
        object.__setattr__(
            self,
            "order_id",
            normalized_order_id,
        )


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    """Unified result returned by the execution gateway."""

    status: ExecutionStatus
    request: ExecutionRequest
    receipt: ExecutionReceipt | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.status,
            ExecutionStatus,
        ):
            raise TypeError(
                "status must be an ExecutionStatus"
            )

        if not isinstance(
            self.request,
            ExecutionRequest,
        ):
            raise TypeError(
                "request must be an ExecutionRequest"
            )

        if (
            self.receipt is not None
            and not isinstance(
                self.receipt,
                ExecutionReceipt,
            )
        ):
            raise TypeError(
                "receipt must be an ExecutionReceipt or None"
            )

        if (
            self.receipt is not None
            and self.receipt.execution_id
            != self.request.execution_id
        ):
            raise ValueError(
                "request and receipt execution_id values must match"
            )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if self.status is ExecutionStatus.COMPLETED:
            if self.receipt is None:
                raise ValueError(
                    "completed reports must include a receipt"
                )

            if normalized_error:
                raise ValueError(
                    "completed reports must not include an error"
                )

        if self.status is ExecutionStatus.FAILED:
            if not normalized_error:
                raise ValueError(
                    "failed reports must include an error"
                )

            if self.receipt is not None:
                raise ValueError(
                    "failed reports must not include a receipt"
                )

        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )
        object.__setattr__(
            self,
            "error",
            normalized_error,
        )