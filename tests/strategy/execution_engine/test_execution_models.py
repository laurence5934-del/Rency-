from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.execution_engine import (
    ExecutionAction,
    ExecutionDecision,
    ExecutionOrder,
    ExecutionOrderType,
    ExecutionReport,
    ExecutionRequest,
    ExecutionResult,
    ExecutionSide,
    ExecutionStage,
    ExecutionStatus,
    ExecutionTimeInForce,
)


NOW = datetime(
    2026,
    8,
    11,
    20,
    30,
    tzinfo=timezone.utc,
)


def execution_request(
    **overrides: object,
) -> ExecutionRequest:
    values: dict[str, object] = {
        "request_id": "execution-request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "allocation_id": "allocation-001",
        "signal_id": "signal-001",
        "intent_id": "trade-intent-001",
        "plan_id": "order-plan-001",
        "symbol": "NVDA",
        "action": ExecutionAction.SUBMIT,
        "side": ExecutionSide.BUY,
        "order_type": ExecutionOrderType.MARKET,
        "time_in_force": ExecutionTimeInForce.DAY,
        "quantity": 10,
        "confidence": 90,
        "created_at": NOW,
        "requested_by": "order-planning-engine",
    }

    values.update(overrides)

    return ExecutionRequest(**values)  # type: ignore[arg-type]


def test_execution_request() -> None:
    request = execution_request()

    assert request.request_id == "execution-request-001"
    assert request.correlation_id == "correlation-001"
    assert request.strategy_id == "strategy-001"
    assert request.portfolio_id == "portfolio-001"
    assert request.allocation_id == "allocation-001"
    assert request.signal_id == "signal-001"
    assert request.intent_id == "trade-intent-001"
    assert request.plan_id == "order-plan-001"
    assert request.symbol == "NVDA"
    assert request.action is ExecutionAction.SUBMIT
    assert request.side is ExecutionSide.BUY
    assert request.order_type is ExecutionOrderType.MARKET
    assert (
        request.time_in_force
        is ExecutionTimeInForce.DAY
    )
    assert request.quantity == 10
    assert request.confidence == 90
    assert request.created_at == NOW
    assert request.requested_by == "order-planning-engine"
    assert request.limit_price is None
    assert request.stop_price is None
    assert request.sequence_number == 0
    assert request.replay is False
    assert request.metadata == ()


def test_execution_request_text_is_normalized() -> None:
    request = execution_request(
        request_id="  execution-request-001  ",
        correlation_id="  correlation-001  ",
        strategy_id="  strategy-001  ",
        portfolio_id="  portfolio-001  ",
        allocation_id="  allocation-001  ",
        signal_id="  signal-001  ",
        intent_id="  trade-intent-001  ",
        plan_id="  order-plan-001  ",
        symbol="  nvda  ",
        requested_by="  order-planning-engine  ",
    )

    assert request.request_id == "execution-request-001"
    assert request.correlation_id == "correlation-001"
    assert request.strategy_id == "strategy-001"
    assert request.portfolio_id == "portfolio-001"
    assert request.allocation_id == "allocation-001"
    assert request.signal_id == "signal-001"
    assert request.intent_id == "trade-intent-001"
    assert request.plan_id == "order-plan-001"
    assert request.symbol == "nvda"
    assert request.requested_by == "order-planning-engine"


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
        "plan_id",
        "symbol",
        "requested_by",
    ],
)
def test_execution_request_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        execution_request(
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
        "plan_id",
        "symbol",
        "requested_by",
    ],
)
def test_execution_request_required_text_must_be_string(
    field_name: str,
) -> None:
    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        execution_request(
            **{field_name: 123}
        )


def test_execution_request_requires_action_enum() -> None:
    with pytest.raises(
        TypeError,
        match="action must be an ExecutionAction",
    ):
        execution_request(
            action="SUBMIT"
        )


def test_execution_request_requires_side_enum() -> None:
    with pytest.raises(
        TypeError,
        match="side must be an ExecutionSide",
    ):
        execution_request(
            side="BUY"
        )


def test_execution_request_requires_order_type_enum() -> None:
    with pytest.raises(
        TypeError,
        match="order_type must be an ExecutionOrderType",
    ):
        execution_request(
            order_type="MARKET"
        )


def test_execution_request_requires_time_in_force_enum() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "time_in_force must be an "
            "ExecutionTimeInForce"
        ),
    ):
        execution_request(
            time_in_force="DAY"
        )


def test_execution_request_quantity_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="quantity must be an integer",
    ):
        execution_request(
            quantity=10.5
        )


def test_execution_request_quantity_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="quantity must be an integer",
    ):
        execution_request(
            quantity=True
        )


@pytest.mark.parametrize(
    "quantity",
    [0, -1],
)
def test_execution_request_quantity_must_be_positive(
    quantity: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="quantity must be positive",
    ):
        execution_request(
            quantity=quantity
        )


@pytest.mark.parametrize(
    "confidence",
    [-1, 101],
)
def test_execution_request_confidence_bounds(
    confidence: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="confidence must be between 0 and 100",
    ):
        execution_request(
            confidence=confidence
        )


def test_execution_request_confidence_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        execution_request(
            confidence=90.5
        )


def test_execution_request_confidence_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        execution_request(
            confidence=True
        )


@pytest.mark.parametrize(
    "confidence",
    [0, 100],
)
def test_execution_request_confidence_boundaries_allowed(
    confidence: int,
) -> None:
    request = execution_request(
        confidence=confidence
    )

    assert request.confidence == confidence


def test_execution_request_created_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="created_at must be a datetime",
    ):
        execution_request(
            created_at="2026-08-11"
        )


def test_execution_request_created_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="created_at must be timezone-aware",
    ):
        execution_request(
            created_at=datetime(
                2026,
                8,
                11,
                20,
                30,
            )
        )


def test_execution_request_sequence_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="sequence_number must be an integer",
    ):
        execution_request(
            sequence_number=1.5
        )


def test_execution_request_sequence_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="sequence_number must be an integer",
    ):
        execution_request(
            sequence_number=True
        )


def test_execution_request_sequence_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="sequence_number must not be negative",
    ):
        execution_request(
            sequence_number=-1
        )


def test_execution_request_zero_sequence_allowed() -> None:
    request = execution_request(
        sequence_number=0
    )

    assert request.sequence_number == 0


def test_execution_request_replay_requires_bool() -> None:
    with pytest.raises(
        TypeError,
        match="replay must be a bool",
    ):
        execution_request(
            replay="yes"
        )


def test_execution_request_replay() -> None:
    request = execution_request(
        replay=True
    )

    assert request.replay is True


def test_hold_execution_request_requires_none_side() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "HOLD execution requests "
            "require NONE side"
        ),
    ):
        execution_request(
            action=ExecutionAction.HOLD,
            side=ExecutionSide.BUY,
        )


def test_hold_execution_request_with_none_side() -> None:
    request = execution_request(
        action=ExecutionAction.HOLD,
        side=ExecutionSide.NONE,
    )

    assert request.is_actionable is False


def test_actionable_execution_request_rejects_none_side() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "actionable execution requests "
            "require an actionable side"
        ),
    ):
        execution_request(
            side=ExecutionSide.NONE
        )


def test_market_order_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "MARKET orders must not "
            "define limit_price"
        ),
    ):
        execution_request(
            limit_price=100.0
        )


def test_market_order_rejects_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "MARKET orders must not "
            "define stop_price"
        ),
    ):
        execution_request(
            stop_price=95.0
        )


def test_limit_order_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="LIMIT orders require limit_price",
    ):
        execution_request(
            order_type=ExecutionOrderType.LIMIT
        )


def test_limit_order_rejects_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "LIMIT orders must not "
            "define stop_price"
        ),
    ):
        execution_request(
            order_type=ExecutionOrderType.LIMIT,
            limit_price=100.0,
            stop_price=95.0,
        )


def test_limit_execution_request() -> None:
    request = execution_request(
        order_type=ExecutionOrderType.LIMIT,
        limit_price=100.0,
    )

    assert request.limit_price == 100.0
    assert request.stop_price is None


def test_stop_order_requires_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="STOP orders require stop_price",
    ):
        execution_request(
            order_type=ExecutionOrderType.STOP
        )


def test_stop_order_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "STOP orders must not "
            "define limit_price"
        ),
    ):
        execution_request(
            order_type=ExecutionOrderType.STOP,
            stop_price=95.0,
            limit_price=100.0,
        )


def test_stop_execution_request() -> None:
    request = execution_request(
        order_type=ExecutionOrderType.STOP,
        stop_price=95.0,
    )

    assert request.stop_price == 95.0
    assert request.limit_price is None


def test_stop_limit_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "STOP_LIMIT orders require "
            "limit_price"
        ),
    ):
        execution_request(
            order_type=ExecutionOrderType.STOP_LIMIT,
            stop_price=95.0,
        )


def test_stop_limit_requires_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "STOP_LIMIT orders require "
            "stop_price"
        ),
    ):
        execution_request(
            order_type=ExecutionOrderType.STOP_LIMIT,
            limit_price=100.0,
        )


def test_stop_limit_execution_request() -> None:
    request = execution_request(
        order_type=ExecutionOrderType.STOP_LIMIT,
        limit_price=100.0,
        stop_price=95.0,
    )

    assert request.limit_price == 100.0
    assert request.stop_price == 95.0


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("limit_price", 0),
        ("limit_price", -1),
        ("stop_price", 0),
        ("stop_price", -1),
    ],
)
def test_execution_request_prices_must_be_positive(
    field_name: str,
    value: int,
) -> None:
    kwargs: dict[str, object] = {
        "order_type": ExecutionOrderType.STOP_LIMIT,
        "limit_price": 100.0,
        "stop_price": 95.0,
    }

    kwargs[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be positive",
    ):
        execution_request(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("limit_price", "100"),
        ("limit_price", True),
        ("stop_price", "95"),
        ("stop_price", True),
    ],
)
def test_execution_request_prices_require_numbers(
    field_name: str,
    value: object,
) -> None:
    kwargs: dict[str, object] = {
        "order_type": ExecutionOrderType.STOP_LIMIT,
        "limit_price": 100.0,
        "stop_price": 95.0,
    }

    kwargs[field_name] = value

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a number",
    ):
        execution_request(**kwargs)


def test_execution_request_is_actionable() -> None:
    request = execution_request()

    assert request.is_actionable is True


def test_execution_request_market_order_property() -> None:
    request = execution_request()

    assert request.is_market_order is True


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (79, False),
        (80, True),
        (100, True),
    ],
)
def test_execution_request_high_confidence_property(
    confidence: int,
    expected: bool,
) -> None:
    request = execution_request(
        confidence=confidence
    )

    assert request.is_high_confidence is expected


def test_execution_request_metadata_is_normalized() -> None:
    request = execution_request(
        metadata=(
            (
                " source ",
                " order-planning-engine ",
            ),
            (
                " route ",
                " primary ",
            ),
        )
    )

    assert request.metadata == (
        (
            "source",
            "order-planning-engine",
        ),
        (
            "route",
            "primary",
        ),
    )


def test_execution_request_metadata_requires_tuple() -> None:
    with pytest.raises(
        TypeError,
        match="metadata must be a tuple",
    ):
        execution_request(
            metadata=[
                ("source", "order-planning-engine"),
            ]
        )


def test_execution_request_metadata_keys_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        execution_request(
            metadata=(
                ("source", "one"),
                ("source", "two"),
            )
        )


def test_execution_request_metadata_items_must_be_pairs() -> None:
    with pytest.raises(
        TypeError,
        match="metadata items must be pairs",
    ):
        execution_request(
            metadata=(
                ("source", "one", "extra"),
            )
        )


def test_execution_request_metadata_keys_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        execution_request(
            metadata=(
                (1, "value"),
            )
        )


def test_execution_request_metadata_values_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        execution_request(
            metadata=(
                ("source", 1),
            )
        )


def test_execution_request_metadata_keys_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must not be empty",
    ):
        execution_request(
            metadata=(
                ("   ", "value"),
            )
        )


def test_execution_request_is_immutable() -> None:
    request = execution_request()

    with pytest.raises(FrozenInstanceError):
        request.quantity = 20  # type: ignore[misc]

def execution_order(
    **overrides: object,
) -> ExecutionOrder:
    values: dict[str, object] = {
        "order_id": "execution-order-001",
        "request_id": "execution-request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "allocation_id": "allocation-001",
        "signal_id": "signal-001",
        "intent_id": "trade-intent-001",
        "plan_id": "order-plan-001",
        "symbol": "NVDA",
        "action": ExecutionAction.SUBMIT,
        "side": ExecutionSide.BUY,
        "order_type": ExecutionOrderType.MARKET,
        "time_in_force": ExecutionTimeInForce.DAY,
        "quantity": 10,
        "confidence": 90,
        "created_at": NOW,
        "prepared_at": NOW,
        "rationale": "Approved order plan prepared for execution.",
    }

    values.update(overrides)

    return ExecutionOrder(**values)  # type: ignore[arg-type]


def test_execution_order() -> None:
    order = execution_order()

    assert order.order_id == "execution-order-001"
    assert order.request_id == "execution-request-001"
    assert order.correlation_id == "correlation-001"
    assert order.strategy_id == "strategy-001"
    assert order.portfolio_id == "portfolio-001"
    assert order.allocation_id == "allocation-001"
    assert order.signal_id == "signal-001"
    assert order.intent_id == "trade-intent-001"
    assert order.plan_id == "order-plan-001"
    assert order.symbol == "NVDA"
    assert order.action is ExecutionAction.SUBMIT
    assert order.side is ExecutionSide.BUY
    assert order.order_type is ExecutionOrderType.MARKET
    assert (
        order.time_in_force
        is ExecutionTimeInForce.DAY
    )
    assert order.quantity == 10
    assert order.confidence == 90
    assert order.created_at == NOW
    assert order.prepared_at == NOW
    assert order.rationale == (
        "Approved order plan prepared for execution."
    )
    assert order.limit_price is None
    assert order.stop_price is None
    assert order.warnings == ()
    assert order.metadata == ()
    assert order.is_actionable is True
    assert order.is_market_order is True
    assert order.is_high_confidence is True
    assert order.has_warnings is False


def test_execution_order_text_is_normalized() -> None:
    order = execution_order(
        order_id="  execution-order-001  ",
        request_id="  execution-request-001  ",
        correlation_id="  correlation-001  ",
        strategy_id="  strategy-001  ",
        portfolio_id="  portfolio-001  ",
        allocation_id="  allocation-001  ",
        signal_id="  signal-001  ",
        intent_id="  trade-intent-001  ",
        plan_id="  order-plan-001  ",
        symbol="  NVDA  ",
        rationale=(
            "  Approved order plan prepared "
            "for execution.  "
        ),
    )

    assert order.order_id == "execution-order-001"
    assert order.request_id == "execution-request-001"
    assert order.correlation_id == "correlation-001"
    assert order.strategy_id == "strategy-001"
    assert order.portfolio_id == "portfolio-001"
    assert order.allocation_id == "allocation-001"
    assert order.signal_id == "signal-001"
    assert order.intent_id == "trade-intent-001"
    assert order.plan_id == "order-plan-001"
    assert order.symbol == "NVDA"
    assert order.rationale == (
        "Approved order plan prepared for execution."
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "order_id",
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "allocation_id",
        "signal_id",
        "intent_id",
        "plan_id",
        "symbol",
        "rationale",
    ],
)
def test_execution_order_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        execution_order(
            **{field_name: "   "}
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "order_id",
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "allocation_id",
        "signal_id",
        "intent_id",
        "plan_id",
        "symbol",
        "rationale",
    ],
)
def test_execution_order_required_text_must_be_string(
    field_name: str,
) -> None:
    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        execution_order(
            **{field_name: 123}
        )


def test_execution_order_requires_action_enum() -> None:
    with pytest.raises(
        TypeError,
        match="action must be an ExecutionAction",
    ):
        execution_order(
            action="SUBMIT"
        )


def test_execution_order_requires_side_enum() -> None:
    with pytest.raises(
        TypeError,
        match="side must be an ExecutionSide",
    ):
        execution_order(
            side="BUY"
        )


def test_execution_order_requires_order_type_enum() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "order_type must be an ExecutionOrderType"
        ),
    ):
        execution_order(
            order_type="MARKET"
        )


def test_execution_order_requires_time_in_force_enum() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "time_in_force must be an "
            "ExecutionTimeInForce"
        ),
    ):
        execution_order(
            time_in_force="DAY"
        )


def test_execution_order_quantity_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="quantity must be an integer",
    ):
        execution_order(
            quantity=10.5
        )


def test_execution_order_quantity_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="quantity must be an integer",
    ):
        execution_order(
            quantity=True
        )


@pytest.mark.parametrize(
    "quantity",
    [0, -1],
)
def test_execution_order_quantity_must_be_positive(
    quantity: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="quantity must be positive",
    ):
        execution_order(
            quantity=quantity
        )


@pytest.mark.parametrize(
    "confidence",
    [-1, 101],
)
def test_execution_order_confidence_bounds(
    confidence: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="confidence must be between 0 and 100",
    ):
        execution_order(
            confidence=confidence
        )


def test_execution_order_confidence_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        execution_order(
            confidence=90.5
        )


def test_execution_order_confidence_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        execution_order(
            confidence=True
        )


@pytest.mark.parametrize(
    "confidence",
    [0, 100],
)
def test_execution_order_confidence_boundaries_allowed(
    confidence: int,
) -> None:
    order = execution_order(
        confidence=confidence
    )

    assert order.confidence == confidence


def test_execution_order_created_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="created_at must be a datetime",
    ):
        execution_order(
            created_at="2026-08-11"
        )


def test_execution_order_created_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="created_at must be timezone-aware",
    ):
        execution_order(
            created_at=datetime(
                2026,
                8,
                11,
                20,
                30,
            )
        )


def test_execution_order_prepared_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="prepared_at must be a datetime",
    ):
        execution_order(
            prepared_at="2026-08-11"
        )


def test_execution_order_prepared_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="prepared_at must be timezone-aware",
    ):
        execution_order(
            prepared_at=datetime(
                2026,
                8,
                11,
                20,
                30,
            )
        )


def test_execution_order_prepared_at_must_not_precede_created_at() -> None:
    from datetime import timedelta

    with pytest.raises(
        ValueError,
        match=(
            "prepared_at must not be earlier "
            "than created_at"
        ),
    ):
        execution_order(
            prepared_at=(
                NOW - timedelta(microseconds=1)
            )
        )


def test_hold_execution_order_requires_none_side() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "HOLD execution orders "
            "require NONE side"
        ),
    ):
        execution_order(
            action=ExecutionAction.HOLD,
            side=ExecutionSide.BUY,
        )


def test_hold_execution_order_with_none_side() -> None:
    order = execution_order(
        action=ExecutionAction.HOLD,
        side=ExecutionSide.NONE,
    )

    assert order.is_actionable is False


def test_actionable_execution_order_rejects_none_side() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "actionable execution orders "
            "require an actionable side"
        ),
    ):
        execution_order(
            side=ExecutionSide.NONE
        )


def test_execution_order_market_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "MARKET orders must not "
            "define limit_price"
        ),
    ):
        execution_order(
            limit_price=100.0
        )


def test_execution_order_market_rejects_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "MARKET orders must not "
            "define stop_price"
        ),
    ):
        execution_order(
            stop_price=95.0
        )


def test_execution_order_limit_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="LIMIT orders require limit_price",
    ):
        execution_order(
            order_type=ExecutionOrderType.LIMIT
        )


def test_execution_order_limit_rejects_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "LIMIT orders must not "
            "define stop_price"
        ),
    ):
        execution_order(
            order_type=ExecutionOrderType.LIMIT,
            limit_price=100.0,
            stop_price=95.0,
        )


def test_limit_execution_order() -> None:
    order = execution_order(
        order_type=ExecutionOrderType.LIMIT,
        limit_price=100.0,
    )

    assert order.limit_price == 100.0
    assert order.stop_price is None
    assert order.is_market_order is False


def test_execution_order_stop_requires_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match="STOP orders require stop_price",
    ):
        execution_order(
            order_type=ExecutionOrderType.STOP
        )


def test_execution_order_stop_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "STOP orders must not "
            "define limit_price"
        ),
    ):
        execution_order(
            order_type=ExecutionOrderType.STOP,
            stop_price=95.0,
            limit_price=100.0,
        )


def test_stop_execution_order() -> None:
    order = execution_order(
        order_type=ExecutionOrderType.STOP,
        stop_price=95.0,
    )

    assert order.stop_price == 95.0
    assert order.limit_price is None


def test_execution_order_stop_limit_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "STOP_LIMIT orders require "
            "limit_price"
        ),
    ):
        execution_order(
            order_type=ExecutionOrderType.STOP_LIMIT,
            stop_price=95.0,
        )


def test_execution_order_stop_limit_requires_stop_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "STOP_LIMIT orders require "
            "stop_price"
        ),
    ):
        execution_order(
            order_type=ExecutionOrderType.STOP_LIMIT,
            limit_price=100.0,
        )


def test_stop_limit_execution_order() -> None:
    order = execution_order(
        order_type=ExecutionOrderType.STOP_LIMIT,
        limit_price=100.0,
        stop_price=95.0,
    )

    assert order.limit_price == 100.0
    assert order.stop_price == 95.0


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("limit_price", 0),
        ("limit_price", -1),
        ("stop_price", 0),
        ("stop_price", -1),
    ],
)
def test_execution_order_prices_must_be_positive(
    field_name: str,
    value: int,
) -> None:
    kwargs: dict[str, object] = {
        "order_type": ExecutionOrderType.STOP_LIMIT,
        "limit_price": 100.0,
        "stop_price": 95.0,
    }

    kwargs[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be positive",
    ):
        execution_order(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("limit_price", "100"),
        ("limit_price", True),
        ("stop_price", "95"),
        ("stop_price", True),
    ],
)
def test_execution_order_prices_require_numbers(
    field_name: str,
    value: object,
) -> None:
    kwargs: dict[str, object] = {
        "order_type": ExecutionOrderType.STOP_LIMIT,
        "limit_price": 100.0,
        "stop_price": 95.0,
    }

    kwargs[field_name] = value

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a number",
    ):
        execution_order(**kwargs)


def test_execution_order_is_actionable() -> None:
    order = execution_order()

    assert order.is_actionable is True


def test_execution_order_market_order_property() -> None:
    order = execution_order()

    assert order.is_market_order is True


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (79, False),
        (80, True),
        (100, True),
    ],
)
def test_execution_order_high_confidence_property(
    confidence: int,
    expected: bool,
) -> None:
    order = execution_order(
        confidence=confidence
    )

    assert order.is_high_confidence is expected


def test_execution_order_warnings_are_normalized() -> None:
    order = execution_order(
        warnings=(
            " spread elevated ",
            "spread elevated",
            " liquidity constrained ",
        )
    )

    assert order.warnings == (
        "spread elevated",
        "liquidity constrained",
    )

    assert order.has_warnings is True


def test_execution_order_warnings_require_tuple() -> None:
    with pytest.raises(
        TypeError,
        match="warnings must be a tuple",
    ):
        execution_order(
            warnings=["warning"]
        )


def test_execution_order_warnings_reject_empty_values() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        execution_order(
            warnings=(
                "valid",
                "   ",
            )
        )


def test_execution_order_warnings_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        execution_order(
            warnings=(
                "valid",
                123,
            )
        )


def test_execution_order_metadata_is_normalized() -> None:
    order = execution_order(
        metadata=(
            (
                " source ",
                " order-planning-engine ",
            ),
            (
                " route ",
                " primary ",
            ),
        )
    )

    assert order.metadata == (
        (
            "source",
            "order-planning-engine",
        ),
        (
            "route",
            "primary",
        ),
    )


def test_execution_order_metadata_requires_tuple() -> None:
    with pytest.raises(
        TypeError,
        match="metadata must be a tuple",
    ):
        execution_order(
            metadata=[
                ("source", "value"),
            ]
        )


def test_execution_order_metadata_keys_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        execution_order(
            metadata=(
                ("source", "one"),
                ("source", "two"),
            )
        )


def test_execution_order_metadata_items_must_be_pairs() -> None:
    with pytest.raises(
        TypeError,
        match="metadata items must be pairs",
    ):
        execution_order(
            metadata=(
                ("source", "one", "extra"),
            )
        )


def test_execution_order_metadata_keys_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        execution_order(
            metadata=(
                (1, "value"),
            )
        )


def test_execution_order_metadata_values_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        execution_order(
            metadata=(
                ("source", 1),
            )
        )


def test_execution_order_metadata_keys_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must not be empty",
    ):
        execution_order(
            metadata=(
                ("   ", "value"),
            )
        )


def test_execution_order_is_immutable() -> None:
    order = execution_order()

    with pytest.raises(FrozenInstanceError):
        order.quantity = 20  # type: ignore[misc]

LATER = NOW + timedelta(seconds=1)


def execution_result(
    **overrides: object,
) -> ExecutionResult:
    values: dict[str, object] = {
        "request_id": "execution-request-001",
        "correlation_id": "correlation-001",
        "status": ExecutionStatus.PENDING,
        "decision": ExecutionDecision.NO_ACTION,
        "started_at": NOW,
        "updated_at": NOW,
    }

    values.update(overrides)

    return ExecutionResult(**values)  # type: ignore[arg-type]


def ready_execution_result(
    **overrides: object,
) -> ExecutionResult:
    values: dict[str, object] = {
        "status": ExecutionStatus.READY,
        "decision": ExecutionDecision.PROCEED,
        "order": execution_order(),
    }

    values.update(overrides)

    return execution_result(**values)


def test_execution_result_pending() -> None:
    result = execution_result()

    assert result.request_id == "execution-request-001"
    assert result.correlation_id == "correlation-001"
    assert result.status is ExecutionStatus.PENDING
    assert (
        result.decision
        is ExecutionDecision.NO_ACTION
    )
    assert result.started_at == NOW
    assert result.updated_at == NOW
    assert result.completed_at is None
    assert result.order is None
    assert result.filled_quantity == 0
    assert result.average_fill_price is None
    assert result.warnings == ()
    assert result.error is None
    assert result.metadata == ()
    assert result.is_terminal is False
    assert result.is_successful is False
    assert result.has_order is False
    assert result.is_partial_fill is False
    assert result.remaining_quantity is None


def test_execution_result_text_is_normalized() -> None:
    result = execution_result(
        request_id="  execution-request-001  ",
        correlation_id="  correlation-001  ",
    )

    assert result.request_id == "execution-request-001"
    assert result.correlation_id == "correlation-001"


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
    ],
)
def test_execution_result_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        execution_result(
            **{field_name: "   "}
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
    ],
)
def test_execution_result_required_text_must_be_string(
    field_name: str,
) -> None:
    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        execution_result(
            **{field_name: 123}
        )


def test_execution_result_requires_status_enum() -> None:
    with pytest.raises(
        TypeError,
        match="status must be an ExecutionStatus",
    ):
        execution_result(
            status="PENDING"
        )


def test_execution_result_requires_decision_enum() -> None:
    with pytest.raises(
        TypeError,
        match="decision must be an ExecutionDecision",
    ):
        execution_result(
            decision="NO_ACTION"
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "started_at",
        "updated_at",
    ],
)
def test_execution_result_times_require_datetime(
    field_name: str,
) -> None:
    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a datetime",
    ):
        execution_result(
            **{field_name: "2026-08-11"}
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "started_at",
        "updated_at",
    ],
)
def test_execution_result_times_must_be_aware(
    field_name: str,
) -> None:
    naive = datetime(
        2026,
        8,
        11,
        20,
        30,
    )

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be timezone-aware",
    ):
        execution_result(
            **{field_name: naive}
        )


def test_execution_result_updated_at_must_not_precede_started_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "updated_at must not be earlier "
            "than started_at"
        ),
    ):
        execution_result(
            updated_at=(
                NOW - timedelta(microseconds=1)
            )
        )


def test_execution_result_completed_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="completed_at must be a datetime",
    ):
        execution_result(
            status=ExecutionStatus.CANCELLED,
            decision=ExecutionDecision.CANCEL,
            completed_at="2026-08-11",
        )


def test_execution_result_completed_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="completed_at must be timezone-aware",
    ):
        execution_result(
            status=ExecutionStatus.CANCELLED,
            decision=ExecutionDecision.CANCEL,
            completed_at=datetime(
                2026,
                8,
                11,
                20,
                30,
            ),
        )


def test_execution_result_completed_at_must_not_precede_updated_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed_at must not be earlier "
            "than updated_at"
        ),
    ):
        execution_result(
            status=ExecutionStatus.CANCELLED,
            decision=ExecutionDecision.CANCEL,
            updated_at=LATER,
            completed_at=NOW,
        )


def test_execution_result_order_requires_execution_order() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "order must be an ExecutionOrder or None"
        ),
    ):
        ready_execution_result(
            order="execution-order"
        )


def test_execution_result_order_request_id_must_match() -> None:
    order = execution_order(
        request_id="different-request"
    )

    with pytest.raises(
        ValueError,
        match=(
            "order request_id must match "
            "result request_id"
        ),
    ):
        ready_execution_result(
            order=order
        )


def test_execution_result_order_correlation_id_must_match() -> None:
    order = execution_order(
        correlation_id="different-correlation"
    )

    with pytest.raises(
        ValueError,
        match=(
            "order correlation_id must match "
            "result correlation_id"
        ),
    ):
        ready_execution_result(
            order=order
        )


def test_execution_result_order_prepared_at_must_not_precede_started_at() -> None:
    started = NOW + timedelta(seconds=1)

    with pytest.raises(
        ValueError,
        match=(
            "order prepared_at must not be "
            "earlier than result started_at"
        ),
    ):
        ready_execution_result(
            started_at=started,
            updated_at=started,
        )


def test_execution_result_order_prepared_at_must_not_exceed_updated_at() -> None:
    order = execution_order(
        prepared_at=LATER,
    )

    with pytest.raises(
        ValueError,
        match=(
            "order prepared_at must not be "
            "later than result updated_at"
        ),
    ):
        ready_execution_result(
            order=order
        )


def test_execution_result_filled_quantity_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="filled_quantity must be an integer",
    ):
        execution_result(
            filled_quantity=1.5
        )


def test_execution_result_filled_quantity_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="filled_quantity must be an integer",
    ):
        execution_result(
            filled_quantity=True
        )


def test_execution_result_filled_quantity_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "filled_quantity must not be negative"
        ),
    ):
        execution_result(
            filled_quantity=-1
        )


def test_execution_result_fill_must_not_exceed_order_quantity() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "filled_quantity must not exceed "
            "order quantity"
        ),
    ):
        ready_execution_result(
            filled_quantity=11
        )


@pytest.mark.parametrize(
    "value",
    [0, -1],
)
def test_execution_result_average_fill_price_must_be_positive(
    value: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "average_fill_price must be positive"
        ),
    ):
        execution_result(
            filled_quantity=1,
            average_fill_price=value,
        )


@pytest.mark.parametrize(
    "value",
    ["100", True],
)
def test_execution_result_average_fill_price_requires_number(
    value: object,
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "average_fill_price must be a number"
        ),
    ):
        execution_result(
            filled_quantity=1,
            average_fill_price=value,
        )


def test_average_fill_price_requires_positive_fill() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "average_fill_price requires "
            "positive filled_quantity"
        ),
    ):
        execution_result(
            average_fill_price=100.0
        )


def test_non_terminal_execution_result_rejects_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-terminal execution results "
            "must not include completed_at"
        ),
    ):
        execution_result(
            completed_at=NOW
        )


def test_terminal_execution_result_requires_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "terminal execution results "
            "require completed_at"
        ),
    ):
        execution_result(
            status=ExecutionStatus.CANCELLED,
            decision=ExecutionDecision.CANCEL,
        )


def test_pending_execution_result_requires_no_action() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "PENDING execution results "
            "require NO_ACTION decision"
        ),
    ):
        execution_result(
            decision=ExecutionDecision.PROCEED
        )


def test_pending_execution_result_rejects_order() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "PENDING execution results "
            "must not include an order"
        ),
    ):
        execution_result(
            order=execution_order()
        )


def test_ready_execution_result() -> None:
    result = ready_execution_result()

    assert result.status is ExecutionStatus.READY
    assert (
        result.decision
        is ExecutionDecision.PROCEED
    )
    assert result.order is not None
    assert result.has_order is True
    assert result.remaining_quantity == 10
    assert result.is_terminal is False


def test_ready_execution_result_requires_proceed() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "READY execution results "
            "require PROCEED decision"
        ),
    ):
        ready_execution_result(
            decision=ExecutionDecision.NO_ACTION
        )


def test_ready_execution_result_requires_order() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "READY execution results "
            "require an order"
        ),
    ):
        ready_execution_result(
            order=None
        )


def test_submitted_execution_result() -> None:
    result = execution_result(
        status=ExecutionStatus.SUBMITTED,
        decision=ExecutionDecision.SUBMIT,
        order=execution_order(),
    )

    assert result.status is ExecutionStatus.SUBMITTED
    assert (
        result.decision
        is ExecutionDecision.SUBMIT
    )
    assert result.order is not None
    assert result.remaining_quantity == 10
    assert result.is_terminal is False


def test_submitted_execution_result_requires_submit() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "SUBMITTED execution results "
            "require SUBMIT decision"
        ),
    ):
        execution_result(
            status=ExecutionStatus.SUBMITTED,
            decision=ExecutionDecision.PROCEED,
            order=execution_order(),
        )


def test_submitted_execution_result_requires_order() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "SUBMITTED execution results "
            "require an order"
        ),
    ):
        execution_result(
            status=ExecutionStatus.SUBMITTED,
            decision=ExecutionDecision.SUBMIT,
        )


def test_partially_filled_execution_result() -> None:
    result = execution_result(
        status=ExecutionStatus.PARTIALLY_FILLED,
        decision=ExecutionDecision.PROCEED,
        order=execution_order(),
        filled_quantity=4,
        average_fill_price=101.25,
    )

    assert (
        result.status
        is ExecutionStatus.PARTIALLY_FILLED
    )
    assert (
        result.decision
        is ExecutionDecision.PROCEED
    )
    assert result.filled_quantity == 4
    assert result.average_fill_price == 101.25
    assert result.remaining_quantity == 6
    assert result.is_partial_fill is True
    assert result.is_terminal is False


def test_partially_filled_requires_proceed() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "PARTIALLY_FILLED execution results "
            "require PROCEED decision"
        ),
    ):
        execution_result(
            status=ExecutionStatus.PARTIALLY_FILLED,
            decision=ExecutionDecision.NO_ACTION,
            order=execution_order(),
            filled_quantity=4,
            average_fill_price=101.25,
        )


def test_partially_filled_requires_order() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "PARTIALLY_FILLED execution results "
            "require an order"
        ),
    ):
        execution_result(
            status=ExecutionStatus.PARTIALLY_FILLED,
            decision=ExecutionDecision.PROCEED,
            filled_quantity=4,
            average_fill_price=101.25,
        )


def test_partially_filled_requires_positive_quantity() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "PARTIALLY_FILLED execution results "
            "require positive filled_quantity"
        ),
    ):
        execution_result(
            status=ExecutionStatus.PARTIALLY_FILLED,
            decision=ExecutionDecision.PROCEED,
            order=execution_order(),
            filled_quantity=0,
        )


def test_partially_filled_must_be_less_than_order_quantity() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "PARTIALLY_FILLED filled_quantity "
            "must be less than order quantity"
        ),
    ):
        execution_result(
            status=ExecutionStatus.PARTIALLY_FILLED,
            decision=ExecutionDecision.PROCEED,
            order=execution_order(),
            filled_quantity=10,
            average_fill_price=101.25,
        )


def test_partially_filled_requires_average_fill_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "PARTIALLY_FILLED execution results "
            "require average_fill_price"
        ),
    ):
        execution_result(
            status=ExecutionStatus.PARTIALLY_FILLED,
            decision=ExecutionDecision.PROCEED,
            order=execution_order(),
            filled_quantity=4,
        )


def test_filled_execution_result() -> None:
    result = execution_result(
        status=ExecutionStatus.FILLED,
        decision=ExecutionDecision.NO_ACTION,
        order=execution_order(),
        filled_quantity=10,
        average_fill_price=101.25,
        completed_at=NOW,
    )

    assert result.status is ExecutionStatus.FILLED
    assert (
        result.decision
        is ExecutionDecision.NO_ACTION
    )
    assert result.filled_quantity == 10
    assert result.average_fill_price == 101.25
    assert result.remaining_quantity == 0
    assert result.is_terminal is True
    assert result.is_successful is True


def test_filled_execution_result_requires_no_action() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "FILLED execution results "
            "require NO_ACTION decision"
        ),
    ):
        execution_result(
            status=ExecutionStatus.FILLED,
            decision=ExecutionDecision.PROCEED,
            order=execution_order(),
            filled_quantity=10,
            average_fill_price=101.25,
            completed_at=NOW,
        )


def test_filled_execution_result_requires_order() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "FILLED execution results "
            "require an order"
        ),
    ):
        execution_result(
            status=ExecutionStatus.FILLED,
            decision=ExecutionDecision.NO_ACTION,
            completed_at=NOW,
        )


def test_filled_quantity_must_equal_order_quantity() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "FILLED execution results require "
            "filled_quantity equal to order quantity"
        ),
    ):
        execution_result(
            status=ExecutionStatus.FILLED,
            decision=ExecutionDecision.NO_ACTION,
            order=execution_order(),
            filled_quantity=9,
            average_fill_price=101.25,
            completed_at=NOW,
        )


def test_filled_execution_result_requires_average_fill_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "FILLED execution results "
            "require average_fill_price"
        ),
    ):
        execution_result(
            status=ExecutionStatus.FILLED,
            decision=ExecutionDecision.NO_ACTION,
            order=execution_order(),
            filled_quantity=10,
            completed_at=NOW,
        )


def test_cancelled_execution_result() -> None:
    result = execution_result(
        status=ExecutionStatus.CANCELLED,
        decision=ExecutionDecision.CANCEL,
        completed_at=NOW,
    )

    assert result.is_terminal is True
    assert result.is_successful is False


def test_cancelled_requires_cancel_decision() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "CANCELLED execution results "
            "require CANCEL decision"
        ),
    ):
        execution_result(
            status=ExecutionStatus.CANCELLED,
            decision=ExecutionDecision.NO_ACTION,
            completed_at=NOW,
        )


def test_rejected_execution_result() -> None:
    result = execution_result(
        status=ExecutionStatus.REJECTED,
        decision=ExecutionDecision.REJECT,
        completed_at=NOW,
    )

    assert result.is_terminal is True
    assert result.is_successful is False


def test_rejected_requires_reject_decision() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "REJECTED execution results "
            "require REJECT decision"
        ),
    ):
        execution_result(
            status=ExecutionStatus.REJECTED,
            decision=ExecutionDecision.NO_ACTION,
            completed_at=NOW,
        )


@pytest.mark.parametrize(
    "decision",
    [
        ExecutionDecision.RETRY,
        ExecutionDecision.NO_ACTION,
    ],
)
def test_failed_execution_result(
    decision: ExecutionDecision,
) -> None:
    result = execution_result(
        status=ExecutionStatus.FAILED,
        decision=decision,
        completed_at=NOW,
        error="Broker dependency failed.",
    )

    assert result.status is ExecutionStatus.FAILED
    assert result.decision is decision
    assert result.error == "Broker dependency failed."
    assert result.is_terminal is True
    assert result.is_successful is False


def test_failed_execution_result_requires_valid_decision() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "FAILED execution results require "
            "RETRY or NO_ACTION decision"
        ),
    ):
        execution_result(
            status=ExecutionStatus.FAILED,
            decision=ExecutionDecision.REJECT,
            completed_at=NOW,
            error="Broker dependency failed.",
        )


def test_failed_execution_result_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "FAILED execution results "
            "require an error"
        ),
    ):
        execution_result(
            status=ExecutionStatus.FAILED,
            decision=ExecutionDecision.NO_ACTION,
            completed_at=NOW,
        )


def test_execution_result_error_is_normalized() -> None:
    result = execution_result(
        status=ExecutionStatus.FAILED,
        decision=ExecutionDecision.NO_ACTION,
        completed_at=NOW,
        error="  Broker dependency failed.  ",
    )

    assert result.error == "Broker dependency failed."


def test_non_failed_execution_result_rejects_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only FAILED execution results "
            "may include an error"
        ),
    ):
        execution_result(
            error="unexpected error"
        )


def test_execution_result_warnings_are_normalized() -> None:
    result = execution_result(
        warnings=(
            " latency elevated ",
            "latency elevated",
            " broker degraded ",
        )
    )

    assert result.warnings == (
        "latency elevated",
        "broker degraded",
    )


def test_execution_result_metadata_is_normalized() -> None:
    result = execution_result(
        metadata=(
            (" venue ", " primary "),
            (" route ", " smart "),
        )
    )

    assert result.metadata == (
        ("venue", "primary"),
        ("route", "smart"),
    )


def test_execution_result_is_immutable() -> None:
    result = execution_result()

    with pytest.raises(FrozenInstanceError):
        result.filled_quantity = 1  # type: ignore[misc]

def execution_report(
    **overrides: object,
) -> ExecutionReport:
    request = execution_request()

    result = execution_result(
        request_id=request.request_id,
        correlation_id=request.correlation_id,
    )

    values: dict[str, object] = {
        "report_id": "execution-report-001",
        "request": request,
        "result": result,
        "reported_at": NOW,
        "message": "Execution request accepted.",
    }

    values.update(overrides)

    return ExecutionReport(**values)  # type: ignore[arg-type]


def test_execution_report() -> None:
    report = execution_report()

    assert report.report_id == "execution-report-001"
    assert isinstance(report.request, ExecutionRequest)
    assert isinstance(report.result, ExecutionResult)
    assert report.reported_at == NOW
    assert report.message == "Execution request accepted."
    assert report.warnings == ()
    assert report.metadata == ()

    assert report.request_id == "execution-request-001"
    assert report.correlation_id == "correlation-001"
    assert report.strategy_id == "strategy-001"
    assert report.portfolio_id == "portfolio-001"
    assert report.allocation_id == "allocation-001"
    assert report.signal_id == "signal-001"
    assert report.intent_id == "trade-intent-001"
    assert report.plan_id == "order-plan-001"
    assert report.symbol == "NVDA"

    assert report.status is ExecutionStatus.PENDING
    assert (
        report.decision
        is ExecutionDecision.NO_ACTION
    )

    assert report.order is None
    assert report.is_terminal is False
    assert report.is_successful is False


def test_execution_report_text_is_normalized() -> None:
    report = execution_report(
        report_id="  execution-report-001  ",
        message="  Execution request accepted.  ",
    )

    assert report.report_id == "execution-report-001"
    assert report.message == "Execution request accepted."


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_execution_report_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        execution_report(
            **{field_name: "   "}
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_execution_report_required_text_must_be_string(
    field_name: str,
) -> None:
    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        execution_report(
            **{field_name: 123}
        )


def test_execution_report_requires_execution_request() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "request must be an ExecutionRequest"
        ),
    ):
        execution_report(
            request="execution-request"
        )


def test_execution_report_requires_execution_result() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "result must be an ExecutionResult"
        ),
    ):
        execution_report(
            result="execution-result"
        )


def test_execution_report_reported_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="reported_at must be a datetime",
    ):
        execution_report(
            reported_at="2026-08-11"
        )


def test_execution_report_reported_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="reported_at must be timezone-aware",
    ):
        execution_report(
            reported_at=datetime(
                2026,
                8,
                11,
                20,
                30,
            )
        )


def test_execution_report_request_id_must_match() -> None:
    result = execution_result(
        request_id="different-request",
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result request_id "
            "values must match"
        ),
    ):
        execution_report(
            result=result
        )


def test_execution_report_correlation_id_must_match() -> None:
    result = execution_result(
        correlation_id="different-correlation",
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result correlation_id "
            "values must match"
        ),
    ):
        execution_report(
            result=result
        )


def test_execution_report_result_must_not_start_before_request() -> None:
    request = execution_request(
        created_at=LATER,
    )

    result = execution_result(
        request_id=request.request_id,
        correlation_id=request.correlation_id,
        started_at=NOW,
        updated_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match=(
            "result started_at must not be earlier "
            "than request created_at"
        ),
    ):
        execution_report(
            request=request,
            result=result,
            reported_at=LATER,
        )


def test_execution_report_reported_at_must_not_precede_result_update() -> None:
    result = execution_result(
        updated_at=LATER,
    )

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier "
            "than result updated_at"
        ),
    ):
        execution_report(
            result=result,
            reported_at=NOW,
        )


def test_execution_report_reported_at_must_not_precede_completion() -> None:
    completed = LATER

    result = execution_result(
        status=ExecutionStatus.CANCELLED,
        decision=ExecutionDecision.CANCEL,
        updated_at=NOW,
        completed_at=completed,
    )

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier "
            "than result completed_at"
        ),
    ):
        execution_report(
            result=result,
            reported_at=NOW,
        )


def execution_report_with_order(
    *,
    request: ExecutionRequest | None = None,
    order: ExecutionOrder | None = None,
    **overrides: object,
) -> ExecutionReport:
    if request is None:
        request = execution_request()

    if order is None:
        order = execution_order(
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
            prepared_at=request.created_at,
        )

    result = execution_result(
        request_id=request.request_id,
        correlation_id=request.correlation_id,
        status=ExecutionStatus.READY,
        decision=ExecutionDecision.PROCEED,
        started_at=request.created_at,
        updated_at=order.prepared_at,
        order=order,
    )

    values: dict[str, object] = {
        "report_id": "execution-report-001",
        "request": request,
        "result": result,
        "reported_at": result.updated_at,
        "message": "Execution order prepared.",
    }

    values.update(overrides)

    return ExecutionReport(**values)  # type: ignore[arg-type]


def test_execution_report_with_order() -> None:
    report = execution_report_with_order()

    assert report.order is not None
    assert report.status is ExecutionStatus.READY
    assert (
        report.decision
        is ExecutionDecision.PROCEED
    )
    assert report.order.request_id == report.request_id
    assert report.order.plan_id == report.plan_id
    assert report.order.symbol == report.symbol


@pytest.mark.parametrize(
    (
        "request_field",
        "order_value",
        "message",
    ),
    [
        (
            "strategy_id",
            "different-strategy",
            "order strategy_id must match request",
        ),
        (
            "portfolio_id",
            "different-portfolio",
            "order portfolio_id must match request",
        ),
        (
            "allocation_id",
            "different-allocation",
            "order allocation_id must match request",
        ),
        (
            "signal_id",
            "different-signal",
            "order signal_id must match request",
        ),
        (
            "intent_id",
            "different-intent",
            "order intent_id must match request",
        ),
        (
            "plan_id",
            "different-plan",
            "order plan_id must match request",
        ),
        (
            "symbol",
            "AMD",
            "order symbol must match request",
        ),
    ],
)
def test_execution_report_order_lineage_must_match_request(
    request_field: str,
    order_value: str,
    message: str,
) -> None:
    request = execution_request()

    order_values: dict[str, object] = {
        "request_id": request.request_id,
        "correlation_id": request.correlation_id,
        "strategy_id": request.strategy_id,
        "portfolio_id": request.portfolio_id,
        "allocation_id": request.allocation_id,
        "signal_id": request.signal_id,
        "intent_id": request.intent_id,
        "plan_id": request.plan_id,
        "symbol": request.symbol,
        "action": request.action,
        "side": request.side,
        "order_type": request.order_type,
        "time_in_force": request.time_in_force,
        "quantity": request.quantity,
        "confidence": request.confidence,
        "created_at": request.created_at,
        "prepared_at": request.created_at,
    }

    order_values[request_field] = order_value

    order = execution_order(
        **order_values
    )

    with pytest.raises(
        ValueError,
        match=message,
    ):
        execution_report_with_order(
            request=request,
            order=order,
        )


def test_execution_report_order_action_must_match_request() -> None:
    request = execution_request(
        action=ExecutionAction.HOLD,
        side=ExecutionSide.NONE,
    )

    order = execution_order(
        request_id=request.request_id,
        correlation_id=request.correlation_id,
        strategy_id=request.strategy_id,
        portfolio_id=request.portfolio_id,
        allocation_id=request.allocation_id,
        signal_id=request.signal_id,
        intent_id=request.intent_id,
        plan_id=request.plan_id,
        symbol=request.symbol,
        action=ExecutionAction.SUBMIT,
        side=ExecutionSide.BUY,
        order_type=request.order_type,
        time_in_force=request.time_in_force,
        quantity=request.quantity,
        confidence=request.confidence,
        created_at=request.created_at,
        prepared_at=request.created_at,
    )

    with pytest.raises(
        ValueError,
        match="order action must match request",
    ):
        execution_report_with_order(
            request=request,
            order=order,
        )


def test_execution_report_order_side_must_match_request() -> None:
    request = execution_request(
        side=ExecutionSide.BUY,
    )

    order = execution_order(
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
        side=ExecutionSide.SELL,
        order_type=request.order_type,
        time_in_force=request.time_in_force,
        quantity=request.quantity,
        confidence=request.confidence,
        created_at=request.created_at,
        prepared_at=request.created_at,
    )

    with pytest.raises(
        ValueError,
        match="order side must match request",
    ):
        execution_report_with_order(
            request=request,
            order=order,
        )


def test_execution_report_order_type_must_match_request() -> None:
    request = execution_request()

    order = execution_order(
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
        order_type=ExecutionOrderType.LIMIT,
        time_in_force=request.time_in_force,
        quantity=request.quantity,
        confidence=request.confidence,
        created_at=request.created_at,
        prepared_at=request.created_at,
        limit_price=100.0,
    )

    with pytest.raises(
        ValueError,
        match="order order_type must match request",
    ):
        execution_report_with_order(
            request=request,
            order=order,
        )


def test_execution_report_time_in_force_must_match_request() -> None:
    request = execution_request()

    order = execution_order(
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
        time_in_force=ExecutionTimeInForce.GTC,
        quantity=request.quantity,
        confidence=request.confidence,
        created_at=request.created_at,
        prepared_at=request.created_at,
    )

    with pytest.raises(
        ValueError,
        match=(
            "order time_in_force must match request"
        ),
    ):
        execution_report_with_order(
            request=request,
            order=order,
        )


def test_execution_report_quantity_must_match_request() -> None:
    request = execution_request()

    order = execution_order(
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
        quantity=request.quantity + 1,
        confidence=request.confidence,
        created_at=request.created_at,
        prepared_at=request.created_at,
    )

    with pytest.raises(
        ValueError,
        match="order quantity must match request",
    ):
        execution_report_with_order(
            request=request,
            order=order,
        )


def test_execution_report_warnings_are_normalized() -> None:
    report = execution_report(
        warnings=(
            " venue latency elevated ",
            "venue latency elevated",
            " broker degraded ",
        )
    )

    assert report.warnings == (
        "venue latency elevated",
        "broker degraded",
    )


def test_execution_report_warnings_require_tuple() -> None:
    with pytest.raises(
        TypeError,
        match="warnings must be a tuple",
    ):
        execution_report(
            warnings=["warning"]
        )


def test_execution_report_warnings_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        execution_report(
            warnings=(
                "valid warning",
                123,
            )
        )


def test_execution_report_warnings_reject_empty_values() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        execution_report(
            warnings=(
                "valid warning",
                "   ",
            )
        )


def test_execution_report_metadata_is_normalized() -> None:
    report = execution_report(
        metadata=(
            (" venue ", " primary "),
            (" route ", " smart "),
        )
    )

    assert report.metadata == (
        ("venue", "primary"),
        ("route", "smart"),
    )


def test_execution_report_metadata_requires_tuple() -> None:
    with pytest.raises(
        TypeError,
        match="metadata must be a tuple",
    ):
        execution_report(
            metadata=[
                ("venue", "primary"),
            ]
        )


def test_execution_report_metadata_keys_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        execution_report(
            metadata=(
                ("venue", "primary"),
                ("venue", "secondary"),
            )
        )


def test_execution_report_metadata_items_must_be_pairs() -> None:
    with pytest.raises(
        TypeError,
        match="metadata items must be pairs",
    ):
        execution_report(
            metadata=(
                ("venue", "primary", "extra"),
            )
        )


def test_execution_report_metadata_keys_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        execution_report(
            metadata=(
                (1, "primary"),
            )
        )


def test_execution_report_metadata_values_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        execution_report(
            metadata=(
                ("venue", 1),
            )
        )


def test_execution_report_metadata_keys_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must not be empty",
    ):
        execution_report(
            metadata=(
                ("   ", "primary"),
            )
        )


def test_execution_report_terminal_properties() -> None:
    request = execution_request()

    order = execution_order(
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
        prepared_at=request.created_at,
    )

    result = execution_result(
        request_id=request.request_id,
        correlation_id=request.correlation_id,
        status=ExecutionStatus.FILLED,
        decision=ExecutionDecision.NO_ACTION,
        started_at=request.created_at,
        updated_at=request.created_at,
        completed_at=request.created_at,
        order=order,
        filled_quantity=order.quantity,
        average_fill_price=101.25,
    )

    report = execution_report(
        request=request,
        result=result,
        reported_at=request.created_at,
        message="Execution completed.",
    )

    assert report.status is ExecutionStatus.FILLED
    assert (
        report.decision
        is ExecutionDecision.NO_ACTION
    )
    assert report.order is order
    assert report.is_terminal is True
    assert report.is_successful is True


def test_execution_report_is_immutable() -> None:
    report = execution_report()

    with pytest.raises(FrozenInstanceError):
        report.message = "Changed."  # type: ignore[misc]