from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .execution_models import (
    ExecutionDecision,
    ExecutionReport,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStage,
    ExecutionStatus,
    ExecutionStep,
)


Clock = Callable[[], datetime]


_TERMINAL_STATUSES = {
    ExecutionStatus.COMPLETED,
    ExecutionStatus.HELD,
    ExecutionStatus.REJECTED,
    ExecutionStatus.FAILED,
    ExecutionStatus.CANCELLED,
}


class EnterpriseExecutionCoordinator:
    """
    Coordinates the enterprise trade-execution lifecycle.

    Responsibilities:
    - register immutable execution requests
    - prevent duplicate identifiers
    - start coordinated executions
    - maintain current results and histories
    - provide deterministic step and report identifiers
    - enforce lifecycle transitions
    """

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

        self._requests: dict[
            str,
            ExecutionRequest,
        ] = {}

        self._execution_by_correlation_id: dict[
            str,
            str,
        ] = {}

        self._current_results: dict[
            str,
            ExecutionResult,
        ] = {}

        self._result_history: dict[
            str,
            list[ExecutionResult],
        ] = {}

        self._reports: dict[
            str,
            ExecutionReport,
        ] = {}

        self._report_history: list[
            ExecutionReport
        ] = []

        self._next_step_number = 1
        self._next_report_number = 1

    @property
    def execution_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(self._requests)
        )

    @property
    def report_history(
        self,
    ) -> tuple[ExecutionReport, ...]:
        return tuple(self._report_history)

    def register_request(
        self,
        request: ExecutionRequest,
    ) -> ExecutionRequest:
        if not isinstance(
            request,
            ExecutionRequest,
        ):
            raise TypeError(
                "request must be an ExecutionRequest"
            )

        if request.execution_id in self._requests:
            raise ValueError(
                "execution_id is already registered"
            )

        if (
            request.correlation_id
            in self._execution_by_correlation_id
        ):
            raise ValueError(
                "correlation_id is already registered"
            )

        self._requests[
            request.execution_id
        ] = request

        self._execution_by_correlation_id[
            request.correlation_id
        ] = request.execution_id

        return request

    def unregister_request(
        self,
        execution_id: str,
    ) -> ExecutionRequest:
        request = self.get_request(
            execution_id
        )

        if execution_id in self._current_results:
            raise RuntimeError(
                "started executions cannot be unregistered"
            )

        self._requests.pop(
            request.execution_id
        )

        self._execution_by_correlation_id.pop(
            request.correlation_id,
            None,
        )

        return request

    def get_request(
        self,
        execution_id: str,
    ) -> ExecutionRequest:
        normalized_execution_id = (
            self._normalize_identifier(
                execution_id,
                "execution_id",
            )
        )

        try:
            return self._requests[
                normalized_execution_id
            ]
        except KeyError as exc:
            raise KeyError(
                "execution request not found: "
                f"{normalized_execution_id}"
            ) from exc

    def request_for_correlation(
        self,
        correlation_id: str,
    ) -> ExecutionRequest:
        normalized_correlation_id = (
            self._normalize_identifier(
                correlation_id,
                "correlation_id",
            )
        )

        try:
            execution_id = (
                self._execution_by_correlation_id[
                    normalized_correlation_id
                ]
            )
        except KeyError as exc:
            raise KeyError(
                "execution request not found for "
                f"correlation_id: "
                f"{normalized_correlation_id}"
            ) from exc

        return self._requests[
            execution_id
        ]

    def start_execution(
        self,
        execution_id: str,
    ) -> ExecutionReport:
        request = self.get_request(
            execution_id
        )

        existing = self._current_results.get(
            request.execution_id
        )

        if existing is not None:
            return self.get_report(
                request.execution_id
            )

        now = self._current_time()

        if now < request.created_at:
            raise ValueError(
                "execution start time must not be earlier "
                "than request created_at"
            )

        result = ExecutionResult(
            execution_id=request.execution_id,
            status=ExecutionStatus.EXECUTING,
            decision=ExecutionDecision.PROCEED,
            started_at=now,
            updated_at=now,
            steps=(),
        )

        return self._store_result_and_report(
            request=request,
            result=result,
            message=(
                "Enterprise execution coordination started."
            ),
        )

    def get_result(
        self,
        execution_id: str,
    ) -> ExecutionResult:
        request = self.get_request(
            execution_id
        )

        try:
            return self._current_results[
                request.execution_id
            ]
        except KeyError as exc:
            raise KeyError(
                "execution has no result state: "
                f"{request.execution_id}"
            ) from exc

    def get_report(
        self,
        execution_id: str,
    ) -> ExecutionReport:
        request = self.get_request(
            execution_id
        )

        try:
            return self._reports[
                request.execution_id
            ]
        except KeyError as exc:
            raise KeyError(
                "execution has no report: "
                f"{request.execution_id}"
            ) from exc

    def results_for_execution(
        self,
        execution_id: str,
    ) -> tuple[ExecutionResult, ...]:
        request = self.get_request(
            execution_id
        )

        return tuple(
            self._result_history.get(
                request.execution_id,
                (),
            )
        )

    def reports_for_order(
        self,
        order_id: str,
    ) -> tuple[ExecutionReport, ...]:
        normalized_order_id = (
            self._normalize_identifier(
                order_id,
                "order_id",
            )
        )

        return tuple(
            report
            for report in self._report_history
            if (
                report.request.order_request.order_id
                == normalized_order_id
            )
        )

    def reports_for_portfolio(
        self,
        portfolio_id: str,
    ) -> tuple[ExecutionReport, ...]:
        normalized_portfolio_id = (
            self._normalize_identifier(
                portfolio_id,
                "portfolio_id",
            )
        )

        return tuple(
            report
            for report in self._report_history
            if (
                report.request.portfolio_id
                == normalized_portfolio_id
            )
        )

    def latest_report(
        self,
    ) -> ExecutionReport:
        if not self._report_history:
            raise KeyError(
                "execution coordinator has no reports"
            )

        return self._report_history[-1]

    def record_step(
        self,
        execution_id: str,
        *,
        stage: ExecutionStage,
        decision: ExecutionDecision,
        successful: bool,
        message: str,
        reference_id: str | None = None,
        warnings: tuple[str, ...] | list[str] = (),
        error: str | None = None,
        metadata: (
            tuple[tuple[str, str], ...]
            | list[tuple[str, str]]
        ) = (),
    ) -> ExecutionReport:
        request, current = self._require_active_result(
            execution_id
        )

        if not isinstance(stage, ExecutionStage):
            raise TypeError(
                "stage must be an ExecutionStage"
            )

        if not isinstance(
            decision,
            ExecutionDecision,
        ):
            raise TypeError(
                "decision must be an ExecutionDecision"
            )

        if not isinstance(successful, bool):
            raise TypeError(
                "successful must be a bool"
            )

        existing_stages = {
            step.stage
            for step in current.steps
        }

        if stage in existing_stages:
            raise ValueError(
                "execution stage is already recorded"
            )

        if current.steps:
            previous_stage = current.steps[-1].stage

            if (
                self._stage_position(stage)
                <= self._stage_position(previous_stage)
            ):
                raise ValueError(
                    "execution stages must be recorded "
                    "in pipeline order"
                )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "step time must not be earlier than "
                "the current execution update"
            )

        step = ExecutionStep(
            step_id=self._next_step_id(),
            execution_id=request.execution_id,
            stage=stage,
            decision=decision,
            started_at=now,
            completed_at=now,
            successful=successful,
            message=message,
            reference_id=reference_id,
            warnings=warnings,
            error=error,
            metadata=metadata,
        )

        updated = ExecutionResult(
            execution_id=request.execution_id,
            status=ExecutionStatus.EXECUTING,
            decision=ExecutionDecision.PROCEED,
            started_at=current.started_at,
            updated_at=now,
            steps=current.steps + (step,),
            warnings=self._combine_warnings(
                current.warnings,
                step.warnings,
            ),
        )

        return self._store_result_and_report(
            request=request,
            result=updated,
            message=(
                f"Execution stage {stage.value} recorded."
            ),
        )

    def complete_execution(
        self,
        execution_id: str,
        *,
        final_order_id: str,
        broker_order_id: str,
    ) -> ExecutionReport:
        request, current = self._require_active_result(
            execution_id
        )

        normalized_final_order_id = (
            self._normalize_identifier(
                final_order_id,
                "final_order_id",
            )
        )
        normalized_broker_order_id = (
            self._normalize_identifier(
                broker_order_id,
                "broker_order_id",
            )
        )

        if (
            normalized_final_order_id
            != request.order_request.order_id
        ):
            raise ValueError(
                "final_order_id must match "
                "the execution order_id"
            )

        if not current.steps:
            raise RuntimeError(
                "execution cannot complete without steps"
            )

        if not all(
            step.successful
            for step in current.steps
        ):
            raise RuntimeError(
                "execution cannot complete with "
                "unsuccessful steps"
            )

        if (
            current.steps[-1].stage
            is not ExecutionStage.BROKER
            and current.steps[-1].stage
            is not ExecutionStage.EXECUTION
        ):
            raise RuntimeError(
                "execution must reach the broker or "
                "execution stage before completion"
            )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "completion time must not be earlier "
                "than the current execution update"
            )

        result = ExecutionResult(
            execution_id=request.execution_id,
            status=ExecutionStatus.COMPLETED,
            decision=ExecutionDecision.PROCEED,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            steps=current.steps,
            final_order_id=(
                normalized_final_order_id
            ),
            broker_order_id=(
                normalized_broker_order_id
            ),
            warnings=current.warnings,
        )

        return self._store_result_and_report(
            request=request,
            result=result,
            message=(
                "Enterprise execution completed "
                "successfully."
            ),
        )

    def hold_execution(
        self,
        execution_id: str,
        *,
        stage: ExecutionStage,
        reason: str,
        reference_id: str | None = None,
    ) -> ExecutionReport:
        return self._terminate_execution(
            execution_id=execution_id,
            stage=stage,
            status=ExecutionStatus.HELD,
            decision=ExecutionDecision.HOLD,
            reason=reason,
            reference_id=reference_id,
            report_message=(
                "Enterprise execution was placed on hold."
            ),
        )

    def reject_execution(
        self,
        execution_id: str,
        *,
        stage: ExecutionStage,
        reason: str,
        reference_id: str | None = None,
    ) -> ExecutionReport:
        return self._terminate_execution(
            execution_id=execution_id,
            stage=stage,
            status=ExecutionStatus.REJECTED,
            decision=ExecutionDecision.REJECT,
            reason=reason,
            reference_id=reference_id,
            report_message=(
                "Enterprise execution was rejected."
            ),
        )

    def cancel_execution(
        self,
        execution_id: str,
        *,
        stage: ExecutionStage,
        reason: str,
        reference_id: str | None = None,
    ) -> ExecutionReport:
        return self._terminate_execution(
            execution_id=execution_id,
            stage=stage,
            status=ExecutionStatus.CANCELLED,
            decision=ExecutionDecision.CANCEL,
            reason=reason,
            reference_id=reference_id,
            report_message=(
                "Enterprise execution was cancelled."
            ),
        )

    def fail_execution(
        self,
        execution_id: str,
        *,
        stage: ExecutionStage,
        error: str,
        reference_id: str | None = None,
    ) -> ExecutionReport:
        request, current = self._require_active_result(
            execution_id
        )

        if not isinstance(stage, ExecutionStage):
            raise TypeError(
                "stage must be an ExecutionStage"
            )

        normalized_error = (
            self._normalize_identifier(
                error,
                "error",
            )
        )

        self._validate_new_stage(
            current=current,
            stage=stage,
        )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "failure time must not be earlier than "
                "the current execution update"
            )

        step = ExecutionStep(
            step_id=self._next_step_id(),
            execution_id=request.execution_id,
            stage=stage,
            decision=ExecutionDecision.NO_ACTION,
            started_at=now,
            completed_at=now,
            successful=False,
            message="Execution stage failed.",
            reference_id=reference_id,
            error=normalized_error,
        )

        result = ExecutionResult(
            execution_id=request.execution_id,
            status=ExecutionStatus.FAILED,
            decision=ExecutionDecision.NO_ACTION,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            steps=current.steps + (step,),
            warnings=current.warnings,
            error=normalized_error,
        )

        return self._store_result_and_report(
            request=request,
            result=result,
            message=(
                "Enterprise execution failed."
            ),
        )

    def _terminate_execution(
        self,
        *,
        execution_id: str,
        stage: ExecutionStage,
        status: ExecutionStatus,
        decision: ExecutionDecision,
        reason: str,
        reference_id: str | None,
        report_message: str,
    ) -> ExecutionReport:
        request, current = self._require_active_result(
            execution_id
        )

        if not isinstance(stage, ExecutionStage):
            raise TypeError(
                "stage must be an ExecutionStage"
            )

        normalized_reason = (
            self._normalize_identifier(
                reason,
                "reason",
            )
        )

        self._validate_new_stage(
            current=current,
            stage=stage,
        )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "termination time must not be earlier than "
                "the current execution update"
            )

        step = ExecutionStep(
            step_id=self._next_step_id(),
            execution_id=request.execution_id,
            stage=stage,
            decision=decision,
            started_at=now,
            completed_at=now,
            successful=False,
            message=normalized_reason,
            reference_id=reference_id,
            error=normalized_reason,
        )

        result = ExecutionResult(
            execution_id=request.execution_id,
            status=status,
            decision=decision,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            steps=current.steps + (step,),
            warnings=current.warnings,
        )

        return self._store_result_and_report(
            request=request,
            result=result,
            message=report_message,
        )

    def _validate_new_stage(
        self,
        *,
        current: ExecutionResult,
        stage: ExecutionStage,
    ) -> None:
        existing_stages = {
            step.stage
            for step in current.steps
        }

        if stage in existing_stages:
            raise ValueError(
                "execution stage is already recorded"
            )

        if not current.steps:
            return

        previous_stage = current.steps[-1].stage

        if (
            self._stage_position(stage)
            <= self._stage_position(previous_stage)
        ):
            raise ValueError(
                "execution stages must be recorded "
                "in pipeline order"
            )

    @staticmethod
    def _stage_position(
        stage: ExecutionStage,
    ) -> int:
        positions = {
            ExecutionStage.SESSION: 1,
            ExecutionStage.PORTFOLIO: 2,
            ExecutionStage.ORDER: 3,
            ExecutionStage.RISK: 4,
            ExecutionStage.BROKER: 5,
            ExecutionStage.EXECUTION: 6,
        }

        return positions[stage]

    @staticmethod
    def _combine_warnings(
        existing: tuple[str, ...],
        additional: tuple[str, ...],
    ) -> tuple[str, ...]:
        combined: list[str] = []
        seen: set[str] = set()

        for warning in existing + additional:
            if warning not in seen:
                seen.add(warning)
                combined.append(warning)

        return tuple(combined)
    def _store_result_and_report(
        self,
        *,
        request: ExecutionRequest,
        result: ExecutionResult,
        message: str,
    ) -> ExecutionReport:
        self._current_results[
            request.execution_id
        ] = result

        self._result_history.setdefault(
            request.execution_id,
            [],
        ).append(result)

        report = ExecutionReport(
            report_id=self._next_report_id(),
            request=request,
            result=result,
            reported_at=result.updated_at,
            message=message,
            warnings=result.warnings,
            metadata=(
                (
                    "correlation_id",
                    request.correlation_id,
                ),
                (
                    "order_id",
                    request.order_request.order_id,
                ),
            ),
        )

        self._reports[
            request.execution_id
        ] = report

        self._report_history.append(
            report
        )

        return report

    def _require_active_result(
        self,
        execution_id: str,
    ) -> tuple[
        ExecutionRequest,
        ExecutionResult,
    ]:
        request = self.get_request(
            execution_id
        )
        result = self.get_result(
            execution_id
        )

        if result.status in _TERMINAL_STATUSES:
            raise RuntimeError(
                "terminal executions cannot be modified"
            )

        if result.status is not ExecutionStatus.EXECUTING:
            raise RuntimeError(
                "execution must be in EXECUTING status"
            )

        return request, result

    def _next_step_id(self) -> str:
        value = (
            f"execution-step-"
            f"{self._next_step_number:06d}"
        )
        self._next_step_number += 1
        return value

    def _next_report_id(self) -> str:
        value = (
            f"execution-report-"
            f"{self._next_report_number:06d}"
        )
        self._next_report_number += 1
        return value

    def _current_time(self) -> datetime:
        value = self._clock()

        if not isinstance(
            value,
            datetime,
        ):
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