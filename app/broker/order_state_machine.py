"""
Order Lifecycle State Machine
AI Trading Platform Version 7.7

Validates OMS state transitions and normalizes IBKR statuses.
"""

from __future__ import annotations

from typing import Any

from app.models.order_models import (
    OrderState,
    TERMINAL_ORDER_STATES,
)


ALLOWED_TRANSITIONS: dict[
    OrderState,
    set[OrderState],
] = {
    OrderState.CREATED: {
        OrderState.VALIDATED,
        OrderState.REJECTED,
        OrderState.ERROR,
    },
    OrderState.VALIDATED: {
        OrderState.APPROVED,
        OrderState.REJECTED,
        OrderState.ERROR,
    },
    OrderState.APPROVED: {
        OrderState.SUBMITTING,
        OrderState.REJECTED,
        OrderState.ERROR,
    },
    
    OrderState.SUBMITTING: {
        OrderState.PRESUBMITTED,
        OrderState.SUBMITTED,
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
        OrderState.CANCEL_PENDING,
        OrderState.CANCELLED,
        OrderState.REJECTED,
        OrderState.INACTIVE,
        OrderState.ERROR,
    },
    OrderState.PRESUBMITTED: {
        OrderState.SUBMITTED,
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
        OrderState.CANCEL_PENDING,
        OrderState.CANCELLED,
        OrderState.INACTIVE,
        OrderState.ERROR,
    },
    OrderState.SUBMITTED: {
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
        OrderState.CANCEL_PENDING,
        OrderState.CANCELLED,
        OrderState.INACTIVE,
        OrderState.ERROR,
    },
    OrderState.PARTIALLY_FILLED: {
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
        OrderState.CANCEL_PENDING,
        OrderState.CANCELLED,
        OrderState.INACTIVE,
        OrderState.ERROR,
    },
    OrderState.CANCEL_PENDING: {
        OrderState.CANCELLED,
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
        OrderState.INACTIVE,
        OrderState.ERROR,
    },
    OrderState.FILLED: set(),
    OrderState.CANCELLED: set(),
    OrderState.REJECTED: set(),
    OrderState.INACTIVE: set(),
    OrderState.ERROR: set(),
}


IBKR_STATUS_MAP: dict[str, OrderState] = {
    "PENDINGSUBMIT": OrderState.SUBMITTING,
    "PRESUBMITTED": OrderState.PRESUBMITTED,
    "SUBMITTED": OrderState.SUBMITTED,
    "PENDINGCANCEL": OrderState.CANCEL_PENDING,
    "CANCELLED": OrderState.CANCELLED,
    "APICANCELLED": OrderState.CANCELLED,
    "FILLED": OrderState.FILLED,
    "INACTIVE": OrderState.INACTIVE,
}


def normalize_ibkr_status(
    status: Any,
    *,
    filled: float = 0.0,
    remaining: float = 0.0,
) -> OrderState:
    normalized = str(status or "").strip().upper()

    normalized_filled = max(float(filled or 0.0), 0.0)
    normalized_remaining = max(float(remaining or 0.0), 0.0)

    if normalized_filled > 0 and normalized_remaining > 0:
        return OrderState.PARTIALLY_FILLED

    if normalized_filled > 0 and normalized_remaining == 0:
        return OrderState.FILLED

    return IBKR_STATUS_MAP.get(
        normalized,
        OrderState.ERROR,
    )


def can_transition(
    current_state: OrderState,
    new_state: OrderState,
) -> bool:
    if current_state == new_state:
        return current_state not in TERMINAL_ORDER_STATES

    return new_state in ALLOWED_TRANSITIONS.get(
        current_state,
        set(),
    )


def require_transition(
    current_state: OrderState,
    new_state: OrderState,
) -> None:
    if not can_transition(
        current_state,
        new_state,
    ):
        raise ValueError(
            "Invalid order-state transition: "
            f"{current_state.value} -> {new_state.value}"
        )


def next_state_from_ibkr(
    *,
    current_state: OrderState,
    ibkr_status: Any,
    filled: float = 0.0,
    remaining: float = 0.0,
) -> OrderState:
    new_state = normalize_ibkr_status(
        ibkr_status,
        filled=filled,
        remaining=remaining,
    )

    require_transition(
        current_state,
        new_state,
    )

    return new_state