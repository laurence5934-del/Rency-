from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TypeAlias


class OrderPlanAction(str, Enum):
    CREATE = "CREATE"
    REPLACE = "REPLACE"
    CANCEL = "CANCEL"
    HOLD = "HOLD"


class OrderPlanSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    SELL_SHORT = "SELL_SHORT"
    BUY_TO_COVER = "BUY_TO_COVER"
    NONE = "NONE"


class OrderPlanType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderPlanTimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class OrderPlanningStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class OrderPlanningDecision(str, Enum):
    PROCEED = "PROCEED"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    HOLD = "HOLD"
    CANCEL = "CANCEL"
    RETRY = "RETRY"
    NO_ACTION = "NO_ACTION"


class OrderPlanningStage(str, Enum):
    RECEIVED = "RECEIVED"
    VALIDATION = "VALIDATION"
    INTENT_CONTEXT = "INTENT_CONTEXT"
    POSITION_CONTEXT = "POSITION_CONTEXT"
    EXECUTION_CONTEXT = "EXECUTION_CONTEXT"
    ORDER_CONSTRUCTION = "ORDER_CONSTRUCTION"
    FINALIZATION = "FINALIZATION"


ORDER_PLANNING_STAGE_POSITIONS: dict[
    OrderPlanningStage,
    int,
] = {
    OrderPlanningStage.RECEIVED: 1,
    OrderPlanningStage.VALIDATION: 2,
    OrderPlanningStage.INTENT_CONTEXT: 3,
    OrderPlanningStage.POSITION_CONTEXT: 4,
    OrderPlanningStage.EXECUTION_CONTEXT: 5,
    OrderPlanningStage.ORDER_CONSTRUCTION: 6,
    OrderPlanningStage.FINALIZATION: 7,
}


TERMINAL_ORDER_PLANNING_STATUSES: frozenset[
    OrderPlanningStatus
] = frozenset(
    {
        OrderPlanningStatus.APPROVED,
        OrderPlanningStatus.REJECTED,
        OrderPlanningStatus.CANCELLED,
        OrderPlanningStatus.FAILED,
    }
)


Metadata: TypeAlias = tuple[
    tuple[str, str],
    ...,
]


class OrderPlanModelSupport:
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

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
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
        if not isinstance(
            values,
            (tuple, list),
        ):
            raise TypeError(
                "metadata must be a tuple or list"
            )

        normalized: list[
            tuple[str, str]
        ] = []

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

            if not isinstance(raw_key, str):
                raise TypeError(
                    "metadata keys must be strings"
                )

            if not isinstance(raw_value, str):
                raise TypeError(
                    "metadata values must be strings"
                )

            key = raw_key.strip()
            value = raw_value.strip()

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
    def normalize_warnings(
        values: tuple[str, ...] | list[str],
    ) -> tuple[str, ...]:
        if not isinstance(
            values,
            (tuple, list),
        ):
            raise TypeError(
                "warnings must be a tuple or list"
            )

        normalized: list[str] = []
        seen: set[str] = set()

        for warning in values:
            if not isinstance(
                warning,
                str,
            ):
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

    @staticmethod
    def percentage(
        value: int,
        field_name: str,
    ) -> int:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
        ):
            raise TypeError(
                f"{field_name} must be an integer"
            )

        if value < 0 or value > 100:
            raise ValueError(
                f"{field_name} must be between 0 and 100"
            )

        return value

    @staticmethod
    def non_negative_integer(
        value: int,
        field_name: str,
    ) -> int:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
        ):
            raise TypeError(
                f"{field_name} must be an integer"
            )

        if value < 0:
            raise ValueError(
                f"{field_name} must not be negative"
            )

        return value

    @staticmethod
    def positive_integer(
        value: int,
        field_name: str,
    ) -> int:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
        ):
            raise TypeError(
                f"{field_name} must be an integer"
            )

        if value <= 0:
            raise ValueError(
                f"{field_name} must be positive"
            )

        return value

    @staticmethod
    def positive_number(
        value: int | float,
        field_name: str,
    ) -> float:
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
        ):
            raise TypeError(
                f"{field_name} must be a number"
            )

        normalized = float(value)

        if normalized <= 0:
            raise ValueError(
                f"{field_name} must be positive"
            )

        return normalized

    @staticmethod
    def optional_positive_number(
        value: int | float | None,
        field_name: str,
    ) -> float | None:
        if value is None:
            return None

        return OrderPlanModelSupport.positive_number(
            value,
            field_name,
        )
@dataclass(frozen=True, slots=True)
class OrderPlanningRequest:
    request_id: str
    correlation_id: str
    strategy_id: str
    portfolio_id: str
    allocation_id: str
    signal_id: str
    intent_id: str
    symbol: str
    action: OrderPlanAction
    side: OrderPlanSide
    order_type: OrderPlanType
    time_in_force: OrderPlanTimeInForce
    quantity: int
    confidence: int
    created_at: datetime
    sequence_number: int
    requested_by: str
    limit_price: float | None = None
    stop_price: float | None = None
    is_replay: bool = False
    metadata: Metadata = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        request_id = OrderPlanModelSupport.required_text(
            self.request_id,
            "request_id",
        )

        correlation_id = OrderPlanModelSupport.required_text(
            self.correlation_id,
            "correlation_id",
        )

        strategy_id = OrderPlanModelSupport.required_text(
            self.strategy_id,
            "strategy_id",
        )

        portfolio_id = OrderPlanModelSupport.required_text(
            self.portfolio_id,
            "portfolio_id",
        )

        allocation_id = OrderPlanModelSupport.required_text(
            self.allocation_id,
            "allocation_id",
        )

        signal_id = OrderPlanModelSupport.required_text(
            self.signal_id,
            "signal_id",
        )

        intent_id = OrderPlanModelSupport.required_text(
            self.intent_id,
            "intent_id",
        )

        symbol = OrderPlanModelSupport.required_text(
            self.symbol,
            "symbol",
        ).upper()

        requested_by = OrderPlanModelSupport.required_text(
            self.requested_by,
            "requested_by",
        )

        if not isinstance(
            self.action,
            OrderPlanAction,
        ):
            raise TypeError(
                "action must be an OrderPlanAction"
            )

        if not isinstance(
            self.side,
            OrderPlanSide,
        ):
            raise TypeError(
                "side must be an OrderPlanSide"
            )

        if not isinstance(
            self.order_type,
            OrderPlanType,
        ):
            raise TypeError(
                "order_type must be an OrderPlanType"
            )

        if not isinstance(
            self.time_in_force,
            OrderPlanTimeInForce,
        ):
            raise TypeError(
                "time_in_force must be an "
                "OrderPlanTimeInForce"
            )

        quantity = OrderPlanModelSupport.positive_integer(
            self.quantity,
            "quantity",
        )

        confidence = OrderPlanModelSupport.percentage(
            self.confidence,
            "confidence",
        )

        OrderPlanModelSupport.aware_datetime(
            self.created_at,
            "created_at",
        )

        sequence_number = (
            OrderPlanModelSupport.non_negative_integer(
                self.sequence_number,
                "sequence_number",
            )
        )

        limit_price = (
            OrderPlanModelSupport.optional_positive_number(
                self.limit_price,
                "limit_price",
            )
        )

        stop_price = (
            OrderPlanModelSupport.optional_positive_number(
                self.stop_price,
                "stop_price",
            )
        )

        if not isinstance(
            self.is_replay,
            bool,
        ):
            raise TypeError(
                "is_replay must be a bool"
            )

        if self.action is OrderPlanAction.HOLD:
            if self.side is not OrderPlanSide.NONE:
                raise ValueError(
                    "HOLD order plans require NONE side"
                )

        elif self.side is OrderPlanSide.NONE:
            raise ValueError(
                "actionable order plans require an order side"
            )

        if (
            self.order_type is OrderPlanType.MARKET
            and (
                limit_price is not None
                or stop_price is not None
            )
        ):
            raise ValueError(
                "MARKET orders must not include "
                "limit_price or stop_price"
            )

        if (
            self.order_type is OrderPlanType.LIMIT
            and limit_price is None
        ):
            raise ValueError(
                "LIMIT orders require limit_price"
            )

        if (
            self.order_type is OrderPlanType.LIMIT
            and stop_price is not None
        ):
            raise ValueError(
                "LIMIT orders must not include stop_price"
            )

        if (
            self.order_type is OrderPlanType.STOP
            and stop_price is None
        ):
            raise ValueError(
                "STOP orders require stop_price"
            )

        if (
            self.order_type is OrderPlanType.STOP
            and limit_price is not None
        ):
            raise ValueError(
                "STOP orders must not include limit_price"
            )

        if self.order_type is OrderPlanType.STOP_LIMIT:
            if limit_price is None:
                raise ValueError(
                    "STOP_LIMIT orders require limit_price"
                )

            if stop_price is None:
                raise ValueError(
                    "STOP_LIMIT orders require stop_price"
                )

        metadata = OrderPlanModelSupport.normalize_metadata(
            self.metadata
        )

        object.__setattr__(
            self,
            "request_id",
            request_id,
        )

        object.__setattr__(
            self,
            "correlation_id",
            correlation_id,
        )

        object.__setattr__(
            self,
            "strategy_id",
            strategy_id,
        )

        object.__setattr__(
            self,
            "portfolio_id",
            portfolio_id,
        )

        object.__setattr__(
            self,
            "allocation_id",
            allocation_id,
        )

        object.__setattr__(
            self,
            "signal_id",
            signal_id,
        )

        object.__setattr__(
            self,
            "intent_id",
            intent_id,
        )

        object.__setattr__(
            self,
            "symbol",
            symbol,
        )

        object.__setattr__(
            self,
            "quantity",
            quantity,
        )

        object.__setattr__(
            self,
            "confidence",
            confidence,
        )

        object.__setattr__(
            self,
            "sequence_number",
            sequence_number,
        )

        object.__setattr__(
            self,
            "requested_by",
            requested_by,
        )

        object.__setattr__(
            self,
            "limit_price",
            limit_price,
        )

        object.__setattr__(
            self,
            "stop_price",
            stop_price,
        )

        object.__setattr__(
            self,
            "metadata",
            metadata,
        )

    @property
    def is_actionable(self) -> bool:
        return (
            self.action is not OrderPlanAction.HOLD
            and self.side is not OrderPlanSide.NONE
        )

    @property
    def is_market_order(self) -> bool:
        return self.order_type is OrderPlanType.MARKET

    @property
    def is_limit_order(self) -> bool:
        return self.order_type is OrderPlanType.LIMIT

    @property
    def is_stop_order(self) -> bool:
        return self.order_type in {
            OrderPlanType.STOP,
            OrderPlanType.STOP_LIMIT,
        }

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 80

@dataclass(frozen=True, slots=True)
class OrderPlan:
    plan_id: str
    request_id: str
    correlation_id: str
    strategy_id: str
    portfolio_id: str
    allocation_id: str
    signal_id: str
    intent_id: str
    symbol: str
    action: OrderPlanAction
    side: OrderPlanSide
    order_type: OrderPlanType
    time_in_force: OrderPlanTimeInForce
    quantity: int
    confidence: int
    generated_at: datetime
    expires_at: datetime | None
    rationale: str
    limit_price: float | None = None
    stop_price: float | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    metadata: Metadata = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        plan_id = OrderPlanModelSupport.required_text(
            self.plan_id,
            "plan_id",
        )

        request_id = OrderPlanModelSupport.required_text(
            self.request_id,
            "request_id",
        )

        correlation_id = OrderPlanModelSupport.required_text(
            self.correlation_id,
            "correlation_id",
        )

        strategy_id = OrderPlanModelSupport.required_text(
            self.strategy_id,
            "strategy_id",
        )

        portfolio_id = OrderPlanModelSupport.required_text(
            self.portfolio_id,
            "portfolio_id",
        )

        allocation_id = OrderPlanModelSupport.required_text(
            self.allocation_id,
            "allocation_id",
        )

        signal_id = OrderPlanModelSupport.required_text(
            self.signal_id,
            "signal_id",
        )

        intent_id = OrderPlanModelSupport.required_text(
            self.intent_id,
            "intent_id",
        )

        symbol = OrderPlanModelSupport.required_text(
            self.symbol,
            "symbol",
        ).upper()

        rationale = OrderPlanModelSupport.required_text(
            self.rationale,
            "rationale",
        )

        if not isinstance(
            self.action,
            OrderPlanAction,
        ):
            raise TypeError(
                "action must be an OrderPlanAction"
            )

        if not isinstance(
            self.side,
            OrderPlanSide,
        ):
            raise TypeError(
                "side must be an OrderPlanSide"
            )

        if not isinstance(
            self.order_type,
            OrderPlanType,
        ):
            raise TypeError(
                "order_type must be an OrderPlanType"
            )

        if not isinstance(
            self.time_in_force,
            OrderPlanTimeInForce,
        ):
            raise TypeError(
                "time_in_force must be an "
                "OrderPlanTimeInForce"
            )

        quantity = OrderPlanModelSupport.positive_integer(
            self.quantity,
            "quantity",
        )

        confidence = OrderPlanModelSupport.percentage(
            self.confidence,
            "confidence",
        )

        OrderPlanModelSupport.aware_datetime(
            self.generated_at,
            "generated_at",
        )

        if self.expires_at is not None:
            OrderPlanModelSupport.aware_datetime(
                self.expires_at,
                "expires_at",
            )

            if self.expires_at < self.generated_at:
                raise ValueError(
                    "expires_at must not be earlier "
                    "than generated_at"
                )

        limit_price = (
            OrderPlanModelSupport.optional_positive_number(
                self.limit_price,
                "limit_price",
            )
        )

        stop_price = (
            OrderPlanModelSupport.optional_positive_number(
                self.stop_price,
                "stop_price",
            )
        )

        if self.action is OrderPlanAction.HOLD:
            if self.side is not OrderPlanSide.NONE:
                raise ValueError(
                    "HOLD order plans require NONE side"
                )

        elif self.side is OrderPlanSide.NONE:
            raise ValueError(
                "actionable order plans require an order side"
            )

        if (
            self.order_type is OrderPlanType.MARKET
            and (
                limit_price is not None
                or stop_price is not None
            )
        ):
            raise ValueError(
                "MARKET orders must not include "
                "limit_price or stop_price"
            )

        if (
            self.order_type is OrderPlanType.LIMIT
            and limit_price is None
        ):
            raise ValueError(
                "LIMIT orders require limit_price"
            )

        if (
            self.order_type is OrderPlanType.LIMIT
            and stop_price is not None
        ):
            raise ValueError(
                "LIMIT orders must not include stop_price"
            )

        if (
            self.order_type is OrderPlanType.STOP
            and stop_price is None
        ):
            raise ValueError(
                "STOP orders require stop_price"
            )

        if (
            self.order_type is OrderPlanType.STOP
            and limit_price is not None
        ):
            raise ValueError(
                "STOP orders must not include limit_price"
            )

        if self.order_type is OrderPlanType.STOP_LIMIT:
            if limit_price is None:
                raise ValueError(
                    "STOP_LIMIT orders require limit_price"
                )

            if stop_price is None:
                raise ValueError(
                    "STOP_LIMIT orders require stop_price"
                )

        warnings = OrderPlanModelSupport.normalize_warnings(
            self.warnings
        )

        metadata = OrderPlanModelSupport.normalize_metadata(
            self.metadata
        )

        object.__setattr__(
            self,
            "plan_id",
            plan_id,
        )

        object.__setattr__(
            self,
            "request_id",
            request_id,
        )

        object.__setattr__(
            self,
            "correlation_id",
            correlation_id,
        )

        object.__setattr__(
            self,
            "strategy_id",
            strategy_id,
        )

        object.__setattr__(
            self,
            "portfolio_id",
            portfolio_id,
        )

        object.__setattr__(
            self,
            "allocation_id",
            allocation_id,
        )

        object.__setattr__(
            self,
            "signal_id",
            signal_id,
        )

        object.__setattr__(
            self,
            "intent_id",
            intent_id,
        )

        object.__setattr__(
            self,
            "symbol",
            symbol,
        )

        object.__setattr__(
            self,
            "quantity",
            quantity,
        )

        object.__setattr__(
            self,
            "confidence",
            confidence,
        )

        object.__setattr__(
            self,
            "rationale",
            rationale,
        )

        object.__setattr__(
            self,
            "limit_price",
            limit_price,
        )

        object.__setattr__(
            self,
            "stop_price",
            stop_price,
        )

        object.__setattr__(
            self,
            "warnings",
            warnings,
        )

        object.__setattr__(
            self,
            "metadata",
            metadata,
        )

    @property
    def is_actionable(self) -> bool:
        return (
            self.action is not OrderPlanAction.HOLD
            and self.side is not OrderPlanSide.NONE
        )

    @property
    def is_market_order(self) -> bool:
        return self.order_type is OrderPlanType.MARKET

    @property
    def is_limit_order(self) -> bool:
        return self.order_type is OrderPlanType.LIMIT

    @property
    def is_stop_order(self) -> bool:
        return self.order_type in {
            OrderPlanType.STOP,
            OrderPlanType.STOP_LIMIT,
        }

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 80

    @property
    def has_expiration(self) -> bool:
        return self.expires_at is not None

    def is_expired_at(
        self,
        value: datetime,
    ) -> bool:
        OrderPlanModelSupport.aware_datetime(
            value,
            "value",
        )

        if self.expires_at is None:
            return False

        return value > self.expires_at

@dataclass(frozen=True, slots=True)
class OrderPlanningResult:
    request_id: str
    correlation_id: str
    status: OrderPlanningStatus
    decision: OrderPlanningDecision
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    plan: OrderPlan | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None
    metadata: Metadata = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        request_id = OrderPlanModelSupport.required_text(
            self.request_id,
            "request_id",
        )

        correlation_id = OrderPlanModelSupport.required_text(
            self.correlation_id,
            "correlation_id",
        )

        if not isinstance(
            self.status,
            OrderPlanningStatus,
        ):
            raise TypeError(
                "status must be an OrderPlanningStatus"
            )

        if not isinstance(
            self.decision,
            OrderPlanningDecision,
        ):
            raise TypeError(
                "decision must be an OrderPlanningDecision"
            )

        OrderPlanModelSupport.aware_datetime(
            self.started_at,
            "started_at",
        )

        OrderPlanModelSupport.aware_datetime(
            self.updated_at,
            "updated_at",
        )

        if self.updated_at < self.started_at:
            raise ValueError(
                "updated_at must not be earlier "
                "than started_at"
            )

        if self.completed_at is not None:
            OrderPlanModelSupport.aware_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.updated_at:
                raise ValueError(
                    "completed_at must not be earlier "
                    "than updated_at"
                )

        if (
            self.plan is not None
            and not isinstance(
                self.plan,
                OrderPlan,
            )
        ):
            raise TypeError(
                "plan must be an OrderPlan or None"
            )

        if self.plan is not None:
            if (
                self.plan.request_id
                != request_id
            ):
                raise ValueError(
                    "plan request_id must match "
                    "result request_id"
                )

            if (
                self.plan.correlation_id
                != correlation_id
            ):
                raise ValueError(
                    "plan correlation_id must match "
                    "result correlation_id"
                )

            if (
                self.plan.generated_at
                < self.started_at
            ):
                raise ValueError(
                    "plan generated_at must not be "
                    "earlier than result started_at"
                )

            if (
                self.plan.generated_at
                > self.updated_at
            ):
                raise ValueError(
                    "plan generated_at must not be "
                    "later than result updated_at"
                )

        warnings = (
            OrderPlanModelSupport.normalize_warnings(
                self.warnings
            )
        )

        error = OrderPlanModelSupport.optional_text(
            self.error,
            "error",
        )

        metadata = (
            OrderPlanModelSupport.normalize_metadata(
                self.metadata
            )
        )

        is_terminal = (
            self.status
            in TERMINAL_ORDER_PLANNING_STATUSES
        )

        if is_terminal:
            if self.completed_at is None:
                raise ValueError(
                    "terminal order planning results require "
                    "completed_at"
                )
        elif self.completed_at is not None:
            raise ValueError(
                "non-terminal order planning results must not "
                "include completed_at"
            )

        if self.status is OrderPlanningStatus.PENDING:
            if (
                self.decision
                is not OrderPlanningDecision.NO_ACTION
            ):
                raise ValueError(
                    "pending order planning results require "
                    "NO_ACTION decision"
                )

            if self.plan is not None:
                raise ValueError(
                    "pending order planning results must not "
                    "include a plan"
                )

        if self.status is OrderPlanningStatus.ACTIVE:
            if (
                self.decision
                is not OrderPlanningDecision.PROCEED
            ):
                raise ValueError(
                    "active order planning results require "
                    "PROCEED decision"
                )

        if self.status is OrderPlanningStatus.APPROVED:
            if (
                self.decision
                is not OrderPlanningDecision.APPROVE
            ):
                raise ValueError(
                    "approved order planning results require "
                    "APPROVE decision"
                )

            if self.plan is None:
                raise ValueError(
                    "approved order planning results require "
                    "a plan"
                )

        if self.status is OrderPlanningStatus.REJECTED:
            if (
                self.decision
                is not OrderPlanningDecision.REJECT
            ):
                raise ValueError(
                    "rejected order planning results require "
                    "REJECT decision"
                )

        if self.status is OrderPlanningStatus.CANCELLED:
            if (
                self.decision
                is not OrderPlanningDecision.CANCEL
            ):
                raise ValueError(
                    "cancelled order planning results require "
                    "CANCEL decision"
                )

        if self.status is OrderPlanningStatus.FAILED:
            if self.decision not in {
                OrderPlanningDecision.RETRY,
                OrderPlanningDecision.NO_ACTION,
            }:
                raise ValueError(
                    "failed order planning results require "
                    "RETRY or NO_ACTION decision"
                )

            if error is None:
                raise ValueError(
                    "failed order planning results require "
                    "an error"
                )

        if (
            self.status is not OrderPlanningStatus.FAILED
            and error is not None
        ):
            raise ValueError(
                "only failed order planning results may "
                "include an error"
            )

        object.__setattr__(
            self,
            "request_id",
            request_id,
        )

        object.__setattr__(
            self,
            "correlation_id",
            correlation_id,
        )

        object.__setattr__(
            self,
            "warnings",
            warnings,
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
    def is_terminal(self) -> bool:
        return (
            self.status
            in TERMINAL_ORDER_PLANNING_STATUSES
        )

    @property
    def is_successful(self) -> bool:
        return (
            self.status
            is OrderPlanningStatus.APPROVED
        )

    @property
    def has_plan(self) -> bool:
        return self.plan is not None

@dataclass(frozen=True, slots=True)
class OrderPlanningReport:
    report_id: str
    request: OrderPlanningRequest
    result: OrderPlanningResult
    reported_at: datetime
    message: str
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    metadata: Metadata = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        report_id = OrderPlanModelSupport.required_text(
            self.report_id,
            "report_id",
        )

        if not isinstance(
            self.request,
            OrderPlanningRequest,
        ):
            raise TypeError(
                "request must be an OrderPlanningRequest"
            )

        if not isinstance(
            self.result,
            OrderPlanningResult,
        ):
            raise TypeError(
                "result must be an OrderPlanningResult"
            )

        message = OrderPlanModelSupport.required_text(
            self.message,
            "message",
        )

        OrderPlanModelSupport.aware_datetime(
            self.reported_at,
            "reported_at",
        )

        if (
            self.request.request_id
            != self.result.request_id
        ):
            raise ValueError(
                "request and result request_id values "
                "must match"
            )

        if (
            self.request.correlation_id
            != self.result.correlation_id
        ):
            raise ValueError(
                "request and result correlation_id values "
                "must match"
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

        if self.result.plan is not None:
            plan = self.result.plan

            if (
                plan.strategy_id
                != self.request.strategy_id
            ):
                raise ValueError(
                    "plan strategy_id must match request"
                )

            if (
                plan.portfolio_id
                != self.request.portfolio_id
            ):
                raise ValueError(
                    "plan portfolio_id must match request"
                )

            if (
                plan.allocation_id
                != self.request.allocation_id
            ):
                raise ValueError(
                    "plan allocation_id must match request"
                )

            if (
                plan.signal_id
                != self.request.signal_id
            ):
                raise ValueError(
                    "plan signal_id must match request"
                )

            if (
                plan.intent_id
                != self.request.intent_id
            ):
                raise ValueError(
                    "plan intent_id must match request"
                )

            if (
                plan.symbol
                != self.request.symbol
            ):
                raise ValueError(
                    "plan symbol must match request"
                )

            if (
                plan.action
                is not self.request.action
            ):
                raise ValueError(
                    "plan action must match request"
                )

            if (
                plan.side
                is not self.request.side
            ):
                raise ValueError(
                    "plan side must match request"
                )

            if (
                plan.order_type
                is not self.request.order_type
            ):
                raise ValueError(
                    "plan order_type must match request"
                )

            if (
                plan.time_in_force
                is not self.request.time_in_force
            ):
                raise ValueError(
                    "plan time_in_force must match request"
                )

        warnings = (
            OrderPlanModelSupport.normalize_warnings(
                self.warnings
            )
        )

        metadata = (
            OrderPlanModelSupport.normalize_metadata(
                self.metadata
            )
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
            "warnings",
            warnings,
        )

        object.__setattr__(
            self,
            "metadata",
            metadata,
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
    def symbol(self) -> str:
        return self.request.symbol

    @property
    def status(self) -> OrderPlanningStatus:
        return self.result.status

    @property
    def decision(self) -> OrderPlanningDecision:
        return self.result.decision

    @property
    def plan(self) -> OrderPlan | None:
        return self.result.plan

    @property
    def is_terminal(self) -> bool:
        return self.result.is_terminal