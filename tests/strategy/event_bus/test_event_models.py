from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.event_bus.event_models import (
    EnterpriseEvent,
    EventBusReport,
    EventBusStatus,
    EventCategory,
    EventDeliveryRecord,
    EventDeliveryStatus,
    EventSeverity,
    EventSubscription,
)


NOW = datetime(
    2026,
    8,
    3,
    15,
    0,
    tzinfo=timezone.utc,
)


def enterprise_event(
    *,
    replayed: bool = False,
    original_event_id: str | None = None,
) -> EnterpriseEvent:
    return EnterpriseEvent(
        event_id=(
            "event-replay-001"
            if replayed
            else "event-001"
        ),
        event_type="portfolio.risk.completed",
        category=EventCategory.PORTFOLIO_RISK,
        severity=EventSeverity.INFO,
        source="portfolio-risk-manager",
        occurred_at=NOW,
        correlation_id="correlation-001",
        sequence_number=1,
        payload=(
            ("decision", "APPROVE"),
        ),
        replayed=replayed,
        original_event_id=original_event_id,
    )


def subscription() -> EventSubscription:
    return EventSubscription(
        subscription_id="subscription-001",
        subscriber_name="risk-dashboard",
        categories=(
            EventCategory.PORTFOLIO_RISK,
        ),
        minimum_severity=EventSeverity.INFO,
        event_types=(
            "portfolio.risk.completed",
        ),
        enabled=True,
        max_delivery_attempts=3,
    )


def delivered_record() -> EventDeliveryRecord:
    return EventDeliveryRecord(
        delivery_id="delivery-001",
        event_id="event-001",
        subscription_id="subscription-001",
        subscriber_name="risk-dashboard",
        status=EventDeliveryStatus.DELIVERED,
        attempt_number=1,
        attempted_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
        message="Event delivered successfully.",
    )


def failed_record() -> EventDeliveryRecord:
    return EventDeliveryRecord(
        delivery_id="delivery-002",
        event_id="event-001",
        subscription_id="subscription-002",
        subscriber_name="alerting-service",
        status=EventDeliveryStatus.FAILED,
        attempt_number=1,
        attempted_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
        message="Event delivery failed.",
        error="Subscriber unavailable.",
    )


def test_enterprise_event() -> None:
    value = enterprise_event()

    assert value.event_id == "event-001"
    assert (
        value.category
        is EventCategory.PORTFOLIO_RISK
    )
    assert value.sequence_number == 1


def test_event_text_is_normalized() -> None:
    value = EnterpriseEvent(
        event_id="  event-001  ",
        event_type="  execution.completed  ",
        category=EventCategory.EXECUTION,
        severity=EventSeverity.INFO,
        source="  execution-gateway  ",
        occurred_at=NOW,
        correlation_id="  correlation-001  ",
        sequence_number=1,
    )

    assert value.event_id == "event-001"
    assert value.event_type == "execution.completed"
    assert value.source == "execution-gateway"
    assert value.correlation_id == "correlation-001"


@pytest.mark.parametrize(
    "field_name",
    [
        "event_id",
        "event_type",
        "source",
        "correlation_id",
    ],
)
def test_event_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "event_id": "event-001",
        "event_type": "execution.completed",
        "category": EventCategory.EXECUTION,
        "severity": EventSeverity.INFO,
        "source": "execution-gateway",
        "occurred_at": NOW,
        "correlation_id": "correlation-001",
        "sequence_number": 1,
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        EnterpriseEvent(**arguments)


def test_event_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="occurred_at must be timezone-aware",
    ):
        EnterpriseEvent(
            event_id="event-001",
            event_type="execution.completed",
            category=EventCategory.EXECUTION,
            severity=EventSeverity.INFO,
            source="execution-gateway",
            occurred_at=datetime(2026, 8, 3),
            correlation_id="correlation-001",
            sequence_number=1,
        )


@pytest.mark.parametrize(
    "sequence_number",
    [0, -1],
)
def test_event_sequence_number_must_be_positive(
    sequence_number: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "sequence_number must be greater than zero"
        ),
    ):
        EnterpriseEvent(
            event_id="event-001",
            event_type="execution.completed",
            category=EventCategory.EXECUTION,
            severity=EventSeverity.INFO,
            source="execution-gateway",
            occurred_at=NOW,
            correlation_id="correlation-001",
            sequence_number=sequence_number,
        )


def test_event_payload_is_normalized() -> None:
    value = EnterpriseEvent(
        event_id="event-001",
        event_type="execution.completed",
        category=EventCategory.EXECUTION,
        severity=EventSeverity.INFO,
        source="execution-gateway",
        occurred_at=NOW,
        correlation_id="correlation-001",
        sequence_number=1,
        payload=[
            (
                "  order_id  ",
                "  SIM-001  ",
            ),
        ],
    )

    assert value.payload == (
        (
            "order_id",
            "SIM-001",
        ),
    )


def test_event_payload_keys_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="payload keys must be unique",
    ):
        EnterpriseEvent(
            event_id="event-001",
            event_type="execution.completed",
            category=EventCategory.EXECUTION,
            severity=EventSeverity.INFO,
            source="execution-gateway",
            occurred_at=NOW,
            correlation_id="correlation-001",
            sequence_number=1,
            payload=(
                ("order_id", "SIM-001"),
                ("order_id", "SIM-002"),
            ),
        )


def test_replayed_event_requires_original_event_id() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "replayed events must include original_event_id"
        ),
    ):
        enterprise_event(replayed=True)


def test_non_replayed_event_rejects_original_event_id() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only replayed events may include "
            "original_event_id"
        ),
    ):
        enterprise_event(
            replayed=False,
            original_event_id="event-original",
        )


def test_replayed_event() -> None:
    value = enterprise_event(
        replayed=True,
        original_event_id="event-001",
    )

    assert value.replayed is True
    assert value.original_event_id == "event-001"


def test_original_event_id_must_differ() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "original_event_id must differ from event_id"
        ),
    ):
        EnterpriseEvent(
            event_id="event-001",
            event_type="execution.completed",
            category=EventCategory.EXECUTION,
            severity=EventSeverity.INFO,
            source="execution-gateway",
            occurred_at=NOW,
            correlation_id="correlation-001",
            sequence_number=1,
            replayed=True,
            original_event_id="event-001",
        )


def test_event_subscription() -> None:
    value = subscription()

    assert value.subscription_id == "subscription-001"
    assert value.enabled is True
    assert value.max_delivery_attempts == 3


def test_subscription_text_is_normalized() -> None:
    value = EventSubscription(
        subscription_id="  subscription-001  ",
        subscriber_name="  risk-dashboard  ",
        event_types=(
            "  portfolio.risk.completed  ",
        ),
    )

    assert value.subscription_id == "subscription-001"
    assert value.subscriber_name == "risk-dashboard"
    assert value.event_types == (
        "portfolio.risk.completed",
    )


def test_subscription_categories_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "subscription categories must be unique"
        ),
    ):
        EventSubscription(
            subscription_id="subscription-001",
            subscriber_name="risk-dashboard",
            categories=(
                EventCategory.PORTFOLIO_RISK,
                EventCategory.PORTFOLIO_RISK,
            ),
        )


def test_subscription_event_types_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "subscription event_types must be unique"
        ),
    ):
        EventSubscription(
            subscription_id="subscription-001",
            subscriber_name="risk-dashboard",
            event_types=(
                "risk.completed",
                "risk.completed",
            ),
        )


@pytest.mark.parametrize(
    "attempts",
    [0, -1],
)
def test_max_delivery_attempts_must_be_positive(
    attempts: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "max_delivery_attempts must be greater "
            "than zero"
        ),
    ):
        EventSubscription(
            subscription_id="subscription-001",
            subscriber_name="risk-dashboard",
            max_delivery_attempts=attempts,
        )


def test_delivered_record() -> None:
    value = delivered_record()

    assert (
        value.status
        is EventDeliveryStatus.DELIVERED
    )
    assert value.attempt_number == 1
    assert value.error is None


def test_delivery_text_is_normalized() -> None:
    value = EventDeliveryRecord(
        delivery_id="  delivery-001  ",
        event_id="  event-001  ",
        subscription_id="  subscription-001  ",
        subscriber_name="  risk-dashboard  ",
        status=EventDeliveryStatus.SKIPPED,
        attempt_number=1,
        attempted_at=NOW,
        completed_at=NOW,
        message="  Subscription disabled.  ",
    )

    assert value.delivery_id == "delivery-001"
    assert value.event_id == "event-001"
    assert value.subscription_id == "subscription-001"
    assert value.subscriber_name == "risk-dashboard"
    assert value.message == "Subscription disabled."


def test_pending_delivery_has_no_completion_time() -> None:
    value = EventDeliveryRecord(
        delivery_id="delivery-001",
        event_id="event-001",
        subscription_id="subscription-001",
        subscriber_name="risk-dashboard",
        status=EventDeliveryStatus.PENDING,
        attempt_number=1,
        attempted_at=NOW,
        completed_at=None,
        message="Delivery pending.",
    )

    assert value.completed_at is None


def test_pending_delivery_rejects_completion_time() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "pending deliveries must not include "
            "completed_at"
        ),
    ):
        EventDeliveryRecord(
            delivery_id="delivery-001",
            event_id="event-001",
            subscription_id="subscription-001",
            subscriber_name="risk-dashboard",
            status=EventDeliveryStatus.PENDING,
            attempt_number=1,
            attempted_at=NOW,
            completed_at=NOW,
            message="Delivery pending.",
        )


def test_completed_delivery_requires_completion_time() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed delivery outcomes must include "
            "completed_at"
        ),
    ):
        EventDeliveryRecord(
            delivery_id="delivery-001",
            event_id="event-001",
            subscription_id="subscription-001",
            subscriber_name="risk-dashboard",
            status=EventDeliveryStatus.DELIVERED,
            attempt_number=1,
            attempted_at=NOW,
            completed_at=None,
            message="Delivered.",
        )


def test_failed_delivery_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed deliveries must include an error",
    ):
        EventDeliveryRecord(
            delivery_id="delivery-001",
            event_id="event-001",
            subscription_id="subscription-001",
            subscriber_name="risk-dashboard",
            status=EventDeliveryStatus.FAILED,
            attempt_number=1,
            attempted_at=NOW,
            completed_at=NOW,
            message="Delivery failed.",
        )


def test_successful_delivery_rejects_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only failed deliveries may include an error"
        ),
    ):
        EventDeliveryRecord(
            delivery_id="delivery-001",
            event_id="event-001",
            subscription_id="subscription-001",
            subscriber_name="risk-dashboard",
            status=EventDeliveryStatus.DELIVERED,
            attempt_number=1,
            attempted_at=NOW,
            completed_at=NOW,
            message="Delivered.",
            error="Unexpected error.",
        )


def test_dead_letter_record() -> None:
    value = EventDeliveryRecord(
        delivery_id="delivery-001",
        event_id="event-001",
        subscription_id="subscription-001",
        subscriber_name="risk-dashboard",
        status=EventDeliveryStatus.DEAD_LETTERED,
        attempt_number=3,
        attempted_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
        message="Delivery moved to dead letter.",
        error="Retry limit exhausted.",
        dead_lettered=True,
    )

    assert value.dead_lettered is True


def test_dead_letter_status_requires_flag() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "dead-letter delivery status requires "
            "dead_lettered=True"
        ),
    ):
        EventDeliveryRecord(
            delivery_id="delivery-001",
            event_id="event-001",
            subscription_id="subscription-001",
            subscriber_name="risk-dashboard",
            status=EventDeliveryStatus.DEAD_LETTERED,
            attempt_number=3,
            attempted_at=NOW,
            completed_at=NOW,
            message="Dead lettered.",
            error="Retry limit exhausted.",
        )


def test_event_bus_report() -> None:
    report = EventBusReport(
        status=EventBusStatus.COMPLETED,
        event=enterprise_event(),
        deliveries=(
            delivered_record(),
            failed_record(),
        ),
        matched_subscriptions=2,
        delivered_count=1,
        failed_count=1,
        skipped_count=0,
        dead_letter_count=0,
    )

    assert report.status is EventBusStatus.COMPLETED
    assert report.matched_subscriptions == 2
    assert report.delivered_count == 1
    assert report.failed_count == 1


def test_report_delivery_ids_must_be_unique() -> None:
    duplicate = delivered_record()

    with pytest.raises(
        ValueError,
        match="delivery_id values must be unique",
    ):
        EventBusReport(
            status=EventBusStatus.COMPLETED,
            event=enterprise_event(),
            deliveries=(duplicate, duplicate),
            matched_subscriptions=2,
            delivered_count=2,
        )


def test_delivery_event_id_must_match_report() -> None:
    wrong_delivery = EventDeliveryRecord(
        delivery_id="delivery-001",
        event_id="different-event",
        subscription_id="subscription-001",
        subscriber_name="risk-dashboard",
        status=EventDeliveryStatus.DELIVERED,
        attempt_number=1,
        attempted_at=NOW,
        completed_at=NOW,
        message="Delivered.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "delivery event_id must match the "
            "report event"
        ),
    ):
        EventBusReport(
            status=EventBusStatus.COMPLETED,
            event=enterprise_event(),
            deliveries=(wrong_delivery,),
            matched_subscriptions=1,
            delivered_count=1,
        )


def test_matched_subscription_count_must_match() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "matched_subscriptions must equal delivery count"
        ),
    ):
        EventBusReport(
            status=EventBusStatus.COMPLETED,
            event=enterprise_event(),
            deliveries=(delivered_record(),),
            matched_subscriptions=2,
            delivered_count=1,
        )


def test_delivery_counts_must_match_outcomes() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "delivered_count must match delivery outcomes"
        ),
    ):
        EventBusReport(
            status=EventBusStatus.COMPLETED,
            event=enterprise_event(),
            deliveries=(delivered_record(),),
            matched_subscriptions=1,
            delivered_count=0,
        )


def test_completed_report_requires_event() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed reports must include an event"
        ),
    ):
        EventBusReport(
            status=EventBusStatus.COMPLETED,
            event=None,
        )


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        EventBusReport(
            status=EventBusStatus.FAILED,
            event=None,
        )


def test_report_warnings_are_tuples() -> None:
    report = EventBusReport(
        status=EventBusStatus.COMPLETED,
        event=enterprise_event(),
        warnings=["Event warning."],
    )

    assert report.warnings == (
        "Event warning.",
    )


def test_models_are_immutable() -> None:
    value = enterprise_event()

    with pytest.raises(FrozenInstanceError):
        value.source = "changed"