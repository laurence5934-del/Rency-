from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EventBusStatus(str, Enum):
    """Lifecycle status of an event-bus operation."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EventDeliveryStatus(str, Enum):
    """Delivery outcome for one event subscription."""

    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    DEAD_LETTERED = "DEAD_LETTERED"


class EventSeverity(str, Enum):
    """Severity assigned to an enterprise event."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventCategory(str, Enum):
    """Supported enterprise event categories."""

    MARKET_DATA = "MARKET_DATA"
    MARKET_REGIME = "MARKET_REGIME"
    AGENT_COORDINATION = "AGENT_COORDINATION"
    PORTFOLIO_OPTIMIZATION = "PORTFOLIO_OPTIMIZATION"
    PORTFOLIO_RISK = "PORTFOLIO_RISK"
    REBALANCING = "REBALANCING"
    PAPER_TRADING = "PAPER_TRADING"
    LIVE_TRADING = "LIVE_TRADING"
    EXECUTION = "EXECUTION"
    TRADE_LIFECYCLE = "TRADE_LIFECYCLE"
    AUDIT = "AUDIT"
    PERFORMANCE = "PERFORMANCE"
    STRATEGY_ORCHESTRATION = "STRATEGY_ORCHESTRATION"
    SYSTEM = "SYSTEM"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True, slots=True)
class EnterpriseEvent:
    """Immutable event published through the enterprise event bus."""

    event_id: str
    event_type: str
    category: EventCategory
    severity: EventSeverity
    source: str
    occurred_at: datetime
    correlation_id: str
    sequence_number: int
    payload: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )
    causation_id: str | None = None
    replayed: bool = False
    original_event_id: str | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_event_id = self._normalize_required_text(
            self.event_id,
            "event_id",
        )
        normalized_event_type = self._normalize_required_text(
            self.event_type,
            "event_type",
        )
        normalized_source = self._normalize_required_text(
            self.source,
            "source",
        )
        normalized_correlation_id = (
            self._normalize_required_text(
                self.correlation_id,
                "correlation_id",
            )
        )

        if not isinstance(self.category, EventCategory):
            raise TypeError(
                "category must be an EventCategory"
            )

        if not isinstance(self.severity, EventSeverity):
            raise TypeError(
                "severity must be an EventSeverity"
            )

        self._validate_datetime(
            self.occurred_at,
            "occurred_at",
        )

        if not isinstance(self.sequence_number, int):
            raise TypeError(
                "sequence_number must be an integer"
            )

        if self.sequence_number < 1:
            raise ValueError(
                "sequence_number must be greater than zero"
            )

        if not isinstance(self.replayed, bool):
            raise TypeError(
                "replayed must be a bool"
            )

        normalized_causation_id = self._normalize_optional_text(
            self.causation_id,
            "causation_id",
        )
        normalized_original_event_id = (
            self._normalize_optional_text(
                self.original_event_id,
                "original_event_id",
            )
        )

        if self.replayed and normalized_original_event_id is None:
            raise ValueError(
                "replayed events must include original_event_id"
            )

        if (
            not self.replayed
            and normalized_original_event_id is not None
        ):
            raise ValueError(
                "only replayed events may include original_event_id"
            )

        if normalized_original_event_id == normalized_event_id:
            raise ValueError(
                "original_event_id must differ from event_id"
            )

        normalized_payload = self._normalize_pairs(
            self.payload,
            collection_name="payload",
            key_name="payload keys",
        )

        object.__setattr__(
            self,
            "event_id",
            normalized_event_id,
        )
        object.__setattr__(
            self,
            "event_type",
            normalized_event_type,
        )
        object.__setattr__(
            self,
            "source",
            normalized_source,
        )
        object.__setattr__(
            self,
            "correlation_id",
            normalized_correlation_id,
        )
        object.__setattr__(
            self,
            "causation_id",
            normalized_causation_id,
        )
        object.__setattr__(
            self,
            "original_event_id",
            normalized_original_event_id,
        )
        object.__setattr__(
            self,
            "payload",
            normalized_payload,
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
        if not isinstance(value, datetime):
            raise TypeError(
                f"{field_name} must be a datetime"
            )

        if value.tzinfo is None:
            raise ValueError(
                f"{field_name} must be timezone-aware"
            )

    @staticmethod
    def _normalize_required_text(
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

    @staticmethod
    def _normalize_pairs(
        values: tuple[tuple[str, str], ...],
        *,
        collection_name: str,
        key_name: str,
    ) -> tuple[tuple[str, str], ...]:
        normalized: list[tuple[str, str]] = []
        seen_keys: set[str] = set()

        for item in values:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
            ):
                raise TypeError(
                    f"each {collection_name} item must be "
                    "a two-item tuple"
                )

            raw_key, raw_value = item
            key = str(raw_key).strip()
            value = str(raw_value).strip()

            if not key:
                raise ValueError(
                    f"{key_name} must not be empty"
                )

            if key in seen_keys:
                raise ValueError(
                    f"{key_name} must be unique"
                )

            seen_keys.add(key)
            normalized.append((key, value))

        return tuple(normalized)


@dataclass(frozen=True, slots=True)
class EventSubscription:
    """Immutable event-bus subscription definition."""

    subscription_id: str
    subscriber_name: str
    categories: tuple[EventCategory, ...] = field(
        default_factory=tuple
    )
    minimum_severity: EventSeverity = EventSeverity.DEBUG
    event_types: tuple[str, ...] = field(
        default_factory=tuple
    )
    enabled: bool = True
    max_delivery_attempts: int = 1
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_subscription_id = (
            EnterpriseEvent._normalize_required_text(
                self.subscription_id,
                "subscription_id",
            )
        )
        normalized_subscriber_name = (
            EnterpriseEvent._normalize_required_text(
                self.subscriber_name,
                "subscriber_name",
            )
        )

        normalized_categories = tuple(self.categories)

        for category in normalized_categories:
            if not isinstance(category, EventCategory):
                raise TypeError(
                    "every category must be an EventCategory"
                )

        if len(set(normalized_categories)) != len(
            normalized_categories
        ):
            raise ValueError(
                "subscription categories must be unique"
            )

        if not isinstance(
            self.minimum_severity,
            EventSeverity,
        ):
            raise TypeError(
                "minimum_severity must be an EventSeverity"
            )

        normalized_event_types: list[str] = []

        for event_type in self.event_types:
            normalized_event_types.append(
                EnterpriseEvent._normalize_required_text(
                    event_type,
                    "event_type",
                )
            )

        if len(set(normalized_event_types)) != len(
            normalized_event_types
        ):
            raise ValueError(
                "subscription event_types must be unique"
            )

        if not isinstance(self.enabled, bool):
            raise TypeError(
                "enabled must be a bool"
            )

        if not isinstance(
            self.max_delivery_attempts,
            int,
        ):
            raise TypeError(
                "max_delivery_attempts must be an integer"
            )

        if self.max_delivery_attempts < 1:
            raise ValueError(
                "max_delivery_attempts must be greater than zero"
            )

        normalized_metadata = EnterpriseEvent._normalize_pairs(
            self.metadata,
            collection_name="metadata",
            key_name="metadata keys",
        )

        object.__setattr__(
            self,
            "subscription_id",
            normalized_subscription_id,
        )
        object.__setattr__(
            self,
            "subscriber_name",
            normalized_subscriber_name,
        )
        object.__setattr__(
            self,
            "categories",
            normalized_categories,
        )
        object.__setattr__(
            self,
            "event_types",
            tuple(normalized_event_types),
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )


@dataclass(frozen=True, slots=True)
class EventDeliveryRecord:
    """Immutable delivery outcome for one event and subscription."""

    delivery_id: str
    event_id: str
    subscription_id: str
    subscriber_name: str
    status: EventDeliveryStatus
    attempt_number: int
    attempted_at: datetime
    completed_at: datetime | None
    message: str
    error: str | None = None
    dead_lettered: bool = False
    response_metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_delivery_id = (
            EnterpriseEvent._normalize_required_text(
                self.delivery_id,
                "delivery_id",
            )
        )
        normalized_event_id = (
            EnterpriseEvent._normalize_required_text(
                self.event_id,
                "event_id",
            )
        )
        normalized_subscription_id = (
            EnterpriseEvent._normalize_required_text(
                self.subscription_id,
                "subscription_id",
            )
        )
        normalized_subscriber_name = (
            EnterpriseEvent._normalize_required_text(
                self.subscriber_name,
                "subscriber_name",
            )
        )
        normalized_message = (
            EnterpriseEvent._normalize_required_text(
                self.message,
                "message",
            )
        )

        if not isinstance(
            self.status,
            EventDeliveryStatus,
        ):
            raise TypeError(
                "status must be an EventDeliveryStatus"
            )

        if not isinstance(self.attempt_number, int):
            raise TypeError(
                "attempt_number must be an integer"
            )

        if self.attempt_number < 1:
            raise ValueError(
                "attempt_number must be greater than zero"
            )

        EnterpriseEvent._validate_datetime(
            self.attempted_at,
            "attempted_at",
        )

        if self.completed_at is not None:
            EnterpriseEvent._validate_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.attempted_at:
                raise ValueError(
                    "completed_at must not be earlier than attempted_at"
                )

        if (
            self.status is EventDeliveryStatus.PENDING
            and self.completed_at is not None
        ):
            raise ValueError(
                "pending deliveries must not include completed_at"
            )

        if (
            self.status is not EventDeliveryStatus.PENDING
            and self.completed_at is None
        ):
            raise ValueError(
                "completed delivery outcomes must include completed_at"
            )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        failure_statuses = {
            EventDeliveryStatus.FAILED,
            EventDeliveryStatus.DEAD_LETTERED,
        }

        if self.status in failure_statuses:
            if not normalized_error:
                raise ValueError(
                    "failed deliveries must include an error"
                )
        elif normalized_error:
            raise ValueError(
                "only failed deliveries may include an error"
            )

        if not isinstance(self.dead_lettered, bool):
            raise TypeError(
                "dead_lettered must be a bool"
            )

        if (
            self.status is EventDeliveryStatus.DEAD_LETTERED
            and not self.dead_lettered
        ):
            raise ValueError(
                "dead-letter delivery status requires dead_lettered=True"
            )

        if (
            self.dead_lettered
            and self.status
            is not EventDeliveryStatus.DEAD_LETTERED
        ):
            raise ValueError(
                "dead_lettered=True requires DEAD_LETTERED status"
            )

        normalized_response_metadata = (
            EnterpriseEvent._normalize_pairs(
                self.response_metadata,
                collection_name="response_metadata",
                key_name="response metadata keys",
            )
        )

        object.__setattr__(
            self,
            "delivery_id",
            normalized_delivery_id,
        )
        object.__setattr__(
            self,
            "event_id",
            normalized_event_id,
        )
        object.__setattr__(
            self,
            "subscription_id",
            normalized_subscription_id,
        )
        object.__setattr__(
            self,
            "subscriber_name",
            normalized_subscriber_name,
        )
        object.__setattr__(
            self,
            "message",
            normalized_message,
        )
        object.__setattr__(
            self,
            "error",
            normalized_error,
        )
        object.__setattr__(
            self,
            "response_metadata",
            normalized_response_metadata,
        )


@dataclass(frozen=True, slots=True)
class EventBusReport:
    """Unified result of one event-bus publication operation."""

    status: EventBusStatus
    event: EnterpriseEvent | None
    deliveries: tuple[EventDeliveryRecord, ...] = field(
        default_factory=tuple
    )
    matched_subscriptions: int = 0
    delivered_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    dead_letter_count: int = 0
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, EventBusStatus):
            raise TypeError(
                "status must be an EventBusStatus"
            )

        if (
            self.event is not None
            and not isinstance(
                self.event,
                EnterpriseEvent,
            )
        ):
            raise TypeError(
                "event must be an EnterpriseEvent or None"
            )

        normalized_deliveries = tuple(self.deliveries)

        for delivery in normalized_deliveries:
            if not isinstance(
                delivery,
                EventDeliveryRecord,
            ):
                raise TypeError(
                    "every delivery must be an "
                    "EventDeliveryRecord"
                )

        delivery_ids = [
            delivery.delivery_id
            for delivery in normalized_deliveries
        ]

        if len(set(delivery_ids)) != len(delivery_ids):
            raise ValueError(
                "delivery_id values must be unique"
            )

        if self.event is not None:
            for delivery in normalized_deliveries:
                if delivery.event_id != self.event.event_id:
                    raise ValueError(
                        "delivery event_id must match the report event"
                    )

        for field_name in (
            "matched_subscriptions",
            "delivered_count",
            "failed_count",
            "skipped_count",
            "dead_letter_count",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, int):
                raise TypeError(
                    f"{field_name} must be an integer"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        if self.matched_subscriptions != len(
            normalized_deliveries
        ):
            raise ValueError(
                "matched_subscriptions must equal delivery count"
            )

        expected_delivered = sum(
            1
            for delivery in normalized_deliveries
            if delivery.status
            is EventDeliveryStatus.DELIVERED
        )
        expected_failed = sum(
            1
            for delivery in normalized_deliveries
            if delivery.status
            is EventDeliveryStatus.FAILED
        )
        expected_skipped = sum(
            1
            for delivery in normalized_deliveries
            if delivery.status
            is EventDeliveryStatus.SKIPPED
        )
        expected_dead_letter = sum(
            1
            for delivery in normalized_deliveries
            if delivery.status
            is EventDeliveryStatus.DEAD_LETTERED
        )

        expected_counts = {
            "delivered_count": expected_delivered,
            "failed_count": expected_failed,
            "skipped_count": expected_skipped,
            "dead_letter_count": expected_dead_letter,
        }

        for field_name, expected_value in expected_counts.items():
            if getattr(self, field_name) != expected_value:
                raise ValueError(
                    f"{field_name} must match delivery outcomes"
                )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if self.status is EventBusStatus.FAILED:
            if not normalized_error:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error:
            raise ValueError(
                "only failed reports may include an error"
            )

        if (
            self.status is EventBusStatus.COMPLETED
            and self.event is None
        ):
            raise ValueError(
                "completed reports must include an event"
            )

        if self.event is None and normalized_deliveries:
            raise ValueError(
                "reports without an event must not include deliveries"
            )

        object.__setattr__(
            self,
            "deliveries",
            normalized_deliveries,
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