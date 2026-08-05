from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.strategy.broker_gateway import (
    BrokerOrderRequest,
)
from app.strategy.order_manager import (
    OrderRequest,
)
from app.strategy.risk_gateway import (
    RiskEvaluationRequest,
)
from app.strategy.trading_session import (
    TradingSession,
)


class ExecutionStatus(str, Enum):
    """Lifecycle status of a coordinated execution."""

    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    HELD = "HELD"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ExecutionDecision(str, Enum):
    """Decision produced by an execution stage."""

    PROCEED = "PROCEED"
    HOLD = "HOLD"
    REJECT = "REJECT"
    CANCEL = "CANCEL"
    NO_ACTION = "NO_ACTION"


class ExecutionStage(str, Enum):
    """Ordered stages in the enterprise execution pipeline."""

    SESSION = "SESSION"
    PORTFOLIO = "PORTFOLIO"
    ORDER = "ORDER"
    RISK = "RISK"
    BROKER = "BROKER"
    EXECUTION = "EXECUTION"


_STAGE_ORDER = {
    ExecutionStage.SESSION: 1,
    ExecutionStage.PORTFOLIO: 2,
    ExecutionStage.ORDER: 3,
    ExecutionStage.RISK: 4,
    ExecutionStage.BROKER: 5,
    ExecutionStage.EXECUTION: 6,
}


_TERMINAL_STATUSES = {
    ExecutionStatus.COMPLETED,
    ExecutionStatus.HELD,
    ExecutionStatus.REJECTED,
    ExecutionStatus.FAILED,
    ExecutionStatus.CANCELLED,
}


class ExecutionModelSupport:
    """Shared validation helpers for coordinator models."""

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
class ExecutionRequest:
    """Immutable request to coordinate an enterprise trade."""

    execution_id: str
    correlation_id: str
    strategy_id: str
    portfolio_id: str
    session: TradingSession
    order_request: OrderRequest
    created_at: datetime
    risk_request: RiskEvaluationRequest | None = None
    broker_request: BrokerOrderRequest | None = None
    requested_by: str = "strategy-orchestrator"
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_execution_id = (
            ExecutionModelSupport.required_text(
                self.execution_id,
                "execution_id",
            )
        )
        normalized_correlation_id = (
            ExecutionModelSupport.required_text(
                self.correlation_id,
                "correlation_id",
            )
        )
        normalized_strategy_id = (
            ExecutionModelSupport.required_text(
                self.strategy_id,
                "strategy_id",
            )
        )
        normalized_portfolio_id = (
            ExecutionModelSupport.required_text(
                self.portfolio_id,
                "portfolio_id",
            )
        )
        normalized_requested_by = (
            ExecutionModelSupport.required_text(
                self.requested_by,
                "requested_by",
            )
        )

        if not isinstance(
            self.session,
            TradingSession,
        ):
            raise TypeError(
                "session must be a TradingSession"
            )

        if not isinstance(
            self.order_request,
            OrderRequest,
        ):
            raise TypeError(
                "order_request must be an OrderRequest"
            )

        if (
            self.risk_request is not None
            and not isinstance(
                self.risk_request,
                RiskEvaluationRequest,
            )
        ):
            raise TypeError(
                "risk_request must be a "
                "RiskEvaluationRequest or None"
            )

        if (
            self.broker_request is not None
            and not isinstance(
                self.broker_request,
                BrokerOrderRequest,
            )
        ):
            raise TypeError(
                "broker_request must be a "
                "BrokerOrderRequest or None"
            )

        ExecutionModelSupport.validate_datetime(
            self.created_at,
            "created_at",
        )

        if (
            normalized_portfolio_id
            != self.order_request.portfolio_id
        ):
            raise ValueError(
                "portfolio_id must match "
                "order_request portfolio_id"
            )

        if (
            self.order_request.strategy_id is not None
            and normalized_strategy_id
            != self.order_request.strategy_id
        ):
            raise ValueError(
                "strategy_id must match "
                "order_request strategy_id"
            )

        if (
            self.order_request.created_at
            > self.created_at
        ):
            raise ValueError(
                "order_request created_at must not be later "
                "than execution created_at"
            )

        if (
            self.session.evaluated_at
            > self.created_at
        ):
            raise ValueError(
                "session evaluated_at must not be later "
                "than execution created_at"
            )

        if (
            self.risk_request is not None
            and self.risk_request.request
            != self.order_request
        ):
            raise ValueError(
                "risk_request order must match "
                "order_request"
            )

        if (
            self.risk_request is not None
            and self.risk_request.portfolio_id
            != normalized_portfolio_id
        ):
            raise ValueError(
                "risk_request portfolio_id must match "
                "execution portfolio_id"
            )

        if self.broker_request is not None:
            if (
                self.broker_request.order_id
                != self.order_request.order_id
            ):
                raise ValueError(
                    "broker_request order_id must match "
                    "order_request order_id"
                )

            if (
                self.broker_request.client_order_id
                != self.order_request.client_order_id
            ):
                raise ValueError(
                    "broker_request client_order_id must "
                    "match order_request"
                )

            if (
                self.broker_request.symbol
                != self.order_request.symbol
            ):
                raise ValueError(
                    "broker_request symbol must match "
                    "order_request symbol"
                )

            if (
                self.broker_request.quantity
                != self.order_request.quantity
            ):
                raise ValueError(
                    "broker_request quantity must match "
                    "order_request quantity"
                )

        normalized_metadata = (
            ExecutionModelSupport.normalize_pairs(
                self.metadata,
                "metadata",
            )
        )

        object.__setattr__(
            self,
            "execution_id",
            normalized_execution_id,
        )
        object.__setattr__(
            self,
            "correlation_id",
            normalized_correlation_id,
        )
        object.__setattr__(
            self,
            "strategy_id",
            normalized_strategy_id,
        )
        object.__setattr__(
            self,
            "portfolio_id",
            normalized_portfolio_id,
        )
        object.__setattr__(
            self,
            "requested_by",
            normalized_requested_by,
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )


@dataclass(frozen=True, slots=True)
class ExecutionStep:
    """Immutable record of one execution pipeline stage."""

    step_id: str
    execution_id: str
    stage: ExecutionStage
    decision: ExecutionDecision
    started_at: datetime
    message: str
    successful: bool
    completed_at: datetime | None = None
    reference_id: str | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_step_id = (
            ExecutionModelSupport.required_text(
                self.step_id,
                "step_id",
            )
        )
        normalized_execution_id = (
            ExecutionModelSupport.required_text(
                self.execution_id,
                "execution_id",
            )
        )
        normalized_message = (
            ExecutionModelSupport.required_text(
                self.message,
                "message",
            )
        )

        if not isinstance(
            self.stage,
            ExecutionStage,
        ):
            raise TypeError(
                "stage must be an ExecutionStage"
            )

        if not isinstance(
            self.decision,
            ExecutionDecision,
        ):
            raise TypeError(
                "decision must be an ExecutionDecision"
            )

        if not isinstance(self.successful, bool):
            raise TypeError(
                "successful must be a bool"
            )

        ExecutionModelSupport.validate_datetime(
            self.started_at,
            "started_at",
        )

        if self.completed_at is not None:
            ExecutionModelSupport.validate_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.started_at:
                raise ValueError(
                    "completed_at must not be earlier "
                    "than started_at"
                )

        normalized_reference_id = (
            ExecutionModelSupport.optional_text(
                self.reference_id,
                "reference_id",
            )
        )
        normalized_error = (
            ExecutionModelSupport.optional_text(
                self.error,
                "error",
            )
        )

        if self.successful:
            if normalized_error is not None:
                raise ValueError(
                    "successful steps must not include "
                    "an error"
                )

            if self.decision in {
                ExecutionDecision.REJECT,
                ExecutionDecision.CANCEL,
            }:
                raise ValueError(
                    "successful steps must not have "
                    "a reject or cancel decision"
                )
        else:
            if normalized_error is None:
                raise ValueError(
                    "unsuccessful steps must include "
                    "an error"
                )

            if self.decision is ExecutionDecision.PROCEED:
                raise ValueError(
                    "unsuccessful steps must not proceed"
                )

        if (
            self.decision
            is ExecutionDecision.PROCEED
            and not self.successful
        ):
            raise ValueError(
                "proceed decisions require a successful step"
            )

        normalized_warnings = (
            ExecutionModelSupport.normalize_warnings(
                self.warnings
            )
        )
        normalized_metadata = (
            ExecutionModelSupport.normalize_pairs(
                self.metadata,
                "metadata",
            )
        )

        object.__setattr__(
            self,
            "step_id",
            normalized_step_id,
        )
        object.__setattr__(
            self,
            "execution_id",
            normalized_execution_id,
        )
        object.__setattr__(
            self,
            "message",
            normalized_message,
        )
        object.__setattr__(
            self,
            "reference_id",
            normalized_reference_id,
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
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    @property
    def stage_position(self) -> int:
        return _STAGE_ORDER[self.stage]


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Immutable aggregate result of a coordinated execution."""

    execution_id: str
    status: ExecutionStatus
    decision: ExecutionDecision
    started_at: datetime
    updated_at: datetime
    steps: tuple[ExecutionStep, ...] = field(
        default_factory=tuple
    )
    completed_at: datetime | None = None
    final_order_id: str | None = None
    broker_order_id: str | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        normalized_execution_id = (
            ExecutionModelSupport.required_text(
                self.execution_id,
                "execution_id",
            )
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

        ExecutionModelSupport.validate_datetime(
            self.started_at,
            "started_at",
        )
        ExecutionModelSupport.validate_datetime(
            self.updated_at,
            "updated_at",
        )

        if self.updated_at < self.started_at:
            raise ValueError(
                "updated_at must not be earlier "
                "than started_at"
            )

        if self.completed_at is not None:
            ExecutionModelSupport.validate_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.started_at:
                raise ValueError(
                    "completed_at must not be earlier "
                    "than started_at"
                )

            if self.completed_at < self.updated_at:
                raise ValueError(
                    "completed_at must not be earlier "
                    "than updated_at"
                )

        normalized_steps = tuple(self.steps)

        for step in normalized_steps:
            if not isinstance(
                step,
                ExecutionStep,
            ):
                raise TypeError(
                    "every step must be an ExecutionStep"
                )

            if (
                step.execution_id
                != normalized_execution_id
            ):
                raise ValueError(
                    "step execution_id must match result"
                )

            if step.started_at < self.started_at:
                raise ValueError(
                    "step started_at must not be earlier "
                    "than result started_at"
                )

            if step.started_at > self.updated_at:
                raise ValueError(
                    "step started_at must not be later "
                    "than result updated_at"
                )

            if (
                step.completed_at is not None
                and step.completed_at > self.updated_at
            ):
                raise ValueError(
                    "step completed_at must not be later "
                    "than result updated_at"
                )

        step_ids = [
            step.step_id
            for step in normalized_steps
        ]

        if len(set(step_ids)) != len(step_ids):
            raise ValueError(
                "step_id values must be unique"
            )

        stage_positions = [
            step.stage_position
            for step in normalized_steps
        ]

        if stage_positions != sorted(
            stage_positions
        ):
            raise ValueError(
                "steps must be ordered by execution stage"
            )

        if len(set(stage_positions)) != len(
            stage_positions
        ):
            raise ValueError(
                "execution stages must be unique"
            )

        normalized_final_order_id = (
            ExecutionModelSupport.optional_text(
                self.final_order_id,
                "final_order_id",
            )
        )
        normalized_broker_order_id = (
            ExecutionModelSupport.optional_text(
                self.broker_order_id,
                "broker_order_id",
            )
        )
        normalized_error = (
            ExecutionModelSupport.optional_text(
                self.error,
                "error",
            )
        )

        if self.status in _TERMINAL_STATUSES:
            if self.completed_at is None:
                raise ValueError(
                    "terminal execution results must include "
                    "completed_at"
                )
        elif self.completed_at is not None:
            raise ValueError(
                "non-terminal execution results must not "
                "include completed_at"
            )

        if self.status is ExecutionStatus.COMPLETED:
            if self.decision is not ExecutionDecision.PROCEED:
                raise ValueError(
                    "completed executions require "
                    "a proceed decision"
                )

            if normalized_error is not None:
                raise ValueError(
                    "completed executions must not include "
                    "an error"
                )

            if normalized_final_order_id is None:
                raise ValueError(
                    "completed executions must include "
                    "final_order_id"
                )

            if normalized_broker_order_id is None:
                raise ValueError(
                    "completed executions must include "
                    "broker_order_id"
                )

            if not normalized_steps:
                raise ValueError(
                    "completed executions must include steps"
                )

            if not all(
                step.successful
                for step in normalized_steps
            ):
                raise ValueError(
                    "completed executions require all steps "
                    "to be successful"
                )

        if self.status is ExecutionStatus.HELD:
            if self.decision is not ExecutionDecision.HOLD:
                raise ValueError(
                    "held executions require a hold decision"
                )

        if self.status is ExecutionStatus.REJECTED:
            if self.decision is not ExecutionDecision.REJECT:
                raise ValueError(
                    "rejected executions require "
                    "a reject decision"
                )

        if self.status is ExecutionStatus.CANCELLED:
            if self.decision is not ExecutionDecision.CANCEL:
                raise ValueError(
                    "cancelled executions require "
                    "a cancel decision"
                )

        if self.status is ExecutionStatus.FAILED:
            if normalized_error is None:
                raise ValueError(
                    "failed executions must include an error"
                )
        elif normalized_error is not None:
            raise ValueError(
                "only failed executions may include an error"
            )

        if (
            self.status is ExecutionStatus.EXECUTING
            and self.decision is not ExecutionDecision.PROCEED
        ):
            raise ValueError(
                "executing results require "
                "a proceed decision"
            )

        normalized_warnings = (
            ExecutionModelSupport.normalize_warnings(
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
            "steps",
            normalized_steps,
        )
        object.__setattr__(
            self,
            "final_order_id",
            normalized_final_order_id,
        )
        object.__setattr__(
            self,
            "broker_order_id",
            normalized_broker_order_id,
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

    @property
    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATUSES

    @property
    def successful_step_count(self) -> int:
        return sum(
            1
            for step in self.steps
            if step.successful
        )

    @property
    def failed_step(self) -> ExecutionStep | None:
        for step in self.steps:
            if not step.successful:
                return step

        return None


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    """Immutable audit report for one coordinated execution."""

    report_id: str
    request: ExecutionRequest
    result: ExecutionResult
    reported_at: datetime
    message: str
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_report_id = (
            ExecutionModelSupport.required_text(
                self.report_id,
                "report_id",
            )
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

        normalized_message = (
            ExecutionModelSupport.required_text(
                self.message,
                "message",
            )
        )

        ExecutionModelSupport.validate_datetime(
            self.reported_at,
            "reported_at",
        )

        if (
            self.request.execution_id
            != self.result.execution_id
        ):
            raise ValueError(
                "request and result execution_id values "
                "must match"
            )

        if self.result.started_at < self.request.created_at:
            raise ValueError(
                "result started_at must not be earlier "
                "than request created_at"
            )

        if self.reported_at < self.result.updated_at:
            raise ValueError(
                "reported_at must not be earlier than "
                "result updated_at"
            )

        if (
            self.result.completed_at is not None
            and self.reported_at
            < self.result.completed_at
        ):
            raise ValueError(
                "reported_at must not be earlier than "
                "result completed_at"
            )

        normalized_metadata = (
            ExecutionModelSupport.normalize_pairs(
                self.metadata,
                "metadata",
            )
        )
        normalized_warnings = (
            ExecutionModelSupport.normalize_warnings(
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
            "message",
            normalized_message,
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