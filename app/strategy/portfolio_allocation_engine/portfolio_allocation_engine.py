from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .allocation_models import (
    AllocationDecision,
    AllocationStatus,
    PortfolioAllocation,
    PortfolioAllocationReport,
    PortfolioAllocationRequest,
    PortfolioAllocationResult,
)


Clock = Callable[[], datetime]


class EnterprisePortfolioAllocationEngine:
    """
    Coordinates the lifecycle of portfolio-allocation requests.

    Responsibilities:
    - register immutable allocation requests
    - protect request and correlation identifiers
    - start allocation evaluation
    - generate portfolio allocations
    - approve, reject, cancel, or fail requests
    - preserve immutable result/report histories
    - provide deterministic allocation/report identifiers
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
            PortfolioAllocationRequest,
        ] = {}

        self._request_id_by_correlation: dict[
            str,
            str,
        ] = {}

        self._results: dict[
            str,
            PortfolioAllocationResult,
        ] = {}

        self._result_history: dict[
            str,
            list[PortfolioAllocationResult],
        ] = {}

        self._reports: dict[
            str,
            PortfolioAllocationReport,
        ] = {}

        self._report_history: list[
            PortfolioAllocationReport
        ] = []

        self._allocations: dict[
            str,
            PortfolioAllocation,
        ] = {}

        self._allocation_id_by_request: dict[
            str,
            str,
        ] = {}

        self._next_allocation_number = 1
        self._next_report_number = 1

    @property
    def request_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._requests))

    @property
    def allocation_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._allocations))

    @property
    def report_history(
        self,
    ) -> tuple[PortfolioAllocationReport, ...]:
        return tuple(self._report_history)

    def register_request(
        self,
        request: PortfolioAllocationRequest,
    ) -> PortfolioAllocationRequest:
        if not isinstance(
            request,
            PortfolioAllocationRequest,
        ):
            raise TypeError(
                "request must be a PortfolioAllocationRequest"
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
    ) -> PortfolioAllocationRequest:
        request = self.get_request(request_id)

        if request.request_id in self._results:
            raise RuntimeError(
                "started allocation requests cannot be "
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
    ) -> PortfolioAllocationRequest:
        normalized = self._normalize_identifier(
            request_id,
            "request_id",
        )

        try:
            return self._requests[normalized]
        except KeyError as exc:
            raise KeyError(
                "portfolio allocation request not found: "
                f"{normalized}"
            ) from exc

    def request_for_correlation(
        self,
        correlation_id: str,
    ) -> PortfolioAllocationRequest:
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
                "portfolio allocation request not found for "
                f"correlation_id: {normalized}"
            ) from exc

        return self._requests[request_id]

    def start_evaluation(
        self,
        request_id: str,
    ) -> PortfolioAllocationReport:
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
                "allocation evaluation start time must not "
                "be earlier than request created_at"
            )

        result = PortfolioAllocationResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=AllocationStatus.ACTIVE,
            decision=AllocationDecision.PROCEED,
            started_at=now,
            updated_at=now,
        )

        return self._record_state(
            request=request,
            result=result,
            message=(
                "Portfolio allocation evaluation started."
            ),
        )

    def attach_allocation(
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
    ) -> PortfolioAllocationReport:
        request = self.get_request(request_id)
        current = self.get_result(
            request.request_id
        )

        self._ensure_modifiable(current)

        if current.allocation is not None:
            raise RuntimeError(
                "allocation is already attached to request"
            )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "allocation generation time must not be "
                "earlier than latest result update"
            )

        allocation = PortfolioAllocation(
            allocation_id=self._next_allocation_id(),
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            strategy_id=request.strategy_id,
            portfolio_id=request.portfolio_id,
            signal_id=request.signal_id,
            symbol=request.symbol,
            action=request.action,
            direction=request.direction,
            strength=request.strength,
            target_allocation_percent=(
                request.target_allocation_percent
            ),
            confidence=request.confidence,
            generated_at=now,
            expires_at=expires_at,
            rationale=rationale,
            warnings=warnings,
            metadata=metadata,
        )

        self._allocations[
            allocation.allocation_id
        ] = allocation

        self._allocation_id_by_request[
            request.request_id
        ] = allocation.allocation_id

        result = PortfolioAllocationResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=AllocationStatus.ACTIVE,
            decision=AllocationDecision.PROCEED,
            started_at=current.started_at,
            updated_at=now,
            allocation=allocation,
            warnings=allocation.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message="Portfolio allocation generated.",
        )

    def approve_request(
        self,
        request_id: str,
        *,
        message: str = "Portfolio allocation approved.",
    ) -> PortfolioAllocationReport:
        request = self.get_request(request_id)
        current = self.get_result(
            request.request_id
        )

        self._ensure_modifiable(current)

        if current.allocation is None:
            raise RuntimeError(
                "allocation request cannot be approved "
                "without an allocation"
            )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "approval time must not be earlier "
                "than latest result update"
            )

        result = PortfolioAllocationResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=AllocationStatus.APPROVED,
            decision=AllocationDecision.APPROVE,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            allocation=current.allocation,
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
    ) -> PortfolioAllocationReport:
        return self._terminal_without_error(
            request_id=request_id,
            status=AllocationStatus.REJECTED,
            decision=AllocationDecision.REJECT,
            message=reason,
        )

    def cancel_request(
        self,
        request_id: str,
        *,
        reason: str,
    ) -> PortfolioAllocationReport:
        return self._terminal_without_error(
            request_id=request_id,
            status=AllocationStatus.CANCELLED,
            decision=AllocationDecision.CANCEL,
            message=reason,
        )

    def fail_request(
        self,
        request_id: str,
        *,
        error: str,
        retryable: bool = False,
    ) -> PortfolioAllocationReport:
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

        result = PortfolioAllocationResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=AllocationStatus.FAILED,
            decision=(
                AllocationDecision.RETRY
                if retryable
                else AllocationDecision.NO_ACTION
            ),
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            allocation=current.allocation,
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
    ) -> PortfolioAllocationResult:
        request = self.get_request(request_id)

        try:
            return self._results[
                request.request_id
            ]
        except KeyError as exc:
            raise KeyError(
                "portfolio allocation request has no result: "
                f"{request.request_id}"
            ) from exc

    def get_report(
        self,
        request_id: str,
    ) -> PortfolioAllocationReport:
        request = self.get_request(request_id)

        try:
            return self._reports[
                request.request_id
            ]
        except KeyError as exc:
            raise KeyError(
                "portfolio allocation request has no report: "
                f"{request.request_id}"
            ) from exc

    def get_allocation(
        self,
        allocation_id: str,
    ) -> PortfolioAllocation:
        normalized = self._normalize_identifier(
            allocation_id,
            "allocation_id",
        )

        try:
            return self._allocations[normalized]
        except KeyError as exc:
            raise KeyError(
                "portfolio allocation not found: "
                f"{normalized}"
            ) from exc

    def allocation_for_request(
        self,
        request_id: str,
    ) -> PortfolioAllocation:
        request = self.get_request(request_id)

        try:
            allocation_id = (
                self._allocation_id_by_request[
                    request.request_id
                ]
            )
        except KeyError as exc:
            raise KeyError(
                "portfolio allocation request has no "
                f"allocation: {request.request_id}"
            ) from exc

        return self._allocations[allocation_id]

    def results_for_request(
        self,
        request_id: str,
    ) -> tuple[PortfolioAllocationResult, ...]:
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
    ) -> tuple[PortfolioAllocationReport, ...]:
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
    ) -> tuple[PortfolioAllocationReport, ...]:
        normalized = self._normalize_identifier(
            portfolio_id,
            "portfolio_id",
        )

        return tuple(
            report
            for report in self._report_history
            if report.portfolio_id == normalized
        )

    def reports_for_signal(
        self,
        signal_id: str,
    ) -> tuple[PortfolioAllocationReport, ...]:
        normalized = self._normalize_identifier(
            signal_id,
            "signal_id",
        )

        return tuple(
            report
            for report in self._report_history
            if report.signal_id == normalized
        )

    def reports_for_symbol(
        self,
        symbol: str,
    ) -> tuple[PortfolioAllocationReport, ...]:
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
    ) -> PortfolioAllocationReport:
        if not self._report_history:
            raise KeyError(
                "portfolio allocation engine has no reports"
            )

        return self._report_history[-1]

    def _terminal_without_error(
        self,
        *,
        request_id: str,
        status: AllocationStatus,
        decision: AllocationDecision,
        message: str,
    ) -> PortfolioAllocationReport:
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

        result = PortfolioAllocationResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=status,
            decision=decision,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            allocation=current.allocation,
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
        request: PortfolioAllocationRequest,
        result: PortfolioAllocationResult,
        message: str,
    ) -> PortfolioAllocationReport:
        self._results[
            request.request_id
        ] = result

        self._result_history.setdefault(
            request.request_id,
            [],
        ).append(result)

        report = PortfolioAllocationReport(
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
                    "signal_id",
                    request.signal_id,
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
        result: PortfolioAllocationResult,
    ) -> None:
        if result.is_terminal:
            raise RuntimeError(
                "terminal allocation requests cannot be modified"
            )

    def _next_allocation_id(self) -> str:
        value = (
            "portfolio-allocation-"
            f"{self._next_allocation_number:06d}"
        )

        self._next_allocation_number += 1
        return value

    def _next_report_id(self) -> str:
        value = (
            "portfolio-allocation-report-"
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