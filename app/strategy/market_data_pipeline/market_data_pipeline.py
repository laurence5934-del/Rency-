from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .pipeline_models import (
    PIPELINE_STAGE_POSITIONS,
    MarketDataPipelineReport,
    MarketDataPipelineRequest,
    MarketDataPipelineResult,
    PipelineCheckpoint,
    PipelineDecision,
    PipelineStage,
    PipelineStatus,
)


Clock = Callable[[], datetime]


class EnterpriseMarketDataPipeline:
    """
    Coordinates the lifecycle of normalized market-data events.

    Responsibilities:
    - register immutable pipeline requests
    - protect event and correlation identifiers
    - start event processing
    - record ordered pipeline checkpoints
    - complete, reject, drop, or fail events
    - preserve immutable result and report histories
    - generate deterministic checkpoint and report IDs
    """

    def __init__(
        self,
        *,
        clock: Clock | None = None,
    ) -> None:
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")

        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

        self._requests: dict[
            str,
            MarketDataPipelineRequest,
        ] = {}

        self._event_id_by_correlation: dict[
            str,
            str,
        ] = {}

        self._results: dict[
            str,
            MarketDataPipelineResult,
        ] = {}

        self._result_history: dict[
            str,
            list[MarketDataPipelineResult],
        ] = {}

        self._reports: dict[
            str,
            MarketDataPipelineReport,
        ] = {}

        self._report_history: list[
            MarketDataPipelineReport
        ] = []

        self._next_checkpoint_number = 1
        self._next_report_number = 1

    @property
    def event_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._requests))

    @property
    def report_history(
        self,
    ) -> tuple[MarketDataPipelineReport, ...]:
        return tuple(self._report_history)

    def register_request(
        self,
        request: MarketDataPipelineRequest,
    ) -> MarketDataPipelineRequest:
        if not isinstance(
            request,
            MarketDataPipelineRequest,
        ):
            raise TypeError(
                "request must be a "
                "MarketDataPipelineRequest"
            )

        if request.event_id in self._requests:
            raise ValueError(
                "event_id is already registered"
            )

        if (
            request.correlation_id
            in self._event_id_by_correlation
        ):
            raise ValueError(
                "correlation_id is already registered"
            )

        self._requests[request.event_id] = request

        self._event_id_by_correlation[
            request.correlation_id
        ] = request.event_id

        return request

    def unregister_request(
        self,
        event_id: str,
    ) -> MarketDataPipelineRequest:
        request = self.get_request(event_id)

        if request.event_id in self._results:
            raise RuntimeError(
                "started pipeline events cannot be "
                "unregistered"
            )

        self._requests.pop(request.event_id)

        self._event_id_by_correlation.pop(
            request.correlation_id,
            None,
        )

        return request

    def get_request(
        self,
        event_id: str,
    ) -> MarketDataPipelineRequest:
        normalized_event_id = self._normalize_identifier(
            event_id,
            "event_id",
        )

        try:
            return self._requests[
                normalized_event_id
            ]
        except KeyError as exc:
            raise KeyError(
                "market-data pipeline request not found: "
                f"{normalized_event_id}"
            ) from exc

    def request_for_correlation(
        self,
        correlation_id: str,
    ) -> MarketDataPipelineRequest:
        normalized_correlation_id = (
            self._normalize_identifier(
                correlation_id,
                "correlation_id",
            )
        )

        try:
            event_id = self._event_id_by_correlation[
                normalized_correlation_id
            ]
        except KeyError as exc:
            raise KeyError(
                "market-data pipeline request not found "
                "for correlation_id: "
                f"{normalized_correlation_id}"
            ) from exc

        return self._requests[event_id]

    def start_processing(
        self,
        event_id: str,
    ) -> MarketDataPipelineReport:
        request = self.get_request(event_id)

        current = self._results.get(
            request.event_id
        )

        if current is not None:
            return self.get_report(
                request.event_id
            )

        now = self._current_time()

        if now < request.received_at:
            raise ValueError(
                "pipeline start time must not be earlier "
                "than request received_at"
            )

        result = MarketDataPipelineResult(
            event_id=request.event_id,
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=now,
            updated_at=now,
        )

        return self._record_state(
            request=request,
            result=result,
            message="Market-data pipeline processing started.",
        )

    def get_result(
        self,
        event_id: str,
    ) -> MarketDataPipelineResult:
        request = self.get_request(event_id)

        try:
            return self._results[
                request.event_id
            ]
        except KeyError as exc:
            raise KeyError(
                "market-data pipeline event has no result: "
                f"{request.event_id}"
            ) from exc

    def get_report(
        self,
        event_id: str,
    ) -> MarketDataPipelineReport:
        request = self.get_request(event_id)

        try:
            return self._reports[
                request.event_id
            ]
        except KeyError as exc:
            raise KeyError(
                "market-data pipeline event has no report: "
                f"{request.event_id}"
            ) from exc

    def latest_report(
        self,
    ) -> MarketDataPipelineReport:
        if not self._report_history:
            raise KeyError(
                "market-data pipeline has no reports"
            )

        return self._report_history[-1]

    def results_for_event(
        self,
        event_id: str,
    ) -> tuple[MarketDataPipelineResult, ...]:
        request = self.get_request(event_id)

        return tuple(
            self._result_history.get(
                request.event_id,
                (),
            )
        )

    def reports_for_symbol(
        self,
        symbol: str,
    ) -> tuple[MarketDataPipelineReport, ...]:
        normalized_symbol = self._normalize_identifier(
            symbol,
            "symbol",
        ).upper()

        return tuple(
            report
            for report in self._report_history
            if report.symbol == normalized_symbol
        )

    def reports_for_source(
        self,
        source: str,
    ) -> tuple[MarketDataPipelineReport, ...]:
        normalized_source = self._normalize_identifier(
            source,
            "source",
        )

        return tuple(
            report
            for report in self._report_history
            if report.request.source == normalized_source
        )

    def record_checkpoint(
        self,
        event_id: str,
        *,
        stage: PipelineStage,
        decision: PipelineDecision,
        successful: bool,
        message: str,
        reference_id: str | None = None,
        warnings: tuple[str, ...] = (),
        error: str | None = None,
        metadata: tuple[
            tuple[str, str],
            ...,
        ] = (),
    ) -> MarketDataPipelineReport:
        request = self.get_request(event_id)
        current = self.get_result(
            request.event_id
        )

        self._ensure_modifiable(current)

        if not isinstance(stage, PipelineStage):
            raise TypeError(
                "stage must be a PipelineStage"
            )

        if not isinstance(
            decision,
            PipelineDecision,
        ):
            raise TypeError(
                "decision must be a PipelineDecision"
            )

        if not isinstance(successful, bool):
            raise TypeError(
                "successful must be a bool"
            )

        self._validate_next_stage(
            checkpoints=current.checkpoints,
            stage=stage,
        )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "checkpoint time must not be earlier "
                "than the latest result update"
            )

        checkpoint = PipelineCheckpoint(
            checkpoint_id=self._next_checkpoint_id(),
            event_id=request.event_id,
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

        combined_warnings = self._merge_warnings(
            current.warnings,
            checkpoint.warnings,
        )

        result = MarketDataPipelineResult(
            event_id=request.event_id,
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=current.started_at,
            updated_at=now,
            checkpoints=(
                *current.checkpoints,
                checkpoint,
            ),
            warnings=combined_warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message="Pipeline checkpoint recorded.",
        )

    def complete_event(
        self,
        event_id: str,
        *,
        message: str = (
            "Market-data event processed successfully."
        ),
    ) -> MarketDataPipelineReport:
        request = self.get_request(event_id)
        current = self.get_result(
            request.event_id
        )

        self._ensure_modifiable(current)

        if not current.checkpoints:
            raise RuntimeError(
                "pipeline event cannot complete without "
                "checkpoints"
            )

        if (
            current.checkpoints[-1].stage
            is not PipelineStage.PUBLICATION
        ):
            raise RuntimeError(
                "pipeline event must reach the "
                "publication stage before completion"
            )

        if not all(
            checkpoint.successful
            for checkpoint in current.checkpoints
        ):
            raise RuntimeError(
                "pipeline event cannot complete with "
                "unsuccessful checkpoints"
            )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "completion time must not be earlier "
                "than the latest result update"
            )

        result = MarketDataPipelineResult(
            event_id=request.event_id,
            status=PipelineStatus.COMPLETED,
            decision=PipelineDecision.ACCEPT,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            checkpoints=current.checkpoints,
            warnings=current.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message=message,
        )

    def reject_event(
        self,
        event_id: str,
        *,
        stage: PipelineStage,
        reason: str,
        reference_id: str | None = None,
        warnings: tuple[str, ...] = (),
    ) -> MarketDataPipelineReport:
        return self._terminal_transition(
            event_id=event_id,
            stage=stage,
            status=PipelineStatus.REJECTED,
            decision=PipelineDecision.REJECT,
            message=reason,
            error=reason,
            reference_id=reference_id,
            warnings=warnings,
            result_error=None,
        )

    def drop_event(
        self,
        event_id: str,
        *,
        stage: PipelineStage,
        reason: str,
        reference_id: str | None = None,
        warnings: tuple[str, ...] = (),
    ) -> MarketDataPipelineReport:
        return self._terminal_transition(
            event_id=event_id,
            stage=stage,
            status=PipelineStatus.DROPPED,
            decision=PipelineDecision.DROP,
            message=reason,
            error=reason,
            reference_id=reference_id,
            warnings=warnings,
            result_error=None,
        )

    def fail_event(
        self,
        event_id: str,
        *,
        stage: PipelineStage,
        error: str,
        retryable: bool = False,
        reference_id: str | None = None,
        warnings: tuple[str, ...] = (),
    ) -> MarketDataPipelineReport:
        if not isinstance(retryable, bool):
            raise TypeError(
                "retryable must be a bool"
            )

        decision = (
            PipelineDecision.RETRY
            if retryable
            else PipelineDecision.NO_ACTION
        )

        return self._terminal_transition(
            event_id=event_id,
            stage=stage,
            status=PipelineStatus.FAILED,
            decision=decision,
            message=error,
            error=error,
            reference_id=reference_id,
            warnings=warnings,
            result_error=error,
        )

    def _terminal_transition(
        self,
        *,
        event_id: str,
        stage: PipelineStage,
        status: PipelineStatus,
        decision: PipelineDecision,
        message: str,
        error: str,
        reference_id: str | None,
        warnings: tuple[str, ...],
        result_error: str | None,
    ) -> MarketDataPipelineReport:
        request = self.get_request(event_id)
        current = self.get_result(
            request.event_id
        )

        self._ensure_modifiable(current)

        if not isinstance(stage, PipelineStage):
            raise TypeError(
                "stage must be a PipelineStage"
            )

        normalized_message = self._normalize_identifier(
            message,
            (
                "error"
                if status is PipelineStatus.FAILED
                else "reason"
            ),
        )

        self._validate_next_stage(
            checkpoints=current.checkpoints,
            stage=stage,
        )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "terminal transition time must not be "
                "earlier than the latest result update"
            )

        checkpoint = PipelineCheckpoint(
            checkpoint_id=self._next_checkpoint_id(),
            event_id=request.event_id,
            stage=stage,
            decision=decision,
            started_at=now,
            completed_at=now,
            successful=False,
            message=normalized_message,
            reference_id=reference_id,
            warnings=warnings,
            error=error,
        )

        combined_warnings = self._merge_warnings(
            current.warnings,
            checkpoint.warnings,
        )

        result = MarketDataPipelineResult(
            event_id=request.event_id,
            status=status,
            decision=decision,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            checkpoints=(
                *current.checkpoints,
                checkpoint,
            ),
            warnings=combined_warnings,
            error=result_error,
        )

        return self._record_state(
            request=request,
            result=result,
            message=normalized_message,
        )

    def _record_state(
        self,
        *,
        request: MarketDataPipelineRequest,
        result: MarketDataPipelineResult,
        message: str,
    ) -> MarketDataPipelineReport:
        self._results[
            request.event_id
        ] = result

        self._result_history.setdefault(
            request.event_id,
            [],
        ).append(result)

        report = MarketDataPipelineReport(
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
                    "source",
                    request.source,
                ),
                (
                    "event_type",
                    request.event_type.value,
                ),
            ),
        )

        self._reports[
            request.event_id
        ] = report

        self._report_history.append(report)

        return report

    @staticmethod
    def _ensure_modifiable(
        result: MarketDataPipelineResult,
    ) -> None:
        if result.is_terminal:
            raise RuntimeError(
                "terminal pipeline events cannot be "
                "modified"
            )

    @staticmethod
    def _validate_next_stage(
        *,
        checkpoints: tuple[
            PipelineCheckpoint,
            ...,
        ],
        stage: PipelineStage,
    ) -> None:
        existing_stages = {
            checkpoint.stage
            for checkpoint in checkpoints
        }

        if stage in existing_stages:
            raise ValueError(
                "pipeline stage is already recorded"
            )

        if not checkpoints:
            return

        latest_position = PIPELINE_STAGE_POSITIONS[
            checkpoints[-1].stage
        ]

        next_position = PIPELINE_STAGE_POSITIONS[
            stage
        ]

        if next_position <= latest_position:
            raise ValueError(
                "pipeline stages must be recorded "
                "in pipeline order"
            )

    @staticmethod
    def _merge_warnings(
        existing: tuple[str, ...],
        new: tuple[str, ...],
    ) -> tuple[str, ...]:
        merged: list[str] = []
        seen: set[str] = set()

        for warning in (*existing, *new):
            if warning not in seen:
                seen.add(warning)
                merged.append(warning)

        return tuple(merged)

    def _next_checkpoint_id(self) -> str:
        value = (
            "pipeline-checkpoint-"
            f"{self._next_checkpoint_number:06d}"
        )

        self._next_checkpoint_number += 1
        return value

    def _next_report_id(self) -> str:
        value = (
            "pipeline-report-"
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

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
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