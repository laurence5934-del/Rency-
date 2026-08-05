from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from app.strategy.execution_coordinator import (
    ExecutionReport,
)

from .orchestrator_models import (
    TradingWorkflowReport,
    TradingWorkflowRequest,
    TradingWorkflowResult,
    WorkflowCheckpoint,
    WorkflowDecision,
    WorkflowStage,
    WorkflowStatus,
)


Clock = Callable[[], datetime]


_TERMINAL_STATUSES = {
    WorkflowStatus.COMPLETED,
    WorkflowStatus.HELD,
    WorkflowStatus.REJECTED,
    WorkflowStatus.CANCELLED,
    WorkflowStatus.FAILED,
}


_STAGE_POSITIONS = {
    WorkflowStage.STRATEGY: 1,
    WorkflowStage.SESSION: 2,
    WorkflowStage.PORTFOLIO: 3,
    WorkflowStage.ORDER: 4,
    WorkflowStage.RISK: 5,
    WorkflowStage.BROKER: 6,
    WorkflowStage.EXECUTION: 7,
}


class EnterpriseTradingOrchestrator:
    """
    Coordinates the complete enterprise trading workflow.

    The orchestrator owns workflow state and audit history.
    Business rules remain inside their specialized subsystems.
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
            TradingWorkflowRequest,
        ] = {}

        self._workflow_by_correlation: dict[
            str,
            str,
        ] = {}

        self._workflow_by_execution: dict[
            str,
            str,
        ] = {}

        self._current_results: dict[
            str,
            TradingWorkflowResult,
        ] = {}

        self._result_history: dict[
            str,
            list[TradingWorkflowResult],
        ] = {}

        self._reports: dict[
            str,
            TradingWorkflowReport,
        ] = {}

        self._report_history: list[
            TradingWorkflowReport
        ] = []

        self._next_checkpoint_number = 1
        self._next_report_number = 1

    @property
    def workflow_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(self._requests)
        )

    @property
    def report_history(
        self,
    ) -> tuple[TradingWorkflowReport, ...]:
        return tuple(self._report_history)

    def register_workflow(
        self,
        request: TradingWorkflowRequest,
    ) -> TradingWorkflowRequest:
        if not isinstance(
            request,
            TradingWorkflowRequest,
        ):
            raise TypeError(
                "request must be a TradingWorkflowRequest"
            )

        if request.workflow_id in self._requests:
            raise ValueError(
                "workflow_id is already registered"
            )

        if (
            request.correlation_id
            in self._workflow_by_correlation
        ):
            raise ValueError(
                "correlation_id is already registered"
            )

        if (
            request.execution_id
            in self._workflow_by_execution
        ):
            raise ValueError(
                "execution_id is already registered"
            )

        self._requests[
            request.workflow_id
        ] = request

        self._workflow_by_correlation[
            request.correlation_id
        ] = request.workflow_id

        self._workflow_by_execution[
            request.execution_id
        ] = request.workflow_id

        return request

    def unregister_workflow(
        self,
        workflow_id: str,
    ) -> TradingWorkflowRequest:
        request = self.get_request(
            workflow_id
        )

        if workflow_id in self._current_results:
            raise RuntimeError(
                "started workflows cannot be unregistered"
            )

        self._requests.pop(
            request.workflow_id
        )

        self._workflow_by_correlation.pop(
            request.correlation_id,
            None,
        )

        self._workflow_by_execution.pop(
            request.execution_id,
            None,
        )

        return request

    def get_request(
        self,
        workflow_id: str,
    ) -> TradingWorkflowRequest:
        normalized_workflow_id = (
            self._normalize_identifier(
                workflow_id,
                "workflow_id",
            )
        )

        try:
            return self._requests[
                normalized_workflow_id
            ]
        except KeyError as exc:
            raise KeyError(
                "trading workflow request not found: "
                f"{normalized_workflow_id}"
            ) from exc

    def request_for_correlation(
        self,
        correlation_id: str,
    ) -> TradingWorkflowRequest:
        normalized_correlation_id = (
            self._normalize_identifier(
                correlation_id,
                "correlation_id",
            )
        )

        try:
            workflow_id = (
                self._workflow_by_correlation[
                    normalized_correlation_id
                ]
            )
        except KeyError as exc:
            raise KeyError(
                "trading workflow not found for "
                f"correlation_id: "
                f"{normalized_correlation_id}"
            ) from exc

        return self._requests[workflow_id]

    def request_for_execution(
        self,
        execution_id: str,
    ) -> TradingWorkflowRequest:
        normalized_execution_id = (
            self._normalize_identifier(
                execution_id,
                "execution_id",
            )
        )

        try:
            workflow_id = (
                self._workflow_by_execution[
                    normalized_execution_id
                ]
            )
        except KeyError as exc:
            raise KeyError(
                "trading workflow not found for "
                f"execution_id: "
                f"{normalized_execution_id}"
            ) from exc

        return self._requests[workflow_id]

    def start_workflow(
        self,
        workflow_id: str,
    ) -> TradingWorkflowReport:
        request = self.get_request(
            workflow_id
        )

        existing_result = self._current_results.get(
            request.workflow_id
        )

        if existing_result is not None:
            return self.get_report(
                request.workflow_id
            )

        now = self._current_time()

        if now < request.created_at:
            raise ValueError(
                "workflow start time must not be earlier "
                "than request created_at"
            )

        result = TradingWorkflowResult(
            workflow_id=request.workflow_id,
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=now,
            updated_at=now,
            checkpoints=(),
        )

        return self._store_result_and_report(
            request=request,
            result=result,
            message=(
                "Enterprise trading workflow started."
            ),
        )

    def record_checkpoint(
        self,
        workflow_id: str,
        *,
        stage: WorkflowStage,
        decision: WorkflowDecision,
        successful: bool,
        message: str,
        reference_id: str | None = None,
        warnings: tuple[str, ...] | list[str] = (),
        error: str | None = None,
        metadata: (
            tuple[tuple[str, str], ...]
            | list[tuple[str, str]]
        ) = (),
    ) -> TradingWorkflowReport:
        request, current = self._require_running_result(
            workflow_id
        )

        if not isinstance(stage, WorkflowStage):
            raise TypeError(
                "stage must be a WorkflowStage"
            )

        if not isinstance(
            decision,
            WorkflowDecision,
        ):
            raise TypeError(
                "decision must be a WorkflowDecision"
            )

        if not isinstance(successful, bool):
            raise TypeError(
                "successful must be a bool"
            )

        self._validate_new_stage(
            current=current,
            stage=stage,
        )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "checkpoint time must not be earlier "
                "than the current workflow update"
            )

        checkpoint = WorkflowCheckpoint(
            checkpoint_id=(
                self._next_checkpoint_id()
            ),
            workflow_id=request.workflow_id,
            stage=stage,
            decision=decision,
            started_at=now,
            completed_at=now,
            message=message,
            successful=successful,
            reference_id=reference_id,
            warnings=warnings,
            error=error,
            metadata=metadata,
        )

        result = TradingWorkflowResult(
            workflow_id=request.workflow_id,
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=current.started_at,
            updated_at=now,
            checkpoints=(
                current.checkpoints
                + (checkpoint,)
            ),
            warnings=self._combine_warnings(
                current.warnings,
                checkpoint.warnings,
            ),
        )

        return self._store_result_and_report(
            request=request,
            result=result,
            message=(
                f"Workflow stage {stage.value} recorded."
            ),
        )

    def complete_workflow(
        self,
        workflow_id: str,
        *,
        execution_report: ExecutionReport,
    ) -> TradingWorkflowReport:
        request, current = self._require_running_result(
            workflow_id
        )

        if not isinstance(
            execution_report,
            ExecutionReport,
        ):
            raise TypeError(
                "execution_report must be an "
                "ExecutionReport"
            )

        if (
            execution_report.request.execution_id
            != request.execution_id
        ):
            raise ValueError(
                "execution_report execution_id must match "
                "workflow execution_id"
            )

        if (
            execution_report.request.order_request.order_id
            != request.order_id
        ):
            raise ValueError(
                "execution_report order_id must match "
                "workflow order_id"
            )

        if not current.checkpoints:
            raise RuntimeError(
                "workflow cannot complete without checkpoints"
            )

        if not all(
            checkpoint.successful
            for checkpoint in current.checkpoints
        ):
            raise RuntimeError(
                "workflow cannot complete with "
                "unsuccessful checkpoints"
            )

        if (
            current.checkpoints[-1].stage
            is not WorkflowStage.EXECUTION
        ):
            raise RuntimeError(
                "workflow must reach the execution stage "
                "before completion"
            )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "completion time must not be earlier "
                "than the current workflow update"
            )

        if now < execution_report.reported_at:
            raise ValueError(
                "workflow completion time must not be "
                "earlier than execution report time"
            )

        result = TradingWorkflowResult(
            workflow_id=request.workflow_id,
            status=WorkflowStatus.COMPLETED,
            decision=WorkflowDecision.PROCEED,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            checkpoints=current.checkpoints,
            execution_report=execution_report,
            warnings=current.warnings,
        )

        return self._store_result_and_report(
            request=request,
            result=result,
            message=(
                "Enterprise trading workflow completed "
                "successfully."
            ),
        )

    def hold_workflow(
        self,
        workflow_id: str,
        *,
        stage: WorkflowStage,
        reason: str,
        reference_id: str | None = None,
    ) -> TradingWorkflowReport:
        return self._terminate_workflow(
            workflow_id=workflow_id,
            stage=stage,
            status=WorkflowStatus.HELD,
            decision=WorkflowDecision.HOLD,
            reason=reason,
            reference_id=reference_id,
            report_message=(
                "Enterprise trading workflow was "
                "placed on hold."
            ),
        )

    def reject_workflow(
        self,
        workflow_id: str,
        *,
        stage: WorkflowStage,
        reason: str,
        reference_id: str | None = None,
    ) -> TradingWorkflowReport:
        return self._terminate_workflow(
            workflow_id=workflow_id,
            stage=stage,
            status=WorkflowStatus.REJECTED,
            decision=WorkflowDecision.REJECT,
            reason=reason,
            reference_id=reference_id,
            report_message=(
                "Enterprise trading workflow was rejected."
            ),
        )

    def cancel_workflow(
        self,
        workflow_id: str,
        *,
        stage: WorkflowStage,
        reason: str,
        reference_id: str | None = None,
    ) -> TradingWorkflowReport:
        return self._terminate_workflow(
            workflow_id=workflow_id,
            stage=stage,
            status=WorkflowStatus.CANCELLED,
            decision=WorkflowDecision.CANCEL,
            reason=reason,
            reference_id=reference_id,
            report_message=(
                "Enterprise trading workflow was cancelled."
            ),
        )

    def fail_workflow(
        self,
        workflow_id: str,
        *,
        stage: WorkflowStage,
        error: str,
        reference_id: str | None = None,
    ) -> TradingWorkflowReport:
        request, current = self._require_running_result(
            workflow_id
        )

        if not isinstance(stage, WorkflowStage):
            raise TypeError(
                "stage must be a WorkflowStage"
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
                "failure time must not be earlier "
                "than the current workflow update"
            )

        checkpoint = WorkflowCheckpoint(
            checkpoint_id=(
                self._next_checkpoint_id()
            ),
            workflow_id=request.workflow_id,
            stage=stage,
            decision=WorkflowDecision.NO_ACTION,
            started_at=now,
            completed_at=now,
            message="Workflow stage failed.",
            successful=False,
            reference_id=reference_id,
            error=normalized_error,
        )

        result = TradingWorkflowResult(
            workflow_id=request.workflow_id,
            status=WorkflowStatus.FAILED,
            decision=WorkflowDecision.NO_ACTION,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            checkpoints=(
                current.checkpoints
                + (checkpoint,)
            ),
            warnings=current.warnings,
            error=normalized_error,
        )

        return self._store_result_and_report(
            request=request,
            result=result,
            message=(
                "Enterprise trading workflow failed."
            ),
        )

    def get_result(
        self,
        workflow_id: str,
    ) -> TradingWorkflowResult:
        request = self.get_request(
            workflow_id
        )

        try:
            return self._current_results[
                request.workflow_id
            ]
        except KeyError as exc:
            raise KeyError(
                "trading workflow has no result state: "
                f"{request.workflow_id}"
            ) from exc

    def get_report(
        self,
        workflow_id: str,
    ) -> TradingWorkflowReport:
        request = self.get_request(
            workflow_id
        )

        try:
            return self._reports[
                request.workflow_id
            ]
        except KeyError as exc:
            raise KeyError(
                "trading workflow has no report: "
                f"{request.workflow_id}"
            ) from exc

    def results_for_workflow(
        self,
        workflow_id: str,
    ) -> tuple[TradingWorkflowResult, ...]:
        request = self.get_request(
            workflow_id
        )

        return tuple(
            self._result_history.get(
                request.workflow_id,
                (),
            )
        )

    def reports_for_order(
        self,
        order_id: str,
    ) -> tuple[TradingWorkflowReport, ...]:
        normalized_order_id = (
            self._normalize_identifier(
                order_id,
                "order_id",
            )
        )

        return tuple(
            report
            for report in self._report_history
            if report.request.order_id
            == normalized_order_id
        )

    def reports_for_portfolio(
        self,
        portfolio_id: str,
    ) -> tuple[TradingWorkflowReport, ...]:
        normalized_portfolio_id = (
            self._normalize_identifier(
                portfolio_id,
                "portfolio_id",
            )
        )

        return tuple(
            report
            for report in self._report_history
            if report.request.portfolio_id
            == normalized_portfolio_id
        )

    def reports_for_strategy(
        self,
        strategy_id: str,
    ) -> tuple[TradingWorkflowReport, ...]:
        normalized_strategy_id = (
            self._normalize_identifier(
                strategy_id,
                "strategy_id",
            )
        )

        return tuple(
            report
            for report in self._report_history
            if report.request.strategy_id
            == normalized_strategy_id
        )

    def latest_report(
        self,
    ) -> TradingWorkflowReport:
        if not self._report_history:
            raise KeyError(
                "trading orchestrator has no reports"
            )

        return self._report_history[-1]

    def _terminate_workflow(
        self,
        *,
        workflow_id: str,
        stage: WorkflowStage,
        status: WorkflowStatus,
        decision: WorkflowDecision,
        reason: str,
        reference_id: str | None,
        report_message: str,
    ) -> TradingWorkflowReport:
        request, current = self._require_running_result(
            workflow_id
        )

        if not isinstance(stage, WorkflowStage):
            raise TypeError(
                "stage must be a WorkflowStage"
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
                "termination time must not be earlier "
                "than the current workflow update"
            )

        checkpoint = WorkflowCheckpoint(
            checkpoint_id=(
                self._next_checkpoint_id()
            ),
            workflow_id=request.workflow_id,
            stage=stage,
            decision=decision,
            started_at=now,
            completed_at=now,
            message=normalized_reason,
            successful=False,
            reference_id=reference_id,
            error=normalized_reason,
        )

        result = TradingWorkflowResult(
            workflow_id=request.workflow_id,
            status=status,
            decision=decision,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            checkpoints=(
                current.checkpoints
                + (checkpoint,)
            ),
            warnings=current.warnings,
        )

        return self._store_result_and_report(
            request=request,
            result=result,
            message=report_message,
        )

    def _store_result_and_report(
        self,
        *,
        request: TradingWorkflowRequest,
        result: TradingWorkflowResult,
        message: str,
    ) -> TradingWorkflowReport:
        self._current_results[
            request.workflow_id
        ] = result

        self._result_history.setdefault(
            request.workflow_id,
            [],
        ).append(result)

        report = TradingWorkflowReport(
            report_id=self._next_report_id(),
            request=request,
            result=result,
            reported_at=result.updated_at,
            message=message,
            metadata=(
                (
                    "correlation_id",
                    request.correlation_id,
                ),
                (
                    "execution_id",
                    request.execution_id,
                ),
                (
                    "order_id",
                    request.order_id,
                ),
            ),
            warnings=result.warnings,
        )

        self._reports[
            request.workflow_id
        ] = report

        self._report_history.append(report)

        return report

    def _require_running_result(
        self,
        workflow_id: str,
    ) -> tuple[
        TradingWorkflowRequest,
        TradingWorkflowResult,
    ]:
        request = self.get_request(
            workflow_id
        )

        result = self.get_result(
            workflow_id
        )

        if result.status in _TERMINAL_STATUSES:
            raise RuntimeError(
                "terminal workflows cannot be modified"
            )

        if result.status is not WorkflowStatus.RUNNING:
            raise RuntimeError(
                "workflow must be in RUNNING status"
            )

        return request, result

    def _validate_new_stage(
        self,
        *,
        current: TradingWorkflowResult,
        stage: WorkflowStage,
    ) -> None:
        existing_stages = {
            checkpoint.stage
            for checkpoint in current.checkpoints
        }

        if stage in existing_stages:
            raise ValueError(
                "workflow stage is already recorded"
            )

        if not current.checkpoints:
            return

        previous_stage = (
            current.checkpoints[-1].stage
        )

        if (
            _STAGE_POSITIONS[stage]
            <= _STAGE_POSITIONS[previous_stage]
        ):
            raise ValueError(
                "workflow stages must be recorded "
                "in pipeline order"
            )

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

    def _next_checkpoint_id(self) -> str:
        value = (
            f"workflow-checkpoint-"
            f"{self._next_checkpoint_number:06d}"
        )

        self._next_checkpoint_number += 1
        return value

    def _next_report_id(self) -> str:
        value = (
            f"workflow-report-"
            f"{self._next_report_number:06d}"
        )

        self._next_report_number += 1
        return value

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