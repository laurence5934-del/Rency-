from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable


from .order_plan_models import (
    OrderPlan,
    OrderPlanningDecision,
    OrderPlanningReport,
    OrderPlanningRequest,
    OrderPlanningResult,
    OrderPlanningStatus,
)


Clock = Callable[[], datetime]


class EnterpriseOrderPlanningEngine:
    """
    Coordinates the lifecycle of enterprise order-planning requests.

    Phase 2A Part 1 responsibilities:
    - register immutable order-planning requests
    - enforce unique request and correlation identifiers
    - unregister requests before planning begins
    - start order-planning evaluation
    - preserve immutable result/report histories
    - expose deterministic report identifiers
    - validate engine clock behavior
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
            OrderPlanningRequest,
        ] = {}

        self._request_id_by_correlation: dict[
            str,
            str,
        ] = {}

        self._results: dict[
            str,
            OrderPlanningResult,
        ] = {}

        self._result_history: dict[
            str,
            list[OrderPlanningResult],
        ] = {}

        self._reports: dict[
            str,
            OrderPlanningReport,
        ] = {}

        self._report_history: list[
            OrderPlanningReport
        ] = []

        self._plans: dict[
            str,
            OrderPlan,
        ] = {}

        self._plan_id_by_request: dict[
            str,
            str,
        ] = {}

        self._next_plan_number = 1
        self._next_report_number = 1

    @property
    def plan_ids(self) -> tuple[str, ...]:
        return tuple(
        sorted(self._plans)
    )

    @property
    def request_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(self._requests)
        )

    @property
    def report_history(
        self,
    ) -> tuple[OrderPlanningReport, ...]:
        return tuple(
            self._report_history
        )

    def register_request(
        self,
        request: OrderPlanningRequest,
    ) -> OrderPlanningRequest:
        if not isinstance(
            request,
            OrderPlanningRequest,
        ):
            raise TypeError(
                "request must be an "
                "OrderPlanningRequest"
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
    ) -> OrderPlanningRequest:
        request = self.get_request(
            request_id
        )

        if request.request_id in self._results:
            raise RuntimeError(
                "started order planning requests "
                "cannot be unregistered"
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
    ) -> OrderPlanningRequest:
        normalized = self._normalize_identifier(
            request_id,
            "request_id",
        )

        try:
            return self._requests[
                normalized
            ]
        except KeyError as exc:
            raise KeyError(
                "order planning request not found: "
                f"{normalized}"
            ) from exc

    def request_for_correlation(
        self,
        correlation_id: str,
    ) -> OrderPlanningRequest:
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
                "order planning request not found "
                "for correlation_id: "
                f"{normalized}"
            ) from exc

        return self._requests[
            request_id
        ]

    def start_planning(
        self,
        request_id: str,
    ) -> OrderPlanningReport:
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
                "order planning start time must not "
                "be earlier than request created_at"
            )

        result = OrderPlanningResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=OrderPlanningStatus.ACTIVE,
            decision=OrderPlanningDecision.PROCEED,
            started_at=now,
            updated_at=now,
        )

        return self._record_state(
            request=request,
            result=result,
            message=(
                "Order planning evaluation started."
            ),
        )

    def get_result(
        self,
        request_id: str,
    ) -> OrderPlanningResult:
        request = self.get_request(
            request_id
        )

        try:
            return self._results[
                request.request_id
            ]
        except KeyError as exc:
            raise KeyError(
                "order planning request has no result: "
                f"{request.request_id}"
            ) from exc

    def get_report(
        self,
        request_id: str,
    ) -> OrderPlanningReport:
        request = self.get_request(
            request_id
        )

        try:
            return self._reports[
                request.request_id
            ]
        except KeyError as exc:
            raise KeyError(
                "order planning request has no report: "
                f"{request.request_id}"
            ) from exc

    def results_for_request(
        self,
        request_id: str,
    ) -> tuple[OrderPlanningResult, ...]:
        request = self.get_request(
            request_id
        )

        return tuple(
            self._result_history.get(
                request.request_id,
                (),
            )
        )

    def latest_report(
        self,
    ) -> OrderPlanningReport:
        if not self._report_history:
            raise KeyError(
                "order planning engine has no reports"
            )

        return self._report_history[-1]

    def _record_state(
        self,
        *,
        request: OrderPlanningRequest,
        result: OrderPlanningResult,
        message: str,
    ) -> OrderPlanningReport:
        self._results[
            request.request_id
        ] = result

        self._result_history.setdefault(
            request.request_id,
            [],
        ).append(result)

        report = OrderPlanningReport(
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
            "intent_id",
            request.intent_id,
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
    
    def _next_plan_id(self) -> str:
        plan_id = (
            f"order-plan-{self._next_plan_number:06d}"
        )
        self._next_plan_number += 1
        return plan_id
    
    def _next_report_id(self) -> str:
        value = (
            "order-planning-report-"
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
                "clock must return a "
                "timezone-aware datetime"
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

    def attach_plan(
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
    ) -> OrderPlanningReport:
        request = self.get_request(
            request_id
        )

        current = self.get_result(
            request.request_id
        )

        if current.is_terminal:
            raise RuntimeError(
                "terminal order planning requests "
                "cannot be modified"
            )

        if current.plan is not None:
            raise RuntimeError(
                "order plan is already attached to request"
            )

        generated_at = self._current_time()

        if generated_at < current.updated_at:
            raise ValueError(
                "order plan generation time must not be "
                "earlier than latest result update"
            )

        plan = OrderPlan(
            plan_id=self._next_plan_id(),
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            strategy_id=request.strategy_id,
            portfolio_id=request.portfolio_id,
            allocation_id=request.allocation_id,
            signal_id=request.signal_id,
            intent_id=request.intent_id,
            symbol=request.symbol,
            action=request.action,
            side=request.side,
            order_type=request.order_type,
            time_in_force=request.time_in_force,
            quantity=request.quantity,
            confidence=request.confidence,
            generated_at=generated_at,
            expires_at=expires_at,
            rationale=rationale,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            warnings=warnings,
            metadata=metadata,
        )

        self._plans[
            plan.plan_id
        ] = plan

        self._plan_id_by_request[
            request.request_id
        ] = plan.plan_id

        result = OrderPlanningResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=OrderPlanningStatus.ACTIVE,
            decision=OrderPlanningDecision.PROCEED,
            started_at=current.started_at,
            updated_at=generated_at,
            plan=plan,
            warnings=plan.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message="Order plan generated.",
        )

        return self._record_state(
        request=request,
        status=OrderPlanningStatus.ACTIVE,
        decision=OrderPlanningDecision.PROCEED,
        plan=plan,
        message="Order plan generated.",
        occurred_at=generated_at,
    )

    def reports_for_signal(
        self,
        signal_id: str,
) -> tuple[OrderPlanningReport, ...]:
        signal_id = self._normalize_identifier(
        signal_id,
        "signal_id",
        )

    def get_plan(
        self,
        plan_id: str,
    ) -> OrderPlan:
        plan_id = self._normalize_identifier(
            plan_id,
            "plan_id",
        )

        try:
            return self._plans[plan_id]
        except KeyError:
            raise KeyError(
                f"order plan not found: {plan_id}"
            ) from None


    def plan_for_request(
        self,
        request_id: str,
    ) -> OrderPlan:
        request_id = self._normalize_identifier(
            request_id,
            "request_id",
        )

        # Preserve the engine's normal unknown-request
        # validation behavior.
        self.get_request(request_id)

        try:
            plan_id = self._plan_id_by_request[
                request_id
            ]
        except KeyError:
            raise KeyError(
                "order planning request has no plan"
            ) from None

        return self._plans[plan_id]


    def reports_for_strategy(
        self,
        strategy_id: str,
    ) -> tuple[OrderPlanningReport, ...]:
        strategy_id = self._normalize_identifier(
            strategy_id,
            "strategy_id",
        )

        return tuple(
            report
            for report in self._report_history
            if report.strategy_id == strategy_id
        )


    def reports_for_portfolio(
        self,
        portfolio_id: str,
    ) -> tuple[OrderPlanningReport, ...]:
        portfolio_id = self._normalize_identifier(
            portfolio_id,
            "portfolio_id",
        )

        return tuple(
            report
            for report in self._report_history
            if report.portfolio_id == portfolio_id
        )


    def reports_for_allocation(
        self,
        allocation_id: str,
    ) -> tuple[OrderPlanningReport, ...]:
        allocation_id = self._normalize_identifier(
            allocation_id,
            "allocation_id",
        )

        return tuple(
            report
            for report in self._report_history
            if report.allocation_id == allocation_id
        )


    def reports_for_signal(
        self,
        signal_id: str,
    ) -> tuple[OrderPlanningReport, ...]:
        signal_id = self._normalize_identifier(
            signal_id,
            "signal_id",
        )

        return tuple(
            report
            for report in self._report_history
            if report.signal_id == signal_id
        )


    def reports_for_intent(
        self,
        intent_id: str,
    ) -> tuple[OrderPlanningReport, ...]:
        intent_id = self._normalize_identifier(
            intent_id,
            "intent_id",
        )

        return tuple(
            report
            for report in self._report_history
            if report.intent_id == intent_id
        )


    def reports_for_symbol(
        self,
        symbol: str,
    ) -> tuple[OrderPlanningReport, ...]:
        symbol = self._normalize_identifier(
            symbol,
            "symbol",
        ).upper()

        return tuple(
            report
            for report in self._report_history
            if report.symbol == symbol
        )

    def _terminal_without_error(
        self,
        *,
        request_id: str,
        status: OrderPlanningStatus,
        decision: OrderPlanningDecision,
        message: str,
    ) -> OrderPlanningReport:
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

        result = OrderPlanningResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=status,
            decision=decision,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            plan=current.plan,
            warnings=current.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message=normalized_message,
        )
    
    @staticmethod
    def _ensure_modifiable(
        result: OrderPlanningResult,
    ) -> None:
        if result.is_terminal:
            raise RuntimeError(
                "terminal order planning requests "
                "cannot be modified"
            )

    def _next_plan_id(self) -> str:
        value = (
            "order-plan-"
            f"{self._next_plan_number:06d}"
        )

        self._next_plan_number += 1

        return value

    def approve_request(
        self,
        request_id: str,
        *,
        message: str = "Order plan approved.",
    ) -> OrderPlanningReport:
        request = self.get_request(
            request_id
        )

        current = self.get_result(
            request.request_id
        )

        self._ensure_modifiable(
            current
        )

        if current.plan is None:
            raise RuntimeError(
                "order planning request cannot be approved "
                "without a plan"
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

        result = OrderPlanningResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=OrderPlanningStatus.APPROVED,
            decision=OrderPlanningDecision.APPROVE,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            plan=current.plan,
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
    ) -> OrderPlanningReport:
        return self._terminal_without_error(
            request_id=request_id,
            status=OrderPlanningStatus.REJECTED,
            decision=OrderPlanningDecision.REJECT,
            message=reason,
        )


    def cancel_request(
        self,
        request_id: str,
        *,
        reason: str,
    ) -> OrderPlanningReport:
        return self._terminal_without_error(
            request_id=request_id,
            status=OrderPlanningStatus.CANCELLED,
            decision=OrderPlanningDecision.CANCEL,
            message=reason,
        )


    def fail_request(
        self,
        request_id: str,
        *,
        error: str,
        retryable: bool = False,
    ) -> OrderPlanningReport:
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

        if not isinstance(retryable, bool):
            raise TypeError(
                "retryable must be a bool"
            )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "terminal transition time must not be "
                "earlier than latest result update"
            )

        result = OrderPlanningResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=OrderPlanningStatus.FAILED,
            decision=(
                OrderPlanningDecision.RETRY
                if retryable
                else OrderPlanningDecision.NO_ACTION
            ),
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            plan=current.plan,
            error=normalized_error,
            warnings=current.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message=normalized_error,
        )