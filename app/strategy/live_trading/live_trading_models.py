from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")


class LiveTradingStatus(str, Enum):
    """Lifecycle status of a live-trading workflow."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TradingEnvironment(str, Enum):
    """Supported execution environments."""

    PAPER = "PAPER"
    LIVE = "LIVE"


class TradingSessionStatus(str, Enum):
    """Lifecycle status of a trading session."""

    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    HALTED = "HALTED"
    CLOSED = "CLOSED"


class LiveTradeSide(str, Enum):
    """Supported trade directions."""

    BUY = "BUY"
    SELL = "SELL"


class LiveOrderType(str, Enum):
    """Supported live-trading order types."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"


class LiveTradeDecision(str, Enum):
    """Final routing decision for a proposed trade."""

    EXECUTE = "EXECUTE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECT = "REJECT"


class ExecutionPlanStatus(str, Enum):
    """Lifecycle status of an execution plan."""

    READY = "READY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class TradingSession:
    """Immutable live-trading session configuration."""

    session_id: str
    environment: TradingEnvironment
    status: TradingSessionStatus
    started_at: datetime
    account_id: str
    max_order_value: Decimal
    max_session_loss: Decimal
    live_trading_confirmed: bool = False
    closed_at: datetime | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_session_id = self.session_id.strip()
        normalized_account_id = self.account_id.strip()

        if not normalized_session_id:
            raise ValueError(
                "session_id must not be empty"
            )

        if not normalized_account_id:
            raise ValueError(
                "account_id must not be empty"
            )

        if not isinstance(
            self.environment,
            TradingEnvironment,
        ):
            raise TypeError(
                "environment must be a TradingEnvironment"
            )

        if not isinstance(
            self.status,
            TradingSessionStatus,
        ):
            raise TypeError(
                "status must be a TradingSessionStatus"
            )

        self._validate_datetime(
            self.started_at,
            "started_at",
        )

        if self.closed_at is not None:
            self._validate_datetime(
                self.closed_at,
                "closed_at",
            )

            if self.closed_at < self.started_at:
                raise ValueError(
                    "closed_at must not be earlier than started_at"
                )

        for field_name in (
            "max_order_value",
            "max_session_loss",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

            if value <= _ZERO:
                raise ValueError(
                    f"{field_name} must be greater than zero"
                )

        if not isinstance(
            self.live_trading_confirmed,
            bool,
        ):
            raise TypeError(
                "live_trading_confirmed must be a bool"
            )

        if (
            self.environment is TradingEnvironment.LIVE
            and not self.live_trading_confirmed
        ):
            raise ValueError(
                "live sessions require explicit live-trading confirmation"
            )

        if (
            self.status is TradingSessionStatus.CLOSED
            and self.closed_at is None
        ):
            raise ValueError(
                "closed sessions must include closed_at"
            )

        if (
            self.status is not TradingSessionStatus.CLOSED
            and self.closed_at is not None
        ):
            raise ValueError(
                "only closed sessions may include closed_at"
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
            "session_id",
            normalized_session_id,
        )
        object.__setattr__(
            self,
            "account_id",
            normalized_account_id,
        )
        object.__setattr__(
            self,
            "metadata",
            tuple(normalized_metadata),
        )

    @staticmethod
    def _validate_datetime(
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


@dataclass(frozen=True, slots=True)
class LiveTradeRequest:
    """Immutable trade request submitted to the orchestrator."""

    request_id: str
    session_id: str
    symbol: str
    side: LiveTradeSide
    quantity: Decimal
    order_type: LiveOrderType
    submitted_at: datetime
    strategy_id: str
    limit_price: Decimal | None = None
    estimated_price: Decimal | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_request_id = self.request_id.strip()
        normalized_session_id = self.session_id.strip()
        normalized_symbol = self.symbol.strip().upper()
        normalized_strategy_id = self.strategy_id.strip()

        if not normalized_request_id:
            raise ValueError(
                "request_id must not be empty"
            )

        if not normalized_session_id:
            raise ValueError(
                "session_id must not be empty"
            )

        if not normalized_symbol:
            raise ValueError(
                "symbol must not be empty"
            )

        if not normalized_strategy_id:
            raise ValueError(
                "strategy_id must not be empty"
            )

        if not isinstance(self.side, LiveTradeSide):
            raise TypeError(
                "side must be a LiveTradeSide"
            )

        if not isinstance(
            self.order_type,
            LiveOrderType,
        ):
            raise TypeError(
                "order_type must be a LiveOrderType"
            )

        if not isinstance(self.quantity, Decimal):
            raise TypeError(
                "quantity must be a Decimal"
            )

        if self.quantity <= _ZERO:
            raise ValueError(
                "quantity must be greater than zero"
            )

        TradingSession._validate_datetime(
            self.submitted_at,
            "submitted_at",
        )

        self._validate_optional_price(
            self.limit_price,
            "limit_price",
        )
        self._validate_optional_price(
            self.estimated_price,
            "estimated_price",
        )

        if (
            self.order_type is LiveOrderType.LIMIT
            and self.limit_price is None
        ):
            raise ValueError(
                "limit orders must include a limit_price"
            )

        if (
            self.order_type is LiveOrderType.MARKET
            and self.limit_price is not None
        ):
            raise ValueError(
                "market orders must not include a limit_price"
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
            "request_id",
            normalized_request_id,
        )
        object.__setattr__(
            self,
            "session_id",
            normalized_session_id,
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

    @staticmethod
    def _validate_optional_price(
        value: Decimal | None,
        field_name: str,
    ) -> None:
        if value is None:
            return

        if not isinstance(value, Decimal):
            raise TypeError(
                f"{field_name} must be a Decimal or None"
            )

        if value <= _ZERO:
            raise ValueError(
                f"{field_name} must be greater than zero"
            )

    @property
    def estimated_order_value(self) -> Decimal | None:
        """Return the estimated notional value when price is available."""

        price = self.limit_price or self.estimated_price

        if price is None:
            return None

        return self.quantity * price


@dataclass(frozen=True, slots=True)
class TradeExecutionPlan:
    """Immutable execution plan produced before broker routing."""

    plan_id: str
    request_id: str
    environment: TradingEnvironment
    status: ExecutionPlanStatus
    decision: LiveTradeDecision
    approved_quantity: Decimal
    estimated_order_value: Decimal
    reason: str
    risk_checks_passed: bool
    coordinator_approved: bool
    requires_manual_confirmation: bool = False
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_plan_id = self.plan_id.strip()
        normalized_request_id = self.request_id.strip()
        normalized_reason = self.reason.strip()

        if not normalized_plan_id:
            raise ValueError(
                "plan_id must not be empty"
            )

        if not normalized_request_id:
            raise ValueError(
                "request_id must not be empty"
            )

        if not isinstance(
            self.environment,
            TradingEnvironment,
        ):
            raise TypeError(
                "environment must be a TradingEnvironment"
            )

        if not isinstance(
            self.status,
            ExecutionPlanStatus,
        ):
            raise TypeError(
                "status must be an ExecutionPlanStatus"
            )

        if not isinstance(
            self.decision,
            LiveTradeDecision,
        ):
            raise TypeError(
                "decision must be a LiveTradeDecision"
            )

        for field_name in (
            "approved_quantity",
            "estimated_order_value",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

            if value < _ZERO:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        for field_name in (
            "risk_checks_passed",
            "coordinator_approved",
            "requires_manual_confirmation",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, bool):
                raise TypeError(
                    f"{field_name} must be a bool"
                )

        if not normalized_reason:
            raise ValueError(
                "reason must not be empty"
            )

        if self.decision is LiveTradeDecision.EXECUTE:
            if self.status is not ExecutionPlanStatus.READY:
                raise ValueError(
                    "executable plans must have READY status"
                )

            if self.approved_quantity <= _ZERO:
                raise ValueError(
                    "executable plans must approve a positive quantity"
                )

            if self.estimated_order_value <= _ZERO:
                raise ValueError(
                    "executable plans must have a positive order value"
                )

            if not self.risk_checks_passed:
                raise ValueError(
                    "executable plans require passed risk checks"
                )

            if not self.coordinator_approved:
                raise ValueError(
                    "executable plans require coordinator approval"
                )

        if self.decision is LiveTradeDecision.REVIEW_REQUIRED:
            if (
                self.status
                is not ExecutionPlanStatus.REVIEW_REQUIRED
            ):
                raise ValueError(
                    "review decisions must have REVIEW_REQUIRED status"
                )

        if self.decision is LiveTradeDecision.REJECT:
            if self.status is not ExecutionPlanStatus.BLOCKED:
                raise ValueError(
                    "rejected plans must have BLOCKED status"
                )

            if self.approved_quantity != _ZERO:
                raise ValueError(
                    "rejected plans must approve zero quantity"
                )

        object.__setattr__(
            self,
            "plan_id",
            normalized_plan_id,
        )
        object.__setattr__(
            self,
            "request_id",
            normalized_request_id,
        )
        object.__setattr__(
            self,
            "reason",
            normalized_reason,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )


@dataclass(frozen=True, slots=True)
class LiveTradeExecutionResult:
    """Immutable result returned after execution routing."""

    request_id: str
    plan_id: str
    decision: LiveTradeDecision
    submitted: bool
    broker_name: str | None
    order_id: str | None
    filled_quantity: Decimal
    average_price: Decimal | None
    commission: Decimal
    executed_at: datetime | None
    reason: str
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_request_id = self.request_id.strip()
        normalized_plan_id = self.plan_id.strip()
        normalized_reason = self.reason.strip()

        if not normalized_request_id:
            raise ValueError(
                "request_id must not be empty"
            )

        if not normalized_plan_id:
            raise ValueError(
                "plan_id must not be empty"
            )

        if not isinstance(
            self.decision,
            LiveTradeDecision,
        ):
            raise TypeError(
                "decision must be a LiveTradeDecision"
            )

        if not isinstance(self.submitted, bool):
            raise TypeError(
                "submitted must be a bool"
            )

        normalized_broker_name = self._normalize_optional_text(
            self.broker_name,
            "broker_name",
        )
        normalized_order_id = self._normalize_optional_text(
            self.order_id,
            "order_id",
        )

        if not isinstance(
            self.filled_quantity,
            Decimal,
        ):
            raise TypeError(
                "filled_quantity must be a Decimal"
            )

        if self.filled_quantity < _ZERO:
            raise ValueError(
                "filled_quantity must not be negative"
            )

        LiveTradeRequest._validate_optional_price(
            self.average_price,
            "average_price",
        )

        if not isinstance(self.commission, Decimal):
            raise TypeError(
                "commission must be a Decimal"
            )

        if self.commission < _ZERO:
            raise ValueError(
                "commission must not be negative"
            )

        if self.executed_at is not None:
            TradingSession._validate_datetime(
                self.executed_at,
                "executed_at",
            )

        if not normalized_reason:
            raise ValueError(
                "reason must not be empty"
            )

        if self.submitted:
            if self.decision is not LiveTradeDecision.EXECUTE:
                raise ValueError(
                    "only executable decisions may be submitted"
                )

            if not normalized_broker_name:
                raise ValueError(
                    "submitted results must include broker_name"
                )

            if not normalized_order_id:
                raise ValueError(
                    "submitted results must include order_id"
                )

            if self.executed_at is None:
                raise ValueError(
                    "submitted results must include executed_at"
                )

            if self.filled_quantity <= _ZERO:
                raise ValueError(
                    "submitted results must include a positive fill"
                )

            if self.average_price is None:
                raise ValueError(
                    "submitted results must include average_price"
                )
        else:
            if normalized_order_id is not None:
                raise ValueError(
                    "non-submitted results must not include order_id"
                )

            if self.filled_quantity != _ZERO:
                raise ValueError(
                    "non-submitted results must have zero filled_quantity"
                )

            if self.average_price is not None:
                raise ValueError(
                    "non-submitted results must not include average_price"
                )

            if self.executed_at is not None:
                raise ValueError(
                    "non-submitted results must not include executed_at"
                )

        object.__setattr__(
            self,
            "request_id",
            normalized_request_id,
        )
        object.__setattr__(
            self,
            "plan_id",
            normalized_plan_id,
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
        object.__setattr__(
            self,
            "reason",
            normalized_reason,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )

    @staticmethod
    def _normalize_optional_text(
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


@dataclass(frozen=True, slots=True)
class LiveTradingReport:
    """Unified report from a live-trading orchestration workflow."""

    status: LiveTradingStatus
    session: TradingSession
    request: LiveTradeRequest
    plan: TradeExecutionPlan
    result: LiveTradeExecutionResult
    completed_at: datetime
    audit_id: str | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.status,
            LiveTradingStatus,
        ):
            raise TypeError(
                "status must be a LiveTradingStatus"
            )

        if not isinstance(self.session, TradingSession):
            raise TypeError(
                "session must be a TradingSession"
            )

        if not isinstance(self.request, LiveTradeRequest):
            raise TypeError(
                "request must be a LiveTradeRequest"
            )

        if not isinstance(self.plan, TradeExecutionPlan):
            raise TypeError(
                "plan must be a TradeExecutionPlan"
            )

        if not isinstance(
            self.result,
            LiveTradeExecutionResult,
        ):
            raise TypeError(
                "result must be a LiveTradeExecutionResult"
            )

        TradingSession._validate_datetime(
            self.completed_at,
            "completed_at",
        )

        if self.request.session_id != self.session.session_id:
            raise ValueError(
                "request session_id must match the session"
            )

        if self.plan.request_id != self.request.request_id:
            raise ValueError(
                "plan request_id must match the request"
            )

        if self.result.request_id != self.request.request_id:
            raise ValueError(
                "result request_id must match the request"
            )

        if self.result.plan_id != self.plan.plan_id:
            raise ValueError(
                "result plan_id must match the plan"
            )

        if self.result.decision is not self.plan.decision:
            raise ValueError(
                "result decision must match the plan decision"
            )

        normalized_audit_id = (
            LiveTradeExecutionResult._normalize_optional_text(
                self.audit_id,
                "audit_id",
            )
        )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if self.status is LiveTradingStatus.FAILED:
            if not normalized_error:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error:
            raise ValueError(
                "only failed reports may include an error"
            )

        if (
            self.status is LiveTradingStatus.COMPLETED
            and self.plan.decision is LiveTradeDecision.EXECUTE
            and not self.result.submitted
        ):
            raise ValueError(
                "completed executable reports must include submission"
            )

        object.__setattr__(
            self,
            "audit_id",
            normalized_audit_id,
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