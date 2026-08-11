from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .signal_models import (
    SignalDecision,
    SignalStatus,
    StrategySignal,
    StrategySignalReport,
    StrategySignalRequest,
    StrategySignalResult,
)


Clock = Callable[[], datetime]


class EnterpriseStrategySignalEngine:
    """
    Coordinates the lifecycle of strategy-signal requests.

    Responsibilities:
    - register immutable requests
    - protect request/correlation identifiers
    - start signal evaluation
    - attach generated signals
    - accept, reject, expire, cancel, or fail requests
    - preserve immutable result/report histories
    - provide deterministic signal/report identifiers
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
            StrategySignalRequest,
        ] = {}

        self._request_id_by_correlation: dict[
            str,
            str,
        ] = {}

        self._results: dict[
            str,
            StrategySignalResult,
        ] = {}

        self._result_history: dict[
            str,
            list[StrategySignalResult],
        ] = {}

        self._reports: dict[
            str,
            StrategySignalReport,
        ] = {}

        self._report_history: list[
            StrategySignalReport
        ] = []

        self._signals: dict[
            str,
            StrategySignal,
        ] = {}

        self._signal_id_by_request: dict[
            str,
            str,
        ] = {}

        self._next_signal_number = 1
        self._next_report_number = 1

    @property
    def request_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._requests))

    @property
    def signal_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._signals))

    @property
    def report_history(
        self,
    ) -> tuple[StrategySignalReport, ...]:
        return tuple(self._report_history)

    def register_request(
        self,
        request: StrategySignalRequest,
    ) -> StrategySignalRequest:
        if not isinstance(
            request,
            StrategySignalRequest,
        ):
            raise TypeError(
                "request must be a StrategySignalRequest"
            )

        if request.request_id in self._requests:
            raise ValueError(
                "request_id is already registered"
            )

        if (
            request.correlation_id
            in self._request_id_by_correlation
        ):
            raise ValueError(
                "correlation_id is already registered"
            )

        self._requests[request.request_id] = request
        self._request_id_by_correlation[
            request.correlation_id
        ] = request.request_id

        return request

    def unregister_request(
        self,
        request_id: str,
    ) -> StrategySignalRequest:
        request = self.get_request(request_id)

        if request.request_id in self._results:
            raise RuntimeError(
                "started signal requests cannot be "
                "unregistered"
            )

        self._requests.pop(request.request_id)

        self._request_id_by_correlation.pop(
            request.correlation_id,
            None,
        )

        return request

    def get_request(
        self,
        request_id: str,
    ) -> StrategySignalRequest:
        normalized = self._normalize_identifier(
            request_id,
            "request_id",
        )

        try:
            return self._requests[normalized]
        except KeyError as exc:
            raise KeyError(
                "strategy signal request not found: "
                f"{normalized}"
            ) from exc

    def request_for_correlation(
        self,
        correlation_id: str,
    ) -> StrategySignalRequest:
        normalized = self._normalize_identifier(
            correlation_id,
            "correlation_id",
        )

        try:
            request_id = (
                self._request_id_by_correlation[
                    normalized
                ]
            )
        except KeyError as exc:
            raise KeyError(
                "strategy signal request not found for "
                f"correlation_id: {normalized}"
            ) from exc

        return self._requests[request_id]

    def start_evaluation(
        self,
        request_id: str,
    ) -> StrategySignalReport:
        request = self.get_request(request_id)

        current = self._results.get(
            request.request_id
        )

        if current is not None:
            return self.get_report(
                request.request_id
            )

        now = self._current_time()

        if now < request.created_at:
            raise ValueError(
                "signal evaluation start time must not "
                "be earlier than request created_at"
            )

        result = StrategySignalResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=SignalStatus.ACTIVE,
            decision=SignalDecision.PROCEED,
            started_at=now,
            updated_at=now,
        )

        return self._record_state(
            request=request,
            result=result,
            message="Strategy signal evaluation started.",
        )

    def attach_signal(
        self,
        request_id: str,
        *,
        rationale: str,
        expires_at: datetime | None = None,
        warnings: tuple[str, ...] = (),
        metadata: tuple[
            tuple[str, str],
            ...,
        ] = (),
    ) -> StrategySignalReport:
        request = self.get_request(request_id)
        current = self.get_result(
            request.request_id
        )

        self._ensure_modifiable(current)

        if current.signal is not None:
            raise RuntimeError(
                "signal is already attached to request"
            )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "signal generation time must not be "
                "earlier than latest result update"
            )

        signal = StrategySignal(
            signal_id=self._next_signal_id(),
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            strategy_id=request.strategy_id,
            portfolio_id=request.portfolio_id,
            symbol=request.symbol,
            signal_type=request.signal_type,
            direction=request.direction,
            strength=request.strength,
            confidence=request.confidence,
            generated_at=now,
            expires_at=expires_at,
            rationale=rationale,
            warnings=warnings,
            metadata=metadata,
        )

        self._signals[signal.signal_id] = signal
        self._signal_id_by_request[
            request.request_id
        ] = signal.signal_id

        result = StrategySignalResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=SignalStatus.ACTIVE,
            decision=SignalDecision.PROCEED,
            started_at=current.started_at,
            updated_at=now,
            signal=signal,
            warnings=signal.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message="Strategy signal generated.",
        )

    def accept_request(
        self,
        request_id: str,
        *,
        message: str = "Strategy signal accepted.",
    ) -> StrategySignalReport:
        request = self.get_request(request_id)
        current = self.get_result(
            request.request_id
        )

        self._ensure_modifiable(current)

        if current.signal is None:
            raise RuntimeError(
                "signal request cannot be accepted "
                "without a signal"
            )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "acceptance time must not be earlier "
                "than latest result update"
            )

        result = StrategySignalResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=SignalStatus.ACCEPTED,
            decision=SignalDecision.ACCEPT,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            signal=current.signal,
            warnings=current.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message=message,
        )

    def reject_request(
        self,
        request_id: str,
        *,
        reason: str,
    ) -> StrategySignalReport:
        return self._terminal_without_error(
            request_id=request_id,
            status=SignalStatus.REJECTED,
            decision=SignalDecision.REJECT,
            message=reason,
        )

    def cancel_request(
        self,
        request_id: str,
        *,
        reason: str,
    ) -> StrategySignalReport:
        return self._terminal_without_error(
            request_id=request_id,
            status=SignalStatus.CANCELLED,
            decision=SignalDecision.CANCEL,
            message=reason,
        )

    def expire_request(
        self,
        request_id: str,
        *,
        message: str = "Strategy signal expired.",
    ) -> StrategySignalReport:
        request = self.get_request(request_id)
        current = self.get_result(
            request.request_id
        )

        self._ensure_modifiable(current)

        if current.signal is None:
            raise RuntimeError(
                "signal request cannot expire "
                "without a signal"
            )

        now = self._current_time()

        if not current.signal.is_expired_at(now):
            raise RuntimeError(
                "strategy signal has not expired"
            )

        result = StrategySignalResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=SignalStatus.EXPIRED,
            decision=SignalDecision.NO_ACTION,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            signal=current.signal,
            warnings=current.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message=message,
        )

    def fail_request(
        self,
        request_id: str,
        *,
        error: str,
        retryable: bool = False,
    ) -> StrategySignalReport:
        if not isinstance(retryable, bool):
            raise TypeError(
                "retryable must be a bool"
            )

        request = self.get_request(request_id)
        current = self.get_result(
            request.request_id
        )

        self._ensure_modifiable(current)

        normalized_error = (
            self._normalize_identifier(
                error,
                "error",
            )
        )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "failure time must not be earlier "
                "than latest result update"
            )

        result = StrategySignalResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=SignalStatus.FAILED,
            decision=(
                SignalDecision.RETRY
                if retryable
                else SignalDecision.NO_ACTION
            ),
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            signal=current.signal,
            warnings=current.warnings,
            error=normalized_error,
        )

        return self._record_state(
            request=request,
            result=result,
            message=normalized_error,
        )

    def get_result(
        self,
        request_id: str,
    ) -> StrategySignalResult:
        request = self.get_request(request_id)

        try:
            return self._results[
                request.request_id
            ]
        except KeyError as exc:
            raise KeyError(
                "strategy signal request has no result: "
                f"{request.request_id}"
            ) from exc

    def get_report(
        self,
        request_id: str,
    ) -> StrategySignalReport:
        request = self.get_request(request_id)

        try:
            return self._reports[
                request.request_id
            ]
        except KeyError as exc:
            raise KeyError(
                "strategy signal request has no report: "
                f"{request.request_id}"
            ) from exc

    def get_signal(
        self,
        signal_id: str,
    ) -> StrategySignal:
        normalized = self._normalize_identifier(
            signal_id,
            "signal_id",
        )

        try:
            return self._signals[normalized]
        except KeyError as exc:
            raise KeyError(
                "strategy signal not found: "
                f"{normalized}"
            ) from exc

    def signal_for_request(
        self,
        request_id: str,
    ) -> StrategySignal:
        request = self.get_request(request_id)

        try:
            signal_id = self._signal_id_by_request[
                request.request_id
            ]
        except KeyError as exc:
            raise KeyError(
                "strategy signal request has no signal: "
                f"{request.request_id}"
            ) from exc

        return self._signals[signal_id]

    def results_for_request(
        self,
        request_id: str,
    ) -> tuple[StrategySignalResult, ...]:
        request = self.get_request(request_id)

        return tuple(
            self._result_history.get(
                request.request_id,
                (),
            )
        )

    def reports_for_strategy(
        self,
        strategy_id: str,
    ) -> tuple[StrategySignalReport, ...]:
        normalized = self._normalize_identifier(
            strategy_id,
            "strategy_id",
        )

        return tuple(
            report
            for report in self._report_history
            if report.strategy_id == normalized
        )

    def reports_for_portfolio(
        self,
        portfolio_id: str,
    ) -> tuple[StrategySignalReport, ...]:
        normalized = self._normalize_identifier(
            portfolio_id,
            "portfolio_id",
        )

        return tuple(
            report
            for report in self._report_history
            if report.portfolio_id == normalized
        )

    def reports_for_symbol(
        self,
        symbol: str,
    ) -> tuple[StrategySignalReport, ...]:
        normalized = self._normalize_identifier(
            symbol,
            "symbol",
        ).upper()

        return tuple(
            report
            for report in self._report_history
            if report.symbol == normalized
        )

    def latest_report(
        self,
    ) -> StrategySignalReport:
        if not self._report_history:
            raise KeyError(
                "strategy signal engine has no reports"
            )

        return self._report_history[-1]

    def _terminal_without_error(
        self,
        *,
        request_id: str,
        status: SignalStatus,
        decision: SignalDecision,
        message: str,
    ) -> StrategySignalReport:
        request = self.get_request(request_id)
        current = self.get_result(
            request.request_id
        )

        self._ensure_modifiable(current)

        normalized_message = (
            self._normalize_identifier(
                message,
                "reason",
            )
        )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "terminal transition time must not be "
                "earlier than latest result update"
            )

        result = StrategySignalResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=status,
            decision=decision,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            signal=current.signal,
            warnings=current.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message=normalized_message,
        )

    def _record_state(
        self,
        *,
        request: StrategySignalRequest,
        result: StrategySignalResult,
        message: str,
    ) -> StrategySignalReport:
        self._results[
            request.request_id
        ] = result

        self._result_history.setdefault(
            request.request_id,
            [],
        ).append(result)

        report = StrategySignalReport(
            report_id=self._next_report_id(),
            request=request,
            result=result,
            reported_at=result.updated_at,
            message=message,
            warnings=result.warnings,
            metadata=(
                (
                    "strategy_id",
                    request.strategy_id,
                ),
                (
                    "portfolio_id",
                    request.portfolio_id,
                ),
                (
                    "symbol",
                    request.symbol,
                ),
            ),
        )

        self._reports[
            request.request_id
        ] = report

        self._report_history.append(report)

        return report

    @staticmethod
    def _ensure_modifiable(
        result: StrategySignalResult,
    ) -> None:
        if result.is_terminal:
            raise RuntimeError(
                "terminal signal requests cannot be modified"
            )

    def _next_signal_id(self) -> str:
        value = (
            "strategy-signal-"
            f"{self._next_signal_number:06d}"
        )

        self._next_signal_number += 1
        return value

    def _next_report_id(self) -> str:
        value = (
            "strategy-signal-report-"
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