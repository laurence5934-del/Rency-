from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Callable, Iterable

from .event_models import (
    EnterpriseEvent,
    EventBusReport,
    EventBusStatus,
    EventCategory,
    EventDeliveryRecord,
    EventDeliveryStatus,
    EventSeverity,
    EventSubscription,
)


Clock = Callable[[], datetime]
Subscriber = Callable[[EnterpriseEvent], object]

_SEVERITY_ORDER = {
    EventSeverity.DEBUG: 0,
    EventSeverity.INFO: 1,
    EventSeverity.WARNING: 2,
    EventSeverity.ERROR: 3,
    EventSeverity.CRITICAL: 4,
}


class EnterpriseEventBus:
    """Synchronous enterprise event bus with replay and dead letters."""

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

        self._subscriptions: dict[
            str,
            EventSubscription,
        ] = {}

        self._subscribers: dict[
            str,
            Subscriber,
        ] = {}

        self._events: list[EnterpriseEvent] = []
        self._event_index: dict[str, EnterpriseEvent] = {}

        self._delivery_history: list[
            EventDeliveryRecord
        ] = []

        self._dead_letters: list[
            EventDeliveryRecord
        ] = []

        self._next_sequence_number = 1
        self._next_delivery_number = 1
        self._next_replay_number = 1

    @property
    def subscriptions(
        self,
    ) -> tuple[EventSubscription, ...]:
        return tuple(self._subscriptions.values())

    @property
    def events(
        self,
    ) -> tuple[EnterpriseEvent, ...]:
        return tuple(self._events)

    @property
    def delivery_history(
        self,
    ) -> tuple[EventDeliveryRecord, ...]:
        return tuple(self._delivery_history)

    @property
    def dead_letters(
        self,
    ) -> tuple[EventDeliveryRecord, ...]:
        return tuple(self._dead_letters)

    def register(
        self,
        *,
        subscription: EventSubscription,
        subscriber: Subscriber,
    ) -> EventSubscription:
        if not isinstance(
            subscription,
            EventSubscription,
        ):
            raise TypeError(
                "subscription must be an EventSubscription"
            )

        if not callable(subscriber):
            raise TypeError(
                "subscriber must be callable"
            )

        if (
            subscription.subscription_id
            in self._subscriptions
        ):
            raise ValueError(
                "subscription_id is already registered"
            )

        self._subscriptions[
            subscription.subscription_id
        ] = subscription

        self._subscribers[
            subscription.subscription_id
        ] = subscriber

        return subscription

    def unregister(
        self,
        subscription_id: str,
    ) -> EventSubscription:
        normalized_id = self._normalize_identifier(
            subscription_id,
            "subscription_id",
        )

        if normalized_id not in self._subscriptions:
            raise KeyError(
                f"subscription not found: {normalized_id}"
            )

        subscription = self._subscriptions.pop(
            normalized_id
        )
        self._subscribers.pop(normalized_id)

        return subscription

    def enable(
        self,
        subscription_id: str,
    ) -> EventSubscription:
        return self._set_enabled(
            subscription_id=subscription_id,
            enabled=True,
        )

    def disable(
        self,
        subscription_id: str,
    ) -> EventSubscription:
        return self._set_enabled(
            subscription_id=subscription_id,
            enabled=False,
        )

    def publish(
        self,
        event: EnterpriseEvent,
    ) -> EventBusReport:
        if not isinstance(event, EnterpriseEvent):
            raise TypeError(
                "event must be an EnterpriseEvent"
            )

        if event.replayed:
            raise ValueError(
                "replayed events must be created through replay()"
            )

        if event.event_id in self._event_index:
            raise ValueError(
                "event_id is already published"
            )

        if (
            event.sequence_number
            != self._next_sequence_number
        ):
            raise ValueError(
                "event sequence_number must match "
                "the next bus sequence"
            )

        self._store_event(event)

        return self._deliver_event(event)

    def replay(
        self,
        event_id: str,
    ) -> EventBusReport:
        original = self.get_event(event_id)

        replay_event_id = (
            f"{original.event_id}-replay-"
            f"{self._next_replay_number:03d}"
        )
        self._next_replay_number += 1

        replayed_event = EnterpriseEvent(
            event_id=replay_event_id,
            event_type=original.event_type,
            category=original.category,
            severity=original.severity,
            source=original.source,
            occurred_at=self._current_time(),
            correlation_id=original.correlation_id,
            sequence_number=self._next_sequence_number,
            payload=original.payload,
            causation_id=original.event_id,
            replayed=True,
            original_event_id=original.event_id,
            warnings=original.warnings,
        )

        self._store_event(replayed_event)

        return self._deliver_event(replayed_event)

    def get_event(
        self,
        event_id: str,
    ) -> EnterpriseEvent:
        normalized_id = self._normalize_identifier(
            event_id,
            "event_id",
        )

        try:
            return self._event_index[normalized_id]
        except KeyError as exc:
            raise KeyError(
                f"event not found: {normalized_id}"
            ) from exc

    def find_events(
        self,
        *,
        category: EventCategory | None = None,
        severity: EventSeverity | None = None,
        correlation_id: str | None = None,
        event_type: str | None = None,
    ) -> tuple[EnterpriseEvent, ...]:
        if (
            category is not None
            and not isinstance(category, EventCategory)
        ):
            raise TypeError(
                "category must be an EventCategory or None"
            )

        if (
            severity is not None
            and not isinstance(severity, EventSeverity)
        ):
            raise TypeError(
                "severity must be an EventSeverity or None"
            )

        normalized_correlation_id = (
            self._normalize_optional_identifier(
                correlation_id,
                "correlation_id",
            )
        )

        normalized_event_type = (
            self._normalize_optional_identifier(
                event_type,
                "event_type",
            )
        )

        return tuple(
            event
            for event in self._events
            if (
                category is None
                or event.category is category
            )
            and (
                severity is None
                or event.severity is severity
            )
            and (
                normalized_correlation_id is None
                or event.correlation_id
                == normalized_correlation_id
            )
            and (
                normalized_event_type is None
                or event.event_type
                == normalized_event_type
            )
        )

    def deliveries_for_event(
        self,
        event_id: str,
    ) -> tuple[EventDeliveryRecord, ...]:
        normalized_id = self._normalize_identifier(
            event_id,
            "event_id",
        )

        return tuple(
            delivery
            for delivery in self._delivery_history
            if delivery.event_id == normalized_id
        )

    def deliveries_for_subscription(
        self,
        subscription_id: str,
    ) -> tuple[EventDeliveryRecord, ...]:
        normalized_id = self._normalize_identifier(
            subscription_id,
            "subscription_id",
        )

        return tuple(
            delivery
            for delivery in self._delivery_history
            if delivery.subscription_id
            == normalized_id
        )

    def _deliver_event(
        self,
        event: EnterpriseEvent,
    ) -> EventBusReport:
        deliveries: list[EventDeliveryRecord] = []

        for subscription_id in sorted(
            self._subscriptions
        ):
            subscription = self._subscriptions[
                subscription_id
            ]

            if not subscription.enabled:
                deliveries.append(
                    self._skipped_delivery(
                        event=event,
                        subscription=subscription,
                        message=(
                            "Subscription is disabled."
                        ),
                    )
                )
                continue

            if not self._matches(
                event=event,
                subscription=subscription,
            ):
                continue

            delivery = self._deliver_to_subscription(
                event=event,
                subscription=subscription,
            )

            deliveries.append(delivery)

        delivered_count = sum(
            delivery.status
            is EventDeliveryStatus.DELIVERED
            for delivery in deliveries
        )

        failed_count = sum(
            delivery.status
            is EventDeliveryStatus.FAILED
            for delivery in deliveries
        )

        skipped_count = sum(
            delivery.status
            is EventDeliveryStatus.SKIPPED
            for delivery in deliveries
        )

        dead_letter_count = sum(
            delivery.status
            is EventDeliveryStatus.DEAD_LETTERED
            for delivery in deliveries
        )

        warnings: list[str] = []

        if failed_count:
            warnings.append(
                f"{failed_count} event deliveries failed."
            )

        if dead_letter_count:
            warnings.append(
                f"{dead_letter_count} event deliveries "
                "were dead-lettered."
            )

        return EventBusReport(
            status=EventBusStatus.COMPLETED,
            event=event,
            deliveries=tuple(deliveries),
            matched_subscriptions=len(deliveries),
            delivered_count=delivered_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            dead_letter_count=dead_letter_count,
            warnings=tuple(warnings),
        )

    def _deliver_to_subscription(
        self,
        *,
        event: EnterpriseEvent,
        subscription: EventSubscription,
    ) -> EventDeliveryRecord:
        subscriber = self._subscribers[
            subscription.subscription_id
        ]

        last_error: str | None = None

        for attempt_number in range(
            1,
            subscription.max_delivery_attempts + 1,
        ):
            attempted_at = self._current_time()

            try:
                response = subscriber(event)
            except Exception as exc:
                last_error = str(exc) or exc.__class__.__name__

                if (
                    attempt_number
                    < subscription.max_delivery_attempts
                ):
                    continue

                delivery = EventDeliveryRecord(
                    delivery_id=self._next_delivery_id(),
                    event_id=event.event_id,
                    subscription_id=(
                        subscription.subscription_id
                    ),
                    subscriber_name=(
                        subscription.subscriber_name
                    ),
                    status=(
                        EventDeliveryStatus.DEAD_LETTERED
                    ),
                    attempt_number=attempt_number,
                    attempted_at=attempted_at,
                    completed_at=self._current_time(),
                    message=(
                        "Delivery attempts were exhausted "
                        "and the event was dead-lettered."
                    ),
                    error=last_error,
                    dead_lettered=True,
                )

                self._record_delivery(delivery)
                self._dead_letters.append(delivery)

                return delivery

            response_metadata = (
                self._response_metadata(response)
            )

            delivery = EventDeliveryRecord(
                delivery_id=self._next_delivery_id(),
                event_id=event.event_id,
                subscription_id=(
                    subscription.subscription_id
                ),
                subscriber_name=(
                    subscription.subscriber_name
                ),
                status=EventDeliveryStatus.DELIVERED,
                attempt_number=attempt_number,
                attempted_at=attempted_at,
                completed_at=self._current_time(),
                message="Event delivered successfully.",
                response_metadata=response_metadata,
            )

            self._record_delivery(delivery)

            return delivery

        raise RuntimeError(
            "delivery attempt loop completed unexpectedly"
        )

    def _skipped_delivery(
        self,
        *,
        event: EnterpriseEvent,
        subscription: EventSubscription,
        message: str,
    ) -> EventDeliveryRecord:
        attempted_at = self._current_time()

        delivery = EventDeliveryRecord(
            delivery_id=self._next_delivery_id(),
            event_id=event.event_id,
            subscription_id=(
                subscription.subscription_id
            ),
            subscriber_name=(
                subscription.subscriber_name
            ),
            status=EventDeliveryStatus.SKIPPED,
            attempt_number=1,
            attempted_at=attempted_at,
            completed_at=self._current_time(),
            message=message,
        )

        self._record_delivery(delivery)

        return delivery

    @staticmethod
    def _matches(
        *,
        event: EnterpriseEvent,
        subscription: EventSubscription,
    ) -> bool:
        if (
            subscription.categories
            and event.category
            not in subscription.categories
        ):
            return False

        if (
            subscription.event_types
            and event.event_type
            not in subscription.event_types
        ):
            return False

        return (
            _SEVERITY_ORDER[event.severity]
            >= _SEVERITY_ORDER[
                subscription.minimum_severity
            ]
        )

    def _set_enabled(
        self,
        *,
        subscription_id: str,
        enabled: bool,
    ) -> EventSubscription:
        normalized_id = self._normalize_identifier(
            subscription_id,
            "subscription_id",
        )

        if normalized_id not in self._subscriptions:
            raise KeyError(
                f"subscription not found: {normalized_id}"
            )

        updated = replace(
            self._subscriptions[normalized_id],
            enabled=enabled,
        )

        self._subscriptions[normalized_id] = updated

        return updated

    def _store_event(
        self,
        event: EnterpriseEvent,
    ) -> None:
        self._events.append(event)
        self._event_index[event.event_id] = event
        self._next_sequence_number += 1

    def _record_delivery(
        self,
        delivery: EventDeliveryRecord,
    ) -> None:
        self._delivery_history.append(delivery)

    def _next_delivery_id(self) -> str:
        delivery_id = (
            f"delivery-{self._next_delivery_number:06d}"
        )
        self._next_delivery_number += 1
        return delivery_id

    @staticmethod
    def _response_metadata(
        response: object,
    ) -> tuple[tuple[str, str], ...]:
        if response is None:
            return ()

        if isinstance(response, dict):
            return tuple(
                sorted(
                    (
                        str(key).strip(),
                        str(value).strip(),
                    )
                    for key, value in response.items()
                )
            )

        return (
            (
                "response",
                str(response).strip(),
            ),
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
    def _normalize_optional_identifier(
        value: str | None,
        field_name: str,
    ) -> str | None:
        if value is None:
            return None

        return EnterpriseEventBus._normalize_identifier(
            value,
            field_name,
        )