import pytest

from app.broker.order_state_machine import (
    can_transition,
    next_state_from_ibkr,
    normalize_ibkr_status,
    require_transition,
)
from app.models.order_models import (
    ManagedOrder,
    OrderState,
)


def test_created_order_can_be_validated():
    assert can_transition(
        OrderState.CREATED,
        OrderState.VALIDATED,
    )


def test_validated_order_can_be_approved():
    assert can_transition(
        OrderState.VALIDATED,
        OrderState.APPROVED,
    )


def test_approved_order_can_begin_submission():
    assert can_transition(
        OrderState.APPROVED,
        OrderState.SUBMITTING,
    )


def test_submitted_order_can_be_partially_filled():
    assert can_transition(
        OrderState.SUBMITTED,
        OrderState.PARTIALLY_FILLED,
    )


def test_terminal_order_cannot_return_to_active_state():
    assert not can_transition(
        OrderState.FILLED,
        OrderState.SUBMITTED,
    )


def test_invalid_transition_raises_error():
    with pytest.raises(
        ValueError,
        match="Invalid order-state transition",
    ):
        require_transition(
            OrderState.CREATED,
            OrderState.FILLED,
        )


def test_normalizes_ibkr_submitted_status():
    state = normalize_ibkr_status(
        "Submitted",
        filled=0,
        remaining=10,
    )

    assert state == OrderState.SUBMITTED


def test_detects_partial_fill_from_quantities():
    state = normalize_ibkr_status(
        "Submitted",
        filled=4,
        remaining=6,
    )

    assert state == OrderState.PARTIALLY_FILLED


def test_detects_completed_fill_from_quantities():
    state = normalize_ibkr_status(
        "Submitted",
        filled=10,
        remaining=0,
    )

    assert state == OrderState.FILLED


def test_maps_ibkr_api_cancelled_status():
    state = normalize_ibkr_status(
        "ApiCancelled",
    )

    assert state == OrderState.CANCELLED


def test_unknown_ibkr_status_maps_to_error():
    state = normalize_ibkr_status(
        "UnexpectedStatus",
    )

    assert state == OrderState.ERROR


def test_next_state_from_ibkr_validates_transition():
    state = next_state_from_ibkr(
        current_state=OrderState.SUBMITTED,
        ibkr_status="Submitted",
        filled=5,
        remaining=5,
    )

    assert state == OrderState.PARTIALLY_FILLED


def test_managed_order_reports_active_state():
    order = ManagedOrder(
        local_order_id=1,
        broker_order_id=100,
        candidate_id=10,
        symbol="AAPL",
        action="BUY",
        quantity=10,
        order_type="MKT",
        limit_price=None,
        state=OrderState.SUBMITTED,
        remaining_quantity=10,
    )

    assert order.is_active is True
    assert order.is_terminal is False


def test_managed_order_serializes_enum_values():
    order = ManagedOrder(
        local_order_id=1,
        broker_order_id=None,
        candidate_id=None,
        symbol="NVDA",
        action="BUY",
        quantity=2,
        order_type="LMT",
        limit_price=150.00,
        state=OrderState.CREATED,
    )

    data = order.to_dict()

    assert data["state"] == "CREATED"
    assert data["symbol"] == "NVDA"
    assert data["paper_only"] is True