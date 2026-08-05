from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.strategy.execution_coordinator import (
    ExecutionReport,
    ExecutionRequest,
)


class WorkflowStatus(str, Enum):
    """Lifecycle state of an enterprise trading workflow."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    HELD = "HELD"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class WorkflowDecision(str, Enum):
    """Decision produced by the trading orchestrator."""

    PROCEED = "PROCEED"
    HOLD = "HOLD"
    REJECT = "REJECT"
    CANCEL = "CANCEL"
    NO_ACTION = "NO_ACTION"


class WorkflowStage(str, Enum):
    """Ordered stages in the enterprise trading workflow."""

    STRATEGY = "STRATEGY"
    SESSION = "SESSION"
    PORTFOLIO = "PORTFOLIO"
    ORDER = "ORDER"
    RISK = "RISK"
    BROKER = "BROKER"
    EXECUTION = "EXECUTION"


_STAGE_POSITION = {
    WorkflowStage.STRATEGY: 1,
    WorkflowStage.SESSION: 2,
    WorkflowStage.PORTFOLIO: 3,
    WorkflowStage.ORDER: 4,
    WorkflowStage.RISK: 5,
    WorkflowStage.BROKER: 6,
    WorkflowStage.EXECUTION: 7,
}


_TERMINAL_STATUSES = {
    WorkflowStatus.COMPLETED,
    WorkflowStatus.HELD,
    WorkflowStatus.REJECTED,
    WorkflowStatus.CANCELLED,
    WorkflowStatus.FAILED,
}


class WorkflowModelSupport:
    """Shared validation helpers for orchestrator models."""

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
        values: (
            tuple[tuple[str, str], ...]
            | list[tuple[str, str]]
        ),
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
class TradingWorkflowRequest:
    """Immutable request to orchestrate a complete trade workflow."""

    workflow_id: str
    correlation_id: str
    strategy_id: str
    portfolio_id: str
    execution_request: ExecutionRequest
    created_at: datetime
    requested_by: str = "strategy-orchestrator"
    priority: int = 100
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        workflow_id = WorkflowModelSupport.required_text(
            self.workflow_id,
            "workflow_id",
        )
        correlation_id = WorkflowModelSupport.required_text(
            self.correlation_id,
            "correlation_id",
        )
        strategy_id = WorkflowModelSupport.required_text(
            self.strategy_id,
            "strategy_id",
        )
        portfolio_id = WorkflowModelSupport.required_text(
            self.portfolio_id,
            "portfolio_id",
        )
        requested_by = WorkflowModelSupport.required_text(
            self.requested_by,
            "requested_by",
        )

        if not isinstance(
            self.execution_request,
            ExecutionRequest,
        ):
            raise TypeError(
                "execution_request must be an ExecutionRequest"
            )

        WorkflowModelSupport.validate_datetime(
            self.created_at,
            "created_at",
        )

        if not isinstance(self.priority, int):
            raise TypeError(
                "priority must be an integer"
            )

        if self.priority < 0:
            raise ValueError(
                "priority must not be negative"
            )

        if (
            correlation_id
            != self.execution_request.correlation_id
        ):
            raise ValueError(
                "correlation_id must match "
                "execution_request correlation_id"
            )

        if (
            strategy_id
            != self.execution_request.strategy_id
        ):
            raise ValueError(
                "strategy_id must match "
                "execution_request strategy_id"
            )

        if (
            portfolio_id
            != self.execution_request.portfolio_id
        ):
            raise ValueError(
                "portfolio_id must match "
                "execution_request portfolio_id"
            )

        if (
            self.execution_request.created_at
            > self.created_at
        ):
            raise ValueError(
                "execution_request created_at must not be "
                "later than workflow created_at"
            )

        metadata = WorkflowModelSupport.normalize_pairs(
            self.metadata,
            "metadata",
        )

        object.__setattr__(
            self,
            "workflow_id",
            workflow_id,
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
            "requested_by",
            requested_by,
        )
        object.__setattr__(
            self,
            "metadata",
            metadata,
        )

    @property
    def order_id(self) -> str:
        return (
            self.execution_request
            .order_request
            .order_id
        )

    @property
    def execution_id(self) -> str:
        return self.execution_request.execution_id


@dataclass(frozen=True, slots=True)
class WorkflowCheckpoint:
    """Immutable audit checkpoint for one workflow stage."""

    checkpoint_id: str
    workflow_id: str
    stage: WorkflowStage
    decision: WorkflowDecision
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
        checkpoint_id = WorkflowModelSupport.required_text(
            self.checkpoint_id,
            "checkpoint_id",
        )
        workflow_id = WorkflowModelSupport.required_text(
            self.workflow_id,
            "workflow_id",
        )
        message = WorkflowModelSupport.required_text(
            self.message,
            "message",
        )

        if not isinstance(
            self.stage,
            WorkflowStage,
        ):
            raise TypeError(
                "stage must be a WorkflowStage"
            )

        if not isinstance(
            self.decision,
            WorkflowDecision,
        ):
            raise TypeError(
                "decision must be a WorkflowDecision"
            )

        if not isinstance(self.successful, bool):
            raise TypeError(
                "successful must be a bool"
            )

        WorkflowModelSupport.validate_datetime(
            self.started_at,
            "started_at",
        )

        if self.completed_at is not None:
            WorkflowModelSupport.validate_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.started_at:
                raise ValueError(
                    "completed_at must not be earlier "
                    "than started_at"
                )

        reference_id = WorkflowModelSupport.optional_text(
            self.reference_id,
            "reference_id",
        )
        error = WorkflowModelSupport.optional_text(
            self.error,
            "error",
        )

        if self.successful:
            if error is not None:
                raise ValueError(
                    "successful checkpoints must not "
                    "include an error"
                )

            if self.decision in {
                WorkflowDecision.REJECT,
                WorkflowDecision.CANCEL,
            }:
                raise ValueError(
                    "successful checkpoints must not use "
                    "a reject or cancel decision"
                )
        else:
            if error is None:
                raise ValueError(
                    "unsuccessful checkpoints must include "
                    "an error"
                )

            if self.decision is WorkflowDecision.PROCEED:
                raise ValueError(
                    "unsuccessful checkpoints must not proceed"
                )

        warnings = WorkflowModelSupport.normalize_warnings(
            self.warnings
        )
        metadata = WorkflowModelSupport.normalize_pairs(
            self.metadata,
            "metadata",
        )

        object.__setattr__(
            self,
            "checkpoint_id",
            checkpoint_id,
        )
        object.__setattr__(
            self,
            "workflow_id",
            workflow_id,
        )
        object.__setattr__(
            self,
            "message",
            message,
        )
        object.__setattr__(
            self,
            "reference_id",
            reference_id,
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
    def is_complete(self) -> bool:
        return self.completed_at is not None

    @property
    def stage_position(self) -> int:
        return _STAGE_POSITION[self.stage]


@dataclass(frozen=True, slots=True)
class TradingWorkflowResult:
    """Immutable aggregate result of one trading workflow."""

    workflow_id: str
    status: WorkflowStatus
    decision: WorkflowDecision
    started_at: datetime
    updated_at: datetime
    checkpoints: tuple[WorkflowCheckpoint, ...] = field(
        default_factory=tuple
    )
    completed_at: datetime | None = None
    execution_report: ExecutionReport | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        workflow_id = WorkflowModelSupport.required_text(
            self.workflow_id,
            "workflow_id",
        )

        if not isinstance(
            self.status,
            WorkflowStatus,
        ):
            raise TypeError(
                "status must be a WorkflowStatus"
            )

        if not isinstance(
            self.decision,
            WorkflowDecision,
        ):
            raise TypeError(
                "decision must be a WorkflowDecision"
            )

        WorkflowModelSupport.validate_datetime(
            self.started_at,
            "started_at",
        )
        WorkflowModelSupport.validate_datetime(
            self.updated_at,
            "updated_at",
        )

        if self.updated_at < self.started_at:
            raise ValueError(
                "updated_at must not be earlier than started_at"
            )

        if self.completed_at is not None:
            WorkflowModelSupport.validate_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.updated_at:
                raise ValueError(
                    "completed_at must not be earlier "
                    "than updated_at"
                )

        checkpoints = tuple(self.checkpoints)

        for checkpoint in checkpoints:
            if not isinstance(
                checkpoint,
                WorkflowCheckpoint,
            ):
                raise TypeError(
                    "every checkpoint must be "
                    "a WorkflowCheckpoint"
                )

            if checkpoint.workflow_id != workflow_id:
                raise ValueError(
                    "checkpoint workflow_id must match result"
                )

            if checkpoint.started_at < self.started_at:
                raise ValueError(
                    "checkpoint started_at must not be earlier "
                    "than result started_at"
                )

            if checkpoint.started_at > self.updated_at:
                raise ValueError(
                    "checkpoint started_at must not be later "
                    "than result updated_at"
                )

            if (
                checkpoint.completed_at is not None
                and checkpoint.completed_at > self.updated_at
            ):
                raise ValueError(
                    "checkpoint completed_at must not be later "
                    "than result updated_at"
                )

        checkpoint_ids = [
            checkpoint.checkpoint_id
            for checkpoint in checkpoints
        ]

        if len(checkpoint_ids) != len(
            set(checkpoint_ids)
        ):
            raise ValueError(
                "checkpoint_id values must be unique"
            )

        stage_positions = [
            checkpoint.stage_position
            for checkpoint in checkpoints
        ]

        if stage_positions != sorted(stage_positions):
            raise ValueError(
                "checkpoints must be ordered "
                "by workflow stage"
            )

        if len(stage_positions) != len(
            set(stage_positions)
        ):
            raise ValueError(
                "workflow stages must be unique"
            )

        if (
            self.execution_report is not None
            and not isinstance(
                self.execution_report,
                ExecutionReport,
            )
        ):
            raise TypeError(
                "execution_report must be an "
                "ExecutionReport or None"
            )

        error = WorkflowModelSupport.optional_text(
            self.error,
            "error",
        )

        if self.status in _TERMINAL_STATUSES:
            if self.completed_at is None:
                raise ValueError(
                    "terminal workflow results must include "
                    "completed_at"
                )
        elif self.completed_at is not None:
            raise ValueError(
                "non-terminal workflow results must not "
                "include completed_at"
            )

        if self.status is WorkflowStatus.COMPLETED:
            if self.decision is not WorkflowDecision.PROCEED:
                raise ValueError(
                    "completed workflows require "
                    "a proceed decision"
                )

            if self.execution_report is None:
                raise ValueError(
                    "completed workflows must include "
                    "execution_report"
                )

            if error is not None:
                raise ValueError(
                    "completed workflows must not include "
                    "an error"
                )

            if not checkpoints:
                raise ValueError(
                    "completed workflows must include "
                    "checkpoints"
                )

            if not all(
                checkpoint.successful
                for checkpoint in checkpoints
            ):
                raise ValueError(
                    "completed workflows require all "
                    "checkpoints to be successful"
                )

        if self.status is WorkflowStatus.HELD:
            if self.decision is not WorkflowDecision.HOLD:
                raise ValueError(
                    "held workflows require a hold decision"
                )

        if self.status is WorkflowStatus.REJECTED:
            if self.decision is not WorkflowDecision.REJECT:
                raise ValueError(
                    "rejected workflows require "
                    "a reject decision"
                )

        if self.status is WorkflowStatus.CANCELLED:
            if self.decision is not WorkflowDecision.CANCEL:
                raise ValueError(
                    "cancelled workflows require "
                    "a cancel decision"
                )

        if self.status is WorkflowStatus.FAILED:
            if error is None:
                raise ValueError(
                    "failed workflows must include an error"
                )
        elif error is not None:
            raise ValueError(
                "only failed workflows may include an error"
            )

        if (
            self.status is WorkflowStatus.RUNNING
            and self.decision
            is not WorkflowDecision.PROCEED
        ):
            raise ValueError(
                "running workflows require "
                "a proceed decision"
            )

        warnings = WorkflowModelSupport.normalize_warnings(
            self.warnings
        )

        object.__setattr__(
            self,
            "workflow_id",
            workflow_id,
        )
        object.__setattr__(
            self,
            "checkpoints",
            checkpoints,
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

    @property
    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATUSES

    @property
    def successful_checkpoint_count(self) -> int:
        return sum(
            1
            for checkpoint in self.checkpoints
            if checkpoint.successful
        )

    @property
    def failed_checkpoint(
        self,
    ) -> WorkflowCheckpoint | None:
        for checkpoint in self.checkpoints:
            if not checkpoint.successful:
                return checkpoint

        return None


@dataclass(frozen=True, slots=True)
class TradingWorkflowReport:
    """Immutable audit report for one orchestrated workflow."""

    report_id: str
    request: TradingWorkflowRequest
    result: TradingWorkflowResult
    reported_at: datetime
    message: str
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        report_id = WorkflowModelSupport.required_text(
            self.report_id,
            "report_id",
        )

        if not isinstance(
            self.request,
            TradingWorkflowRequest,
        ):
            raise TypeError(
                "request must be a TradingWorkflowRequest"
            )

        if not isinstance(
            self.result,
            TradingWorkflowResult,
        ):
            raise TypeError(
                "result must be a TradingWorkflowResult"
            )

        message = WorkflowModelSupport.required_text(
            self.message,
            "message",
        )

        WorkflowModelSupport.validate_datetime(
            self.reported_at,
            "reported_at",
        )

        if (
            self.request.workflow_id
            != self.result.workflow_id
        ):
            raise ValueError(
                "request and result workflow_id values "
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

        if self.reported_at < self.result.updated_at:
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

        metadata = WorkflowModelSupport.normalize_pairs(
            self.metadata,
            "metadata",
        )
        warnings = WorkflowModelSupport.normalize_warnings(
            self.warnings
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
        object.__setattr__(
            self,
            "warnings",
            warnings,
        )