from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable

from .order_models import (
    ExecutionType,
    OrderAllocation,
    OrderDecision,
    OrderExecution,
    OrderFill,
    OrderReport,
    OrderRequest,
    OrderStatus,
)


Clock = Callable[[], datetime]

_ZERO = Decimal("0")

_TERMINAL_STATUSES = {
    OrderStatus.FILLED,
    OrderStatus.REJECTED,
    OrderStatus.CANCELLED,
    OrderStatus.EXPIRED,
    OrderStatus.FAILED,
}


class EnterpriseOrderManager:
    """Maintains deterministic enterprise order lifecycles."""

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
            OrderRequest,
        ] = {}

        self._current_executions: dict[
            str,
            OrderExecution,
        ] = {}

        self._execution_history: dict[
            str,
            list[OrderExecution],
        ] = {}

        self._reports: list[
            OrderReport
        ] = []

        self._client_order_ids: set[str] = set()
        self._broker_order_ids: set[str] = set()
        self._fill_ids: set[str] = set()

        self._next_execution_number = 1
        self._next_fill_number = 1
        self._next_allocation_number = 1

    @property
    def order_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._requests))

    @property
    def report_history(
        self,
    ) -> tuple[OrderReport, ...]:
        return tuple(self._reports)

    def register_order(
        self,
        request: OrderRequest,
    ) -> OrderReport:
        if not isinstance(request, OrderRequest):
            raise TypeError(
                "request must be an OrderRequest"
            )

        if request.order_id in self._requests:
            raise ValueError(
                "order_id is already registered"
            )

        if (
            request.client_order_id
            in self._client_order_ids
        ):
            raise ValueError(
                "client_order_id is already registered"
            )

        self._requests[request.order_id] = request
        self._client_order_ids.add(
            request.client_order_id
        )

        return self._record_report(
            status=OrderStatus.CREATED,
            decision=OrderDecision.APPROVE,
            request=request,
            execution=None,
            recommendation=(
                "Order registered successfully."
            ),
        )

    def validate_order(
        self,
        order_id: str,
    ) -> OrderReport:
        request = self.get_request(order_id)

        self._require_status(
            order_id,
            allowed={
                OrderStatus.CREATED,
            },
        )

        execution = self._build_unfilled_execution(
            request=request,
            execution_type=ExecutionType.VALIDATED,
            status=OrderStatus.VALIDATED,
            message="Order validation completed.",
        )

        return self._store_execution_and_report(
            request=request,
            execution=execution,
            decision=OrderDecision.APPROVE,
            recommendation=(
                "Order may proceed to submission."
            ),
        )

    def submit_order(
        self,
        order_id: str,
    ) -> OrderReport:
        request = self.get_request(order_id)

        self._require_status(
            order_id,
            allowed={
                OrderStatus.VALIDATED,
            },
        )

        execution = self._build_unfilled_execution(
            request=request,
            execution_type=ExecutionType.SUBMITTED,
            status=OrderStatus.SUBMITTED,
            message="Order submitted to the broker.",
        )

        return self._store_execution_and_report(
            request=request,
            execution=execution,
            decision=OrderDecision.APPROVE,
            recommendation=(
                "Await broker acknowledgement."
            ),
        )

    def acknowledge_order(
        self,
        order_id: str,
        *,
        broker_order_id: str,
    ) -> OrderReport:
        request = self.get_request(order_id)

        self._require_status(
            order_id,
            allowed={
                OrderStatus.SUBMITTED,
            },
        )

        normalized_broker_order_id = (
            self._normalize_identifier(
                broker_order_id,
                "broker_order_id",
            )
        )

        if (
            normalized_broker_order_id
            in self._broker_order_ids
        ):
            raise ValueError(
                "broker_order_id is already registered"
            )

        self._broker_order_ids.add(
            normalized_broker_order_id
        )

        execution = self._build_unfilled_execution(
            request=request,
            execution_type=ExecutionType.ACKNOWLEDGED,
            status=OrderStatus.ACKNOWLEDGED,
            message="Broker acknowledged the order.",
            broker_order_id=(
                normalized_broker_order_id
            ),
        )

        return self._store_execution_and_report(
            request=request,
            execution=execution,
            decision=OrderDecision.APPROVE,
            recommendation=(
                "Monitor the acknowledged order."
            ),
        )

    def record_fill(
        self,
        order_id: str,
        *,
        quantity: Decimal,
        price: Decimal,
        commission: Decimal,
        venue: str,
        broker_execution_id: str | None = None,
        allocated_portfolio_id: str | None = None,
        allocated_account_id: str | None = None,
    ) -> OrderReport:
        request = self.get_request(order_id)
        current = self.get_execution(order_id)

        if current.status not in {
            OrderStatus.ACKNOWLEDGED,
            OrderStatus.PARTIALLY_FILLED,
        }:
            raise RuntimeError(
                "fills may only be recorded for "
                "acknowledged or partially filled orders"
            )

        self._require_decimal(
            quantity,
            "quantity",
        )
        self._require_decimal(
            price,
            "price",
        )
        self._require_decimal(
            commission,
            "commission",
        )

        if quantity <= _ZERO:
            raise ValueError(
                "quantity must be greater than zero"
            )

        if price <= _ZERO:
            raise ValueError(
                "price must be greater than zero"
            )

        if commission < _ZERO:
            raise ValueError(
                "commission must not be negative"
            )

        if quantity > current.remaining_quantity:
            raise ValueError(
                "fill quantity must not exceed "
                "remaining order quantity"
            )

        now = self._current_time()
        fill_id = self._next_fill_id()

        fill = OrderFill(
            fill_id=fill_id,
            order_id=request.order_id,
            quantity=quantity,
            price=price,
            commission=commission,
            executed_at=now,
            venue=venue,
            broker_execution_id=(
                broker_execution_id
            ),
        )

        if fill.fill_id in self._fill_ids:
            raise ValueError(
                "fill_id is already registered"
            )

        self._fill_ids.add(fill.fill_id)

        fills = current.fills + (fill,)

        allocations = current.allocations

        if allocated_portfolio_id is not None:
            allocation = OrderAllocation(
                allocation_id=(
                    self._next_allocation_id()
                ),
                fill_id=fill.fill_id,
                order_id=request.order_id,
                portfolio_id=(
                    self._normalize_identifier(
                        allocated_portfolio_id,
                        "allocated_portfolio_id",
                    )
                ),
                quantity=quantity,
                allocated_at=now,
                account_id=(
                    allocated_account_id
                ),
            )

            allocations = allocations + (
                allocation,
            )

        filled_quantity = sum(
            (
                item.quantity
                for item in fills
            ),
            _ZERO,
        )

        remaining_quantity = (
            request.quantity - filled_quantity
        )

        weighted_value = sum(
            (
                item.quantity * item.price
                for item in fills
            ),
            _ZERO,
        )

        average_fill_price = (
            weighted_value / filled_quantity
        )

        if remaining_quantity == _ZERO:
            status = OrderStatus.FILLED
            execution_type = ExecutionType.FILL
            message = "Order completely filled."
            recommendation = (
                "Reconcile the completed order "
                "with the portfolio."
            )
        else:
            status = OrderStatus.PARTIALLY_FILLED
            execution_type = (
                ExecutionType.PARTIAL_FILL
            )
            message = "Order partially filled."
            recommendation = (
                "Continue monitoring the remaining "
                "order quantity."
            )

        execution = OrderExecution(
            execution_id=self._next_execution_id(),
            order_id=request.order_id,
            execution_type=execution_type,
            status=status,
            requested_quantity=request.quantity,
            filled_quantity=filled_quantity,
            remaining_quantity=remaining_quantity,
            occurred_at=now,
            message=message,
            fills=fills,
            allocations=allocations,
            average_fill_price=average_fill_price,
            broker_order_id=(
                current.broker_order_id
            ),
        )

        return self._store_execution_and_report(
            request=request,
            execution=execution,
            decision=OrderDecision.APPROVE,
            recommendation=recommendation,
        )

    def request_cancellation(
        self,
        order_id: str,
    ) -> OrderReport:
        request = self.get_request(order_id)
        current = self.get_execution(order_id)

        if current.status not in {
            OrderStatus.SUBMITTED,
            OrderStatus.ACKNOWLEDGED,
            OrderStatus.PARTIALLY_FILLED,
        }:
            raise RuntimeError(
                "order cannot enter cancellation "
                "from its current status"
            )

        execution = OrderExecution(
            execution_id=self._next_execution_id(),
            order_id=request.order_id,
            execution_type=(
                ExecutionType.CANCEL_REQUESTED
            ),
            status=OrderStatus.CANCEL_PENDING,
            requested_quantity=request.quantity,
            filled_quantity=(
                current.filled_quantity
            ),
            remaining_quantity=(
                current.remaining_quantity
            ),
            occurred_at=self._current_time(),
            message="Order cancellation requested.",
            fills=current.fills,
            allocations=current.allocations,
            average_fill_price=(
                current.average_fill_price
            ),
            broker_order_id=(
                current.broker_order_id
            ),
        )

        return self._store_execution_and_report(
            request=request,
            execution=execution,
            decision=OrderDecision.CANCEL,
            recommendation=(
                "Await broker cancellation confirmation."
            ),
        )

    def confirm_cancellation(
        self,
        order_id: str,
    ) -> OrderReport:
        request = self.get_request(order_id)
        current = self.get_execution(order_id)

        if (
            current.status
            is not OrderStatus.CANCEL_PENDING
        ):
            raise RuntimeError(
                "only cancellation-pending orders "
                "may be cancelled"
            )

        execution = OrderExecution(
            execution_id=self._next_execution_id(),
            order_id=request.order_id,
            execution_type=ExecutionType.CANCELLED,
            status=OrderStatus.CANCELLED,
            requested_quantity=request.quantity,
            filled_quantity=(
                current.filled_quantity
            ),
            remaining_quantity=(
                current.remaining_quantity
            ),
            occurred_at=self._current_time(),
            message="Broker confirmed order cancellation.",
            fills=current.fills,
            allocations=current.allocations,
            average_fill_price=(
                current.average_fill_price
            ),
            broker_order_id=(
                current.broker_order_id
            ),
        )

        return self._store_execution_and_report(
            request=request,
            execution=execution,
            decision=OrderDecision.CANCEL,
            recommendation=(
                "No further execution is permitted."
            ),
        )

    def reject_order(
        self,
        order_id: str,
        *,
        error: str,
    ) -> OrderReport:
        request = self.get_request(order_id)

        current = self._current_executions.get(
            request.order_id
        )

        if (
            current is not None
            and current.status in _TERMINAL_STATUSES
        ):
            raise RuntimeError(
                "order is already terminal"
            )

        normalized_error = (
            self._normalize_identifier(
                error,
                "error",
            )
        )

        filled_quantity = (
            current.filled_quantity
            if current is not None
            else _ZERO
        )

        remaining_quantity = (
            current.remaining_quantity
            if current is not None
            else request.quantity
        )

        execution = OrderExecution(
            execution_id=self._next_execution_id(),
            order_id=request.order_id,
            execution_type=ExecutionType.REJECTED,
            status=OrderStatus.REJECTED,
            requested_quantity=request.quantity,
            filled_quantity=filled_quantity,
            remaining_quantity=remaining_quantity,
            occurred_at=self._current_time(),
            message="Order rejected.",
            fills=(
                current.fills
                if current is not None
                else ()
            ),
            allocations=(
                current.allocations
                if current is not None
                else ()
            ),
            average_fill_price=(
                current.average_fill_price
                if current is not None
                else None
            ),
            broker_order_id=(
                current.broker_order_id
                if current is not None
                else None
            ),
            error=normalized_error,
        )

        return self._store_execution_and_report(
            request=request,
            execution=execution,
            decision=OrderDecision.REJECT,
            recommendation=(
                "Correct the rejection reason "
                "before resubmission."
            ),
            error=normalized_error,
        )

    def fail_order(
        self,
        order_id: str,
        *,
        error: str,
    ) -> OrderReport:
        request = self.get_request(order_id)

        current = self._current_executions.get(
            request.order_id
        )

        if (
            current is not None
            and current.status in _TERMINAL_STATUSES
        ):
            raise RuntimeError(
                "order is already terminal"
            )

        normalized_error = (
            self._normalize_identifier(
                error,
                "error",
            )
        )

        execution = OrderExecution(
            execution_id=self._next_execution_id(),
            order_id=request.order_id,
            execution_type=ExecutionType.FAILED,
            status=OrderStatus.FAILED,
            requested_quantity=request.quantity,
            filled_quantity=(
                current.filled_quantity
                if current is not None
                else _ZERO
            ),
            remaining_quantity=(
                current.remaining_quantity
                if current is not None
                else request.quantity
            ),
            occurred_at=self._current_time(),
            message="Order processing failed.",
            fills=(
                current.fills
                if current is not None
                else ()
            ),
            allocations=(
                current.allocations
                if current is not None
                else ()
            ),
            average_fill_price=(
                current.average_fill_price
                if current is not None
                else None
            ),
            broker_order_id=(
                current.broker_order_id
                if current is not None
                else None
            ),
            error=normalized_error,
        )

        return self._store_execution_and_report(
            request=request,
            execution=execution,
            decision=OrderDecision.REJECT,
            recommendation=(
                "Investigate the failure before "
                "retrying the order."
            ),
            error=normalized_error,
        )

    def expire_order(
        self,
        order_id: str,
    ) -> OrderReport:
        request = self.get_request(order_id)
        current = self.get_execution(order_id)

        if current.status in _TERMINAL_STATUSES:
            raise RuntimeError(
                "order is already terminal"
            )

        execution = OrderExecution(
            execution_id=self._next_execution_id(),
            order_id=request.order_id,
            execution_type=ExecutionType.EXPIRED,
            status=OrderStatus.EXPIRED,
            requested_quantity=request.quantity,
            filled_quantity=(
                current.filled_quantity
            ),
            remaining_quantity=(
                current.remaining_quantity
            ),
            occurred_at=self._current_time(),
            message="Order expired.",
            fills=current.fills,
            allocations=current.allocations,
            average_fill_price=(
                current.average_fill_price
            ),
            broker_order_id=(
                current.broker_order_id
            ),
        )

        return self._store_execution_and_report(
            request=request,
            execution=execution,
            decision=OrderDecision.NO_ACTION,
            recommendation=(
                "Create a new order if execution "
                "is still required."
            ),
        )

    def get_request(
        self,
        order_id: str,
    ) -> OrderRequest:
        normalized_order_id = (
            self._normalize_identifier(
                order_id,
                "order_id",
            )
        )

        try:
            return self._requests[
                normalized_order_id
            ]
        except KeyError as exc:
            raise KeyError(
                "order not found: "
                f"{normalized_order_id}"
            ) from exc

    def get_execution(
        self,
        order_id: str,
    ) -> OrderExecution:
        request = self.get_request(order_id)

        try:
            return self._current_executions[
                request.order_id
            ]
        except KeyError as exc:
            raise KeyError(
                "order has no execution state: "
                f"{request.order_id}"
            ) from exc

    def get_report(
        self,
        order_id: str,
    ) -> OrderReport:
        request = self.get_request(order_id)

        for report in reversed(self._reports):
            if (
                report.request.order_id
                == request.order_id
            ):
                return report

        raise KeyError(
            "order has no report: "
            f"{request.order_id}"
        )

    def executions_for_order(
        self,
        order_id: str,
    ) -> tuple[OrderExecution, ...]:
        request = self.get_request(order_id)

        return tuple(
            self._execution_history.get(
                request.order_id,
                (),
            )
        )

    def reports_for_order(
        self,
        order_id: str,
    ) -> tuple[OrderReport, ...]:
        request = self.get_request(order_id)

        return tuple(
            report
            for report in self._reports
            if (
                report.request.order_id
                == request.order_id
            )
        )

    def _require_status(
        self,
        order_id: str,
        *,
        allowed: set[OrderStatus],
    ) -> None:
        current = self._current_executions.get(
            order_id
        )

        effective_status = (
            current.status
            if current is not None
            else OrderStatus.CREATED
        )

        if effective_status not in allowed:
            raise RuntimeError(
                "order transition is not permitted "
                f"from {effective_status.value}"
            )

    def _build_unfilled_execution(
        self,
        *,
        request: OrderRequest,
        execution_type: ExecutionType,
        status: OrderStatus,
        message: str,
        broker_order_id: str | None = None,
    ) -> OrderExecution:
        return OrderExecution(
            execution_id=self._next_execution_id(),
            order_id=request.order_id,
            execution_type=execution_type,
            status=status,
            requested_quantity=request.quantity,
            filled_quantity=_ZERO,
            remaining_quantity=request.quantity,
            occurred_at=self._current_time(),
            message=message,
            broker_order_id=broker_order_id,
        )

    def _store_execution_and_report(
        self,
        *,
        request: OrderRequest,
        execution: OrderExecution,
        decision: OrderDecision,
        recommendation: str,
        error: str | None = None,
    ) -> OrderReport:
        self._current_executions[
            request.order_id
        ] = execution

        self._execution_history.setdefault(
            request.order_id,
            [],
        ).append(execution)

        return self._record_report(
            status=execution.status,
            decision=decision,
            request=request,
            execution=execution,
            recommendation=recommendation,
            error=error,
        )

    def _record_report(
        self,
        *,
        status: OrderStatus,
        decision: OrderDecision,
        request: OrderRequest,
        execution: OrderExecution | None,
        recommendation: str,
        error: str | None = None,
    ) -> OrderReport:
        report = OrderReport(
            status=status,
            decision=decision,
            request=request,
            execution=execution,
            recommendation=recommendation,
            reported_at=self._current_time(),
            error=error,
        )

        self._reports.append(report)
        return report

    def _next_execution_id(self) -> str:
        value = (
            f"execution-"
            f"{self._next_execution_number:06d}"
        )
        self._next_execution_number += 1
        return value

    def _next_fill_id(self) -> str:
        value = (
            f"fill-"
            f"{self._next_fill_number:06d}"
        )
        self._next_fill_number += 1
        return value

    def _next_allocation_id(self) -> str:
        value = (
            f"allocation-"
            f"{self._next_allocation_number:06d}"
        )
        self._next_allocation_number += 1
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
    def _require_decimal(
        value: Decimal,
        field_name: str,
    ) -> None:
        if not isinstance(value, Decimal):
            raise TypeError(
                f"{field_name} must be a Decimal"
            )

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