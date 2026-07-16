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


def test_submitting_order_can_be_presubmitted():
    assert can_transition(
        OrderState.SUBMITTING,
        OrderState.PRESUBMITTED,
    )


def test_submitting_order_can_be_submitted():
    assert can_transition(
        OrderState.SUBMITTING,
        OrderState.SUBMITTED,
    )


def test_submitted_order_can_be_partially_filled():
    assert can_transition(
        OrderState.SUBMITTED,
        OrderState.PARTIALLY_FILLED,
    )


def test_partially_filled_order_can_be_filled():
    assert can_transition(
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
    )


def test_submitted_order_can_enter_cancel_pending():
    assert can_transition(
        OrderState.SUBMITTED,
        OrderState.CANCEL_PENDING,
    )


def test_cancel_pending_order_can_be_cancelled():
    assert can_transition(
        OrderState.CANCEL_PENDING,
        OrderState.CANCELLED,
    )


def test_terminal_order_cannot_return_to_active_state():
    assert not can_transition(
        OrderState.FILLED,
        OrderState.SUBMITTED,
    )


def test_cancelled_order_cannot_return_to_submitted():
    assert not can_transition(
        OrderState.CANCELLED,
        OrderState.SUBMITTED,
    )


def test_duplicate_non_terminal_state_is_allowed():
    assert can_transition(
        OrderState.SUBMITTED,
        OrderState.SUBMITTED,
    )


def test_duplicate_terminal_state_is_not_allowed():
    assert not can_transition(
        OrderState.FILLED,
        OrderState.FILLED,
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


def test_valid_transition_does_not_raise():
    require_transition(
        OrderState.CREATED,
        OrderState.VALIDATED,
    )


def test_normalizes_ibkr_pending_submit_status():
    state = normalize_ibkr_status(
        "PendingSubmit",
        filled=0,
        remaining=10,
    )

    assert state == OrderState.SUBMITTING


def test_normalizes_ibkr_presubmitted_status():
    state = normalize_ibkr_status(
        "PreSubmitted",
        filled=0,
        remaining=10,
    )

    assert state == OrderState.PRESUBMITTED


def test_normalizes_ibkr_submitted_status():
    state = normalize_ibkr_status(
        "Submitted",
        filled=0,
        remaining=10,
    )

    assert state == OrderState.SUBMITTED


def test_normalizes_ibkr_pending_cancel_status():
    state = normalize_ibkr_status(
        "PendingCancel",
        filled=0,
        remaining=10,
    )

    assert state == OrderState.CANCEL_PENDING


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


def test_maps_ibkr_filled_status():
    state = normalize_ibkr_status(
        "Filled",
        filled=10,
        remaining=0,
    )

    assert state == OrderState.FILLED


def test_maps_ibkr_cancelled_status():
    state = normalize_ibkr_status(
        "Cancelled",
    )

    assert state == OrderState.CANCELLED


def test_maps_ibkr_api_cancelled_status():
    state = normalize_ibkr_status(
        "ApiCancelled",
    )

    assert state == OrderState.CANCELLED


def test_maps_ibkr_inactive_status():
    state = normalize_ibkr_status(
        "Inactive",
    )

    assert state == OrderState.INACTIVE


def test_unknown_ibkr_status_maps_to_error():
    state = normalize_ibkr_status(
        "UnexpectedStatus",
    )

    assert state == OrderState.ERROR


def test_negative_fill_values_are_treated_as_zero():
    state = normalize_ibkr_status(
        "Submitted",
        filled=-1,
        remaining=-5,
    )

    assert state == OrderState.SUBMITTED


def test_next_state_from_ibkr_validates_partial_fill():
    state = next_state_from_ibkr(
        current_state=OrderState.SUBMITTED,
        ibkr_status="Submitted",
        filled=5,
        remaining=5,
    )

    assert state == OrderState.PARTIALLY_FILLED


def test_next_state_from_ibkr_validates_completed_fill():
    state = next_state_from_ibkr(
        current_state=OrderState.PARTIALLY_FILLED,
        ibkr_status="Filled",
        filled=10,
        remaining=0,
    )

    assert state == OrderState.FILLED


def test_next_state_from_ibkr_rejects_invalid_transition():
    with pytest.raises(
        ValueError,
        match="Invalid order-state transition",
    ):
        next_state_from_ibkr(
            current_state=OrderState.CREATED,
            ibkr_status="Filled",
            filled=10,
            remaining=0,
        )


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


def test_managed_order_reports_terminal_state():
    order = ManagedOrder(
        local_order_id=2,
        broker_order_id=101,
        candidate_id=11,
        symbol="NVDA",
        action="BUY",
        quantity=5,
        order_type="LMT",
        limit_price=150.00,
        state=OrderState.FILLED,
        filled_quantity=5,
        remaining_quantity=0,
        average_fill_price=149.75,
        last_fill_price=149.75,
    )

    assert order.is_active is False
    assert order.is_terminal is True


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
    assert data["is_active"] is True
    assert data["is_terminal"] is False


def test_managed_order_serializes_fill_values():
    order = ManagedOrder(
        local_order_id=3,
        broker_order_id=102,
        candidate_id=12,
        symbol="MSFT",
        action="SELL",
        quantity=8,
        order_type="MKT",
        limit_price=None,
        state=OrderState.PARTIALLY_FILLED,
        filled_quantity=3,
        remaining_quantity=5,
        average_fill_price=420.25,
        last_fill_price=420.50,
    )

    data = order.to_dict()

    assert data["filled_quantity"] == 3
    assert data["remaining_quantity"] == 5
    assert data["average_fill_price"] == 420.25
    assert data["last_fill_price"] == 420.50