from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from itertools import count
from typing import Callable, Iterable

from .lifecycle_models import (
    LifecycleEventSeverity,
    LifecycleEventType,
    OrderLifecycleEvent,
    TradeLifecycleRecord,
    TradeLifecycleReport,
    TradeLifecycleStage,
    TradeLifecycleStatus,
)


_ZERO = Decimal("0")

Clock = Callable[[], datetime]


class TradeLifecycleEngine:
    """Manages the complete lifecycle of one broker order."""

    _TERMINAL_STAGES = {
        TradeLifecycleStage.FILLED,
        TradeLifecycleStage.CANCELLED,
        TradeLifecycleStage.REJECTED,
        TradeLifecycleStage.EXPIRED,
        TradeLifecycleStage.FAILED,
    }

    _ALLOWED_TRANSITIONS = {
        TradeLifecycleStage.CREATED: {
            TradeLifecycleStage.SUBMITTED,
            TradeLifecycleStage.FAILED,
        },
        TradeLifecycleStage.SUBMITTED: {
            TradeLifecycleStage.ACKNOWLEDGED,
            TradeLifecycleStage.REJECTED,
            TradeLifecycleStage.CANCELLATION_REQUESTED,
            TradeLifecycleStage.EXPIRED,
            TradeLifecycleStage.FAILED,
        },
        TradeLifecycleStage.ACKNOWLEDGED: {
            TradeLifecycleStage.PARTIALLY_FILLED,
            TradeLifecycleStage.FILLED,
            TradeLifecycleStage.MODIFICATION_REQUESTED,
            TradeLifecycleStage.CANCELLATION_REQUESTED,
            TradeLifecycleStage.REJECTED,
            TradeLifecycleStage.EXPIRED,
            TradeLifecycleStage.FAILED,
        },
        TradeLifecycleStage.PARTIALLY_FILLED: {
            TradeLifecycleStage.PARTIALLY_FILLED,
            TradeLifecycleStage.FILLED,
            TradeLifecycleStage.MODIFICATION_REQUESTED,
            TradeLifecycleStage.CANCELLATION_REQUESTED,
            TradeLifecycleStage.EXPIRED,
            TradeLifecycleStage.FAILED,
        },
        TradeLifecycleStage.MODIFICATION_REQUESTED: {
            TradeLifecycleStage.MODIFIED,
            TradeLifecycleStage.CANCELLATION_REQUESTED,
            TradeLifecycleStage.FAILED,
        },
        TradeLifecycleStage.MODIFIED: {
            TradeLifecycleStage.ACKNOWLEDGED,
            TradeLifecycleStage.PARTIALLY_FILLED,
            TradeLifecycleStage.FILLED,
            TradeLifecycleStage.MODIFICATION_REQUESTED,
            TradeLifecycleStage.CANCELLATION_REQUESTED,
            TradeLifecycleStage.EXPIRED,
            TradeLifecycleStage.FAILED,
        },
        TradeLifecycleStage.CANCELLATION_REQUESTED: {
            TradeLifecycleStage.CANCELLED,
            TradeLifecycleStage.PARTIALLY_FILLED,
            TradeLifecycleStage.FILLED,
            TradeLifecycleStage.FAILED,
        },
    }

    def __init__(
        self,
        *,
        lifecycle_id: str,
        execution_id: str,
        order_id: str,
        original_quantity: Decimal,
        clock: Clock | None = None,
    ) -> None:
        self._lifecycle_id = self._normalize_identifier(
            lifecycle_id,
            "lifecycle_id",
        )
        self._execution_id = self._normalize_identifier(
            execution_id,
            "execution_id",
        )
        self._order_id = self._normalize_identifier(
            order_id,
            "order_id",
        )

        if not isinstance(original_quantity, Decimal):
            raise TypeError(
                "original_quantity must be a Decimal"
            )

        if original_quantity <= _ZERO:
            raise ValueError(
                "original_quantity must be greater than zero"
            )

        if clock is not None and not callable(clock):
            raise TypeError(
                "clock must be callable"
            )

        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

        self._created_at = self._current_time()
        self._original_quantity = original_quantity
        self._current_stage = TradeLifecycleStage.CREATED

        self._cumulative_filled_quantity = _ZERO
        self._remaining_quantity = original_quantity
        self._average_fill_price: Decimal | None = None
        self._retry_count = 0
        self._terminal = False
        self._completed_at: datetime | None = None

        self._events: list[OrderLifecycleEvent] = []
        self._warnings: list[str] = []
        self._sequence = count(1)

        self._append_event(
            event_type=LifecycleEventType.ORDER_CREATED,
            stage=TradeLifecycleStage.CREATED,
            severity=LifecycleEventSeverity.INFO,
            message="Order lifecycle was created.",
        )

    @property
    def lifecycle_id(self) -> str:
        return self._lifecycle_id

    @property
    def execution_id(self) -> str:
        return self._execution_id

    @property
    def order_id(self) -> str:
        return self._order_id

    @property
    def current_stage(self) -> TradeLifecycleStage:
        return self._current_stage

    @property
    def original_quantity(self) -> Decimal:
        return self._original_quantity

    @property
    def cumulative_filled_quantity(self) -> Decimal:
        return self._cumulative_filled_quantity

    @property
    def remaining_quantity(self) -> Decimal:
        return self._remaining_quantity

    @property
    def average_fill_price(self) -> Decimal | None:
        return self._average_fill_price

    @property
    def retry_count(self) -> int:
        return self._retry_count

    @property
    def terminal(self) -> bool:
        return self._terminal

    @property
    def events(self) -> tuple[OrderLifecycleEvent, ...]:
        return tuple(self._events)

    def submit(
        self,
        *,
        broker_status: str | None = "SUBMITTED",
    ) -> TradeLifecycleReport:
        self._transition(
            stage=TradeLifecycleStage.SUBMITTED,
            event_type=LifecycleEventType.ORDER_SUBMITTED,
            severity=LifecycleEventSeverity.INFO,
            message="Order was submitted to the broker.",
            broker_status=broker_status,
        )

        return self.snapshot()

    def acknowledge(
        self,
        *,
        broker_status: str | None = "ACKNOWLEDGED",
    ) -> TradeLifecycleReport:
        self._transition(
            stage=TradeLifecycleStage.ACKNOWLEDGED,
            event_type=LifecycleEventType.ORDER_ACKNOWLEDGED,
            severity=LifecycleEventSeverity.INFO,
            message="Broker acknowledged the order.",
            broker_status=broker_status,
        )

        return self.snapshot()

    def record_fill(
        self,
        *,
        filled_quantity: Decimal,
        fill_price: Decimal,
        broker_status: str | None = None,
    ) -> TradeLifecycleReport:
        self._ensure_open()

        if not isinstance(filled_quantity, Decimal):
            raise TypeError(
                "filled_quantity must be a Decimal"
            )

        if filled_quantity <= _ZERO:
            raise ValueError(
                "filled_quantity must be greater than zero"
            )

        if filled_quantity > self._remaining_quantity:
            raise ValueError(
                "filled_quantity must not exceed remaining_quantity"
            )

        if not isinstance(fill_price, Decimal):
            raise TypeError(
                "fill_price must be a Decimal"
            )

        if fill_price <= _ZERO:
            raise ValueError(
                "fill_price must be greater than zero"
            )

        new_cumulative = (
            self._cumulative_filled_quantity
            + filled_quantity
        )

        new_average = self._weighted_average_price(
            previous_quantity=self._cumulative_filled_quantity,
            previous_average=self._average_fill_price,
            additional_quantity=filled_quantity,
            additional_price=fill_price,
        )

        new_remaining = (
            self._original_quantity
            - new_cumulative
        )

        stage = (
            TradeLifecycleStage.FILLED
            if new_remaining == _ZERO
            else TradeLifecycleStage.PARTIALLY_FILLED
        )

        event_type = (
            LifecycleEventType.ORDER_FILLED
            if stage is TradeLifecycleStage.FILLED
            else LifecycleEventType.ORDER_PARTIALLY_FILLED
        )

        self._validate_transition(stage)

        self._cumulative_filled_quantity = new_cumulative
        self._remaining_quantity = new_remaining
        self._average_fill_price = new_average
        self._current_stage = stage

        if stage is TradeLifecycleStage.FILLED:
            self._terminal = True
            self._completed_at = self._current_time()

        self._append_event(
            event_type=event_type,
            stage=stage,
            severity=LifecycleEventSeverity.INFO,
            message=(
                "Order was fully filled."
                if stage is TradeLifecycleStage.FILLED
                else "Order was partially filled."
            ),
            filled_quantity=new_cumulative,
            remaining_quantity=new_remaining,
            average_price=new_average,
            broker_status=broker_status,
        )

        return self.snapshot()

    def request_modification(
        self,
        *,
        message: str = "Order modification was requested.",
    ) -> TradeLifecycleReport:
        self._transition(
            stage=TradeLifecycleStage.MODIFICATION_REQUESTED,
            event_type=(
                LifecycleEventType.ORDER_MODIFICATION_REQUESTED
            ),
            severity=LifecycleEventSeverity.INFO,
            message=message,
        )

        return self.snapshot()

    def confirm_modified(
        self,
        *,
        broker_status: str | None = "MODIFIED",
        attributes: Iterable[tuple[str, str]] = (),
    ) -> TradeLifecycleReport:
        self._transition(
            stage=TradeLifecycleStage.MODIFIED,
            event_type=LifecycleEventType.ORDER_MODIFIED,
            severity=LifecycleEventSeverity.INFO,
            message="Broker confirmed the order modification.",
            broker_status=broker_status,
            attributes=attributes,
        )

        return self.snapshot()

    def request_cancellation(
        self,
        *,
        message: str = "Order cancellation was requested.",
    ) -> TradeLifecycleReport:
        self._transition(
            stage=TradeLifecycleStage.CANCELLATION_REQUESTED,
            event_type=(
                LifecycleEventType.ORDER_CANCELLATION_REQUESTED
            ),
            severity=LifecycleEventSeverity.WARNING,
            message=message,
        )

        return self.snapshot()

    def cancel(
        self,
        *,
        broker_status: str | None = "CANCELLED",
    ) -> TradeLifecycleReport:
        self._terminal_transition(
            stage=TradeLifecycleStage.CANCELLED,
            event_type=LifecycleEventType.ORDER_CANCELLED,
            severity=LifecycleEventSeverity.WARNING,
            message="Order was cancelled.",
            broker_status=broker_status,
        )

        return self.snapshot()

    def reject(
        self,
        *,
        reason: str,
        broker_status: str | None = "REJECTED",
    ) -> TradeLifecycleReport:
        normalized_reason = self._normalize_message(
            reason,
            "reason",
        )

        self._terminal_transition(
            stage=TradeLifecycleStage.REJECTED,
            event_type=LifecycleEventType.ORDER_REJECTED,
            severity=LifecycleEventSeverity.ERROR,
            message=normalized_reason,
            broker_status=broker_status,
        )

        return self.snapshot()

    def expire(
        self,
        *,
        message: str = "Order expired before completion.",
        broker_status: str | None = "EXPIRED",
    ) -> TradeLifecycleReport:
        self._terminal_transition(
            stage=TradeLifecycleStage.EXPIRED,
            event_type=LifecycleEventType.ORDER_EXPIRED,
            severity=LifecycleEventSeverity.WARNING,
            message=message,
            broker_status=broker_status,
        )

        return self.snapshot()

    def fail(
        self,
        *,
        error: str,
        broker_status: str | None = "FAILED",
    ) -> TradeLifecycleReport:
        normalized_error = self._normalize_message(
            error,
            "error",
        )

        self._terminal_transition(
            stage=TradeLifecycleStage.FAILED,
            event_type=LifecycleEventType.ORDER_FAILED,
            severity=LifecycleEventSeverity.ERROR,
            message=normalized_error,
            broker_status=broker_status,
        )

        self._warnings.append(
            "Order lifecycle ended in failure."
        )

        return self.snapshot()

    def schedule_retry(
        self,
        *,
        reason: str,
    ) -> TradeLifecycleReport:
        self._ensure_open()

        normalized_reason = self._normalize_message(
            reason,
            "reason",
        )

        self._retry_count += 1

        self._append_event(
            event_type=LifecycleEventType.RETRY_SCHEDULED,
            stage=self._current_stage,
            severity=LifecycleEventSeverity.WARNING,
            message=normalized_reason,
            attributes=(
                ("retry_count", str(self._retry_count)),
            ),
        )

        return self.snapshot()

    def reconcile(
        self,
        *,
        broker_status: str,
        message: str = (
            "Internal lifecycle state was reconciled "
            "with the broker."
        ),
        attributes: Iterable[tuple[str, str]] = (),
    ) -> TradeLifecycleReport:
        self._ensure_open()

        normalized_broker_status = (
            self._normalize_message(
                broker_status,
                "broker_status",
            )
        )

        self._append_event(
            event_type=LifecycleEventType.BROKER_RECONCILED,
            stage=self._current_stage,
            severity=LifecycleEventSeverity.INFO,
            message=message,
            broker_status=normalized_broker_status,
            attributes=attributes,
        )

        return self.snapshot()

    def events_by_type(
        self,
        event_type: LifecycleEventType,
    ) -> tuple[OrderLifecycleEvent, ...]:
        if not isinstance(
            event_type,
            LifecycleEventType,
        ):
            raise TypeError(
                "event_type must be a LifecycleEventType"
            )

        return tuple(
            event
            for event in self._events
            if event.event_type is event_type
        )

    def events_by_stage(
        self,
        stage: TradeLifecycleStage,
    ) -> tuple[OrderLifecycleEvent, ...]:
        if not isinstance(
            stage,
            TradeLifecycleStage,
        ):
            raise TypeError(
                "stage must be a TradeLifecycleStage"
            )

        return tuple(
            event
            for event in self._events
            if event.stage is stage
        )

    def find_event(
        self,
        event_id: str,
    ) -> OrderLifecycleEvent | None:
        normalized_event_id = self._normalize_identifier(
            event_id,
            "event_id",
        )

        return next(
            (
                event
                for event in self._events
                if event.event_id == normalized_event_id
            ),
            None,
        )

    def snapshot(self) -> TradeLifecycleReport:
        record = TradeLifecycleRecord(
            lifecycle_id=self._lifecycle_id,
            execution_id=self._execution_id,
            order_id=self._order_id,
            original_quantity=self._original_quantity,
            current_stage=self._current_stage,
            created_at=self._created_at,
            events=tuple(self._events),
            cumulative_filled_quantity=(
                self._cumulative_filled_quantity
            ),
            remaining_quantity=self._remaining_quantity,
            average_fill_price=self._average_fill_price,
            retry_count=self._retry_count,
            terminal=self._terminal,
            completed_at=self._completed_at,
            warnings=tuple(self._warnings),
        )

        return TradeLifecycleReport(
            status=(
                TradeLifecycleStatus.COMPLETED
                if self._terminal
                else TradeLifecycleStatus.PENDING
            ),
            record=record,
            event_count=len(self._events),
            terminal=self._terminal,
            current_stage=self._current_stage,
            warnings=tuple(self._warnings),
        )

    def _transition(
        self,
        *,
        stage: TradeLifecycleStage,
        event_type: LifecycleEventType,
        severity: LifecycleEventSeverity,
        message: str,
        broker_status: str | None = None,
        attributes: Iterable[tuple[str, str]] = (),
    ) -> None:
        self._ensure_open()
        self._validate_transition(stage)

        self._current_stage = stage

        self._append_event(
            event_type=event_type,
            stage=stage,
            severity=severity,
            message=message,
            filled_quantity=(
                self._cumulative_filled_quantity
            ),
            remaining_quantity=self._remaining_quantity,
            average_price=self._average_fill_price,
            broker_status=broker_status,
            attributes=attributes,
        )

    def _terminal_transition(
        self,
        *,
        stage: TradeLifecycleStage,
        event_type: LifecycleEventType,
        severity: LifecycleEventSeverity,
        message: str,
        broker_status: str | None = None,
    ) -> None:
        self._ensure_open()
        self._validate_transition(stage)

        completed_at = self._current_time()

        self._current_stage = stage
        self._terminal = True
        self._completed_at = completed_at

        self._append_event(
            event_type=event_type,
            stage=stage,
            severity=severity,
            message=message,
            occurred_at=completed_at,
            filled_quantity=(
                self._cumulative_filled_quantity
            ),
            remaining_quantity=self._remaining_quantity,
            average_price=self._average_fill_price,
            broker_status=broker_status,
        )

    def _append_event(
        self,
        *,
        event_type: LifecycleEventType,
        stage: TradeLifecycleStage,
        severity: LifecycleEventSeverity,
        message: str,
        filled_quantity: Decimal = _ZERO,
        remaining_quantity: Decimal | None = None,
        average_price: Decimal | None = None,
        broker_status: str | None = None,
        attributes: Iterable[tuple[str, str]] = (),
        occurred_at: datetime | None = None,
    ) -> OrderLifecycleEvent:
        event_time = (
            occurred_at
            if occurred_at is not None
            else self._current_time()
        )

        if (
            self._events
            and event_time < self._events[-1].occurred_at
        ):
            raise ValueError(
                "event timestamps must be chronological"
            )

        sequence_number = next(self._sequence)

        event = OrderLifecycleEvent(
            sequence_number=sequence_number,
            event_id=(
                f"{self._lifecycle_id}-"
                f"{sequence_number:06d}"
            ),
            event_type=event_type,
            stage=stage,
            severity=severity,
            occurred_at=event_time,
            message=message,
            execution_id=self._execution_id,
            order_id=self._order_id,
            filled_quantity=filled_quantity,
            remaining_quantity=(
                self._remaining_quantity
                if remaining_quantity is None
                else remaining_quantity
            ),
            average_price=average_price,
            broker_status=broker_status,
            attributes=tuple(attributes),
        )

        self._events.append(event)

        return event

    def _validate_transition(
        self,
        target_stage: TradeLifecycleStage,
    ) -> None:
        if not isinstance(
            target_stage,
            TradeLifecycleStage,
        ):
            raise TypeError(
                "target_stage must be a TradeLifecycleStage"
            )

        allowed = self._ALLOWED_TRANSITIONS.get(
            self._current_stage,
            set(),
        )

        if target_stage not in allowed:
            raise ValueError(
                f"invalid lifecycle transition: "
                f"{self._current_stage.value} -> "
                f"{target_stage.value}"
            )

    def _ensure_open(self) -> None:
        if self._terminal:
            raise RuntimeError(
                "trade lifecycle is already terminal"
            )

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
    def _weighted_average_price(
        *,
        previous_quantity: Decimal,
        previous_average: Decimal | None,
        additional_quantity: Decimal,
        additional_price: Decimal,
    ) -> Decimal:
        if previous_quantity == _ZERO:
            return additional_price

        if previous_average is None:
            raise ValueError(
                "previous_average is required for existing fills"
            )

        total_quantity = (
            previous_quantity
            + additional_quantity
        )

        total_value = (
            previous_quantity * previous_average
            + additional_quantity * additional_price
        )

        return total_value / total_quantity

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

    @staticmethod
    def _normalize_message(
        value: str,
        field_name: str,
    ) -> str:
        return TradeLifecycleEngine._normalize_identifier(
            value,
            field_name,
        )