from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class StrategyOrchestratorStatus(str, Enum):
    """Lifecycle status of an orchestrated strategy workflow."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StrategyWorkflowStage(str, Enum):
    """Ordered stages in the enterprise strategy workflow."""

    REQUEST_RECEIVED = "REQUEST_RECEIVED"
    REGIME_EVALUATED = "REGIME_EVALUATED"
    AGENTS_COORDINATED = "AGENTS_COORDINATED"
    PORTFOLIO_OPTIMIZED = "PORTFOLIO_OPTIMIZED"
    RISK_EVALUATED = "RISK_EVALUATED"
    REBALANCE_EVALUATED = "REBALANCE_EVALUATED"
    EXECUTION_PLANNED = "EXECUTION_PLANNED"
    EXECUTION_COMPLETED = "EXECUTION_COMPLETED"
    AUDIT_COMPLETED = "AUDIT_COMPLETED"
    PERFORMANCE_RECORDED = "PERFORMANCE_RECORDED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class StrategyWorkflowDecision(str, Enum):
    """Final workflow routing decision."""

    EXECUTE_PAPER = "EXECUTE_PAPER"
    EXECUTE_LIVE = "EXECUTE_LIVE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECT = "REJECT"
    NO_ACTION = "NO_ACTION"


class StrategyExecutionEnvironment(str, Enum):
    """Requested execution destination."""

    PAPER = "PAPER"
    LIVE = "LIVE"


class StrategyWorkflowStepStatus(str, Enum):
    """Status of one workflow step."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


_STAGE_ORDER = {
    StrategyWorkflowStage.REQUEST_RECEIVED: 0,
    StrategyWorkflowStage.REGIME_EVALUATED: 1,
    StrategyWorkflowStage.AGENTS_COORDINATED: 2,
    StrategyWorkflowStage.PORTFOLIO_OPTIMIZED: 3,
    StrategyWorkflowStage.RISK_EVALUATED: 4,
    StrategyWorkflowStage.REBALANCE_EVALUATED: 5,
    StrategyWorkflowStage.EXECUTION_PLANNED: 6,
    StrategyWorkflowStage.EXECUTION_COMPLETED: 7,
    StrategyWorkflowStage.AUDIT_COMPLETED: 8,
    StrategyWorkflowStage.PERFORMANCE_RECORDED: 9,
    StrategyWorkflowStage.REVIEW_REQUIRED: 10,
    StrategyWorkflowStage.REJECTED: 10,
    StrategyWorkflowStage.FAILED: 10,
}

_TERMINAL_STAGES = {
    StrategyWorkflowStage.PERFORMANCE_RECORDED,
    StrategyWorkflowStage.REVIEW_REQUIRED,
    StrategyWorkflowStage.REJECTED,
    StrategyWorkflowStage.FAILED,
}


@dataclass(frozen=True, slots=True)
class StrategyWorkflowRequest:
    """Immutable request submitted to the strategy orchestrator."""

    workflow_id: str
    correlation_id: str
    strategy_id: str
    portfolio_id: str
    account_id: str
    environment: StrategyExecutionEnvironment
    requested_at: datetime
    live_trading_confirmed: bool = False
    force_rebalance: bool = False
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_workflow_id = self.workflow_id.strip()
        normalized_correlation_id = self.correlation_id.strip()
        normalized_strategy_id = self.strategy_id.strip()
        normalized_portfolio_id = self.portfolio_id.strip()
        normalized_account_id = self.account_id.strip()

        for field_name, value in (
            ("workflow_id", normalized_workflow_id),
            ("correlation_id", normalized_correlation_id),
            ("strategy_id", normalized_strategy_id),
            ("portfolio_id", normalized_portfolio_id),
            ("account_id", normalized_account_id),
        ):
            if not value:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if not isinstance(
            self.environment,
            StrategyExecutionEnvironment,
        ):
            raise TypeError(
                "environment must be a "
                "StrategyExecutionEnvironment"
            )

        self._validate_datetime(
            self.requested_at,
            "requested_at",
        )

        for field_name in (
            "live_trading_confirmed",
            "force_rebalance",
        ):
            if not isinstance(
                getattr(self, field_name),
                bool,
            ):
                raise TypeError(
                    f"{field_name} must be a bool"
                )

        if (
            self.environment
            is StrategyExecutionEnvironment.LIVE
            and not self.live_trading_confirmed
        ):
            raise ValueError(
                "live workflows require explicit "
                "live-trading confirmation"
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
                    "each metadata item must be a "
                    "two-item tuple"
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
            "workflow_id",
            normalized_workflow_id,
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
class StrategyWorkflowStep:
    """Immutable result from one orchestrated workflow stage."""

    step_id: str
    workflow_id: str
    stage: StrategyWorkflowStage
    status: StrategyWorkflowStepStatus
    started_at: datetime
    completed_at: datetime | None
    summary: str
    component: str
    decision: StrategyWorkflowDecision | None = None
    reference_id: str | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_step_id = self.step_id.strip()
        normalized_workflow_id = self.workflow_id.strip()
        normalized_summary = self.summary.strip()
        normalized_component = self.component.strip()

        for field_name, value in (
            ("step_id", normalized_step_id),
            ("workflow_id", normalized_workflow_id),
            ("summary", normalized_summary),
            ("component", normalized_component),
        ):
            if not value:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if not isinstance(
            self.stage,
            StrategyWorkflowStage,
        ):
            raise TypeError(
                "stage must be a StrategyWorkflowStage"
            )

        if not isinstance(
            self.status,
            StrategyWorkflowStepStatus,
        ):
            raise TypeError(
                "status must be a "
                "StrategyWorkflowStepStatus"
            )

        StrategyWorkflowRequest._validate_datetime(
            self.started_at,
            "started_at",
        )

        if self.completed_at is not None:
            StrategyWorkflowRequest._validate_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.started_at:
                raise ValueError(
                    "completed_at must not be earlier "
                    "than started_at"
                )

        if (
            self.status
            is StrategyWorkflowStepStatus.PENDING
            and self.completed_at is not None
        ):
            raise ValueError(
                "pending steps must not include completed_at"
            )

        if (
            self.status
            is not StrategyWorkflowStepStatus.PENDING
            and self.completed_at is None
        ):
            raise ValueError(
                "non-pending steps must include completed_at"
            )

        if (
            self.decision is not None
            and not isinstance(
                self.decision,
                StrategyWorkflowDecision,
            )
        ):
            raise TypeError(
                "decision must be a "
                "StrategyWorkflowDecision or None"
            )

        normalized_reference_id = (
            self._normalize_optional_text(
                self.reference_id,
                "reference_id",
            )
        )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if (
            self.status
            is StrategyWorkflowStepStatus.FAILED
        ):
            if not normalized_error:
                raise ValueError(
                    "failed steps must include an error"
                )
        elif normalized_error:
            raise ValueError(
                "only failed steps may include an error"
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
                    "each metadata item must be a "
                    "two-item tuple"
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
            "step_id",
            normalized_step_id,
        )
        object.__setattr__(
            self,
            "workflow_id",
            normalized_workflow_id,
        )
        object.__setattr__(
            self,
            "summary",
            normalized_summary,
        )
        object.__setattr__(
            self,
            "component",
            normalized_component,
        )
        object.__setattr__(
            self,
            "reference_id",
            normalized_reference_id,
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
        object.__setattr__(
            self,
            "metadata",
            tuple(normalized_metadata),
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
class StrategyWorkflowPlan:
    """Immutable execution plan for one strategy workflow."""

    plan_id: str
    workflow_id: str
    environment: StrategyExecutionEnvironment
    decision: StrategyWorkflowDecision
    current_stage: StrategyWorkflowStage
    steps: tuple[StrategyWorkflowStep, ...]
    created_at: datetime
    terminal: bool
    completed_at: datetime | None = None
    execution_reference_id: str | None = None
    audit_reference_id: str | None = None
    performance_reference_id: str | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_plan_id = self.plan_id.strip()
        normalized_workflow_id = self.workflow_id.strip()

        if not normalized_plan_id:
            raise ValueError(
                "plan_id must not be empty"
            )

        if not normalized_workflow_id:
            raise ValueError(
                "workflow_id must not be empty"
            )

        if not isinstance(
            self.environment,
            StrategyExecutionEnvironment,
        ):
            raise TypeError(
                "environment must be a "
                "StrategyExecutionEnvironment"
            )

        if not isinstance(
            self.decision,
            StrategyWorkflowDecision,
        ):
            raise TypeError(
                "decision must be a "
                "StrategyWorkflowDecision"
            )

        if not isinstance(
            self.current_stage,
            StrategyWorkflowStage,
        ):
            raise TypeError(
                "current_stage must be a "
                "StrategyWorkflowStage"
            )

        if not isinstance(self.terminal, bool):
            raise TypeError(
                "terminal must be a bool"
            )

        StrategyWorkflowRequest._validate_datetime(
            self.created_at,
            "created_at",
        )

        if self.completed_at is not None:
            StrategyWorkflowRequest._validate_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.created_at:
                raise ValueError(
                    "completed_at must not be earlier "
                    "than created_at"
                )

        if self.terminal and self.completed_at is None:
            raise ValueError(
                "terminal plans must include completed_at"
            )

        if not self.terminal and self.completed_at is not None:
            raise ValueError(
                "only terminal plans may include completed_at"
            )

        if (
            self.terminal
            and self.current_stage not in _TERMINAL_STAGES
        ):
            raise ValueError(
                "terminal plans must use a terminal stage"
            )

        if (
            not self.terminal
            and self.current_stage in _TERMINAL_STAGES
        ):
            raise ValueError(
                "terminal stages require terminal=True"
            )

        normalized_steps = tuple(self.steps)

        if not normalized_steps:
            raise ValueError(
                "steps must not be empty"
            )

        for step in normalized_steps:
            if not isinstance(
                step,
                StrategyWorkflowStep,
            ):
                raise TypeError(
                    "every step must be a "
                    "StrategyWorkflowStep"
                )

            if step.workflow_id != normalized_workflow_id:
                raise ValueError(
                    "step workflow_id must match the plan"
                )

        step_ids = [
            step.step_id
            for step in normalized_steps
        ]

        if len(set(step_ids)) != len(step_ids):
            raise ValueError(
                "step_id values must be unique"
            )

        self._validate_stage_order(normalized_steps)

        if (
            normalized_steps[-1].stage
            is not self.current_stage
        ):
            raise ValueError(
                "current_stage must match the final step"
            )

        if (
            self.decision
            is StrategyWorkflowDecision.EXECUTE_PAPER
            and self.environment
            is not StrategyExecutionEnvironment.PAPER
        ):
            raise ValueError(
                "EXECUTE_PAPER requires PAPER environment"
            )

        if (
            self.decision
            is StrategyWorkflowDecision.EXECUTE_LIVE
            and self.environment
            is not StrategyExecutionEnvironment.LIVE
        ):
            raise ValueError(
                "EXECUTE_LIVE requires LIVE environment"
            )

        normalized_execution_reference = (
            StrategyWorkflowStep._normalize_optional_text(
                self.execution_reference_id,
                "execution_reference_id",
            )
        )
        normalized_audit_reference = (
            StrategyWorkflowStep._normalize_optional_text(
                self.audit_reference_id,
                "audit_reference_id",
            )
        )
        normalized_performance_reference = (
            StrategyWorkflowStep._normalize_optional_text(
                self.performance_reference_id,
                "performance_reference_id",
            )
        )

        if (
            self.current_stage
            in {
                StrategyWorkflowStage.EXECUTION_COMPLETED,
                StrategyWorkflowStage.AUDIT_COMPLETED,
                StrategyWorkflowStage.PERFORMANCE_RECORDED,
            }
            and normalized_execution_reference is None
        ):
            raise ValueError(
                "completed execution stages require "
                "execution_reference_id"
            )

        if (
            self.current_stage
            in {
                StrategyWorkflowStage.AUDIT_COMPLETED,
                StrategyWorkflowStage.PERFORMANCE_RECORDED,
            }
            and normalized_audit_reference is None
        ):
            raise ValueError(
                "completed audit stages require "
                "audit_reference_id"
            )

        if (
            self.current_stage
            is StrategyWorkflowStage.PERFORMANCE_RECORDED
            and normalized_performance_reference is None
        ):
            raise ValueError(
                "performance completion requires "
                "performance_reference_id"
            )

        object.__setattr__(
            self,
            "plan_id",
            normalized_plan_id,
        )
        object.__setattr__(
            self,
            "workflow_id",
            normalized_workflow_id,
        )
        object.__setattr__(
            self,
            "steps",
            normalized_steps,
        )
        object.__setattr__(
            self,
            "execution_reference_id",
            normalized_execution_reference,
        )
        object.__setattr__(
            self,
            "audit_reference_id",
            normalized_audit_reference,
        )
        object.__setattr__(
            self,
            "performance_reference_id",
            normalized_performance_reference,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )

    @staticmethod
    def _validate_stage_order(
        steps: tuple[StrategyWorkflowStep, ...],
    ) -> None:
        previous_order = -1

        for step in steps:
            current_order = _STAGE_ORDER[step.stage]

            if current_order < previous_order:
                raise ValueError(
                    "workflow stages must be ordered"
                )

            previous_order = current_order


@dataclass(frozen=True, slots=True)
class StrategyWorkflowReport:
    """Unified report produced by the strategy orchestrator."""

    status: StrategyOrchestratorStatus
    request: StrategyWorkflowRequest
    plan: StrategyWorkflowPlan | None
    decision: StrategyWorkflowDecision
    completed_at: datetime
    recommendation: str
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.status,
            StrategyOrchestratorStatus,
        ):
            raise TypeError(
                "status must be a "
                "StrategyOrchestratorStatus"
            )

        if not isinstance(
            self.request,
            StrategyWorkflowRequest,
        ):
            raise TypeError(
                "request must be a "
                "StrategyWorkflowRequest"
            )

        if (
            self.plan is not None
            and not isinstance(
                self.plan,
                StrategyWorkflowPlan,
            )
        ):
            raise TypeError(
                "plan must be a StrategyWorkflowPlan "
                "or None"
            )

        if not isinstance(
            self.decision,
            StrategyWorkflowDecision,
        ):
            raise TypeError(
                "decision must be a "
                "StrategyWorkflowDecision"
            )

        StrategyWorkflowRequest._validate_datetime(
            self.completed_at,
            "completed_at",
        )

        if self.completed_at < self.request.requested_at:
            raise ValueError(
                "completed_at must not be earlier "
                "than requested_at"
            )

        normalized_recommendation = (
            self.recommendation.strip()
        )

        if not normalized_recommendation:
            raise ValueError(
                "recommendation must not be empty"
            )

        if self.plan is not None:
            if (
                self.plan.workflow_id
                != self.request.workflow_id
            ):
                raise ValueError(
                    "plan workflow_id must match the request"
                )

            if self.plan.decision is not self.decision:
                raise ValueError(
                    "report decision must match the plan"
                )

            if (
                self.plan.environment
                is not self.request.environment
            ):
                raise ValueError(
                    "plan environment must match the request"
                )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if (
            self.status
            is StrategyOrchestratorStatus.FAILED
        ):
            if not normalized_error:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error:
            raise ValueError(
                "only failed reports may include an error"
            )

        if (
            self.status
            is StrategyOrchestratorStatus.COMPLETED
            and self.plan is None
        ):
            raise ValueError(
                "completed reports must include a plan"
            )

        if (
            self.decision
            is StrategyWorkflowDecision.EXECUTE_LIVE
            and not self.request.live_trading_confirmed
        ):
            raise ValueError(
                "live execution requires explicit "
                "live-trading confirmation"
            )

        object.__setattr__(
            self,
            "recommendation",
            normalized_recommendation,
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