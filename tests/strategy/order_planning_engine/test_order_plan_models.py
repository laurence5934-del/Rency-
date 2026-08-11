from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.order_planning_engine import (
    OrderPlan,
    OrderPlanAction,
    OrderPlanSide,
    OrderPlanTimeInForce,
    OrderPlanType,
    OrderPlanningDecision,
    OrderPlanningReport,
    OrderPlanningRequest,
    OrderPlanningResult,
    OrderPlanningStage,
    OrderPlanningStatus,
)

NOW = datetime(
    2026,
    8,
    11,
    12,
    0,
    tzinfo=timezone.utc,
)


def order_planning_request(
    **overrides: object,
) -> OrderPlanningRequest:
    values: dict[str, object] = {
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "allocation_id": "allocation-001",
        "signal_id": "signal-001",
        "intent_id": "trade-intent-000001",
        "symbol": "NVDA",
        "action": OrderPlanAction.CREATE,
        "side": OrderPlanSide.BUY,
        "order_type": OrderPlanType.MARKET,
        "time_in_force": OrderPlanTimeInForce.DAY,
        "quantity": 10,
        "confidence": 90,
        "created_at": NOW,
        "sequence_number": 1,
        "requested_by": "trade-intent-engine",
    }

    values.update(overrides)

    return OrderPlanningRequest(**values)  # type: ignore[arg-type]


def test_order_planning_request() -> None:
    request = order_planning_request()

    assert request.request_id == "request-001"
    assert request.correlation_id == "correlation-001"
    assert request.strategy_id == "strategy-001"
    assert request.portfolio_id == "portfolio-001"
    assert request.allocation_id == "allocation-001"
    assert request.signal_id == "signal-001"
    assert request.intent_id == "trade-intent-000001"
    assert request.symbol == "NVDA"
    assert request.action is OrderPlanAction.CREATE
    assert request.side is OrderPlanSide.BUY
    assert request.order_type is OrderPlanType.MARKET
    assert (
        request.time_in_force
        is OrderPlanTimeInForce.DAY
    )
    assert request.quantity == 10
    assert request.confidence == 90
    assert request.created_at == NOW
    assert request.sequence_number == 1
    assert request.requested_by == "trade-intent-engine"
    assert request.limit_price is None
    assert request.stop_price is None
    assert request.is_replay is False
    assert request.metadata == ()


def test_order_planning_request_text_is_normalized() -> None:
    request = order_planning_request(
        request_id="  request-001  ",
        correlation_id="  correlation-001  ",
        strategy_id="  strategy-001  ",
        portfolio_id="  portfolio-001  ",
        allocation_id="  allocation-001  ",
        signal_id="  signal-001  ",
        intent_id="  trade-intent-000001  ",
        symbol="  nvda  ",
        requested_by="  trade-intent-engine  ",
    )

    assert request.request_id == "request-001"
    assert request.correlation_id == "correlation-001"
    assert request.strategy_id == "strategy-001"
    assert request.portfolio_id == "portfolio-001"
    assert request.allocation_id == "allocation-001"
    assert request.signal_id == "signal-001"
    assert request.intent_id == "trade-intent-000001"
    assert request.symbol == "NVDA"
    assert request.requested_by == "trade-intent-engine"


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "allocation_id",
        "signal_id",
        "intent_id",
        "symbol",
        "requested_by",
    ],
)
def test_order_planning_request_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        order_planning_request(
            **{field_name: "   "}
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "allocation_id",
        "signal_id",
        "intent_id",
        "symbol",
        "requested_by",
    ],
)
def test_order_planning_request_required_text_must_be_string(
    field_name: str,
) -> None:
    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        order_planning_request(
            **{field_name: 123}
        )


def test_order_planning_request_requires_action_enum() -> None:
    with pytest.raises(
        TypeError,
        match="action must be an OrderPlanAction",
    ):
        order_planning_request(
            action="CREATE"
        )


def test_order_planning_request_requires_side_enum() -> None:
    with pytest.raises(
        TypeError,
        match="side must be an OrderPlanSide",
    ):
        order_planning_request(
            side="BUY"
        )


def test_order_planning_request_requires_order_type_enum() -> None:
    with pytest.raises(
        TypeError,
        match="order_type must be an OrderPlanType",
    ):
        order_planning_request(
            order_type="MARKET"
        )


def test_order_planning_request_requires_time_in_force_enum() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "time_in_force must be an "
            "OrderPlanTimeInForce"
        ),
    ):
        order_planning_request(
            time_in_force="DAY"
        )


def test_order_planning_request_quantity_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="quantity must be an integer",
    ):
        order_planning_request(
            quantity=10.5
        )


def test_order_planning_request_quantity_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="quantity must be an integer",
    ):
        order_planning_request(
            quantity=True
        )


@pytest.mark.parametrize(
    "quantity",
    [0, -1],
)
def test_order_planning_request_quantity_must_be_positive(
    quantity: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="quantity must be positive",
    ):
        order_planning_request(
            quantity=quantity
        )


@pytest.mark.parametrize(
    "confidence",
    [-1, 101],
)
def test_order_planning_request_confidence_bounds(
    confidence: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="confidence must be between 0 and 100",
    ):
        order_planning_request(
            confidence=confidence
        )


def test_order_planning_request_confidence_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        order_planning_request(
            confidence=90.5
        )


def test_order_planning_request_confidence_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        order_planning_request(
            confidence=True
        )


@pytest.mark.parametrize(
    "confidence",
    [0, 100],
)
def test_order_planning_request_confidence_boundaries_allowed(
    confidence: int,
) -> None:
    request = order_planning_request(
        confidence=confidence
    )

    assert request.confidence == confidence


def test_order_planning_request_created_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="created_at must be a datetime",
    ):
        order_planning_request(
            created_at="2026-08-11"
        )


def test_order_planning_request_created_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="created_at must be timezone-aware",
    ):
        order_planning_request(
            created_at=datetime(
                2026,
                8,
                11,
                12,
                0,
            )
        )


def test_order_planning_request_sequence_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="sequence_number must be an integer",
    ):
        order_planning_request(
            sequence_number=1.5
        )


def test_order_planning_request_sequence_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="sequence_number must be an integer",
    ):
        order_planning_request(
            sequence_number=True
        )


def test_order_planning_request_sequence_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="sequence_number must not be negative",
    ):
        order_planning_request(
            sequence_number=-1
        )


def test_zero_sequence_number_is_allowed() -> None:
    request = order_planning_request(
        sequence_number=0
    )

    assert request.sequence_number == 0


def test_order_planning_request_replay_requires_bool() -> None:
    with pytest.raises(
        TypeError,
        match="is_replay must be a bool",
    ):
        order_planning_request(
            is_replay="yes"
        )


def test_replay_order_planning_request() -> None:
    request = order_planning_request(
        is_replay=True
    )

    assert request.is_replay is True


def test_hold_order_plan_requires_none_side() -> None:
    with pytest.raises(
        ValueError,
        match="HOLD order plans require NONE side",
    ):
        order_planning_request(
            action=OrderPlanAction.HOLD,
            side=OrderPlanSide.BUY,
        )


def test_hold_order_plan_with_none_side() -> None:
    request = order_planning_request(
        action=OrderPlanAction.HOLD,
        side=OrderPlanSide.NONE,
    )

    assert request.action is OrderPlanAction.HOLD
    assert request.side is OrderPlanSide.NONE
    assert request.is_actionable is False


def test_actionable_order_plan_rejects_none_side() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "actionable order plans require an order side"
        ),
    ):
        order_planning_request(
            action=OrderPlanAction.CREATE,
            side=OrderPlanSide.NONE,
        )


def test_market_order_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "MARKET orders must not include "
            "limit_price or stop_price"
        ),
    ):
        order_planning_request(
            limit_price=100.0
        )


def test_market_order_rejects_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "MARKET orders must not include "
            "limit_price or stop_price"
        ),
    ):
        order_planning_request(
            stop_price=95.0
        )


def test_limit_order_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="LIMIT orders require limit_price",
    ):
        order_planning_request(
            order_type=OrderPlanType.LIMIT
        )


def test_limit_order_rejects_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="LIMIT orders must not include stop_price",
    ):
        order_planning_request(
            order_type=OrderPlanType.LIMIT,
            limit_price=100.0,
            stop_price=95.0,
        )


def test_limit_order() -> None:
    request = order_planning_request(
        order_type=OrderPlanType.LIMIT,
        limit_price=100.0,
    )

    assert request.limit_price == 100.0
    assert request.stop_price is None
    assert request.is_limit_order is True


def test_stop_order_requires_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="STOP orders require stop_price",
    ):
        order_planning_request(
            order_type=OrderPlanType.STOP
        )


def test_stop_order_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="STOP orders must not include limit_price",
    ):
        order_planning_request(
            order_type=OrderPlanType.STOP,
            stop_price=95.0,
            limit_price=100.0,
        )


def test_stop_order() -> None:
    request = order_planning_request(
        order_type=OrderPlanType.STOP,
        stop_price=95.0,
    )

    assert request.stop_price == 95.0
    assert request.limit_price is None
    assert request.is_stop_order is True


def test_stop_limit_order_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "STOP_LIMIT orders require limit_price"
        ),
    ):
        order_planning_request(
            order_type=OrderPlanType.STOP_LIMIT,
            stop_price=95.0,
        )


def test_stop_limit_order_requires_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "STOP_LIMIT orders require stop_price"
        ),
    ):
        order_planning_request(
            order_type=OrderPlanType.STOP_LIMIT,
            limit_price=100.0,
        )


def test_stop_limit_order() -> None:
    request = order_planning_request(
        order_type=OrderPlanType.STOP_LIMIT,
        limit_price=100.0,
        stop_price=95.0,
    )

    assert request.limit_price == 100.0
    assert request.stop_price == 95.0
    assert request.is_stop_order is True


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("limit_price", 0),
        ("limit_price", -1),
        ("stop_price", 0),
        ("stop_price", -1),
    ],
)
def test_order_planning_request_prices_must_be_positive(
    field_name: str,
    value: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=f"{field_name} must be positive",
    ):
        order_planning_request(
            **{field_name: value}
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("limit_price", "100"),
        ("limit_price", True),
        ("stop_price", "95"),
        ("stop_price", True),
    ],
)
def test_order_planning_request_prices_require_numbers(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a number",
    ):
        order_planning_request(
            **{field_name: value}
        )


def test_order_planning_request_is_actionable() -> None:
    request = order_planning_request()

    assert request.is_actionable is True


def test_market_order_property() -> None:
    request = order_planning_request()

    assert request.is_market_order is True
    assert request.is_limit_order is False
    assert request.is_stop_order is False


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (79, False),
        (80, True),
        (100, True),
    ],
)
def test_order_planning_request_high_confidence_property(
    confidence: int,
    expected: bool,
) -> None:
    request = order_planning_request(
        confidence=confidence
    )

    assert request.is_high_confidence is expected


def test_order_planning_request_metadata_is_normalized() -> None:
    request = order_planning_request(
        metadata=[
            (" source ", " trade-intent-engine "),
            ("route", " primary "),
        ]
    )

    assert request.metadata == (
        ("source", "trade-intent-engine"),
        ("route", "primary"),
    )


def test_order_planning_request_metadata_keys_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        order_planning_request(
            metadata=(
                ("source", "one"),
                ("source", "two"),
            )
        )


def test_order_planning_request_metadata_items_must_be_pairs() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be a two-item tuple"
        ),
    ):
        order_planning_request(
            metadata=(
                ("source", "one", "extra"),
            )
        )


def test_order_planning_request_metadata_keys_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        order_planning_request(
            metadata=(
                (1, "value"),
            )
        )


def test_order_planning_request_metadata_values_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        order_planning_request(
            metadata=(
                ("source", 1),
            )
        )


def test_order_planning_request_is_immutable() -> None:
    request = order_planning_request()

    with pytest.raises(FrozenInstanceError):
        request.quantity = 20  # type: ignore[misc]

def order_plan(
    **overrides: object,
) -> OrderPlan:
    values: dict[str, object] = {
        "plan_id": "order-plan-000001",
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "allocation_id": "allocation-001",
        "signal_id": "signal-001",
        "intent_id": "trade-intent-000001",
        "symbol": "NVDA",
        "action": OrderPlanAction.CREATE,
        "side": OrderPlanSide.BUY,
        "order_type": OrderPlanType.MARKET,
        "time_in_force": OrderPlanTimeInForce.DAY,
        "quantity": 10,
        "confidence": 90,
        "generated_at": NOW,
        "expires_at": None,
        "rationale": "Approved trade intent supports order construction.",
    }

    values.update(overrides)

    return OrderPlan(**values)  # type: ignore[arg-type]


def test_order_plan() -> None:
    plan = order_plan()

    assert plan.plan_id == "order-plan-000001"
    assert plan.request_id == "request-001"
    assert plan.correlation_id == "correlation-001"
    assert plan.strategy_id == "strategy-001"
    assert plan.portfolio_id == "portfolio-001"
    assert plan.allocation_id == "allocation-001"
    assert plan.signal_id == "signal-001"
    assert plan.intent_id == "trade-intent-000001"
    assert plan.symbol == "NVDA"
    assert plan.action is OrderPlanAction.CREATE
    assert plan.side is OrderPlanSide.BUY
    assert plan.order_type is OrderPlanType.MARKET
    assert plan.time_in_force is OrderPlanTimeInForce.DAY
    assert plan.quantity == 10
    assert plan.confidence == 90
    assert plan.generated_at == NOW
    assert plan.expires_at is None
    assert plan.rationale == (
        "Approved trade intent supports order construction."
    )
    assert plan.limit_price is None
    assert plan.stop_price is None
    assert plan.warnings == ()
    assert plan.metadata == ()
    assert plan.is_actionable is True
    assert plan.is_market_order is True
    assert plan.is_high_confidence is True
    assert plan.has_expiration is False


def test_order_plan_text_is_normalized() -> None:
    plan = order_plan(
        plan_id="  order-plan-000001  ",
        request_id="  request-001  ",
        correlation_id="  correlation-001  ",
        strategy_id="  strategy-001  ",
        portfolio_id="  portfolio-001  ",
        allocation_id="  allocation-001  ",
        signal_id="  signal-001  ",
        intent_id="  trade-intent-000001  ",
        symbol="  nvda  ",
        rationale="  Approved trade intent supports order construction.  ",
    )

    assert plan.plan_id == "order-plan-000001"
    assert plan.request_id == "request-001"
    assert plan.correlation_id == "correlation-001"
    assert plan.strategy_id == "strategy-001"
    assert plan.portfolio_id == "portfolio-001"
    assert plan.allocation_id == "allocation-001"
    assert plan.signal_id == "signal-001"
    assert plan.intent_id == "trade-intent-000001"
    assert plan.symbol == "NVDA"
    assert plan.rationale == (
        "Approved trade intent supports order construction."
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "plan_id",
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "allocation_id",
        "signal_id",
        "intent_id",
        "symbol",
        "rationale",
    ],
)
def test_order_plan_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        order_plan(
            **{field_name: "   "}
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "plan_id",
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "allocation_id",
        "signal_id",
        "intent_id",
        "symbol",
        "rationale",
    ],
)
def test_order_plan_required_text_must_be_string(
    field_name: str,
) -> None:
    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        order_plan(
            **{field_name: 123}
        )


def test_order_plan_requires_action_enum() -> None:
    with pytest.raises(
        TypeError,
        match="action must be an OrderPlanAction",
    ):
        order_plan(
            action="CREATE"
        )


def test_order_plan_requires_side_enum() -> None:
    with pytest.raises(
        TypeError,
        match="side must be an OrderPlanSide",
    ):
        order_plan(
            side="BUY"
        )


def test_order_plan_requires_order_type_enum() -> None:
    with pytest.raises(
        TypeError,
        match="order_type must be an OrderPlanType",
    ):
        order_plan(
            order_type="MARKET"
        )


def test_order_plan_requires_time_in_force_enum() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "time_in_force must be an "
            "OrderPlanTimeInForce"
        ),
    ):
        order_plan(
            time_in_force="DAY"
        )


def test_order_plan_quantity_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="quantity must be an integer",
    ):
        order_plan(
            quantity=10.5
        )


def test_order_plan_quantity_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="quantity must be an integer",
    ):
        order_plan(
            quantity=True
        )


@pytest.mark.parametrize(
    "quantity",
    [0, -1],
)
def test_order_plan_quantity_must_be_positive(
    quantity: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="quantity must be positive",
    ):
        order_plan(
            quantity=quantity
        )


@pytest.mark.parametrize(
    "confidence",
    [-1, 101],
)
def test_order_plan_confidence_bounds(
    confidence: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="confidence must be between 0 and 100",
    ):
        order_plan(
            confidence=confidence
        )


def test_order_plan_confidence_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        order_plan(
            confidence=90.5
        )


def test_order_plan_confidence_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        order_plan(
            confidence=True
        )


@pytest.mark.parametrize(
    "confidence",
    [0, 100],
)
def test_order_plan_confidence_boundaries_allowed(
    confidence: int,
) -> None:
    plan = order_plan(
        confidence=confidence
    )

    assert plan.confidence == confidence


def test_order_plan_generated_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="generated_at must be a datetime",
    ):
        order_plan(
            generated_at="2026-08-11"
        )


def test_order_plan_generated_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="generated_at must be timezone-aware",
    ):
        order_plan(
            generated_at=datetime(
                2026,
                8,
                11,
                12,
                0,
            )
        )


def test_order_plan_expires_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="expires_at must be a datetime",
    ):
        order_plan(
            expires_at="2026-08-11"
        )


def test_order_plan_expires_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="expires_at must be timezone-aware",
    ):
        order_plan(
            expires_at=datetime(
                2026,
                8,
                11,
                12,
                5,
            )
        )


def test_order_plan_expiration_must_follow_generation() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "expires_at must not be earlier "
            "than generated_at"
        ),
    ):
        order_plan(
            expires_at=(
                NOW - timedelta(seconds=1)
            )
        )


def test_order_plan_expiration_may_equal_generation() -> None:
    plan = order_plan(
        expires_at=NOW
    )

    assert plan.expires_at == NOW
    assert plan.has_expiration is True


def test_order_plan_has_expiration() -> None:
    plan = order_plan(
        expires_at=(
            NOW + timedelta(minutes=5)
        )
    )

    assert plan.has_expiration is True


def test_order_plan_without_expiration_never_expires() -> None:
    plan = order_plan()

    assert plan.is_expired_at(
        NOW + timedelta(days=1)
    ) is False


def test_order_plan_not_expired_at_boundary() -> None:
    expires_at = (
        NOW + timedelta(minutes=5)
    )

    plan = order_plan(
        expires_at=expires_at
    )

    assert plan.is_expired_at(
        expires_at
    ) is False


def test_order_plan_expires_after_boundary() -> None:
    expires_at = (
        NOW + timedelta(minutes=5)
    )

    plan = order_plan(
        expires_at=expires_at
    )

    assert plan.is_expired_at(
        expires_at + timedelta(microseconds=1)
    ) is True


def test_order_plan_expiry_check_requires_datetime() -> None:
    plan = order_plan(
        expires_at=(
            NOW + timedelta(minutes=5)
        )
    )

    with pytest.raises(
        TypeError,
        match="value must be a datetime",
    ):
        plan.is_expired_at(
            "2026-08-11"
        )


def test_order_plan_expiry_check_requires_aware_datetime() -> None:
    plan = order_plan(
        expires_at=(
            NOW + timedelta(minutes=5)
        )
    )

    with pytest.raises(
        ValueError,
        match="value must be timezone-aware",
    ):
        plan.is_expired_at(
            datetime(
                2026,
                8,
                11,
                12,
                10,
            )
        )


def test_order_plan_hold_requires_none_side() -> None:
    with pytest.raises(
        ValueError,
        match="HOLD order plans require NONE side",
    ):
        order_plan(
            action=OrderPlanAction.HOLD,
            side=OrderPlanSide.BUY,
        )


def test_order_plan_hold_with_none_side() -> None:
    plan = order_plan(
        action=OrderPlanAction.HOLD,
        side=OrderPlanSide.NONE,
    )

    assert plan.is_actionable is False


def test_order_plan_actionable_rejects_none_side() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "actionable order plans require an order side"
        ),
    ):
        order_plan(
            action=OrderPlanAction.CREATE,
            side=OrderPlanSide.NONE,
        )


def test_order_plan_market_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "MARKET orders must not include "
            "limit_price or stop_price"
        ),
    ):
        order_plan(
            limit_price=100.0
        )


def test_order_plan_market_rejects_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "MARKET orders must not include "
            "limit_price or stop_price"
        ),
    ):
        order_plan(
            stop_price=95.0
        )


def test_order_plan_limit_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="LIMIT orders require limit_price",
    ):
        order_plan(
            order_type=OrderPlanType.LIMIT
        )


def test_order_plan_limit_rejects_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="LIMIT orders must not include stop_price",
    ):
        order_plan(
            order_type=OrderPlanType.LIMIT,
            limit_price=100.0,
            stop_price=95.0,
        )


def test_order_plan_limit_order() -> None:
    plan = order_plan(
        order_type=OrderPlanType.LIMIT,
        limit_price=100.0,
    )

    assert plan.limit_price == 100.0
    assert plan.stop_price is None
    assert plan.is_limit_order is True
    assert plan.is_market_order is False


def test_order_plan_stop_requires_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="STOP orders require stop_price",
    ):
        order_plan(
            order_type=OrderPlanType.STOP
        )


def test_order_plan_stop_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="STOP orders must not include limit_price",
    ):
        order_plan(
            order_type=OrderPlanType.STOP,
            stop_price=95.0,
            limit_price=100.0,
        )


def test_order_plan_stop_order() -> None:
    plan = order_plan(
        order_type=OrderPlanType.STOP,
        stop_price=95.0,
    )

    assert plan.stop_price == 95.0
    assert plan.limit_price is None
    assert plan.is_stop_order is True


def test_order_plan_stop_limit_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "STOP_LIMIT orders require limit_price"
        ),
    ):
        order_plan(
            order_type=OrderPlanType.STOP_LIMIT,
            stop_price=95.0,
        )


def test_order_plan_stop_limit_requires_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "STOP_LIMIT orders require stop_price"
        ),
    ):
        order_plan(
            order_type=OrderPlanType.STOP_LIMIT,
            limit_price=100.0,
        )


def test_order_plan_stop_limit_order() -> None:
    plan = order_plan(
        order_type=OrderPlanType.STOP_LIMIT,
        limit_price=100.0,
        stop_price=95.0,
    )

    assert plan.limit_price == 100.0
    assert plan.stop_price == 95.0
    assert plan.is_stop_order is True


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("limit_price", 0),
        ("limit_price", -1),
        ("stop_price", 0),
        ("stop_price", -1),
    ],
)
def test_order_plan_prices_must_be_positive(
    field_name: str,
    value: int,
) -> None:
    kwargs = {
        "order_type": OrderPlanType.STOP_LIMIT,
        "limit_price": 100.0,
        "stop_price": 95.0,
    }

    kwargs[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be positive",
    ):
        order_plan(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("limit_price", "100"),
        ("limit_price", True),
        ("stop_price", "95"),
        ("stop_price", True),
    ],
)
def test_order_plan_prices_require_numbers(
    field_name: str,
    value: object,
) -> None:
    kwargs = {
        "order_type": OrderPlanType.STOP_LIMIT,
        "limit_price": 100.0,
        "stop_price": 95.0,
    }

    kwargs[field_name] = value

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a number",
    ):
        order_plan(**kwargs)


def test_order_plan_is_actionable() -> None:
    plan = order_plan()

    assert plan.is_actionable is True


def test_order_plan_market_order_property() -> None:
    plan = order_plan()

    assert plan.is_market_order is True
    assert plan.is_limit_order is False
    assert plan.is_stop_order is False


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (79, False),
        (80, True),
        (100, True),
    ],
)
def test_order_plan_high_confidence_property(
    confidence: int,
    expected: bool,
) -> None:
    plan = order_plan(
        confidence=confidence
    )

    assert plan.is_high_confidence is expected


def test_order_plan_warnings_are_normalized() -> None:
    plan = order_plan(
        warnings=(
            " spread elevated ",
            "spread elevated",
            " liquidity constrained ",
        )
    )

    assert plan.warnings == (
        "spread elevated",
        "liquidity constrained",
    )


def test_order_plan_warnings_reject_empty_values() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        order_plan(
            warnings=(
                "valid",
                "   ",
            )
        )


def test_order_plan_warnings_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        order_plan(
            warnings=(
                "valid",
                123,
            )
        )


def test_order_plan_metadata_is_normalized() -> None:
    plan = order_plan(
        metadata=[
            (" source ", " trade-intent-engine "),
            (" route ", " primary "),
        ]
    )

    assert plan.metadata == (
        ("source", "trade-intent-engine"),
        ("route", "primary"),
    )


def test_order_plan_metadata_keys_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        order_plan(
            metadata=(
                ("source", "one"),
                ("source", "two"),
            )
        )


def test_order_plan_metadata_items_must_be_pairs() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        order_plan(
            metadata=(
                ("source", "one", "extra"),
            )
        )


def test_order_plan_metadata_keys_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        order_plan(
            metadata=(
                (1, "value"),
            )
        )


def test_order_plan_metadata_values_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        order_plan(
            metadata=(
                ("source", 1),
            )
        )


def test_order_plan_is_immutable() -> None:
    plan = order_plan()

    with pytest.raises(FrozenInstanceError):
        plan.plan_id = "changed"  # type: ignore[misc]

def order_planning_result(
    **overrides: object,
) -> OrderPlanningResult:
    values: dict[str, object] = {
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "status": OrderPlanningStatus.ACTIVE,
        "decision": OrderPlanningDecision.PROCEED,
        "started_at": NOW,
        "updated_at": NOW,
        "completed_at": None,
        "plan": None,
        "warnings": (),
        "error": None,
        "metadata": (),
    }

    values.update(overrides)

    return OrderPlanningResult(**values)  # type: ignore[arg-type]


def approved_order_planning_result() -> OrderPlanningResult:
    return order_planning_result(
        status=OrderPlanningStatus.APPROVED,
        decision=OrderPlanningDecision.APPROVE,
        completed_at=NOW,
        plan=order_plan(),
    )


def failed_order_planning_result(
    *,
    retryable: bool = True,
) -> OrderPlanningResult:
    return order_planning_result(
        status=OrderPlanningStatus.FAILED,
        decision=(
            OrderPlanningDecision.RETRY
            if retryable
            else OrderPlanningDecision.NO_ACTION
        ),
        completed_at=NOW,
        error="Order planning evaluation failed.",
    )


def test_active_order_planning_result() -> None:
    result = order_planning_result()

    assert result.request_id == "request-001"
    assert result.correlation_id == "correlation-001"
    assert result.status is OrderPlanningStatus.ACTIVE
    assert result.decision is OrderPlanningDecision.PROCEED
    assert result.started_at == NOW
    assert result.updated_at == NOW
    assert result.completed_at is None
    assert result.plan is None
    assert result.is_terminal is False
    assert result.is_successful is False
    assert result.has_plan is False


def test_pending_order_planning_result() -> None:
    result = order_planning_result(
        status=OrderPlanningStatus.PENDING,
        decision=OrderPlanningDecision.NO_ACTION,
    )

    assert result.status is OrderPlanningStatus.PENDING
    assert result.is_terminal is False


def test_approved_order_planning_result() -> None:
    result = approved_order_planning_result()

    assert result.status is OrderPlanningStatus.APPROVED
    assert result.decision is OrderPlanningDecision.APPROVE
    assert result.is_terminal is True
    assert result.is_successful is True
    assert result.has_plan is True


def test_rejected_order_planning_result() -> None:
    result = order_planning_result(
        status=OrderPlanningStatus.REJECTED,
        decision=OrderPlanningDecision.REJECT,
        completed_at=NOW,
    )

    assert result.status is OrderPlanningStatus.REJECTED
    assert result.is_terminal is True
    assert result.is_successful is False


def test_cancelled_order_planning_result() -> None:
    result = order_planning_result(
        status=OrderPlanningStatus.CANCELLED,
        decision=OrderPlanningDecision.CANCEL,
        completed_at=NOW,
    )

    assert result.status is OrderPlanningStatus.CANCELLED
    assert result.is_terminal is True


def test_failed_order_planning_result_retryable() -> None:
    result = failed_order_planning_result(
        retryable=True
    )

    assert result.status is OrderPlanningStatus.FAILED
    assert result.decision is OrderPlanningDecision.RETRY
    assert result.error == "Order planning evaluation failed."
    assert result.is_terminal is True


def test_failed_order_planning_result_non_retryable() -> None:
    result = failed_order_planning_result(
        retryable=False
    )

    assert result.decision is OrderPlanningDecision.NO_ACTION


def test_order_planning_result_text_is_normalized() -> None:
    result = OrderPlanningResult(
        request_id="  request-001  ",
        correlation_id="  correlation-001  ",
        status=OrderPlanningStatus.ACTIVE,
        decision=OrderPlanningDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW,
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        ),
        metadata=[
            ("  source  ", "  order-planning-engine  "),
        ],
    )

    assert result.request_id == "request-001"
    assert result.correlation_id == "correlation-001"
    assert result.warnings == (
        "warning one",
        "warning two",
    )
    assert result.metadata == (
        ("source", "order-planning-engine"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
    ],
)
def test_order_planning_result_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        order_planning_result(
            **{field_name: "   "}
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
    ],
)
def test_order_planning_result_required_text_must_be_string(
    field_name: str,
) -> None:
    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        order_planning_result(
            **{field_name: 123}
        )


def test_order_planning_result_requires_status_enum() -> None:
    with pytest.raises(
        TypeError,
        match="status must be an OrderPlanningStatus",
    ):
        order_planning_result(
            status="ACTIVE"
        )


def test_order_planning_result_requires_decision_enum() -> None:
    with pytest.raises(
        TypeError,
        match="decision must be an OrderPlanningDecision",
    ):
        order_planning_result(
            decision="PROCEED"
        )


def test_order_planning_result_started_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="started_at must be a datetime",
    ):
        order_planning_result(
            started_at="2026-08-11"
        )


def test_order_planning_result_started_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="started_at must be timezone-aware",
    ):
        order_planning_result(
            started_at=datetime(
                2026,
                8,
                11,
                12,
                0,
            )
        )


def test_order_planning_result_updated_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="updated_at must be a datetime",
    ):
        order_planning_result(
            updated_at="2026-08-11"
        )


def test_order_planning_result_updated_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="updated_at must be timezone-aware",
    ):
        order_planning_result(
            updated_at=datetime(
                2026,
                8,
                11,
                12,
                0,
            )
        )


def test_order_planning_result_updated_at_must_follow_start() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "updated_at must not be earlier "
            "than started_at"
        ),
    ):
        order_planning_result(
            updated_at=(
                NOW - timedelta(seconds=1)
            )
        )


def test_order_planning_result_completed_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="completed_at must be a datetime",
    ):
        order_planning_result(
            status=OrderPlanningStatus.REJECTED,
            decision=OrderPlanningDecision.REJECT,
            completed_at="2026-08-11",
        )


def test_order_planning_result_completed_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="completed_at must be timezone-aware",
    ):
        order_planning_result(
            status=OrderPlanningStatus.REJECTED,
            decision=OrderPlanningDecision.REJECT,
            completed_at=datetime(
                2026,
                8,
                11,
                12,
                0,
            ),
        )


def test_order_planning_result_completed_at_must_follow_update() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed_at must not be earlier "
            "than updated_at"
        ),
    ):
        order_planning_result(
            status=OrderPlanningStatus.REJECTED,
            decision=OrderPlanningDecision.REJECT,
            completed_at=(
                NOW - timedelta(seconds=1)
            ),
        )


def test_order_planning_result_requires_plan_model() -> None:
    with pytest.raises(
        TypeError,
        match="plan must be an OrderPlan or None",
    ):
        order_planning_result(
            plan=object()
        )


def test_plan_request_id_must_match_result() -> None:
    plan = order_plan(
        request_id="different-request"
    )

    with pytest.raises(
        ValueError,
        match=(
            "plan request_id must match "
            "result request_id"
        ),
    ):
        order_planning_result(
            plan=plan
        )


def test_plan_correlation_id_must_match_result() -> None:
    plan = order_plan(
        correlation_id="different-correlation"
    )

    with pytest.raises(
        ValueError,
        match=(
            "plan correlation_id must match "
            "result correlation_id"
        ),
    ):
        order_planning_result(
            plan=plan
        )


def test_plan_generation_must_not_precede_result_start() -> None:
    plan = order_plan(
        generated_at=(
            NOW - timedelta(seconds=1)
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "plan generated_at must not be "
            "earlier than result started_at"
        ),
    ):
        order_planning_result(
            plan=plan
        )


def test_plan_generation_must_not_follow_result_update() -> None:
    plan = order_plan(
        generated_at=(
            NOW + timedelta(seconds=1)
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "plan generated_at must not be "
            "later than result updated_at"
        ),
    ):
        order_planning_result(
            plan=plan
        )


@pytest.mark.parametrize(
    "status",
    [
        OrderPlanningStatus.APPROVED,
        OrderPlanningStatus.REJECTED,
        OrderPlanningStatus.CANCELLED,
        OrderPlanningStatus.FAILED,
    ],
)
def test_terminal_order_planning_result_requires_completed_at(
    status: OrderPlanningStatus,
) -> None:
    if status is OrderPlanningStatus.APPROVED:
        decision = OrderPlanningDecision.APPROVE
        plan = order_plan()
        error = None
    elif status is OrderPlanningStatus.REJECTED:
        decision = OrderPlanningDecision.REJECT
        plan = None
        error = None
    elif status is OrderPlanningStatus.CANCELLED:
        decision = OrderPlanningDecision.CANCEL
        plan = None
        error = None
    else:
        decision = OrderPlanningDecision.RETRY
        plan = None
        error = "Order planning evaluation failed."

    with pytest.raises(
        ValueError,
        match=(
            "terminal order planning results require "
            "completed_at"
        ),
    ):
        order_planning_result(
            status=status,
            decision=decision,
            plan=plan,
            error=error,
        )


@pytest.mark.parametrize(
    ("status", "decision"),
    [
        (
            OrderPlanningStatus.PENDING,
            OrderPlanningDecision.NO_ACTION,
        ),
        (
            OrderPlanningStatus.ACTIVE,
            OrderPlanningDecision.PROCEED,
        ),
    ],
)
def test_non_terminal_order_planning_result_rejects_completed_at(
    status: OrderPlanningStatus,
    decision: OrderPlanningDecision,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-terminal order planning results must not "
            "include completed_at"
        ),
    ):
        order_planning_result(
            status=status,
            decision=decision,
            completed_at=NOW,
        )


def test_pending_order_planning_result_requires_no_action() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "pending order planning results require "
            "NO_ACTION decision"
        ),
    ):
        order_planning_result(
            status=OrderPlanningStatus.PENDING,
            decision=OrderPlanningDecision.PROCEED,
        )


def test_pending_order_planning_result_rejects_plan() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "pending order planning results must not "
            "include a plan"
        ),
    ):
        order_planning_result(
            status=OrderPlanningStatus.PENDING,
            decision=OrderPlanningDecision.NO_ACTION,
            plan=order_plan(),
        )


def test_active_order_planning_result_requires_proceed() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "active order planning results require "
            "PROCEED decision"
        ),
    ):
        order_planning_result(
            status=OrderPlanningStatus.ACTIVE,
            decision=OrderPlanningDecision.HOLD,
        )


def test_approved_order_planning_result_requires_approve() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "approved order planning results require "
            "APPROVE decision"
        ),
    ):
        order_planning_result(
            status=OrderPlanningStatus.APPROVED,
            decision=OrderPlanningDecision.PROCEED,
            completed_at=NOW,
            plan=order_plan(),
        )


def test_approved_order_planning_result_requires_plan() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "approved order planning results require "
            "a plan"
        ),
    ):
        order_planning_result(
            status=OrderPlanningStatus.APPROVED,
            decision=OrderPlanningDecision.APPROVE,
            completed_at=NOW,
            plan=None,
        )


def test_rejected_order_planning_result_requires_reject() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "rejected order planning results require "
            "REJECT decision"
        ),
    ):
        order_planning_result(
            status=OrderPlanningStatus.REJECTED,
            decision=OrderPlanningDecision.NO_ACTION,
            completed_at=NOW,
        )


def test_cancelled_order_planning_result_requires_cancel() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "cancelled order planning results require "
            "CANCEL decision"
        ),
    ):
        order_planning_result(
            status=OrderPlanningStatus.CANCELLED,
            decision=OrderPlanningDecision.NO_ACTION,
            completed_at=NOW,
        )


@pytest.mark.parametrize(
    "decision",
    [
        OrderPlanningDecision.RETRY,
        OrderPlanningDecision.NO_ACTION,
    ],
)
def test_failed_order_planning_result_allows_retry_or_no_action(
    decision: OrderPlanningDecision,
) -> None:
    result = order_planning_result(
        status=OrderPlanningStatus.FAILED,
        decision=decision,
        completed_at=NOW,
        error="Order planning evaluation failed.",
    )

    assert result.decision is decision


def test_failed_order_planning_result_rejects_success_decision() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed order planning results require "
            "RETRY or NO_ACTION decision"
        ),
    ):
        order_planning_result(
            status=OrderPlanningStatus.FAILED,
            decision=OrderPlanningDecision.APPROVE,
            completed_at=NOW,
            error="Order planning evaluation failed.",
        )


def test_failed_order_planning_result_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed order planning results require "
            "an error"
        ),
    ):
        order_planning_result(
            status=OrderPlanningStatus.FAILED,
            decision=OrderPlanningDecision.RETRY,
            completed_at=NOW,
            error=None,
        )


def test_only_failed_order_planning_result_may_include_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only failed order planning results may "
            "include an error"
        ),
    ):
        order_planning_result(
            status=OrderPlanningStatus.REJECTED,
            decision=OrderPlanningDecision.REJECT,
            completed_at=NOW,
            error="Unexpected error.",
        )


def test_order_planning_result_error_is_normalized() -> None:
    result = order_planning_result(
        status=OrderPlanningStatus.FAILED,
        decision=OrderPlanningDecision.RETRY,
        completed_at=NOW,
        error="  Order planning evaluation failed.  ",
    )

    assert result.error == (
        "Order planning evaluation failed."
    )


def test_order_planning_result_error_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="error must not be empty",
    ):
        order_planning_result(
            status=OrderPlanningStatus.FAILED,
            decision=OrderPlanningDecision.RETRY,
            completed_at=NOW,
            error="   ",
        )


def test_order_planning_result_warnings_are_normalized() -> None:
    result = order_planning_result(
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        )
    )

    assert result.warnings == (
        "warning one",
        "warning two",
    )


def test_order_planning_result_warnings_reject_empty_values() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        order_planning_result(
            warnings=(
                "valid",
                "   ",
            )
        )


def test_order_planning_result_warnings_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        order_planning_result(
            warnings=(
                "valid",
                123,
            )
        )


def test_order_planning_result_metadata_is_normalized() -> None:
    result = order_planning_result(
        metadata=[
            ("  engine  ", "  order-planning  "),
            ("  environment  ", "  paper  "),
        ]
    )

    assert result.metadata == (
        ("engine", "order-planning"),
        ("environment", "paper"),
    )


def test_order_planning_result_metadata_keys_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        order_planning_result(
            metadata=(
                ("engine", "one"),
                ("engine", "two"),
            )
        )


def test_order_planning_result_metadata_items_must_be_pairs() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        order_planning_result(
            metadata=(
                ("engine", "one", "extra"),
            )
        )


def test_order_planning_result_metadata_keys_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        order_planning_result(
            metadata=(
                (1, "value"),
            )
        )


def test_order_planning_result_metadata_values_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        order_planning_result(
            metadata=(
                ("engine", 1),
            )
        )


def test_order_planning_result_is_immutable() -> None:
    result = approved_order_planning_result()

    with pytest.raises(FrozenInstanceError):
        result.status = OrderPlanningStatus.FAILED  # type: ignore[misc]

def order_planning_report(
    **overrides: object,
) -> OrderPlanningReport:
    values: dict[str, object] = {
        "report_id": "order-planning-report-000001",
        "request": order_planning_request(),
        "result": approved_order_planning_result(),
        "reported_at": NOW,
        "message": "Order planning evaluation completed.",
        "warnings": (),
        "metadata": (),
    }

    values.update(overrides)

    return OrderPlanningReport(**values)  # type: ignore[arg-type]


def test_order_planning_report() -> None:
    report = order_planning_report()

    assert report.report_id == (
        "order-planning-report-000001"
    )
    assert report.request_id == "request-001"
    assert report.correlation_id == "correlation-001"
    assert report.strategy_id == "strategy-001"
    assert report.portfolio_id == "portfolio-001"
    assert report.allocation_id == "allocation-001"
    assert report.signal_id == "signal-001"
    assert report.intent_id == "trade-intent-000001"
    assert report.symbol == "NVDA"
    assert report.status is OrderPlanningStatus.APPROVED
    assert report.decision is OrderPlanningDecision.APPROVE
    assert report.plan is not None
    assert report.is_terminal is True
    assert report.reported_at == NOW
    assert report.message == (
        "Order planning evaluation completed."
    )
    assert report.warnings == ()
    assert report.metadata == ()


def test_order_planning_report_text_is_normalized() -> None:
    report = OrderPlanningReport(
        report_id="  order-planning-report-000001  ",
        request=order_planning_request(),
        result=approved_order_planning_result(),
        reported_at=NOW,
        message="  Order planning completed.  ",
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        ),
        metadata=[
            (
                "  source  ",
                "  order-planning-engine  ",
            ),
        ],
    )

    assert report.report_id == (
        "order-planning-report-000001"
    )
    assert report.message == (
        "Order planning completed."
    )
    assert report.warnings == (
        "warning one",
        "warning two",
    )
    assert report.metadata == (
        (
            "source",
            "order-planning-engine",
        ),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_order_planning_report_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "report_id": "order-planning-report-000001",
        "request": order_planning_request(),
        "result": approved_order_planning_result(),
        "reported_at": NOW,
        "message": "Order planning completed.",
    }

    values[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        OrderPlanningReport(
            **values  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_order_planning_report_required_text_must_be_string(
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "report_id": "order-planning-report-000001",
        "request": order_planning_request(),
        "result": approved_order_planning_result(),
        "reported_at": NOW,
        "message": "Order planning completed.",
    }

    values[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        OrderPlanningReport(
            **values  # type: ignore[arg-type]
        )


def test_order_planning_report_requires_request_model() -> None:
    with pytest.raises(
        TypeError,
        match="request must be an OrderPlanningRequest",
    ):
        order_planning_report(
            request=object()
        )


def test_order_planning_report_requires_result_model() -> None:
    with pytest.raises(
        TypeError,
        match="result must be an OrderPlanningResult",
    ):
        order_planning_report(
            result=object()
        )


def test_order_planning_reported_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="reported_at must be a datetime",
    ):
        order_planning_report(
            reported_at="2026-08-11"
        )


def test_order_planning_reported_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="reported_at must be timezone-aware",
    ):
        order_planning_report(
            reported_at=datetime(
                2026,
                8,
                11,
                12,
                0,
            )
        )


def test_order_planning_report_request_id_must_match_result() -> None:
    result = order_planning_result(
        request_id="different-request",
        status=OrderPlanningStatus.REJECTED,
        decision=OrderPlanningDecision.REJECT,
        completed_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result request_id values "
            "must match"
        ),
    ):
        order_planning_report(
            result=result
        )


def test_order_planning_report_correlation_id_must_match_result() -> None:
    result = order_planning_result(
        correlation_id="different-correlation",
        status=OrderPlanningStatus.REJECTED,
        decision=OrderPlanningDecision.REJECT,
        completed_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result correlation_id values "
            "must match"
        ),
    ):
        order_planning_report(
            result=result
        )


def test_order_planning_result_must_not_start_before_request() -> None:
    request = order_planning_request(
        created_at=NOW,
    )

    result = order_planning_result(
        started_at=(
            NOW - timedelta(seconds=1)
        ),
        updated_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match=(
            "result started_at must not be earlier "
            "than request created_at"
        ),
    ):
        order_planning_report(
            request=request,
            result=result,
        )


def test_order_planning_reported_at_must_follow_result_update() -> None:
    result = order_planning_result(
        started_at=NOW,
        updated_at=(
            NOW + timedelta(seconds=1)
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier "
            "than result updated_at"
        ),
    ):
        order_planning_report(
            result=result,
            reported_at=NOW,
        )


def test_order_planning_reported_at_must_follow_completion() -> None:
    completed_at = (
        NOW + timedelta(seconds=1)
    )

    result = order_planning_result(
        status=OrderPlanningStatus.REJECTED,
        decision=OrderPlanningDecision.REJECT,
        started_at=NOW,
        updated_at=NOW,
        completed_at=completed_at,
    )

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier "
            "than result completed_at"
        ),
    ):
        order_planning_report(
            result=result,
            reported_at=NOW,
        )


def test_report_plan_strategy_id_must_match_request() -> None:
    plan = order_plan(
        strategy_id="different-strategy"
    )

    result = order_planning_result(
        status=OrderPlanningStatus.APPROVED,
        decision=OrderPlanningDecision.APPROVE,
        completed_at=NOW,
        plan=plan,
    )

    with pytest.raises(
        ValueError,
        match="plan strategy_id must match request",
    ):
        order_planning_report(
            result=result
        )


def test_report_plan_portfolio_id_must_match_request() -> None:
    plan = order_plan(
        portfolio_id="different-portfolio"
    )

    result = order_planning_result(
        status=OrderPlanningStatus.APPROVED,
        decision=OrderPlanningDecision.APPROVE,
        completed_at=NOW,
        plan=plan,
    )

    with pytest.raises(
        ValueError,
        match="plan portfolio_id must match request",
    ):
        order_planning_report(
            result=result
        )


def test_report_plan_allocation_id_must_match_request() -> None:
    plan = order_plan(
        allocation_id="different-allocation"
    )

    result = order_planning_result(
        status=OrderPlanningStatus.APPROVED,
        decision=OrderPlanningDecision.APPROVE,
        completed_at=NOW,
        plan=plan,
    )

    with pytest.raises(
        ValueError,
        match="plan allocation_id must match request",
    ):
        order_planning_report(
            result=result
        )


def test_report_plan_signal_id_must_match_request() -> None:
    plan = order_plan(
        signal_id="different-signal"
    )

    result = order_planning_result(
        status=OrderPlanningStatus.APPROVED,
        decision=OrderPlanningDecision.APPROVE,
        completed_at=NOW,
        plan=plan,
    )

    with pytest.raises(
        ValueError,
        match="plan signal_id must match request",
    ):
        order_planning_report(
            result=result
        )


def test_report_plan_intent_id_must_match_request() -> None:
    plan = order_plan(
        intent_id="different-intent"
    )

    result = order_planning_result(
        status=OrderPlanningStatus.APPROVED,
        decision=OrderPlanningDecision.APPROVE,
        completed_at=NOW,
        plan=plan,
    )

    with pytest.raises(
        ValueError,
        match="plan intent_id must match request",
    ):
        order_planning_report(
            result=result
        )


def test_report_plan_symbol_must_match_request() -> None:
    plan = order_plan(
        symbol="AAPL"
    )

    result = order_planning_result(
        status=OrderPlanningStatus.APPROVED,
        decision=OrderPlanningDecision.APPROVE,
        completed_at=NOW,
        plan=plan,
    )

    with pytest.raises(
        ValueError,
        match="plan symbol must match request",
    ):
        order_planning_report(
            result=result
        )


def test_report_plan_action_must_match_request() -> None:
    plan = order_plan(
        action=OrderPlanAction.REPLACE,
    )

    result = order_planning_result(
        status=OrderPlanningStatus.APPROVED,
        decision=OrderPlanningDecision.APPROVE,
        completed_at=NOW,
        plan=plan,
    )

    with pytest.raises(
        ValueError,
        match="plan action must match request",
    ):
        order_planning_report(
            result=result
        )


def test_report_plan_side_must_match_request() -> None:
    plan = order_plan(
        side=OrderPlanSide.SELL
    )

    result = order_planning_result(
        status=OrderPlanningStatus.APPROVED,
        decision=OrderPlanningDecision.APPROVE,
        completed_at=NOW,
        plan=plan,
    )

    with pytest.raises(
        ValueError,
        match="plan side must match request",
    ):
        order_planning_report(
            result=result
        )


def test_report_plan_order_type_must_match_request() -> None:
    plan = order_plan(
        order_type=OrderPlanType.LIMIT,
        limit_price=100.0,
    )

    result = order_planning_result(
        status=OrderPlanningStatus.APPROVED,
        decision=OrderPlanningDecision.APPROVE,
        completed_at=NOW,
        plan=plan,
    )

    with pytest.raises(
        ValueError,
        match="plan order_type must match request",
    ):
        order_planning_report(
            result=result
        )


def test_report_plan_time_in_force_must_match_request() -> None:
    plan = order_plan(
        time_in_force=OrderPlanTimeInForce.GTC
    )

    result = order_planning_result(
        status=OrderPlanningStatus.APPROVED,
        decision=OrderPlanningDecision.APPROVE,
        completed_at=NOW,
        plan=plan,
    )

    with pytest.raises(
        ValueError,
        match=(
            "plan time_in_force must match request"
        ),
    ):
        order_planning_report(
            result=result
        )


def test_order_planning_report_exposes_result_state() -> None:
    report = order_planning_report()

    assert (
        report.status
        is OrderPlanningStatus.APPROVED
    )
    assert (
        report.decision
        is OrderPlanningDecision.APPROVE
    )
    assert report.plan is not None
    assert report.is_terminal is True


def test_rejected_order_planning_report() -> None:
    result = order_planning_result(
        status=OrderPlanningStatus.REJECTED,
        decision=OrderPlanningDecision.REJECT,
        completed_at=NOW,
    )

    report = order_planning_report(
        result=result
    )

    assert (
        report.status
        is OrderPlanningStatus.REJECTED
    )
    assert (
        report.decision
        is OrderPlanningDecision.REJECT
    )
    assert report.plan is None
    assert report.is_terminal is True


def test_active_order_planning_report() -> None:
    result = order_planning_result(
        status=OrderPlanningStatus.ACTIVE,
        decision=OrderPlanningDecision.PROCEED,
    )

    report = order_planning_report(
        result=result
    )

    assert report.status is OrderPlanningStatus.ACTIVE
    assert (
        report.decision
        is OrderPlanningDecision.PROCEED
    )
    assert report.is_terminal is False


def test_order_planning_report_warnings_are_normalized() -> None:
    report = order_planning_report(
        warnings=(
            " spread elevated ",
            "spread elevated",
            " liquidity constrained ",
        )
    )

    assert report.warnings == (
        "spread elevated",
        "liquidity constrained",
    )


def test_order_planning_report_warnings_reject_empty_values() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        order_planning_report(
            warnings=(
                "valid",
                "   ",
            )
        )


def test_order_planning_report_warnings_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        order_planning_report(
            warnings=(
                "valid",
                123,
            )
        )


def test_order_planning_report_metadata_is_normalized() -> None:
    report = order_planning_report(
        metadata=[
            (
                " source ",
                " order-planning-engine ",
            ),
            (
                " environment ",
                " paper ",
            ),
        ]
    )

    assert report.metadata == (
        (
            "source",
            "order-planning-engine",
        ),
        (
            "environment",
            "paper",
        ),
    )


def test_order_planning_report_metadata_keys_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        order_planning_report(
            metadata=(
                ("source", "one"),
                ("source", "two"),
            )
        )


def test_order_planning_report_metadata_items_must_be_pairs() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        order_planning_report(
            metadata=(
                (
                    "source",
                    "one",
                    "extra",
                ),
            )
        )


def test_order_planning_report_metadata_keys_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        order_planning_report(
            metadata=(
                (1, "value"),
            )
        )


def test_order_planning_report_metadata_values_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        order_planning_report(
            metadata=(
                ("source", 1),
            )
        )


def test_order_planning_report_is_immutable() -> None:
    report = order_planning_report()

    with pytest.raises(FrozenInstanceError):
        report.report_id = "changed"  # type: ignore[misc]