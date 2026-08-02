from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")


class TradeLifecycleStatus(str, Enum):
    """Lifecycle status of a trade-lifecycle operation."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TradeLifecycleStage(str, Enum):
    """Supported order lifecycle stages."""

    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    MODIFICATION_REQUESTED = "MODIFICATION_REQUESTED"
    MODIFIED = "MODIFIED"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class LifecycleEventType(str, Enum):
    """Supported trade-lifecycle events."""

    ORDER_CREATED = "ORDER_CREATED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_ACKNOWLEDGED = "ORDER_ACKNOWLEDGED"
    ORDER_PARTIALLY_FILLED = "ORDER_PARTIALLY_FILLED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_MODIFICATION_REQUESTED = (
        "ORDER_MODIFICATION_REQUESTED"
    )
    ORDER_MODIFIED = "ORDER_MODIFIED"
    ORDER_CANCELLATION_REQUESTED = (
        "ORDER_CANCELLATION_REQUESTED"
    )
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_EXPIRED = "ORDER_EXPIRED"
    ORDER_FAILED = "ORDER_FAILED"
    BROKER_RECONCILED = "BROKER_RECONCILED"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    CUSTOM = "CUSTOM"


class LifecycleEventSeverity(str, Enum):
    """Severity attached to one lifecycle event."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class OrderLifecycleEvent:
    """One immutable event in an order lifecycle."""

    sequence_number: int
    event_id: str
    event_type: LifecycleEventType
    stage: TradeLifecycleStage
    severity: LifecycleEventSeverity
    occurred_at: datetime
    message: str
    execution_id: str
    order_id: str
    filled_quantity: Decimal = _ZERO
    remaining_quantity: Decimal = _ZERO
    average_price: Decimal | None = None
    broker_status: str | None = None
    attributes: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_event_id = self.event_id.strip()
        normalized_execution_id = self.execution_id.strip()
        normalized_order_id = self.order_id.strip()
        normalized_message = self.message.strip()

        if self.sequence_number < 1:
            raise ValueError(
                "sequence_number must be greater than zero"
            )

        if not normalized_event_id:
            raise ValueError(
                "event_id must not be empty"
            )

        if not normalized_execution_id:
            raise ValueError(
                "execution_id must not be empty"
            )

        if not normalized_order_id:
            raise ValueError(
                "order_id must not be empty"
            )

        if not isinstance(
            self.event_type,
            LifecycleEventType,
        ):
            raise TypeError(
                "event_type must be a LifecycleEventType"
            )

        if not isinstance(
            self.stage,
            TradeLifecycleStage,
        ):
            raise TypeError(
                "stage must be a TradeLifecycleStage"
            )

        if not isinstance(
            self.severity,
            LifecycleEventSeverity,
        ):
            raise TypeError(
                "severity must be a LifecycleEventSeverity"
            )

        self._validate_datetime(
            self.occurred_at,
            "occurred_at",
        )

        if not normalized_message:
            raise ValueError(
                "message must not be empty"
            )

        for field_name in (
            "filled_quantity",
            "remaining_quantity",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

            if value < _ZERO:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        if self.average_price is not None:
            if not isinstance(
                self.average_price,
                Decimal,
            ):
                raise TypeError(
                    "average_price must be a Decimal or None"
                )

            if self.average_price <= _ZERO:
                raise ValueError(
                    "average_price must be greater than zero"
                )

        if (
            self.filled_quantity > _ZERO
            and self.average_price is None
        ):
            raise ValueError(
                "filled events must include average_price"
            )

        normalized_broker_status = (
            self._normalize_optional_text(
                self.broker_status,
                "broker_status",
            )
        )

        normalized_attributes: list[
            tuple[str, str]
        ] = []

        for item in self.attributes:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
            ):
                raise TypeError(
                    "each attribute must be a two-item tuple"
                )

            name, value = item
            normalized_name = str(name).strip()
            normalized_value = str(value).strip()

            if not normalized_name:
                raise ValueError(
                    "attribute names must not be empty"
                )

            normalized_attributes.append(
                (
                    normalized_name,
                    normalized_value,
                )
            )

        object.__setattr__(
            self,
            "event_id",
            normalized_event_id,
        )
        object.__setattr__(
            self,
            "execution_id",
            normalized_execution_id,
        )
        object.__setattr__(
            self,
            "order_id",
            normalized_order_id,
        )
        object.__setattr__(
            self,
            "message",
            normalized_message,
        )
        object.__setattr__(
            self,
            "broker_status",
            normalized_broker_status,
        )
        object.__setattr__(
            self,
            "attributes",
            tuple(normalized_attributes),
        )

    @staticmethod
    def _validate_datetime(
        value: datetime,
        field_name: str,
    ) -> None:
        if not isinstance(value, datetime):
            raise TypeError(
                f"{field_name} must be a datetime"
            )

        if value.tzinfo is None:
            raise ValueError(
                f"{field_name} must be timezone-aware"
            )

    @staticmethod
    def _normalize_optional_text(
        value: str | None,
        field_name: str,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string or None"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return normalized


@dataclass(frozen=True, slots=True)
class TradeLifecycleRecord:
    """Immutable history for one submitted broker order."""

    lifecycle_id: str
    execution_id: str
    order_id: str
    original_quantity: Decimal
    current_stage: TradeLifecycleStage
    created_at: datetime
    events: tuple[OrderLifecycleEvent, ...] = field(
        default_factory=tuple
    )
    cumulative_filled_quantity: Decimal = _ZERO
    remaining_quantity: Decimal = _ZERO
    average_fill_price: Decimal | None = None
    retry_count: int = 0
    terminal: bool = False
    completed_at: datetime | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_lifecycle_id = self.lifecycle_id.strip()
        normalized_execution_id = self.execution_id.strip()
        normalized_order_id = self.order_id.strip()

        if not normalized_lifecycle_id:
            raise ValueError(
                "lifecycle_id must not be empty"
            )

        if not normalized_execution_id:
            raise ValueError(
                "execution_id must not be empty"
            )

        if not normalized_order_id:
            raise ValueError(
                "order_id must not be empty"
            )

        if not isinstance(
            self.current_stage,
            TradeLifecycleStage,
        ):
            raise TypeError(
                "current_stage must be a TradeLifecycleStage"
            )

        for field_name in (
            "original_quantity",
            "cumulative_filled_quantity",
            "remaining_quantity",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if self.original_quantity <= _ZERO:
            raise ValueError(
                "original_quantity must be greater than zero"
            )

        if self.cumulative_filled_quantity < _ZERO:
            raise ValueError(
                "cumulative_filled_quantity must not be negative"
            )

        if self.remaining_quantity < _ZERO:
            raise ValueError(
                "remaining_quantity must not be negative"
            )

        if (
            self.cumulative_filled_quantity
            > self.original_quantity
        ):
            raise ValueError(
                "cumulative_filled_quantity must not exceed "
                "original_quantity"
            )

        expected_remaining = (
            self.original_quantity
            - self.cumulative_filled_quantity
        )

        if self.remaining_quantity != expected_remaining:
            raise ValueError(
                "remaining_quantity must equal original_quantity "
                "minus cumulative_filled_quantity"
            )

        if self.average_fill_price is not None:
            if not isinstance(
                self.average_fill_price,
                Decimal,
            ):
                raise TypeError(
                    "average_fill_price must be a Decimal or None"
                )

            if self.average_fill_price <= _ZERO:
                raise ValueError(
                    "average_fill_price must be greater than zero"
                )

        if (
            self.cumulative_filled_quantity > _ZERO
            and self.average_fill_price is None
        ):
            raise ValueError(
                "filled records must include average_fill_price"
            )

        if not isinstance(self.retry_count, int):
            raise TypeError(
                "retry_count must be an integer"
            )

        if self.retry_count < 0:
            raise ValueError(
                "retry_count must not be negative"
            )

        if not isinstance(self.terminal, bool):
            raise TypeError(
                "terminal must be a bool"
            )

        self._validate_datetime(
            self.created_at,
            "created_at",
        )

        if self.completed_at is not None:
            self._validate_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.created_at:
                raise ValueError(
                    "completed_at must not be earlier than created_at"
                )

        if self.terminal and self.completed_at is None:
            raise ValueError(
                "terminal records must include completed_at"
            )

        if not self.terminal and self.completed_at is not None:
            raise ValueError(
                "only terminal records may include completed_at"
            )

        terminal_stages = {
            TradeLifecycleStage.FILLED,
            TradeLifecycleStage.CANCELLED,
            TradeLifecycleStage.REJECTED,
            TradeLifecycleStage.EXPIRED,
            TradeLifecycleStage.FAILED,
        }

        if self.terminal and self.current_stage not in terminal_stages:
            raise ValueError(
                "terminal records must use a terminal lifecycle stage"
            )

        if not self.terminal and self.current_stage in terminal_stages:
            raise ValueError(
                "terminal lifecycle stages require terminal=True"
            )

        if (
            self.current_stage is TradeLifecycleStage.FILLED
            and self.remaining_quantity != _ZERO
        ):
            raise ValueError(
                "filled records must have zero remaining_quantity"
            )

        normalized_events = tuple(self.events)

        self._validate_events(
            events=normalized_events,
            execution_id=normalized_execution_id,
            order_id=normalized_order_id,
            current_stage=self.current_stage,
        )

        object.__setattr__(
            self,
            "lifecycle_id",
            normalized_lifecycle_id,
        )
        object.__setattr__(
            self,
            "execution_id",
            normalized_execution_id,
        )
        object.__setattr__(
            self,
            "order_id",
            normalized_order_id,
        )
        object.__setattr__(
            self,
            "events",
            normalized_events,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )

    @staticmethod
    def _validate_datetime(
        value: datetime,
        field_name: str,
    ) -> None:
        OrderLifecycleEvent._validate_datetime(
            value,
            field_name,
        )

    @staticmethod
    def _validate_events(
        *,
        events: tuple[OrderLifecycleEvent, ...],
        execution_id: str,
        order_id: str,
        current_stage: TradeLifecycleStage,
    ) -> None:
        seen_event_ids: set[str] = set()
        previous_sequence = 0
        previous_time: datetime | None = None

        for event in events:
            if not isinstance(
                event,
                OrderLifecycleEvent,
            ):
                raise TypeError(
                    "every event must be an OrderLifecycleEvent"
                )

            if event.event_id in seen_event_ids:
                raise ValueError(
                    f"duplicate event_id: {event.event_id}"
                )

            if event.sequence_number <= previous_sequence:
                raise ValueError(
                    "event sequence numbers must be strictly increasing"
                )

            if (
                previous_time is not None
                and event.occurred_at < previous_time
            ):
                raise ValueError(
                    "event timestamps must be chronological"
                )

            if event.execution_id != execution_id:
                raise ValueError(
                    "event execution_id must match the lifecycle record"
                )

            if event.order_id != order_id:
                raise ValueError(
                    "event order_id must match the lifecycle record"
                )

            seen_event_ids.add(event.event_id)
            previous_sequence = event.sequence_number
            previous_time = event.occurred_at

        if events and events[-1].stage is not current_stage:
            raise ValueError(
                "current_stage must match the final event stage"
            )


@dataclass(frozen=True, slots=True)
class TradeLifecycleReport:
    """Unified report from a lifecycle operation."""

    status: TradeLifecycleStatus
    record: TradeLifecycleRecord | None
    event_count: int
    terminal: bool
    current_stage: TradeLifecycleStage | None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.status,
            TradeLifecycleStatus,
        ):
            raise TypeError(
                "status must be a TradeLifecycleStatus"
            )

        if (
            self.record is not None
            and not isinstance(
                self.record,
                TradeLifecycleRecord,
            )
        ):
            raise TypeError(
                "record must be a TradeLifecycleRecord or None"
            )

        if not isinstance(self.event_count, int):
            raise TypeError(
                "event_count must be an integer"
            )

        if self.event_count < 0:
            raise ValueError(
                "event_count must not be negative"
            )

        if not isinstance(self.terminal, bool):
            raise TypeError(
                "terminal must be a bool"
            )

        if (
            self.current_stage is not None
            and not isinstance(
                self.current_stage,
                TradeLifecycleStage,
            )
        ):
            raise TypeError(
                "current_stage must be a TradeLifecycleStage or None"
            )

        if self.record is not None:
            if self.event_count != len(self.record.events):
                raise ValueError(
                    "event_count must match the record event count"
                )

            if self.terminal is not self.record.terminal:
                raise ValueError(
                    "terminal must match the lifecycle record"
                )

            if self.current_stage is not self.record.current_stage:
                raise ValueError(
                    "current_stage must match the lifecycle record"
                )

        if self.record is None:
            if self.event_count != 0:
                raise ValueError(
                    "reports without a record must have zero events"
                )

            if self.terminal:
                raise ValueError(
                    "reports without a record cannot be terminal"
                )

            if self.current_stage is not None:
                raise ValueError(
                    "reports without a record cannot include a stage"
                )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if self.status is TradeLifecycleStatus.FAILED:
            if not normalized_error:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error:
            raise ValueError(
                "only failed reports may include an error"
            )

        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )
        object.__setattr__(
            self,
            "error",
            normalized_error,
        )