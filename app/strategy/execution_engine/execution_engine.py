from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .execution_models import (
    ExecutionDecision,
    ExecutionOrder,
    ExecutionReport,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)


Clock = Callable[[], datetime]


class EnterpriseExecutionEngine:
    """
    Coordinates deterministic execution lifecycle state.

    Phase 2A Part 1 responsibilities:
    - register immutable execution requests
    - enforce request/correlation uniqueness
    - unregister requests before execution starts
    - start execution processing
    - preserve immutable result/report histories
    - generate deterministic report identifiers
    - expose request/result/report lookup APIs
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

        self._request_id_by_correlation: dict[
            str,
            str,
        ] = {}

        self._results: dict[
            str,
            ExecutionResult,
        ] = {}

        self._result_history: dict[
            str,
            list[ExecutionResult],
        ] = {}

        self._orders: dict[
            str,
            ExecutionOrder,
        ] = {}

        self._order_id_by_request: dict[
            str,
            str,
        ] = {}

        self._order_history: list[
            ExecutionOrder
        ] = []

        self._next_order_number = 1

        self._reports: dict[
            str,
            ExecutionReport,
        ] = {}

        self._report_history: list[
            ExecutionReport
        ] = []

        self._next_report_number = 1

    @property
    def request_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(self._requests)
        )
    @property
    def order_history(
            self,
    ) -> tuple[ExecutionOrder, ...]:
        return tuple(
            self._order_history
        )
    
    @property
    def report_history(
        self,
    ) -> tuple[ExecutionReport, ...]:
        return tuple(
            self._report_history
        )

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
    ) -> ExecutionRequest:
        request = self.get_request(
            request_id
        )

        if request.request_id in self._results:
            raise RuntimeError(
                "started execution requests "
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
    ) -> ExecutionRequest:
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
                "execution request not found: "
                f"{normalized}"
            ) from exc

    def request_for_correlation(
        self,
        correlation_id: str,
    ) -> ExecutionRequest:
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
                "execution request not found "
                "for correlation_id: "
                f"{normalized}"
            ) from exc

        return self._requests[
            request_id
        ]

    def start_execution(
        self,
        request_id: str,
    ) -> ExecutionReport:
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
                "execution start time must not "
                "be earlier than request created_at"
            )

        result = ExecutionResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=ExecutionStatus.PENDING,
            decision=ExecutionDecision.NO_ACTION,
            started_at=now,
            updated_at=now,
        )

        return self._record_state(
            request=request,
            result=result,
            message="Execution request received.",
        )

    def get_result(
        self,
        request_id: str,
    ) -> ExecutionResult:
        request = self.get_request(
            request_id
        )

        try:
            return self._results[
                request.request_id
            ]
        except KeyError as exc:
            raise KeyError(
                "execution request has no result: "
                f"{request.request_id}"
            ) from exc

    def get_report(
        self,
        request_id: str,
    ) -> ExecutionReport:
        request = self.get_request(
            request_id
        )

        try:
            return self._reports[
                request.request_id
            ]
        except KeyError as exc:
            raise KeyError(
                "execution request has no report: "
                f"{request.request_id}"
            ) from exc

    def results_for_request(
        self,
        request_id: str,
    ) -> tuple[ExecutionResult, ...]:
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
    ) -> ExecutionReport:
        if not self._report_history:
            raise KeyError(
                "execution engine has no reports"
            )

        return self._report_history[-1]

    def _record_state(
        self,
        *,
        request: ExecutionRequest,
        result: ExecutionResult,
        message: str,
    ) -> ExecutionReport:
        self._results[
            request.request_id
        ] = result

        self._result_history.setdefault(
            request.request_id,
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
                    "plan_id",
                    request.plan_id,
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

    def _next_order_id(self) -> str:
        value = (
            "execution-order-"
            f"{self._next_order_number:06d}"
        )

        self._next_order_number += 1

        return value
    def _next_report_id(self) -> str:
        value = (
            "execution-report-"
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

    def prepare_order(
        self,
        request_id: str,
    ) -> ExecutionReport:
        request = self.get_request(
            request_id
        )

        current = self.get_result(
            request.request_id
        )

        existing_order_id = (
            self._order_id_by_request.get(
                request.request_id
            )
        )

        if existing_order_id is not None:
            return self.get_report(
                request.request_id
            )

        if current.is_terminal:
            raise RuntimeError(
                "terminal execution requests "
                "cannot prepare an order"
            )

        if (
            current.status
            is not ExecutionStatus.PENDING
        ):
            raise RuntimeError(
                "execution request must be PENDING "
                "before order preparation"
            )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "order preparation time must not "
                "be earlier than latest result update"
            )

        order = ExecutionOrder(
            order_id=self._next_order_id(),
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            strategy_id=request.strategy_id,
            portfolio_id=request.portfolio_id,
            allocation_id=request.allocation_id,
            signal_id=request.signal_id,
            intent_id=request.intent_id,
            plan_id=request.plan_id,
            symbol=request.symbol,
            action=request.action,
            side=request.side,
            order_type=request.order_type,
            time_in_force=request.time_in_force,
            quantity=request.quantity,
            confidence=request.confidence,
            created_at=request.created_at,
            prepared_at=now,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
                       rationale=(
                "Execution order prepared from "
                "validated execution request."
            ),
            warnings=(),
            metadata=request.metadata,
        )

        self._orders[
            order.order_id
        ] = order

        self._order_id_by_request[
            request.request_id
        ] = order.order_id

        self._order_history.append(
            order
        )

        result = ExecutionResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=ExecutionStatus.READY,
            decision=ExecutionDecision.PROCEED,
            started_at=current.started_at,
            updated_at=now,
            order=order,
            warnings=current.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message="Execution order prepared.",
        )

    def get_order(
        self,
        order_id: str,
    ) -> ExecutionOrder:
        normalized = self._normalize_identifier(
            order_id,
            "order_id",
        )

        try:
            return self._orders[
                normalized
            ]
        except KeyError as exc:
            raise KeyError(
                "execution order not found: "
                f"{normalized}"
            ) from exc

    def order_for_request(
        self,
        request_id: str,
    ) -> ExecutionOrder:
        request = self.get_request(
            request_id
        )

        try:
            order_id = (
                self._order_id_by_request[
                    request.request_id
                ]
            )
        except KeyError as exc:
            raise KeyError(
                "execution request has no order: "
                f"{request.request_id}"
            ) from exc

        return self._orders[
            order_id
        ]

    def orders_for_symbol(
        self,
        symbol: str,
    ) -> tuple[ExecutionOrder, ...]:
        normalized = self._normalize_identifier(
            symbol,
            "symbol",
        )

        return tuple(
            order
            for order in self._order_history
            if order.symbol == normalized
        )

    def submit_order(
        self,
        request_id: str,
    ) -> ExecutionReport:
        request = self.get_request(
            request_id
        )

        current = self.get_result(
            request.request_id
        )

        if current.is_terminal:
            raise RuntimeError(
                "terminal execution requests "
                "cannot submit an order"
            )

        if (
            current.status
            is ExecutionStatus.SUBMITTED
        ):
            return self.get_report(
                request.request_id
            )

        if (
            current.status
            is not ExecutionStatus.READY
        ):
            raise RuntimeError(
                "execution request must be READY "
                "before order submission"
            )

        if current.order is None:
            raise RuntimeError(
                "execution request must have an "
                "order before submission"
            )

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "order submission time must not "
                "be earlier than latest result update"
            )

        result = ExecutionResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=ExecutionStatus.SUBMITTED,
            decision=ExecutionDecision.SUBMIT,
            started_at=current.started_at,
            updated_at=now,
            order=current.order,
            filled_quantity=current.filled_quantity,
            average_fill_price=(
                current.average_fill_price
            ),
            warnings=current.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message="Execution order submitted.",
        )

    def record_fill(
        self,
        request_id: str,
        *,
        fill_quantity: int,
        fill_price: float,
    ) -> ExecutionReport:
        request = self.get_request(
            request_id
        )

        current = self.get_result(
            request.request_id
        )

        if current.is_terminal:
            raise RuntimeError(
                "terminal execution requests "
                "cannot record fills"
            )

        if current.status not in (
            ExecutionStatus.SUBMITTED,
            ExecutionStatus.PARTIALLY_FILLED,
        ):
            raise RuntimeError(
                "execution request must be SUBMITTED "
                "or PARTIALLY_FILLED before recording fills"
            )

        if current.order is None:
            raise RuntimeError(
                "execution request must have an order "
                "before recording fills"
            )

        if (
            isinstance(fill_quantity, bool)
            or not isinstance(fill_quantity, int)
        ):
            raise TypeError(
                "fill_quantity must be an integer"
            )

        if fill_quantity <= 0:
            raise ValueError(
                "fill_quantity must be positive"
            )

        if (
            isinstance(fill_price, bool)
            or not isinstance(
                fill_price,
                (int, float),
            )
        ):
            raise TypeError(
                "fill_price must be a number"
            )

        fill_price = float(fill_price)

        if fill_price <= 0:
            raise ValueError(
                "fill_price must be positive"
            )

        new_filled_quantity = (
            current.filled_quantity
            + fill_quantity
        )

        if (
            new_filled_quantity
            > current.order.quantity
        ):
            raise ValueError(
                "cumulative filled quantity must not "
                "exceed order quantity"
            )

        previous_value = (
            current.filled_quantity
            * (
                current.average_fill_price
                or 0.0
            )
        )

        new_value = (
            fill_quantity
            * fill_price
        )

        average_fill_price = (
            previous_value
            + new_value
        ) / new_filled_quantity

        now = self._current_time()

        if now < current.updated_at:
            raise ValueError(
                "fill time must not be earlier "
                "than latest result update"
            )

        is_filled = (
            new_filled_quantity
            == current.order.quantity
        )

        result = ExecutionResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=(
                ExecutionStatus.FILLED
                if is_filled
                else ExecutionStatus.PARTIALLY_FILLED
            ),
            decision=(
                ExecutionDecision.NO_ACTION
                if is_filled
                else ExecutionDecision.PROCEED
            ),
            started_at=current.started_at,
            updated_at=now,
            completed_at=(
                now
                if is_filled
                else None
            ),
            order=current.order,
            filled_quantity=new_filled_quantity,
            average_fill_price=(
                average_fill_price
            ),
            warnings=current.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message=(
                "Execution order filled."
                if is_filled
                else "Execution order partially filled."
            ),
        )

    def cancel_execution(
        self,
        request_id: str,
        *,
        reason: str,
    ) -> ExecutionReport:
        return self._terminal_transition(
            request_id=request_id,
            status=ExecutionStatus.CANCELLED,
            decision=ExecutionDecision.CANCEL,
            message=reason,
        )

    def reject_execution(
        self,
        request_id: str,
        *,
        reason: str,
    ) -> ExecutionReport:
        return self._terminal_transition(
            request_id=request_id,
            status=ExecutionStatus.REJECTED,
            decision=ExecutionDecision.REJECT,
            message=reason,
        )

    def fail_execution(
        self,
        request_id: str,
        *,
        error: str,
        retryable: bool = False,
    ) -> ExecutionReport:
        request = self.get_request(
            request_id
        )

        current = self.get_result(
            request.request_id
        )

        if current.is_terminal:
            raise RuntimeError(
                "terminal execution requests "
                "cannot be modified"
            )

        if not isinstance(retryable, bool):
            raise TypeError(
                "retryable must be a bool"
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
                "terminal transition time must not "
                "be earlier than latest result update"
            )

        result = ExecutionResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=ExecutionStatus.FAILED,
            decision=(
                ExecutionDecision.RETRY
                if retryable
                else ExecutionDecision.NO_ACTION
            ),
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            order=current.order,
            filled_quantity=current.filled_quantity,
            average_fill_price=(
                current.average_fill_price
            ),
            warnings=current.warnings,
            error=normalized_error,
        )

        return self._record_state(
            request=request,
            result=result,
            message=normalized_error,
        )

    def _terminal_transition(
        self,
        *,
        request_id: str,
        status: ExecutionStatus,
        decision: ExecutionDecision,
        message: str,
    ) -> ExecutionReport:
        request = self.get_request(
            request_id
        )

        current = self.get_result(
            request.request_id
        )

        if current.is_terminal:
            raise RuntimeError(
                "terminal execution requests "
                "cannot be modified"
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
                "terminal transition time must not "
                "be earlier than latest result update"
            )

        result = ExecutionResult(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=status,
            decision=decision,
            started_at=current.started_at,
            updated_at=now,
            completed_at=now,
            order=current.order,
            filled_quantity=current.filled_quantity,
            average_fill_price=(
                current.average_fill_price
            ),
            warnings=current.warnings,
        )

        return self._record_state(
            request=request,
            result=result,
            message=normalized_message,
        )