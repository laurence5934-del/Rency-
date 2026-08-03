from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class WorkflowStatus(str, Enum):
    """Overall lifecycle status of a workflow."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    COMPENSATED = "COMPENSATED"


class WorkflowDecision(str, Enum):
    """Final routing decision produced by a workflow."""

    CONTINUE = "CONTINUE"
    COMPLETE = "COMPLETE"
    RETRY = "RETRY"
    PAUSE = "PAUSE"
    CANCEL = "CANCEL"
    FAIL = "FAIL"
    COMPENSATE = "COMPENSATE"


class WorkflowStepStatus(str, Enum):
    """Execution status of one workflow step."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"
    COMPENSATED = "COMPENSATED"


class WorkflowFailurePolicy(str, Enum):
    """Policy applied after a workflow step failure."""

    FAIL_FAST = "FAIL_FAST"
    CONTINUE = "CONTINUE"
    RETRY = "RETRY"
    COMPENSATE = "COMPENSATE"


_TERMINAL_WORKFLOW_STATUSES = {
    WorkflowStatus.COMPLETED,
    WorkflowStatus.FAILED,
    WorkflowStatus.CANCELLED,
    WorkflowStatus.COMPENSATED,
}

_TERMINAL_STEP_STATUSES = {
    WorkflowStepStatus.COMPLETED,
    WorkflowStepStatus.FAILED,
    WorkflowStepStatus.SKIPPED,
    WorkflowStepStatus.CANCELLED,
    WorkflowStepStatus.COMPENSATED,
}


@dataclass(frozen=True, slots=True)
class WorkflowRequest:
    """Immutable request to execute an enterprise workflow."""

    workflow_id: str
    correlation_id: str
    workflow_type: str
    requested_by: str
    requested_at: datetime
    priority: int = 0
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_workflow_id = self._required_text(
            self.workflow_id,
            "workflow_id",
        )
        normalized_correlation_id = self._required_text(
            self.correlation_id,
            "correlation_id",
        )
        normalized_workflow_type = self._required_text(
            self.workflow_type,
            "workflow_type",
        )
        normalized_requested_by = self._required_text(
            self.requested_by,
            "requested_by",
        )

        self._validate_datetime(
            self.requested_at,
            "requested_at",
        )

        if not isinstance(self.priority, int):
            raise TypeError(
                "priority must be an integer"
            )

        if self.priority < 0:
            raise ValueError(
                "priority must not be negative"
            )

        normalized_metadata = self._normalize_pairs(
            self.metadata,
            "metadata",
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
            "workflow_type",
            normalized_workflow_type,
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

    @staticmethod
    def _required_text(
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
    def _optional_text(
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

    @staticmethod
    def _normalize_pairs(
        values: tuple[tuple[str, str], ...],
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


@dataclass(frozen=True, slots=True)
class WorkflowStepDefinition:
    """Immutable definition of one workflow step."""

    step_id: str
    name: str
    position: int
    component: str
    failure_policy: WorkflowFailurePolicy
    max_attempts: int = 1
    required: bool = True
    compensation_step_id: str | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_step_id = WorkflowRequest._required_text(
            self.step_id,
            "step_id",
        )
        normalized_name = WorkflowRequest._required_text(
            self.name,
            "name",
        )
        normalized_component = WorkflowRequest._required_text(
            self.component,
            "component",
        )

        if not isinstance(self.position, int):
            raise TypeError(
                "position must be an integer"
            )

        if self.position < 1:
            raise ValueError(
                "position must be greater than zero"
            )

        if not isinstance(
            self.failure_policy,
            WorkflowFailurePolicy,
        ):
            raise TypeError(
                "failure_policy must be a "
                "WorkflowFailurePolicy"
            )

        if not isinstance(self.max_attempts, int):
            raise TypeError(
                "max_attempts must be an integer"
            )

        if self.max_attempts < 1:
            raise ValueError(
                "max_attempts must be greater than zero"
            )

        if not isinstance(self.required, bool):
            raise TypeError(
                "required must be a bool"
            )

        normalized_compensation_step_id = (
            WorkflowRequest._optional_text(
                self.compensation_step_id,
                "compensation_step_id",
            )
        )

        if (
            normalized_compensation_step_id
            == normalized_step_id
        ):
            raise ValueError(
                "compensation_step_id must differ from step_id"
            )

        if (
            self.failure_policy
            is WorkflowFailurePolicy.RETRY
            and self.max_attempts < 2
        ):
            raise ValueError(
                "retry steps must allow at least two attempts"
            )

        if (
            self.failure_policy
            is WorkflowFailurePolicy.COMPENSATE
            and normalized_compensation_step_id is None
        ):
            raise ValueError(
                "compensating steps must include "
                "compensation_step_id"
            )

        normalized_metadata = WorkflowRequest._normalize_pairs(
            self.metadata,
            "metadata",
        )

        object.__setattr__(
            self,
            "step_id",
            normalized_step_id,
        )
        object.__setattr__(
            self,
            "name",
            normalized_name,
        )
        object.__setattr__(
            self,
            "component",
            normalized_component,
        )
        object.__setattr__(
            self,
            "compensation_step_id",
            normalized_compensation_step_id,
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )


@dataclass(frozen=True, slots=True)
class WorkflowStepResult:
    """Immutable result of one workflow-step attempt."""

    result_id: str
    workflow_id: str
    step_id: str
    status: WorkflowStepStatus
    attempt_number: int
    started_at: datetime
    completed_at: datetime | None
    message: str
    output: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )
    error: str | None = None
    compensated_step_id: str | None = None

    def __post_init__(self) -> None:
        normalized_result_id = WorkflowRequest._required_text(
            self.result_id,
            "result_id",
        )
        normalized_workflow_id = WorkflowRequest._required_text(
            self.workflow_id,
            "workflow_id",
        )
        normalized_step_id = WorkflowRequest._required_text(
            self.step_id,
            "step_id",
        )
        normalized_message = WorkflowRequest._required_text(
            self.message,
            "message",
        )

        if not isinstance(
            self.status,
            WorkflowStepStatus,
        ):
            raise TypeError(
                "status must be a WorkflowStepStatus"
            )

        if not isinstance(self.attempt_number, int):
            raise TypeError(
                "attempt_number must be an integer"
            )

        if self.attempt_number < 1:
            raise ValueError(
                "attempt_number must be greater than zero"
            )

        WorkflowRequest._validate_datetime(
            self.started_at,
            "started_at",
        )

        if self.completed_at is not None:
            WorkflowRequest._validate_datetime(
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
            in {
                WorkflowStepStatus.PENDING,
                WorkflowStepStatus.RUNNING,
            }
            and self.completed_at is not None
        ):
            raise ValueError(
                "non-terminal step results must not include "
                "completed_at"
            )

        if (
            self.status in _TERMINAL_STEP_STATUSES
            and self.completed_at is None
        ):
            raise ValueError(
                "terminal step results must include completed_at"
            )

        normalized_error = WorkflowRequest._optional_text(
            self.error,
            "error",
        )

        if self.status is WorkflowStepStatus.FAILED:
            if normalized_error is None:
                raise ValueError(
                    "failed step results must include an error"
                )
        elif normalized_error is not None:
            raise ValueError(
                "only failed step results may include an error"
            )

        normalized_compensated_step_id = (
            WorkflowRequest._optional_text(
                self.compensated_step_id,
                "compensated_step_id",
            )
        )

        if (
            self.status
            is WorkflowStepStatus.COMPENSATED
            and normalized_compensated_step_id is None
        ):
            raise ValueError(
                "compensated results must include "
                "compensated_step_id"
            )

        if (
            self.status
            is not WorkflowStepStatus.COMPENSATED
            and normalized_compensated_step_id is not None
        ):
            raise ValueError(
                "only compensated results may include "
                "compensated_step_id"
            )

        normalized_output = WorkflowRequest._normalize_pairs(
            self.output,
            "output",
        )

        object.__setattr__(
            self,
            "result_id",
            normalized_result_id,
        )
        object.__setattr__(
            self,
            "workflow_id",
            normalized_workflow_id,
        )
        object.__setattr__(
            self,
            "step_id",
            normalized_step_id,
        )
        object.__setattr__(
            self,
            "message",
            normalized_message,
        )
        object.__setattr__(
            self,
            "error",
            normalized_error,
        )
        object.__setattr__(
            self,
            "compensated_step_id",
            normalized_compensated_step_id,
        )
        object.__setattr__(
            self,
            "output",
            normalized_output,
        )


@dataclass(frozen=True, slots=True)
class WorkflowExecutionRecord:
    """Immutable complete state of one workflow execution."""

    workflow_id: str
    status: WorkflowStatus
    decision: WorkflowDecision
    definitions: tuple[WorkflowStepDefinition, ...]
    results: tuple[WorkflowStepResult, ...]
    current_step_id: str | None
    started_at: datetime
    completed_at: datetime | None = None
    cancelled_reason: str | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_workflow_id = WorkflowRequest._required_text(
            self.workflow_id,
            "workflow_id",
        )

        if not isinstance(self.status, WorkflowStatus):
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

        WorkflowRequest._validate_datetime(
            self.started_at,
            "started_at",
        )

        if self.completed_at is not None:
            WorkflowRequest._validate_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.started_at:
                raise ValueError(
                    "completed_at must not be earlier "
                    "than started_at"
                )

        if (
            self.status in _TERMINAL_WORKFLOW_STATUSES
            and self.completed_at is None
        ):
            raise ValueError(
                "terminal workflows must include completed_at"
            )

        if (
            self.status not in _TERMINAL_WORKFLOW_STATUSES
            and self.completed_at is not None
        ):
            raise ValueError(
                "only terminal workflows may include completed_at"
            )

        normalized_definitions = tuple(self.definitions)
        normalized_results = tuple(self.results)

        if not normalized_definitions:
            raise ValueError(
                "definitions must not be empty"
            )

        for definition in normalized_definitions:
            if not isinstance(
                definition,
                WorkflowStepDefinition,
            ):
                raise TypeError(
                    "every definition must be a "
                    "WorkflowStepDefinition"
                )

        for result in normalized_results:
            if not isinstance(
                result,
                WorkflowStepResult,
            ):
                raise TypeError(
                    "every result must be a WorkflowStepResult"
                )

            if result.workflow_id != normalized_workflow_id:
                raise ValueError(
                    "result workflow_id must match the record"
                )

        definition_ids = [
            definition.step_id
            for definition in normalized_definitions
        ]

        if len(set(definition_ids)) != len(definition_ids):
            raise ValueError(
                "step_id values must be unique"
            )

        positions = [
            definition.position
            for definition in normalized_definitions
        ]

        if len(set(positions)) != len(positions):
            raise ValueError(
                "step positions must be unique"
            )

        if positions != sorted(positions):
            raise ValueError(
                "step definitions must be ordered by position"
            )

        known_step_ids = set(definition_ids)

        for definition in normalized_definitions:
            if (
                definition.compensation_step_id is not None
                and definition.compensation_step_id
                not in known_step_ids
            ):
                raise ValueError(
                    "compensation_step_id must reference "
                    "a known step"
                )

        for result in normalized_results:
            if result.step_id not in known_step_ids:
                raise ValueError(
                    "every result must reference a known step"
                )

        normalized_current_step_id = (
            WorkflowRequest._optional_text(
                self.current_step_id,
                "current_step_id",
            )
        )

        if (
            normalized_current_step_id is not None
            and normalized_current_step_id
            not in known_step_ids
        ):
            raise ValueError(
                "current_step_id must reference a known step"
            )

        if (
            self.status in _TERMINAL_WORKFLOW_STATUSES
            and normalized_current_step_id is not None
        ):
            raise ValueError(
                "terminal workflows must not include "
                "current_step_id"
            )

        normalized_cancelled_reason = (
            WorkflowRequest._optional_text(
                self.cancelled_reason,
                "cancelled_reason",
            )
        )

        if self.status is WorkflowStatus.CANCELLED:
            if normalized_cancelled_reason is None:
                raise ValueError(
                    "cancelled workflows must include "
                    "cancelled_reason"
                )
        elif normalized_cancelled_reason is not None:
            raise ValueError(
                "only cancelled workflows may include "
                "cancelled_reason"
            )

        object.__setattr__(
            self,
            "workflow_id",
            normalized_workflow_id,
        )
        object.__setattr__(
            self,
            "definitions",
            normalized_definitions,
        )
        object.__setattr__(
            self,
            "results",
            normalized_results,
        )
        object.__setattr__(
            self,
            "current_step_id",
            normalized_current_step_id,
        )
        object.__setattr__(
            self,
            "cancelled_reason",
            normalized_cancelled_reason,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )


@dataclass(frozen=True, slots=True)
class WorkflowReport:
    """Unified workflow-engine result."""

    status: WorkflowStatus
    decision: WorkflowDecision
    request: WorkflowRequest
    record: WorkflowExecutionRecord | None
    recommendation: str
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, WorkflowStatus):
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

        if not isinstance(self.request, WorkflowRequest):
            raise TypeError(
                "request must be a WorkflowRequest"
            )

        if (
            self.record is not None
            and not isinstance(
                self.record,
                WorkflowExecutionRecord,
            )
        ):
            raise TypeError(
                "record must be a WorkflowExecutionRecord "
                "or None"
            )

        normalized_recommendation = (
            WorkflowRequest._required_text(
                self.recommendation,
                "recommendation",
            )
        )

        if self.record is not None:
            if (
                self.record.workflow_id
                != self.request.workflow_id
            ):
                raise ValueError(
                    "record workflow_id must match the request"
                )

            if self.record.status is not self.status:
                raise ValueError(
                    "report status must match the record"
                )

            if self.record.decision is not self.decision:
                raise ValueError(
                    "report decision must match the record"
                )

        normalized_error = WorkflowRequest._optional_text(
            self.error,
            "error",
        )

        if self.status is WorkflowStatus.FAILED:
            if normalized_error is None:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error is not None:
            raise ValueError(
                "only failed reports may include an error"
            )

        if (
            self.status is not WorkflowStatus.FAILED
            and self.record is None
        ):
            raise ValueError(
                "non-failed reports must include a record"
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