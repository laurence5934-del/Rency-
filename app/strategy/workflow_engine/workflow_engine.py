from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Iterable, Mapping

from .workflow_models import (
    WorkflowDecision,
    WorkflowExecutionRecord,
    WorkflowFailurePolicy,
    WorkflowReport,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowStepDefinition,
    WorkflowStepResult,
    WorkflowStepStatus,
)


Clock = Callable[[], datetime]
StepHandler = Callable[
    [WorkflowRequest, tuple[WorkflowStepResult, ...]],
    object,
]


_TERMINAL_STATUSES = {
    WorkflowStatus.COMPLETED,
    WorkflowStatus.FAILED,
    WorkflowStatus.CANCELLED,
    WorkflowStatus.COMPENSATED,
}


@dataclass(slots=True)
class _WorkflowRegistration:
    workflow_type: str
    definitions: tuple[WorkflowStepDefinition, ...]
    handlers: dict[str, StepHandler]
    executable_step_ids: tuple[str, ...]


@dataclass(slots=True)
class _WorkflowRuntime:
    request: WorkflowRequest
    registration: _WorkflowRegistration
    status: WorkflowStatus
    decision: WorkflowDecision
    current_step_id: str | None
    started_at: datetime
    completed_at: datetime | None = None
    cancelled_reason: str | None = None
    results: list[WorkflowStepResult] = field(
        default_factory=list
    )
    warnings: list[str] = field(
        default_factory=list
    )


class EnterpriseWorkflowEngine:
    """Executes deterministic, resumable enterprise workflows."""

    def __init__(
        self,
        *,
        clock: Clock | None = None,
    ) -> None:
        if clock is not None and not callable(clock):
            raise TypeError(
                "clock must be callable"
            )

        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

        self._registrations: dict[
            str,
            _WorkflowRegistration,
        ] = {}

        self._runtimes: dict[
            str,
            _WorkflowRuntime,
        ] = {}

        self._report_history: list[
            WorkflowReport
        ] = []

        self._next_result_number = 1

    @property
    def registered_workflow_types(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(self._registrations)
        )

    @property
    def workflow_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(self._runtimes)
        )

    @property
    def history(
        self,
    ) -> tuple[WorkflowReport, ...]:
        return tuple(self._report_history)

    def register_workflow(
        self,
        *,
        workflow_type: str,
        definitions: Iterable[
            WorkflowStepDefinition
        ],
        handlers: Mapping[str, StepHandler],
    ) -> tuple[WorkflowStepDefinition, ...]:
        normalized_workflow_type = (
            self._normalize_identifier(
                workflow_type,
                "workflow_type",
            )
        )

        if normalized_workflow_type in self._registrations:
            raise ValueError(
                "workflow_type is already registered"
            )

        try:
            normalized_definitions = tuple(definitions)
        except TypeError as exc:
            raise TypeError(
                "definitions must be iterable"
            ) from exc

        self._validate_definitions(
            normalized_definitions
        )

        if not isinstance(handlers, Mapping):
            raise TypeError(
                "handlers must be a mapping"
            )

        normalized_handlers: dict[
            str,
            StepHandler,
        ] = {}

        known_step_ids = {
            definition.step_id
            for definition in normalized_definitions
        }

        for raw_step_id, handler in handlers.items():
            step_id = self._normalize_identifier(
                raw_step_id,
                "handler step_id",
            )

            if step_id not in known_step_ids:
                raise ValueError(
                    "handler step_id must reference "
                    "a known workflow step"
                )

            if not callable(handler):
                raise TypeError(
                    "every workflow handler must be callable"
                )

            normalized_handlers[step_id] = handler

        compensation_ids = {
            definition.compensation_step_id
            for definition in normalized_definitions
            if definition.compensation_step_id is not None
        }

        executable_step_ids = tuple(
            definition.step_id
            for definition in normalized_definitions
            if definition.step_id not in compensation_ids
        )

        if not executable_step_ids:
            raise ValueError(
                "workflow must include at least one "
                "executable step"
            )

        registration = _WorkflowRegistration(
            workflow_type=normalized_workflow_type,
            definitions=normalized_definitions,
            handlers=normalized_handlers,
            executable_step_ids=executable_step_ids,
        )

        self._registrations[
            normalized_workflow_type
        ] = registration

        return normalized_definitions

    def unregister_workflow(
        self,
        workflow_type: str,
    ) -> tuple[WorkflowStepDefinition, ...]:
        normalized_workflow_type = (
            self._normalize_identifier(
                workflow_type,
                "workflow_type",
            )
        )

        try:
            registration = self._registrations.pop(
                normalized_workflow_type
            )
        except KeyError as exc:
            raise KeyError(
                "workflow type not found: "
                f"{normalized_workflow_type}"
            ) from exc

        return registration.definitions

    def start(
        self,
        request: WorkflowRequest,
    ) -> WorkflowReport:
        if not isinstance(request, WorkflowRequest):
            raise TypeError(
                "request must be a WorkflowRequest"
            )

        if request.workflow_id in self._runtimes:
            raise ValueError(
                "workflow_id is already started"
            )

        try:
            registration = self._registrations[
                request.workflow_type
            ]
        except KeyError as exc:
            raise KeyError(
                "workflow type not registered: "
                f"{request.workflow_type}"
            ) from exc

        started_at = self._current_time()

        runtime = _WorkflowRuntime(
            request=request,
            registration=registration,
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.CONTINUE,
            current_step_id=(
                registration.executable_step_ids[0]
            ),
            started_at=started_at,
        )

        self._runtimes[
            request.workflow_id
        ] = runtime

        return self._record_report(
            runtime,
            recommendation=(
                "Advance the workflow to execute its "
                "current step."
            ),
        )

    def run(
        self,
        request: WorkflowRequest,
    ) -> WorkflowReport:
        report = self.start(request)

        while report.status is WorkflowStatus.RUNNING:
            report = self.advance(
                request.workflow_id
            )

        return report

    def advance(
        self,
        workflow_id: str,
    ) -> WorkflowReport:
        runtime = self._runtime(workflow_id)

        self._ensure_not_terminal(runtime)

        if runtime.status is WorkflowStatus.PAUSED:
            raise RuntimeError(
                "paused workflows must be resumed "
                "before advancing"
            )

        if runtime.status is not WorkflowStatus.RUNNING:
            raise RuntimeError(
                "only running workflows may advance"
            )

        if runtime.current_step_id is None:
            raise RuntimeError(
                "running workflow has no current step"
            )

        definition = self._definition(
            runtime,
            runtime.current_step_id,
        )

        handler = runtime.registration.handlers.get(
            definition.step_id
        )

        if handler is None:
            return self._handle_missing_handler(
                runtime=runtime,
                definition=definition,
            )

        return self._execute_definition(
            runtime=runtime,
            definition=definition,
            handler=handler,
        )

    def pause(
        self,
        workflow_id: str,
    ) -> WorkflowReport:
        runtime = self._runtime(workflow_id)

        self._ensure_not_terminal(runtime)

        if runtime.status is WorkflowStatus.PAUSED:
            raise RuntimeError(
                "workflow is already paused"
            )

        if runtime.status is not WorkflowStatus.RUNNING:
            raise RuntimeError(
                "only running workflows may be paused"
            )

        runtime.status = WorkflowStatus.PAUSED
        runtime.decision = WorkflowDecision.PAUSE

        return self._record_report(
            runtime,
            recommendation=(
                "Resume the workflow when execution "
                "may continue."
            ),
        )

    def resume(
        self,
        workflow_id: str,
    ) -> WorkflowReport:
        runtime = self._runtime(workflow_id)

        self._ensure_not_terminal(runtime)

        if runtime.status is not WorkflowStatus.PAUSED:
            raise RuntimeError(
                "only paused workflows may be resumed"
            )

        runtime.status = WorkflowStatus.RUNNING
        runtime.decision = WorkflowDecision.CONTINUE

        return self._record_report(
            runtime,
            recommendation=(
                "Advance the resumed workflow."
            ),
        )

    def cancel(
        self,
        workflow_id: str,
        *,
        reason: str,
    ) -> WorkflowReport:
        runtime = self._runtime(workflow_id)

        self._ensure_not_terminal(runtime)

        normalized_reason = self._normalize_identifier(
            reason,
            "reason",
        )

        cancelled_at = self._current_time()

        if runtime.current_step_id is not None:
            runtime.results.append(
                WorkflowStepResult(
                    result_id=self._next_result_id(),
                    workflow_id=runtime.request.workflow_id,
                    step_id=runtime.current_step_id,
                    status=WorkflowStepStatus.CANCELLED,
                    attempt_number=1,
                    started_at=cancelled_at,
                    completed_at=cancelled_at,
                    message=(
                        "Workflow step was cancelled."
                    ),
                )
            )

        runtime.status = WorkflowStatus.CANCELLED
        runtime.decision = WorkflowDecision.CANCEL
        runtime.current_step_id = None
        runtime.completed_at = cancelled_at
        runtime.cancelled_reason = normalized_reason

        return self._record_report(
            runtime,
            recommendation=(
                "Review the cancellation reason before "
                "starting another workflow."
            ),
        )

    def get_report(
        self,
        workflow_id: str,
    ) -> WorkflowReport:
        runtime = self._runtime(workflow_id)

        return self._build_report(
            runtime,
            recommendation=self._recommendation(
                runtime
            ),
        )

    def results_for_workflow(
        self,
        workflow_id: str,
    ) -> tuple[WorkflowStepResult, ...]:
        return tuple(
            self._runtime(workflow_id).results
        )

    def reports_for_workflow(
        self,
        workflow_id: str,
    ) -> tuple[WorkflowReport, ...]:
        normalized_workflow_id = (
            self._normalize_identifier(
                workflow_id,
                "workflow_id",
            )
        )

        return tuple(
            report
            for report in self._report_history
            if (
                report.request.workflow_id
                == normalized_workflow_id
            )
        )

    def _execute_definition(
        self,
        *,
        runtime: _WorkflowRuntime,
        definition: WorkflowStepDefinition,
        handler: StepHandler,
    ) -> WorkflowReport:
        max_attempts = (
            definition.max_attempts
            if definition.failure_policy
            is WorkflowFailurePolicy.RETRY
            else 1
        )

        final_error: str | None = None

        for attempt_number in range(
            1,
            max_attempts + 1,
        ):
            started_at = self._current_time()

            try:
                response = handler(
                    runtime.request,
                    tuple(runtime.results),
                )
            except Exception as exc:
                final_error = (
                    str(exc).strip()
                    or exc.__class__.__name__
                )

                completed_at = self._current_time()

                runtime.results.append(
                    WorkflowStepResult(
                        result_id=self._next_result_id(),
                        workflow_id=(
                            runtime.request.workflow_id
                        ),
                        step_id=definition.step_id,
                        status=WorkflowStepStatus.FAILED,
                        attempt_number=attempt_number,
                        started_at=started_at,
                        completed_at=completed_at,
                        message=(
                            "Workflow step execution failed."
                        ),
                        error=final_error,
                    )
                )

                if attempt_number < max_attempts:
                    runtime.decision = (
                        WorkflowDecision.RETRY
                    )
                    continue

                return self._handle_exhausted_failure(
                    runtime=runtime,
                    definition=definition,
                    error=final_error,
                )

            completed_at = self._current_time()

            runtime.results.append(
                WorkflowStepResult(
                    result_id=self._next_result_id(),
                    workflow_id=(
                        runtime.request.workflow_id
                    ),
                    step_id=definition.step_id,
                    status=WorkflowStepStatus.COMPLETED,
                    attempt_number=attempt_number,
                    started_at=started_at,
                    completed_at=completed_at,
                    message=(
                        "Workflow step completed "
                        "successfully."
                    ),
                    output=self._normalize_output(
                        response
                    ),
                )
            )

            return self._move_to_next_step(runtime)

        raise RuntimeError(
            "workflow attempt loop completed unexpectedly"
        )

    def _handle_missing_handler(
        self,
        *,
        runtime: _WorkflowRuntime,
        definition: WorkflowStepDefinition,
    ) -> WorkflowReport:
        occurred_at = self._current_time()

        if not definition.required:
            runtime.results.append(
                WorkflowStepResult(
                    result_id=self._next_result_id(),
                    workflow_id=(
                        runtime.request.workflow_id
                    ),
                    step_id=definition.step_id,
                    status=WorkflowStepStatus.SKIPPED,
                    attempt_number=1,
                    started_at=occurred_at,
                    completed_at=occurred_at,
                    message=(
                        "Optional workflow step was skipped "
                        "because no handler was registered."
                    ),
                )
            )

            runtime.warnings.append(
                f"Optional step {definition.step_id} "
                "was skipped."
            )

            return self._move_to_next_step(runtime)

        error = (
            f"Required workflow step "
            f"{definition.step_id} has no handler."
        )

        runtime.results.append(
            WorkflowStepResult(
                result_id=self._next_result_id(),
                workflow_id=runtime.request.workflow_id,
                step_id=definition.step_id,
                status=WorkflowStepStatus.FAILED,
                attempt_number=1,
                started_at=occurred_at,
                completed_at=occurred_at,
                message=(
                    "Required workflow step could not "
                    "be executed."
                ),
                error=error,
            )
        )

        return self._fail_runtime(
            runtime,
            error=error,
        )

    def _handle_exhausted_failure(
        self,
        *,
        runtime: _WorkflowRuntime,
        definition: WorkflowStepDefinition,
        error: str,
    ) -> WorkflowReport:
        policy = definition.failure_policy

        if policy is WorkflowFailurePolicy.CONTINUE:
            runtime.warnings.append(
                f"Step {definition.step_id} failed "
                "but workflow execution continued."
            )

            return self._move_to_next_step(runtime)

        if policy is WorkflowFailurePolicy.COMPENSATE:
            return self._execute_compensation(
                runtime=runtime,
                failed_definition=definition,
                original_error=error,
            )

        return self._fail_runtime(
            runtime,
            error=error,
        )

    def _execute_compensation(
        self,
        *,
        runtime: _WorkflowRuntime,
        failed_definition: WorkflowStepDefinition,
        original_error: str,
    ) -> WorkflowReport:
        compensation_step_id = (
            failed_definition.compensation_step_id
        )

        if compensation_step_id is None:
            return self._fail_runtime(
                runtime,
                error=(
                    "Compensation step is missing for "
                    f"{failed_definition.step_id}."
                ),
            )

        compensation_definition = self._definition(
            runtime,
            compensation_step_id,
        )

        compensation_handler = (
            runtime.registration.handlers.get(
                compensation_step_id
            )
        )

        if compensation_handler is None:
            return self._fail_runtime(
                runtime,
                error=(
                    "Compensation handler is missing for "
                    f"{compensation_step_id}."
                ),
            )

        started_at = self._current_time()

        try:
            response = compensation_handler(
                runtime.request,
                tuple(runtime.results),
            )
        except Exception as exc:
            compensation_error = (
                str(exc).strip()
                or exc.__class__.__name__
            )
            completed_at = self._current_time()

            runtime.results.append(
                WorkflowStepResult(
                    result_id=self._next_result_id(),
                    workflow_id=(
                        runtime.request.workflow_id
                    ),
                    step_id=compensation_step_id,
                    status=WorkflowStepStatus.FAILED,
                    attempt_number=1,
                    started_at=started_at,
                    completed_at=completed_at,
                    message=(
                        "Workflow compensation failed."
                    ),
                    error=compensation_error,
                )
            )

            return self._fail_runtime(
                runtime,
                error=(
                    f"{original_error}; compensation failed: "
                    f"{compensation_error}"
                ),
            )

        completed_at = self._current_time()

        runtime.results.append(
            WorkflowStepResult(
                result_id=self._next_result_id(),
                workflow_id=runtime.request.workflow_id,
                step_id=compensation_step_id,
                status=WorkflowStepStatus.COMPENSATED,
                attempt_number=1,
                started_at=started_at,
                completed_at=completed_at,
                message=(
                    "Workflow compensation completed."
                ),
                output=self._normalize_output(response),
                compensated_step_id=(
                    failed_definition.step_id
                ),
            )
        )

        runtime.status = WorkflowStatus.COMPENSATED
        runtime.decision = WorkflowDecision.COMPENSATE
        runtime.current_step_id = None
        runtime.completed_at = completed_at
        runtime.warnings.append(
            f"Step {failed_definition.step_id} failed "
            f"and was compensated by "
            f"{compensation_step_id}."
        )

        return self._record_report(
            runtime,
            recommendation=(
                "Review the compensated workflow before "
                "starting a replacement execution."
            ),
        )

    def _move_to_next_step(
        self,
        runtime: _WorkflowRuntime,
    ) -> WorkflowReport:
        current_step_id = runtime.current_step_id

        if current_step_id is None:
            raise RuntimeError(
                "workflow has no current step"
            )

        executable_ids = (
            runtime.registration.executable_step_ids
        )

        current_index = executable_ids.index(
            current_step_id
        )

        next_index = current_index + 1

        if next_index >= len(executable_ids):
            completed_at = self._current_time()

            runtime.status = WorkflowStatus.COMPLETED
            runtime.decision = WorkflowDecision.COMPLETE
            runtime.current_step_id = None
            runtime.completed_at = completed_at

            return self._record_report(
                runtime,
                recommendation=(
                    "Workflow completed successfully."
                ),
            )

        runtime.status = WorkflowStatus.RUNNING
        runtime.decision = WorkflowDecision.CONTINUE
        runtime.current_step_id = executable_ids[
            next_index
        ]

        return self._record_report(
            runtime,
            recommendation=(
                "Advance the workflow to execute its "
                "next step."
            ),
        )

    def _fail_runtime(
        self,
        runtime: _WorkflowRuntime,
        *,
        error: str,
    ) -> WorkflowReport:
        completed_at = self._current_time()

        runtime.status = WorkflowStatus.FAILED
        runtime.decision = WorkflowDecision.FAIL
        runtime.current_step_id = None
        runtime.completed_at = completed_at

        return self._record_report(
            runtime,
            recommendation=(
                "Correct the workflow failure before "
                "starting another execution."
            ),
            error=error,
        )

    def _record_report(
        self,
        runtime: _WorkflowRuntime,
        *,
        recommendation: str,
        error: str | None = None,
    ) -> WorkflowReport:
        report = self._build_report(
            runtime,
            recommendation=recommendation,
            error=error,
        )

        self._report_history.append(report)

        return report

    def _build_report(
        self,
        runtime: _WorkflowRuntime,
        *,
        recommendation: str,
        error: str | None = None,
    ) -> WorkflowReport:
        record = WorkflowExecutionRecord(
            workflow_id=runtime.request.workflow_id,
            status=runtime.status,
            decision=runtime.decision,
            definitions=(
                runtime.registration.definitions
            ),
            results=tuple(runtime.results),
            current_step_id=runtime.current_step_id,
            started_at=runtime.started_at,
            completed_at=runtime.completed_at,
            cancelled_reason=runtime.cancelled_reason,
            warnings=tuple(runtime.warnings),
        )

        effective_error = error

        if (
            runtime.status is WorkflowStatus.FAILED
            and effective_error is None
        ):
            effective_error = self._latest_error(runtime)

        return WorkflowReport(
            status=runtime.status,
            decision=runtime.decision,
            request=runtime.request,
            record=record,
            recommendation=recommendation,
            warnings=tuple(runtime.warnings),
            error=effective_error,
        )

    @staticmethod
    def _latest_error(
        runtime: _WorkflowRuntime,
    ) -> str:
        for result in reversed(runtime.results):
            if result.error is not None:
                return result.error

        return "Workflow execution failed."

    @staticmethod
    def _recommendation(
        runtime: _WorkflowRuntime,
    ) -> str:
        recommendations = {
            WorkflowStatus.RUNNING: (
                "Advance the workflow."
            ),
            WorkflowStatus.PAUSED: (
                "Resume the workflow when ready."
            ),
            WorkflowStatus.COMPLETED: (
                "Workflow completed successfully."
            ),
            WorkflowStatus.FAILED: (
                "Review and correct the workflow failure."
            ),
            WorkflowStatus.CANCELLED: (
                "Review the workflow cancellation."
            ),
            WorkflowStatus.COMPENSATED: (
                "Review the compensated workflow."
            ),
            WorkflowStatus.PENDING: (
                "Start the workflow."
            ),
        }

        return recommendations[runtime.status]

    @staticmethod
    def _normalize_output(
        value: object,
    ) -> tuple[tuple[str, str], ...]:
        if value is None:
            return ()

        if isinstance(value, Mapping):
            normalized: list[
                tuple[str, str]
            ] = []
            seen_keys: set[str] = set()

            for raw_key, raw_value in value.items():
                key = str(raw_key).strip()
                output_value = str(raw_value).strip()

                if not key:
                    raise ValueError(
                        "workflow output keys must not "
                        "be empty"
                    )

                if key in seen_keys:
                    raise ValueError(
                        "workflow output keys must be unique"
                    )

                seen_keys.add(key)
                normalized.append(
                    (key, output_value)
                )

            return tuple(
                sorted(normalized)
            )

        return (
            (
                "result",
                str(value).strip(),
            ),
        )

    @staticmethod
    def _validate_definitions(
        definitions: tuple[
            WorkflowStepDefinition,
            ...
        ],
    ) -> None:
        if not definitions:
            raise ValueError(
                "definitions must not be empty"
            )

        for definition in definitions:
            if not isinstance(
                definition,
                WorkflowStepDefinition,
            ):
                raise TypeError(
                    "every definition must be a "
                    "WorkflowStepDefinition"
                )

        step_ids = [
            definition.step_id
            for definition in definitions
        ]

        if len(set(step_ids)) != len(step_ids):
            raise ValueError(
                "step_id values must be unique"
            )

        positions = [
            definition.position
            for definition in definitions
        ]

        if len(set(positions)) != len(positions):
            raise ValueError(
                "step positions must be unique"
            )

        if positions != sorted(positions):
            raise ValueError(
                "step definitions must be ordered "
                "by position"
            )

        known_step_ids = set(step_ids)

        for definition in definitions:
            compensation_step_id = (
                definition.compensation_step_id
            )

            if (
                compensation_step_id is not None
                and compensation_step_id
                not in known_step_ids
            ):
                raise ValueError(
                    "compensation_step_id must reference "
                    "a known workflow step"
                )

    @staticmethod
    def _definition(
        runtime: _WorkflowRuntime,
        step_id: str,
    ) -> WorkflowStepDefinition:
        return next(
            definition
            for definition
            in runtime.registration.definitions
            if definition.step_id == step_id
        )

    def _runtime(
        self,
        workflow_id: str,
    ) -> _WorkflowRuntime:
        normalized_workflow_id = (
            self._normalize_identifier(
                workflow_id,
                "workflow_id",
            )
        )

        try:
            return self._runtimes[
                normalized_workflow_id
            ]
        except KeyError as exc:
            raise KeyError(
                "workflow not found: "
                f"{normalized_workflow_id}"
            ) from exc

    @staticmethod
    def _ensure_not_terminal(
        runtime: _WorkflowRuntime,
    ) -> None:
        if runtime.status in _TERMINAL_STATUSES:
            raise RuntimeError(
                "workflow is already terminal"
            )

    def _next_result_id(self) -> str:
        result_id = (
            f"workflow-result-"
            f"{self._next_result_number:06d}"
        )
        self._next_result_number += 1
        return result_id

    def _current_time(self) -> datetime:
        value = self._clock()

        if not isinstance(value, datetime):
            raise TypeError(
                "clock must return a datetime"
            )

        if value.tzinfo is None:
            raise ValueError(
                "clock must return a timezone-aware datetime"
            )

        return value

    @staticmethod
    def _normalize_identifier(
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