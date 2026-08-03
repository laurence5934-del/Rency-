from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.event_bus.event_bus import (
    EnterpriseEventBus,
)
from app.strategy.event_bus.event_models import (
    EnterpriseEvent,
    EventBusStatus,
    EventCategory,
    EventDeliveryStatus,
    EventSeverity,
    EventSubscription,
)


NOW = datetime(
    2026,
    8,
    3,
    16,
    0,
    tzinfo=timezone.utc,
)


class IncrementingClock:
    def __init__(self) -> None:
        self.value = NOW

    def __call__(self) -> datetime:
        current = self.value
        self.value += timedelta(seconds=1)
        return current


def event(
    *,
    event_id: str = "event-001",
    sequence_number: int = 1,
    category: EventCategory = (
        EventCategory.PORTFOLIO_RISK
    ),
    severity: EventSeverity = EventSeverity.INFO,
    event_type: str = "portfolio.risk.completed",
) -> EnterpriseEvent:
    return EnterpriseEvent(
        event_id=event_id,
        event_type=event_type,
        category=category,
        severity=severity,
        source="portfolio-risk-manager",
        occurred_at=NOW,
        correlation_id="correlation-001",
        sequence_number=sequence_number,
        payload=(
            ("decision", "APPROVE"),
        ),
    )


def subscription(
    subscription_id: str = "subscription-001",
    *,
    subscriber_name: str = "risk-dashboard",
    categories=(
        EventCategory.PORTFOLIO_RISK,
    ),
    minimum_severity: EventSeverity = EventSeverity.INFO,
    event_types=(
        "portfolio.risk.completed",
    ),
    enabled: bool = True,
    max_delivery_attempts: int = 1,
) -> EventSubscription:
    return EventSubscription(
        subscription_id=subscription_id,
        subscriber_name=subscriber_name,
        categories=tuple(categories),
        minimum_severity=minimum_severity,
        event_types=tuple(event_types),
        enabled=enabled,
        max_delivery_attempts=max_delivery_attempts,
    )


def bus() -> EnterpriseEventBus:
    return EnterpriseEventBus(
        clock=IncrementingClock(),
    )


def test_register_subscription() -> None:
    value = bus()

    registered = value.register(
        subscription=subscription(),
        subscriber=lambda published: None,
    )

    assert registered.subscription_id == "subscription-001"
    assert value.subscriptions == (registered,)


def test_duplicate_subscription_is_rejected() -> None:
    value = bus()
    item = subscription()

    value.register(
        subscription=item,
        subscriber=lambda published: None,
    )

    with pytest.raises(
        ValueError,
        match="subscription_id is already registered",
    ):
        value.register(
            subscription=item,
            subscriber=lambda published: None,
        )


def test_subscription_type_is_validated() -> None:
    with pytest.raises(
        TypeError,
        match="subscription must be an EventSubscription",
    ):
        bus().register(
            subscription=object(),
            subscriber=lambda published: None,
        )


def test_subscriber_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="subscriber must be callable",
    ):
        bus().register(
            subscription=subscription(),
            subscriber=object(),
        )


def test_unregister_subscription() -> None:
    value = bus()

    value.register(
        subscription=subscription(),
        subscriber=lambda published: None,
    )

    removed = value.unregister("subscription-001")

    assert removed.subscription_id == "subscription-001"
    assert value.subscriptions == ()


def test_unregister_unknown_subscription() -> None:
    with pytest.raises(
        KeyError,
        match="subscription not found",
    ):
        bus().unregister("missing")


def test_disable_subscription() -> None:
    value = bus()

    value.register(
        subscription=subscription(),
        subscriber=lambda published: None,
    )

    disabled = value.disable("subscription-001")

    assert disabled.enabled is False
    assert value.subscriptions[0].enabled is False


def test_enable_subscription() -> None:
    value = bus()

    value.register(
        subscription=subscription(
            enabled=False,
        ),
        subscriber=lambda published: None,
    )

    enabled = value.enable("subscription-001")

    assert enabled.enabled is True
    assert value.subscriptions[0].enabled is True


def test_enable_unknown_subscription() -> None:
    with pytest.raises(
        KeyError,
        match="subscription not found",
    ):
        bus().enable("missing")


def test_disable_unknown_subscription() -> None:
    with pytest.raises(
        KeyError,
        match="subscription not found",
    ):
        bus().disable("missing")


def test_publish_delivers_event() -> None:
    received: list[EnterpriseEvent] = []
    value = bus()

    value.register(
        subscription=subscription(),
        subscriber=received.append,
    )

    published = event()
    report = value.publish(published)

    assert report.status is EventBusStatus.COMPLETED
    assert report.delivered_count == 1
    assert report.matched_subscriptions == 1
    assert received == [published]


def test_publish_requires_enterprise_event() -> None:
    with pytest.raises(
        TypeError,
        match="event must be an EnterpriseEvent",
    ):
        bus().publish(object())


def test_published_event_is_stored() -> None:
    value = bus()
    published = event()

    value.publish(published)

    assert value.events == (published,)
    assert value.get_event("event-001") == published


def test_duplicate_event_id_is_rejected() -> None:
    value = bus()
    value.publish(event())

    with pytest.raises(
        ValueError,
        match="event_id is already published",
    ):
        value.publish(event())


def test_sequence_number_must_match_bus_sequence() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "event sequence_number must match "
            "the next bus sequence"
        ),
    ):
        bus().publish(
            event(sequence_number=2)
        )


def test_category_filter() -> None:
    value = bus()

    value.register(
        subscription=subscription(
            categories=(EventCategory.EXECUTION,),
        ),
        subscriber=lambda published: None,
    )

    report = value.publish(event())

    assert report.matched_subscriptions == 0
    assert report.delivered_count == 0


def test_event_type_filter() -> None:
    value = bus()

    value.register(
        subscription=subscription(
            event_types=("execution.completed",),
        ),
        subscriber=lambda published: None,
    )

    report = value.publish(event())

    assert report.matched_subscriptions == 0


def test_severity_filter() -> None:
    value = bus()

    value.register(
        subscription=subscription(
            minimum_severity=EventSeverity.ERROR,
        ),
        subscriber=lambda published: None,
    )

    report = value.publish(
        event(severity=EventSeverity.WARNING)
    )

    assert report.matched_subscriptions == 0


def test_severity_at_threshold_is_delivered() -> None:
    value = bus()

    value.register(
        subscription=subscription(
            minimum_severity=EventSeverity.WARNING,
        ),
        subscriber=lambda published: None,
    )

    report = value.publish(
        event(severity=EventSeverity.WARNING)
    )

    assert report.delivered_count == 1


def test_severity_above_threshold_is_delivered() -> None:
    value = bus()

    value.register(
        subscription=subscription(
            minimum_severity=EventSeverity.WARNING,
        ),
        subscriber=lambda published: None,
    )

    report = value.publish(
        event(severity=EventSeverity.CRITICAL)
    )

    assert report.delivered_count == 1


def test_empty_category_and_type_filters_match_all() -> None:
    value = bus()

    value.register(
        subscription=subscription(
            categories=(),
            event_types=(),
        ),
        subscriber=lambda published: None,
    )

    report = value.publish(
        event(
            category=EventCategory.EXECUTION,
            event_type="execution.completed",
        )
    )

    assert report.delivered_count == 1


def test_disabled_subscription_is_skipped() -> None:
    value = bus()

    value.register(
        subscription=subscription(
            enabled=False,
        ),
        subscriber=lambda published: None,
    )

    report = value.publish(event())

    assert report.skipped_count == 1
    assert report.matched_subscriptions == 1
    assert (
        report.deliveries[0].status
        is EventDeliveryStatus.SKIPPED
    )


def test_disabled_subscriber_is_not_called() -> None:
    calls = 0
    value = bus()

    def subscriber(
        published: EnterpriseEvent,
    ) -> None:
        nonlocal calls
        calls += 1

    value.register(
        subscription=subscription(
            enabled=False,
        ),
        subscriber=subscriber,
    )

    value.publish(event())

    assert calls == 0


def test_subscriber_response_metadata_is_recorded() -> None:
    value = bus()

    value.register(
        subscription=subscription(),
        subscriber=lambda published: {
            "accepted": True,
            "component": "dashboard",
        },
    )

    report = value.publish(event())

    assert report.deliveries[0].response_metadata == (
        ("accepted", "True"),
        ("component", "dashboard"),
    )


def test_non_mapping_response_is_recorded() -> None:
    value = bus()

    value.register(
        subscription=subscription(),
        subscriber=lambda published: "accepted",
    )

    report = value.publish(event())

    assert report.deliveries[0].response_metadata == (
        ("response", "accepted"),
    )


def test_none_response_has_no_metadata() -> None:
    value = bus()

    value.register(
        subscription=subscription(),
        subscriber=lambda published: None,
    )

    report = value.publish(event())

    assert report.deliveries[0].response_metadata == ()


def test_subscriber_failure_is_dead_lettered() -> None:
    value = bus()

    def failing_subscriber(
        published: EnterpriseEvent,
    ) -> None:
        raise RuntimeError("subscriber unavailable")

    value.register(
        subscription=subscription(
            max_delivery_attempts=1,
        ),
        subscriber=failing_subscriber,
    )

    report = value.publish(event())

    assert report.dead_letter_count == 1
    assert report.failed_count == 0
    assert len(value.dead_letters) == 1
    assert (
        report.deliveries[0].status
        is EventDeliveryStatus.DEAD_LETTERED
    )
    assert (
        report.deliveries[0].error
        == "subscriber unavailable"
    )


def test_subscriber_is_retried() -> None:
    value = bus()
    attempts = 0

    def flaky_subscriber(
        published: EnterpriseEvent,
    ) -> None:
        nonlocal attempts
        attempts += 1

        if attempts < 3:
            raise RuntimeError("temporary failure")

    value.register(
        subscription=subscription(
            max_delivery_attempts=3,
        ),
        subscriber=flaky_subscriber,
    )

    report = value.publish(event())

    assert attempts == 3
    assert report.delivered_count == 1
    assert report.dead_letter_count == 0
    assert report.deliveries[0].attempt_number == 3


def test_retry_exhaustion_uses_final_attempt_number() -> None:
    value = bus()
    attempts = 0

    def failing_subscriber(
        published: EnterpriseEvent,
    ) -> None:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("still unavailable")

    value.register(
        subscription=subscription(
            max_delivery_attempts=3,
        ),
        subscriber=failing_subscriber,
    )

    report = value.publish(event())

    assert attempts == 3
    assert report.dead_letter_count == 1
    assert report.deliveries[0].attempt_number == 3


def test_failure_isolated_from_other_subscribers() -> None:
    value = bus()
    received: list[str] = []

    def failing_subscriber(
        published: EnterpriseEvent,
    ) -> None:
        raise RuntimeError("failure")

    value.register(
        subscription=subscription(
            "subscription-001",
            subscriber_name="broken",
        ),
        subscriber=failing_subscriber,
    )

    value.register(
        subscription=subscription(
            "subscription-002",
            subscriber_name="healthy",
        ),
        subscriber=lambda published: received.append(
            published.event_id
        ),
    )

    report = value.publish(event())

    assert report.dead_letter_count == 1
    assert report.delivered_count == 1
    assert received == ["event-001"]


def test_delivery_order_is_deterministic() -> None:
    value = bus()
    delivery_order: list[str] = []

    value.register(
        subscription=subscription(
            "subscription-b",
            subscriber_name="subscriber-b",
        ),
        subscriber=lambda published: (
            delivery_order.append("b")
        ),
    )

    value.register(
        subscription=subscription(
            "subscription-a",
            subscriber_name="subscriber-a",
        ),
        subscriber=lambda published: (
            delivery_order.append("a")
        ),
    )

    value.publish(event())

    assert delivery_order == ["a", "b"]


def test_get_unknown_event() -> None:
    with pytest.raises(
        KeyError,
        match="event not found",
    ):
        bus().get_event("missing")


def test_get_event_normalizes_identifier() -> None:
    value = bus()
    published = event()

    value.publish(published)

    assert value.get_event("  event-001  ") == published


def test_replay_event() -> None:
    value = bus()
    received: list[EnterpriseEvent] = []

    value.register(
        subscription=subscription(),
        subscriber=received.append,
    )

    value.publish(event())
    report = value.replay("event-001")

    assert report.event is not None
    assert report.event.replayed is True
    assert report.event.original_event_id == "event-001"
    assert report.event.causation_id == "event-001"
    assert report.event.sequence_number == 2
    assert len(received) == 2


def test_replay_event_id_is_deterministic() -> None:
    value = bus()

    value.publish(event())

    first = value.replay("event-001")
    second = value.replay("event-001")

    assert first.event is not None
    assert second.event is not None

    assert first.event.event_id == (
        "event-001-replay-001"
    )
    assert second.event.event_id == (
        "event-001-replay-002"
    )


def test_replay_unknown_event_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="event not found",
    ):
        bus().replay("missing")


def test_publish_replayed_event_is_rejected() -> None:
    replayed = EnterpriseEvent(
        event_id="event-replay",
        event_type="portfolio.risk.completed",
        category=EventCategory.PORTFOLIO_RISK,
        severity=EventSeverity.INFO,
        source="portfolio-risk-manager",
        occurred_at=NOW,
        correlation_id="correlation-001",
        sequence_number=1,
        replayed=True,
        original_event_id="event-original",
    )

    with pytest.raises(
        ValueError,
        match=(
            "replayed events must be created through replay"
        ),
    ):
        bus().publish(replayed)


def test_find_events_by_category() -> None:
    value = bus()

    value.publish(event())

    value.publish(
        event(
            event_id="event-002",
            sequence_number=2,
            category=EventCategory.EXECUTION,
            event_type="execution.completed",
        )
    )

    matches = value.find_events(
        category=EventCategory.EXECUTION
    )

    assert len(matches) == 1
    assert matches[0].event_id == "event-002"


def test_find_events_by_severity() -> None:
    value = bus()

    value.publish(
        event(
            severity=EventSeverity.WARNING,
        )
    )

    matches = value.find_events(
        severity=EventSeverity.WARNING
    )

    assert len(matches) == 1
    assert matches[0].severity is EventSeverity.WARNING


def test_find_events_by_correlation_id() -> None:
    value = bus()
    published = event()

    value.publish(published)

    matches = value.find_events(
        correlation_id="correlation-001"
    )

    assert matches == (published,)


def test_find_events_by_event_type() -> None:
    value = bus()
    published = event()

    value.publish(published)

    matches = value.find_events(
        event_type="portfolio.risk.completed"
    )

    assert matches == (published,)


def test_find_events_with_multiple_filters() -> None:
    value = bus()
    published = event(
        category=EventCategory.PORTFOLIO_RISK,
        severity=EventSeverity.INFO,
        event_type="portfolio.risk.completed",
    )

    value.publish(published)

    matches = value.find_events(
        category=EventCategory.PORTFOLIO_RISK,
        severity=EventSeverity.INFO,
        correlation_id="correlation-001",
        event_type="portfolio.risk.completed",
    )

    assert matches == (published,)


def test_find_events_returns_empty_tuple_when_no_match() -> None:
    value = bus()
    value.publish(event())

    matches = value.find_events(
        category=EventCategory.EXECUTION
    )

    assert matches == ()


def test_deliveries_for_event() -> None:
    value = bus()

    value.register(
        subscription=subscription(),
        subscriber=lambda published: None,
    )

    value.publish(event())

    deliveries = value.deliveries_for_event(
        "event-001"
    )

    assert len(deliveries) == 1


def test_deliveries_for_subscription() -> None:
    value = bus()

    value.register(
        subscription=subscription(),
        subscriber=lambda published: None,
    )

    value.publish(event())

    deliveries = value.deliveries_for_subscription(
        "subscription-001"
    )

    assert len(deliveries) == 1


def test_delivery_history_is_recorded() -> None:
    value = bus()

    value.register(
        subscription=subscription(),
        subscriber=lambda published: None,
    )

    value.publish(event())

    assert len(value.delivery_history) == 1
    assert (
        value.delivery_history[0].status
        is EventDeliveryStatus.DELIVERED
    )


def test_delivery_ids_are_sequential() -> None:
    value = bus()

    value.register(
        subscription=subscription(
            "subscription-001",
        ),
        subscriber=lambda published: None,
    )

    value.register(
        subscription=subscription(
            "subscription-002",
        ),
        subscriber=lambda published: None,
    )

    report = value.publish(event())

    assert tuple(
        delivery.delivery_id
        for delivery in report.deliveries
    ) == (
        "delivery-000001",
        "delivery-000002",
    )


def test_category_is_validated_in_find() -> None:
    with pytest.raises(
        TypeError,
        match="category must be an EventCategory or None",
    ):
        bus().find_events(
            category=object()
        )


def test_severity_is_validated_in_find() -> None:
    with pytest.raises(
        TypeError,
        match="severity must be an EventSeverity or None",
    ):
        bus().find_events(
            severity=object()
        )


def test_event_type_is_validated_in_find() -> None:
    with pytest.raises(
        TypeError,
        match="event_type must be a string",
    ):
        bus().find_events(
            event_type=object()
        )


def test_correlation_id_is_validated_in_find() -> None:
    with pytest.raises(
        TypeError,
        match="correlation_id must be a string",
    ):
        bus().find_events(
            correlation_id=object()
        )


def test_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="event_id must not be empty",
    ):
        bus().get_event("   ")


def test_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterpriseEventBus(clock=NOW)


def test_clock_must_return_datetime() -> None:
    value = EnterpriseEventBus(
        clock=lambda: "now"
    )

    value.register(
        subscription=subscription(),
        subscriber=lambda published: None,
    )

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        value.publish(event())


def test_clock_must_return_timezone_aware_datetime() -> None:
    value = EnterpriseEventBus(
        clock=lambda: datetime(2026, 8, 3)
    )

    value.register(
        subscription=subscription(),
        subscriber=lambda published: None,
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        value.publish(event())