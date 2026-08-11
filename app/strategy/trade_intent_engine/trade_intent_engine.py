from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .trade_intent_models import (
    TradeIntent,
    TradeIntentDecision,
    TradeIntentReport,
    TradeIntentRequest,
    TradeIntentResult,
    TradeIntentStatus,
)


Clock = Callable[[], datetime]


class EnterpriseTradeIntentEngine:
    """
    Coordinates the lifecycle of enterprise trade-intent requests.

    Responsibilities:
    - register immutable trade-intent requests
    - enforce unique request and correlation identifiers
    - start trade-intent evaluation
    - generate deterministic trade intents
    - approve, reject, cancel, or fail requests
    - preserve immutable result/report histories
    - expose deterministic intent/report identifiers
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
            TradeIntentRequest,
        ] = {}

        self._request_id_by_correlation: dict[
            str,
            str,
        ] = {}

        self._results: dict[
            str,
            TradeIntentResult,
        ] = {}

        self._result_history: dict[
            str,
            list[TradeIntentResult],
        ] = {}

        self._reports: dict[
            str,
            TradeIntentReport,
        ] = {}

        self._report_history: list[
            TradeIntentReport
        ] = []

        self._intents: dict[
            str,
            TradeIntent,
        ] = {}

        self._intent_id_by_request: dict[
            str,
            str,
        ] = {}

        self._next_intent_number = 1
        self._next_report_number = 1

    @property
    def request_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._requests))

    @property
    def intent_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._intents))

    @property
    def report_history(
        self,
    ) -> tuple[TradeIntentReport, ...]:
        return tuple(self._report_history)

    def register_request(
        self,
        request: TradeIntentRequest,
    ) -> TradeIntentRequest:
        if not isinstance(
            request,
            TradeIntentRequest,
        ):
            raise TypeError(
                "request must be a TradeIntentRequest"
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

        self._requests[
            request.request_id
        ] = request

        self._request_id_by_correlation[
            request.correlation_id
        ] = request.request_id

        return request

    def unregister_request(
        self,
        request_id: str,
    ) -> TradeIntentRequest:
        request = self.get_request(request_id)

        if request.request_id in self._results:
            raise RuntimeError(
                "started trade intent requests cannot be "
                "unregistered"
            )

        self._requests.pop(
            request.request_id
        )

        self._request_id_by_correlation.pop(
            request.correlation_id,
            None,
        )

        return request

    def get_request(
        self,
        request_id: str,
    ) -> TradeIntentRequest:
        normalized = self._normalize_identifier(
            request_id,
            "request_id",
        )

        try:
            return self._requests[normalized]
        except KeyError as exc:
            raise KeyError(
                "trade intent request not found: "
                f"{normalized}"
            ) from exc

    def request_for_correlation(
        self,
        correlation_id: str,
    ) -> TradeIntentRequest:
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
                "trade intent request not found for "
                f"correlation_id: {normalized}"
            ) from exc

        return self._requests[request_id]

    def start_evaluation(
        self,
        request_id: str,
    ) -> TradeIntentReport:
        request = self.get_request(
            request_id
        )

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
                "trade intent evaluation start time must not "
                "be earlier than request created_at"
            )

        result = TradeIntentResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=TradeIntentStatus.ACTIVE,
            decision=TradeIntentDecision.PROCEED,
            started_at=now,
            updated_at=now,
        )

        return self._record_state(
            request=request,
            result=result,
            message=(
                "Trade intent evaluation started."
            ),
        )

    def attach_intent(
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
    ) -> TradeIntentReport:
        request = self.get_request(
            request_id
        )

        current = self.get_result(
            request.request_id
        )

        self._ensure_modifiable(
            current
        )

        if current.intent is not None:
            raise RuntimeError(
                "trade intent is already attached to request"
            )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "trade intent generation time must not be "
                "earlier than latest result update"
            )

        intent = TradeIntent(
            intent_id=self._next_intent_id(),
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            strategy_id=request.strategy_id,
            portfolio_id=request.portfolio_id,
            allocation_id=request.allocation_id,
            signal_id=request.signal_id,
            symbol=request.symbol,
            action=request.action,
            side=request.side,
            order_type=request.order_type,
            time_in_force=request.time_in_force,
            quantity=request.quantity,
            confidence=request.confidence,
            generated_at=now,
            expires_at=expires_at,
            rationale=rationale,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            warnings=warnings,
            metadata=metadata,
        )

        self._intents[
            intent.intent_id
        ] = intent

        self._intent_id_by_request[
            request.request_id
        ] = intent.intent_id

        result = TradeIntentResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=TradeIntentStatus.ACTIVE,
            decision=TradeIntentDecision.PROCEED,
            started_at=current.started_at,
            updated_at=now,
            intent=intent,
            warnings=intent.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message="Trade intent generated.",
        )

    def approve_request(
        self,
        request_id: str,
        *,
        message: str = "Trade intent approved.",
    ) -> TradeIntentReport:
        request = self.get_request(
            request_id
        )

        current = self.get_result(
            request.request_id
        )

        self._ensure_modifiable(
            current
        )

        if current.intent is None:
            raise RuntimeError(
                "trade intent request cannot be approved "
                "without an intent"
            )

        normalized_message = (
            self._normalize_identifier(
                message,
                "message",
            )
        )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "approval time must not be earlier "
                "than latest result update"
            )

        result = TradeIntentResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=TradeIntentStatus.APPROVED,
            decision=TradeIntentDecision.APPROVE,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            intent=current.intent,
            warnings=current.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message=normalized_message,
        )

    def reject_request(
        self,
        request_id: str,
        *,
        reason: str,
    ) -> TradeIntentReport:
        return self._terminal_without_error(
            request_id=request_id,
            status=TradeIntentStatus.REJECTED,
            decision=TradeIntentDecision.REJECT,
            message=reason,
        )

    def cancel_request(
        self,
        request_id: str,
        *,
        reason: str,
    ) -> TradeIntentReport:
        return self._terminal_without_error(
            request_id=request_id,
            status=TradeIntentStatus.CANCELLED,
            decision=TradeIntentDecision.CANCEL,
            message=reason,
        )

    def fail_request(
        self,
        request_id: str,
        *,
        error: str,
        retryable: bool = False,
    ) -> TradeIntentReport:
        if not isinstance(
            retryable,
            bool,
        ):
            raise TypeError(
                "retryable must be a bool"
            )

        request = self.get_request(
            request_id
        )

        current = self.get_result(
            request.request_id
        )

        self._ensure_modifiable(
            current
        )

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

        result = TradeIntentResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=TradeIntentStatus.FAILED,
            decision=(
                TradeIntentDecision.RETRY
                if retryable
                else TradeIntentDecision.NO_ACTION
            ),
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            intent=current.intent,
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
    ) -> TradeIntentResult:
        request = self.get_request(
            request_id
        )

        try:
            return self._results[
                request.request_id
            ]
        except KeyError as exc:
            raise KeyError(
                "trade intent request has no result: "
                f"{request.request_id}"
            ) from exc

    def get_report(
        self,
        request_id: str,
    ) -> TradeIntentReport:
        request = self.get_request(
            request_id
        )

        try:
            return self._reports[
                request.request_id
            ]
        except KeyError as exc:
            raise KeyError(
                "trade intent request has no report: "
                f"{request.request_id}"
            ) from exc

    def get_intent(
        self,
        intent_id: str,
    ) -> TradeIntent:
        normalized = self._normalize_identifier(
            intent_id,
            "intent_id",
        )

        try:
            return self._intents[
                normalized
            ]
        except KeyError as exc:
            raise KeyError(
                "trade intent not found: "
                f"{normalized}"
            ) from exc

    def intent_for_request(
        self,
        request_id: str,
    ) -> TradeIntent:
        request = self.get_request(
            request_id
        )

        try:
            intent_id = (
                self._intent_id_by_request[
                    request.request_id
                ]
            )
        except KeyError as exc:
            raise KeyError(
                "trade intent request has no intent: "
                f"{request.request_id}"
            ) from exc

        return self._intents[
            intent_id
        ]

    def results_for_request(
        self,
        request_id: str,
    ) -> tuple[TradeIntentResult, ...]:
        request = self.get_request(
            request_id
        )

        return tuple(
            self._result_history.get(
                request.request_id,
                (),
            )
        )

    def reports_for_strategy(
        self,
        strategy_id: str,
    ) -> tuple[TradeIntentReport, ...]:
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
    ) -> tuple[TradeIntentReport, ...]:
        normalized = self._normalize_identifier(
            portfolio_id,
            "portfolio_id",
        )

        return tuple(
            report
            for report in self._report_history
            if report.portfolio_id == normalized
        )

    def reports_for_allocation(
        self,
        allocation_id: str,
    ) -> tuple[TradeIntentReport, ...]:
        normalized = self._normalize_identifier(
            allocation_id,
            "allocation_id",
        )

        return tuple(
            report
            for report in self._report_history
            if report.allocation_id == normalized
        )

    def reports_for_signal(
        self,
        signal_id: str,
    ) -> tuple[TradeIntentReport, ...]:
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
    ) -> tuple[TradeIntentReport, ...]:
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
    ) -> TradeIntentReport:
        if not self._report_history:
            raise KeyError(
                "trade intent engine has no reports"
            )

        return self._report_history[-1]

    def _terminal_without_error(
        self,
        *,
        request_id: str,
        status: TradeIntentStatus,
        decision: TradeIntentDecision,
        message: str,
    ) -> TradeIntentReport:
        request = self.get_request(
            request_id
        )

        current = self.get_result(
            request.request_id
        )

        self._ensure_modifiable(
            current
        )

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

        result = TradeIntentResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=status,
            decision=decision,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            intent=current.intent,
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
        request: TradeIntentRequest,
        result: TradeIntentResult,
        message: str,
    ) -> TradeIntentReport:
        self._results[
            request.request_id
        ] = result

        self._result_history.setdefault(
            request.request_id,
            [],
        ).append(result)

        report = TradeIntentReport(
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
                    "allocation_id",
                    request.allocation_id,
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

        self._report_history.append(
            report
        )

        return report

    @staticmethod
    def _ensure_modifiable(
        result: TradeIntentResult,
    ) -> None:
        if result.is_terminal:
            raise RuntimeError(
                "terminal trade intent requests cannot be modified"
            )

    def _next_intent_id(self) -> str:
        value = (
            "trade-intent-"
            f"{self._next_intent_number:06d}"
        )

        self._next_intent_number += 1

        return value

    def _next_report_id(self) -> str:
        value = (
            "trade-intent-report-"
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
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be a string"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return normalized