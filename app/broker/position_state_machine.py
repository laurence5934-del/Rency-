from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final

from app.models.position_models import (
    ManagedPosition,
    PositionState,
)


class InvalidPositionTransition(ValueError):
    """Raised when a position lifecycle transition is invalid."""


ALLOWED_POSITION_TRANSITIONS: Final[
    dict[PositionState, frozenset[PositionState]]
] = {
    PositionState.PENDING: frozenset(
        {
            PositionState.OPEN,
            PositionState.CLOSED,
            PositionState.ERROR,
        }
    ),
    PositionState.OPEN: frozenset(
        {
            PositionState.PARTIALLY_CLOSED,
            PositionState.CLOSED,
            PositionState.ERROR,
        }
    ),
    PositionState.PARTIALLY_CLOSED: frozenset(
        {
            PositionState.PARTIALLY_CLOSED,
            PositionState.CLOSED,
            PositionState.ERROR,
        }
    ),
    PositionState.CLOSED: frozenset(),
    PositionState.ERROR: frozenset(),
}


@dataclass(frozen=True, slots=True)
class PositionTransition:
    previous_state: PositionState
    new_state: PositionState
    message: str | None = None


def can_transition_position(
    current_state: PositionState,
    new_state: PositionState,
) -> bool:
    if current_state == new_state:
        return True

    return (
        new_state
        in ALLOWED_POSITION_TRANSITIONS[current_state]
    )


def validate_position_transition(
    current_state: PositionState,
    new_state: PositionState,
) -> None:
    if can_transition_position(
        current_state,
        new_state,
    ):
        return

    raise InvalidPositionTransition(
        "Invalid position transition: "
        f"{current_state.value} -> {new_state.value}"
    )


def transition_position(
    position: ManagedPosition,
    new_state: PositionState,
    *,
    message: str | None = None,
) -> PositionTransition:
    previous_state = position.state

    validate_position_transition(
        previous_state,
        new_state,
    )

    position.state = new_state
    position.updated_at = datetime.now(timezone.utc)

    if new_state == PositionState.CLOSED:
        position.quantity = 0.0
        position.closed_at = position.updated_at

    return PositionTransition(
        previous_state=previous_state,
        new_state=new_state,
        message=message,
    )


def state_for_position_quantity(
    *,
    current_quantity: float,
    opened_quantity: float,
) -> PositionState:
    current_absolute = abs(float(current_quantity))
    opened_absolute = abs(float(opened_quantity))

    if current_absolute == 0:
        return PositionState.CLOSED

    if opened_absolute <= 0:
        return PositionState.OPEN

    if current_absolute < opened_absolute:
        return PositionState.PARTIALLY_CLOSED

    return PositionState.OPEN


def synchronize_position_quantity(
    position: ManagedPosition,
    new_quantity: float,
    *,
    message: str | None = None,
) -> PositionTransition:
    quantity = float(new_quantity)

    new_state = state_for_position_quantity(
        current_quantity=quantity,
        opened_quantity=float(
            position.opened_quantity or 0.0
        ),
    )

    position.quantity = quantity

    return transition_position(
        position,
        new_state,
        message=message,
    )

  