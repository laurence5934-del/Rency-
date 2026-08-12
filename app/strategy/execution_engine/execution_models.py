from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import TypeAlias

class ExecutionAction(str, Enum):
    SUBMIT = "SUBMIT"
    REPLACE = "REPLACE"
    CANCEL = "CANCEL"
    HOLD = "HOLD"


class ExecutionSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    SELL_SHORT = "SELL_SHORT"
    BUY_TO_COVER = "BUY_TO_COVER"
    NONE = "NONE"


class ExecutionOrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class ExecutionTimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ExecutionDecision(str, Enum):
    NO_ACTION = "NO_ACTION"
    PROCEED = "PROCEED"
    SUBMIT = "SUBMIT"
    RETRY = "RETRY"
    CANCEL = "CANCEL"
    REJECT = "REJECT"


class ExecutionStage(str, Enum):
    RECEIVED = "RECEIVED"
    VALIDATION = "VALIDATION"
    PREPARATION = "PREPARATION"
    SUBMISSION = "SUBMISSION"
    MONITORING = "MONITORING"
    FINALIZATION = "FINALIZATION"


TERMINAL_EXECUTION_STATUSES = frozenset(
    {
        ExecutionStatus.FILLED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.REJECTED,
        ExecutionStatus.FAILED,
    }
)

Metadata: TypeAlias = tuple[tuple[str, str], ...]


def _normalize_required_text(
    value: object,
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


def _normalize_metadata(
    metadata: object,
) -> Metadata:
    if not isinstance(metadata, tuple):
        raise TypeError(
            "metadata must be a tuple"
        )

    normalized: list[tuple[str, str]] = []
    seen: set[str] = set()

    for item in metadata:
        if (
            not isinstance(item, tuple)
            or len(item) != 2
        ):
            raise TypeError(
                "metadata items must be pairs"
            )

        key, value = item

        if not isinstance(key, str):
            raise TypeError(
                "metadata keys must be strings"
            )

        if not isinstance(value, str):
            raise TypeError(
                "metadata values must be strings"
            )

        normalized_key = key.strip()
        normalized_value = value.strip()

        if not normalized_key:
            raise ValueError(
                "metadata keys must not be empty"
            )

        if normalized_key in seen:
            raise ValueError(
                "metadata keys must be unique"
            )

        seen.add(normalized_key)

        normalized.append(
            (
                normalized_key,
                normalized_value,
            )
        )

    return tuple(normalized)


def _require_aware_datetime(
    value: object,
    field_name: str,
) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(
            f"{field_name} must be a datetime"
        )

    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(
            f"{field_name} must be timezone-aware"
        )

    return value


def _normalize_optional_price(
    value: object,
    field_name: str,
) -> float | None:
    if value is None:
        return None

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise TypeError(
            f"{field_name} must be a number"
        )

    normalized = float(value)

    if (
        not isfinite(normalized)
        or normalized <= 0
    ):
        raise ValueError(
            f"{field_name} must be positive"
        )

    return normalized


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    request_id: str
    correlation_id: str
    strategy_id: str
    portfolio_id: str
    allocation_id: str
    signal_id: str
    intent_id: str
    plan_id: str
    symbol: str

    action: ExecutionAction
    side: ExecutionSide
    order_type: ExecutionOrderType
    time_in_force: ExecutionTimeInForce

    quantity: int
    confidence: int

    created_at: datetime
    requested_by: str

    limit_price: float | None = None
    stop_price: float | None = None

    sequence_number: int = 0
    replay: bool = False
    metadata: Metadata = ()

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "correlation_id",
            "strategy_id",
            "portfolio_id",
            "allocation_id",
            "signal_id",
            "intent_id",
            "plan_id",
            "symbol",
            "requested_by",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalize_required_text(
                    getattr(self, field_name),
                    field_name,
                ),
            )

        if not isinstance(
            self.action,
            ExecutionAction,
        ):
            raise TypeError(
                "action must be an ExecutionAction"
            )

        if not isinstance(
            self.side,
            ExecutionSide,
        ):
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

        if not isinstance(
            self.time_in_force,
            ExecutionTimeInForce,
        ):
            raise TypeError(
                "time_in_force must be an "
                "ExecutionTimeInForce"
            )

        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
        ):
            raise TypeError(
                "quantity must be an integer"
            )

        if self.quantity <= 0:
            raise ValueError(
                "quantity must be positive"
            )

        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, int)
        ):
            raise TypeError(
                "confidence must be an integer"
            )

        if not 0 <= self.confidence <= 100:
            raise ValueError(
                "confidence must be between 0 and 100"
            )

        if (
            isinstance(self.sequence_number, bool)
            or not isinstance(
                self.sequence_number,
                int,
            )
        ):
            raise TypeError(
                "sequence_number must be an integer"
            )

        if self.sequence_number < 0:
            raise ValueError(
                "sequence_number must not be negative"
            )

        if not isinstance(self.replay, bool):
            raise TypeError(
                "replay must be a bool"
            )

        object.__setattr__(
            self,
            "created_at",
            _require_aware_datetime(
                self.created_at,
                "created_at",
            ),
        )

        object.__setattr__(
            self,
            "limit_price",
            _normalize_optional_price(
                self.limit_price,
                "limit_price",
            ),
        )

        object.__setattr__(
            self,
            "stop_price",
            _normalize_optional_price(
                self.stop_price,
                "stop_price",
            ),
        )

        object.__setattr__(
            self,
            "metadata",
            _normalize_metadata(
                self.metadata
            ),
        )

        self._validate_execution_contract()

    def _validate_execution_contract(
        self,
    ) -> None:
        if self.action is ExecutionAction.HOLD:
            if self.side is not ExecutionSide.NONE:
                raise ValueError(
                    "HOLD execution requests "
                    "require NONE side"
                )
        elif self.side is ExecutionSide.NONE:
            raise ValueError(
                "actionable execution requests "
                "require an actionable side"
            )

        if (
            self.order_type
            is ExecutionOrderType.MARKET
        ):
            if self.limit_price is not None:
                raise ValueError(
                    "MARKET orders must not "
                    "define limit_price"
                )

            if self.stop_price is not None:
                raise ValueError(
                    "MARKET orders must not "
                    "define stop_price"
                )

        elif (
            self.order_type
            is ExecutionOrderType.LIMIT
        ):
            if self.limit_price is None:
                raise ValueError(
                    "LIMIT orders require limit_price"
                )

            if self.stop_price is not None:
                raise ValueError(
                    "LIMIT orders must not "
                    "define stop_price"
                )

        elif (
            self.order_type
            is ExecutionOrderType.STOP
        ):
            if self.stop_price is None:
                raise ValueError(
                    "STOP orders require stop_price"
                )

            if self.limit_price is not None:
                raise ValueError(
                    "STOP orders must not "
                    "define limit_price"
                )

        elif (
            self.order_type
            is ExecutionOrderType.STOP_LIMIT
        ):
            if self.limit_price is None:
                raise ValueError(
                    "STOP_LIMIT orders require "
                    "limit_price"
                )

            if self.stop_price is None:
                raise ValueError(
                    "STOP_LIMIT orders require "
                    "stop_price"
                )

    @property
    def is_actionable(self) -> bool:
        return (
            self.action
            is not ExecutionAction.HOLD
        )

    @property
    def is_market_order(self) -> bool:
        return (
            self.order_type
            is ExecutionOrderType.MARKET
        )

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 80

@dataclass(frozen=True, slots=True)
class ExecutionOrder:
    order_id: str
    request_id: str
    correlation_id: str
    strategy_id: str
    portfolio_id: str
    allocation_id: str
    signal_id: str
    intent_id: str
    plan_id: str
    symbol: str

    action: ExecutionAction
    side: ExecutionSide
    order_type: ExecutionOrderType
    time_in_force: ExecutionTimeInForce

    quantity: int
    confidence: int

    created_at: datetime
    prepared_at: datetime

    rationale: str

    limit_price: float | None = None
    stop_price: float | None = None

    warnings: tuple[str, ...] = ()
    metadata: Metadata = ()

    def __post_init__(self) -> None:
        for field_name in (
            "order_id",
            "request_id",
            "correlation_id",
            "strategy_id",
            "portfolio_id",
            "allocation_id",
            "signal_id",
            "intent_id",
            "plan_id",
            "symbol",
            "rationale",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalize_required_text(
                    getattr(self, field_name),
                    field_name,
                ),
            )

        if not isinstance(
            self.action,
            ExecutionAction,
        ):
            raise TypeError(
                "action must be an ExecutionAction"
            )

        if not isinstance(
            self.side,
            ExecutionSide,
        ):
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

        if not isinstance(
            self.time_in_force,
            ExecutionTimeInForce,
        ):
            raise TypeError(
                "time_in_force must be an "
                "ExecutionTimeInForce"
            )

        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
        ):
            raise TypeError(
                "quantity must be an integer"
            )

        if self.quantity <= 0:
            raise ValueError(
                "quantity must be positive"
            )

        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, int)
        ):
            raise TypeError(
                "confidence must be an integer"
            )

        if not 0 <= self.confidence <= 100:
            raise ValueError(
                "confidence must be between 0 and 100"
            )

        object.__setattr__(
            self,
            "created_at",
            _require_aware_datetime(
                self.created_at,
                "created_at",
            ),
        )

        object.__setattr__(
            self,
            "prepared_at",
            _require_aware_datetime(
                self.prepared_at,
                "prepared_at",
            ),
        )

        if self.prepared_at < self.created_at:
            raise ValueError(
                "prepared_at must not be earlier "
                "than created_at"
            )

        object.__setattr__(
            self,
            "limit_price",
            _normalize_optional_price(
                self.limit_price,
                "limit_price",
            ),
        )

        object.__setattr__(
            self,
            "stop_price",
            _normalize_optional_price(
                self.stop_price,
                "stop_price",
            ),
        )

        object.__setattr__(
            self,
            "warnings",
            self._normalize_warnings(
                self.warnings
            ),
        )

        object.__setattr__(
            self,
            "metadata",
            _normalize_metadata(
                self.metadata
            ),
        )

        self._validate_execution_contract()

    @staticmethod
    def _normalize_warnings(
        warnings: object,
    ) -> tuple[str, ...]:
        if not isinstance(warnings, tuple):
            raise TypeError(
                "warnings must be a tuple"
            )

        normalized: list[str] = []
        seen: set[str] = set()

        for warning in warnings:
            if not isinstance(warning, str):
                raise TypeError(
                    "every warning must be a string"
                )

            value = warning.strip()

            if not value:
                raise ValueError(
                    "warnings must not contain "
                    "empty values"
                )

            if value not in seen:
                seen.add(value)
                normalized.append(value)

        return tuple(normalized)

    def _validate_execution_contract(
        self,
    ) -> None:
        if self.action is ExecutionAction.HOLD:
            if self.side is not ExecutionSide.NONE:
                raise ValueError(
                    "HOLD execution orders "
                    "require NONE side"
                )
        elif self.side is ExecutionSide.NONE:
            raise ValueError(
                "actionable execution orders "
                "require an actionable side"
            )

        if (
            self.order_type
            is ExecutionOrderType.MARKET
        ):
            if self.limit_price is not None:
                raise ValueError(
                    "MARKET orders must not "
                    "define limit_price"
                )

            if self.stop_price is not None:
                raise ValueError(
                    "MARKET orders must not "
                    "define stop_price"
                )

        elif (
            self.order_type
            is ExecutionOrderType.LIMIT
        ):
            if self.limit_price is None:
                raise ValueError(
                    "LIMIT orders require limit_price"
                )

            if self.stop_price is not None:
                raise ValueError(
                    "LIMIT orders must not "
                    "define stop_price"
                )

        elif (
            self.order_type
            is ExecutionOrderType.STOP
        ):
            if self.stop_price is None:
                raise ValueError(
                    "STOP orders require stop_price"
                )

            if self.limit_price is not None:
                raise ValueError(
                    "STOP orders must not "
                    "define limit_price"
                )

        elif (
            self.order_type
            is ExecutionOrderType.STOP_LIMIT
        ):
            if self.limit_price is None:
                raise ValueError(
                    "STOP_LIMIT orders require "
                    "limit_price"
                )

            if self.stop_price is None:
                raise ValueError(
                    "STOP_LIMIT orders require "
                    "stop_price"
                )

    @property
    def is_actionable(self) -> bool:
        return (
            self.action
            is not ExecutionAction.HOLD
        )

    @property
    def is_market_order(self) -> bool:
        return (
            self.order_type
            is ExecutionOrderType.MARKET
        )

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 80

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

@dataclass(frozen=True, slots=True)
class ExecutionResult:
    request_id: str
    correlation_id: str

    status: ExecutionStatus
    decision: ExecutionDecision

    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    order: ExecutionOrder | None = None

    filled_quantity: int = 0
    average_fill_price: float | None = None

    warnings: tuple[str, ...] = ()
    error: str | None = None
    metadata: Metadata = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            _normalize_required_text(
                self.request_id,
                "request_id",
            ),
        )

        object.__setattr__(
            self,
            "correlation_id",
            _normalize_required_text(
                self.correlation_id,
                "correlation_id",
            ),
        )

        if not isinstance(
            self.status,
            ExecutionStatus,
        ):
            raise TypeError(
                "status must be an ExecutionStatus"
            )

        if not isinstance(
            self.decision,
            ExecutionDecision,
        ):
            raise TypeError(
                "decision must be an ExecutionDecision"
            )

        object.__setattr__(
            self,
            "started_at",
            _require_aware_datetime(
                self.started_at,
                "started_at",
            ),
        )

        object.__setattr__(
            self,
            "updated_at",
            _require_aware_datetime(
                self.updated_at,
                "updated_at",
            ),
        )

        if self.updated_at < self.started_at:
            raise ValueError(
                "updated_at must not be earlier "
                "than started_at"
            )

        if self.completed_at is not None:
            object.__setattr__(
                self,
                "completed_at",
                _require_aware_datetime(
                    self.completed_at,
                    "completed_at",
                ),
            )

            if self.completed_at < self.updated_at:
                raise ValueError(
                    "completed_at must not be earlier "
                    "than updated_at"
                )

        if (
            self.order is not None
            and not isinstance(
                self.order,
                ExecutionOrder,
            )
        ):
            raise TypeError(
                "order must be an ExecutionOrder or None"
            )

        if self.order is not None:
            if (
                self.order.request_id
                != self.request_id
            ):
                raise ValueError(
                    "order request_id must match "
                    "result request_id"
                )

            if (
                self.order.correlation_id
                != self.correlation_id
            ):
                raise ValueError(
                    "order correlation_id must match "
                    "result correlation_id"
                )

            if (
                self.order.prepared_at
                < self.started_at
            ):
                raise ValueError(
                    "order prepared_at must not be "
                    "earlier than result started_at"
                )

            if (
                self.order.prepared_at
                > self.updated_at
            ):
                raise ValueError(
                    "order prepared_at must not be "
                    "later than result updated_at"
                )

        if (
            isinstance(self.filled_quantity, bool)
            or not isinstance(
                self.filled_quantity,
                int,
            )
        ):
            raise TypeError(
                "filled_quantity must be an integer"
            )

        if self.filled_quantity < 0:
            raise ValueError(
                "filled_quantity must not be negative"
            )

        if (
            self.order is not None
            and self.filled_quantity
            > self.order.quantity
        ):
            raise ValueError(
                "filled_quantity must not exceed "
                "order quantity"
            )

        object.__setattr__(
            self,
            "average_fill_price",
            _normalize_optional_price(
                self.average_fill_price,
                "average_fill_price",
            ),
        )

        object.__setattr__(
            self,
            "warnings",
            ExecutionOrder._normalize_warnings(
                self.warnings
            ),
        )

        if self.error is not None:
            object.__setattr__(
                self,
                "error",
                _normalize_required_text(
                    self.error,
                    "error",
                ),
            )

        object.__setattr__(
            self,
            "metadata",
            _normalize_metadata(
                self.metadata
            ),
        )

        self._validate_lifecycle()

    def _validate_lifecycle(
        self,
    ) -> None:
        is_terminal = (
            self.status
            in TERMINAL_EXECUTION_STATUSES
        )

        if is_terminal:
            if self.completed_at is None:
                raise ValueError(
                    "terminal execution results "
                    "require completed_at"
                )
        elif self.completed_at is not None:
            raise ValueError(
                "non-terminal execution results "
                "must not include completed_at"
            )

        if self.status is ExecutionStatus.PENDING:
            if (
                self.decision
                is not ExecutionDecision.NO_ACTION
            ):
                raise ValueError(
                    "PENDING execution results "
                    "require NO_ACTION decision"
                )

            if self.order is not None:
                raise ValueError(
                    "PENDING execution results "
                    "must not include an order"
                )

        elif self.status is ExecutionStatus.READY:
            if (
                self.decision
                is not ExecutionDecision.PROCEED
            ):
                raise ValueError(
                    "READY execution results "
                    "require PROCEED decision"
                )

            if self.order is None:
                raise ValueError(
                    "READY execution results "
                    "require an order"
                )

        elif self.status is ExecutionStatus.SUBMITTED:
            if (
                self.decision
                is not ExecutionDecision.SUBMIT
            ):
                raise ValueError(
                    "SUBMITTED execution results "
                    "require SUBMIT decision"
                )

            if self.order is None:
                raise ValueError(
                    "SUBMITTED execution results "
                    "require an order"
                )

        elif (
            self.status
            is ExecutionStatus.PARTIALLY_FILLED
        ):
            if (
                self.decision
                is not ExecutionDecision.PROCEED
            ):
                raise ValueError(
                    "PARTIALLY_FILLED execution results "
                    "require PROCEED decision"
                )

            if self.order is None:
                raise ValueError(
                    "PARTIALLY_FILLED execution results "
                    "require an order"
                )

            if self.filled_quantity <= 0:
                raise ValueError(
                    "PARTIALLY_FILLED execution results "
                    "require positive filled_quantity"
                )

            if (
                self.filled_quantity
                >= self.order.quantity
            ):
                raise ValueError(
                    "PARTIALLY_FILLED filled_quantity "
                    "must be less than order quantity"
                )

            if self.average_fill_price is None:
                raise ValueError(
                    "PARTIALLY_FILLED execution results "
                    "require average_fill_price"
                )

        elif self.status is ExecutionStatus.FILLED:
            if (
                self.decision
                is not ExecutionDecision.NO_ACTION
            ):
                raise ValueError(
                    "FILLED execution results "
                    "require NO_ACTION decision"
                )

            if self.order is None:
                raise ValueError(
                    "FILLED execution results "
                    "require an order"
                )

            if (
                self.filled_quantity
                != self.order.quantity
            ):
                raise ValueError(
                    "FILLED execution results require "
                    "filled_quantity equal to "
                    "order quantity"
                )

            if self.average_fill_price is None:
                raise ValueError(
                    "FILLED execution results "
                    "require average_fill_price"
                )

        elif self.status is ExecutionStatus.CANCELLED:
            if (
                self.decision
                is not ExecutionDecision.CANCEL
            ):
                raise ValueError(
                    "CANCELLED execution results "
                    "require CANCEL decision"
                )

        elif self.status is ExecutionStatus.REJECTED:
            if (
                self.decision
                is not ExecutionDecision.REJECT
            ):
                raise ValueError(
                    "REJECTED execution results "
                    "require REJECT decision"
                )

        elif self.status is ExecutionStatus.FAILED:
            if self.decision not in (
                ExecutionDecision.RETRY,
                ExecutionDecision.NO_ACTION,
            ):
                raise ValueError(
                    "FAILED execution results require "
                    "RETRY or NO_ACTION decision"
                )

            if self.error is None:
                raise ValueError(
                    "FAILED execution results "
                    "require an error"
                )

        if (
            self.status
            is not ExecutionStatus.FAILED
            and self.error is not None
        ):
            raise ValueError(
                "only FAILED execution results "
                "may include an error"
            )

        if self.filled_quantity == 0:
            if self.average_fill_price is not None:
                raise ValueError(
                    "average_fill_price requires "
                    "positive filled_quantity"
                )

    @property
    def is_terminal(self) -> bool:
        return (
            self.status
            in TERMINAL_EXECUTION_STATUSES
        )

    @property
    def is_successful(self) -> bool:
        return (
            self.status
            is ExecutionStatus.FILLED
        )

    @property
    def has_order(self) -> bool:
        return self.order is not None

    @property
    def is_partial_fill(self) -> bool:
        return (
            self.status
            is ExecutionStatus.PARTIALLY_FILLED
        )

    @property
    def remaining_quantity(self) -> int | None:
        if self.order is None:
            return None

        return (
            self.order.quantity
            - self.filled_quantity
        )


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    report_id: str
    request: ExecutionRequest
    result: ExecutionResult
    reported_at: datetime
    message: str

    warnings: tuple[str, ...] = ()
    metadata: Metadata = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "report_id",
            _normalize_required_text(
                self.report_id,
                "report_id",
            ),
        )

        if not isinstance(
            self.request,
            ExecutionRequest,
        ):
            raise TypeError(
                "request must be an ExecutionRequest"
            )

        if not isinstance(
            self.result,
            ExecutionResult,
        ):
            raise TypeError(
                "result must be an ExecutionResult"
            )

        object.__setattr__(
            self,
            "reported_at",
            _require_aware_datetime(
                self.reported_at,
                "reported_at",
            ),
        )

        object.__setattr__(
            self,
            "message",
            _normalize_required_text(
                self.message,
                "message",
            ),
        )

        if (
            self.request.request_id
            != self.result.request_id
        ):
            raise ValueError(
                "request and result request_id "
                "values must match"
            )

        if (
            self.request.correlation_id
            != self.result.correlation_id
        ):
            raise ValueError(
                "request and result correlation_id "
                "values must match"
            )

        if (
            self.result.started_at
            < self.request.created_at
        ):
            raise ValueError(
                "result started_at must not be earlier "
                "than request created_at"
            )

        if (
            self.reported_at
            < self.result.updated_at
        ):
            raise ValueError(
                "reported_at must not be earlier "
                "than result updated_at"
            )

        if (
            self.result.completed_at is not None
            and self.reported_at
            < self.result.completed_at
        ):
            raise ValueError(
                "reported_at must not be earlier "
                "than result completed_at"
            )

        if self.result.order is not None:
            order = self.result.order

            if (
                order.strategy_id
                != self.request.strategy_id
            ):
                raise ValueError(
                    "order strategy_id must match request"
                )

            if (
                order.portfolio_id
                != self.request.portfolio_id
            ):
                raise ValueError(
                    "order portfolio_id must match request"
                )

            if (
                order.allocation_id
                != self.request.allocation_id
            ):
                raise ValueError(
                    "order allocation_id must match request"
                )

            if (
                order.signal_id
                != self.request.signal_id
            ):
                raise ValueError(
                    "order signal_id must match request"
                )

            if (
                order.intent_id
                != self.request.intent_id
            ):
                raise ValueError(
                    "order intent_id must match request"
                )

            if (
                order.plan_id
                != self.request.plan_id
            ):
                raise ValueError(
                    "order plan_id must match request"
                )

            if (
                order.symbol
                != self.request.symbol
            ):
                raise ValueError(
                    "order symbol must match request"
                )

            if (
                order.action
                is not self.request.action
            ):
                raise ValueError(
                    "order action must match request"
                )

            if (
                order.side
                is not self.request.side
            ):
                raise ValueError(
                    "order side must match request"
                )

            if (
                order.order_type
                is not self.request.order_type
            ):
                raise ValueError(
                    "order order_type must match request"
                )

            if (
                order.time_in_force
                is not self.request.time_in_force
            ):
                raise ValueError(
                    "order time_in_force must match request"
                )

            if (
                order.quantity
                != self.request.quantity
            ):
                raise ValueError(
                    "order quantity must match request"
                )

        object.__setattr__(
            self,
            "warnings",
            ExecutionOrder._normalize_warnings(
                self.warnings
            ),
        )

        object.__setattr__(
            self,
            "metadata",
            _normalize_metadata(
                self.metadata
            ),
        )

    @property
    def request_id(self) -> str:
        return self.request.request_id

    @property
    def correlation_id(self) -> str:
        return self.request.correlation_id

    @property
    def strategy_id(self) -> str:
        return self.request.strategy_id

    @property
    def portfolio_id(self) -> str:
        return self.request.portfolio_id

    @property
    def allocation_id(self) -> str:
        return self.request.allocation_id

    @property
    def signal_id(self) -> str:
        return self.request.signal_id

    @property
    def intent_id(self) -> str:
        return self.request.intent_id

    @property
    def plan_id(self) -> str:
        return self.request.plan_id

    @property
    def symbol(self) -> str:
        return self.request.symbol

    @property
    def status(self) -> ExecutionStatus:
        return self.result.status

    @property
    def decision(self) -> ExecutionDecision:
        return self.result.decision

    @property
    def order(self) -> ExecutionOrder | None:
        return self.result.order

    @property
    def is_terminal(self) -> bool:
        return self.result.is_terminal

    @property
    def is_successful(self) -> bool:
        return self.result.is_successful