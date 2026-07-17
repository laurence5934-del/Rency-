import pytest

from app.broker.position_state_machine import (
    InvalidPositionTransition,
    can_transition_position,
    state_for_position_quantity,
    synchronize_position_quantity,
    transition_position,
)
from app.models.position_models import (
    ManagedPosition,
    PositionSide,
    PositionState,
    determine_position_side,
)


def make_position(
    *,
    quantity: float = 10,
    average_cost: float = 100,
    state: PositionState = PositionState.OPEN,
) -> ManagedPosition:
    return ManagedPosition(
        account="DU123456",
        symbol="aapl",
        security_type="STK",
        currency="USD",
        exchange="SMART",
        quantity=quantity,
        average_cost=average_cost,
        state=state,
    )


def test_determine_long_position_side() -> None:
    assert determine_position_side(10) == PositionSide.LONG


def test_determine_short_position_side() -> None:
    assert determine_position_side(-10) == PositionSide.SHORT


def test_determine_flat_position_side() -> None:
    assert determine_position_side(0) == PositionSide.FLAT


def test_position_normalizes_symbol_and_fields() -> None:
    position = make_position()

    assert position.symbol == "AAPL"
    assert position.security_type == "STK"
    assert position.side == PositionSide.LONG


def test_long_position_unrealized_pnl() -> None:
    position = make_position(
        quantity=10,
        average_cost=100,
    )

    position.update_market_price(110)

    assert position.market_value == 1100
    assert position.unrealized_pnl == 100
    assert position.unrealized_pnl_percent == 10


def test_short_position_unrealized_pnl() -> None:
    position = make_position(
        quantity=-10,
        average_cost=100,
    )

    position.update_market_price(90)

    assert position.market_value == -900
    assert position.unrealized_pnl == 100
    assert position.unrealized_pnl_percent == 10


def test_position_rejects_negative_average_cost() -> None:
    with pytest.raises(
        ValueError,
        match="Average cost",
    ):
        make_position(average_cost=-1)


def test_position_rejects_negative_market_price() -> None:
    position = make_position()

    with pytest.raises(
        ValueError,
        match="Current price",
    ):
        position.update_market_price(-1)


def test_ibkr_payload_creates_open_position() -> None:
    position = ManagedPosition.from_ibkr(
        {
            "account": "DU123456",
            "symbol": "MSFT",
            "secType": "STK",
            "currency": "USD",
            "exchange": "SMART",
            "position": 25,
            "avgCost": 400,
        }
    )

    assert position.symbol == "MSFT"
    assert position.quantity == 25
    assert position.state == PositionState.OPEN


def test_pending_position_can_open() -> None:
    position = make_position(
        state=PositionState.PENDING
    )

    result = transition_position(
        position,
        PositionState.OPEN,
    )

    assert result.previous_state == PositionState.PENDING
    assert result.new_state == PositionState.OPEN
    assert position.state == PositionState.OPEN


def test_open_position_can_partially_close() -> None:
    position = make_position()

    result = synchronize_position_quantity(
        position,
        5,
    )

    assert (
        result.new_state
        == PositionState.PARTIALLY_CLOSED
    )
    assert position.quantity == 5
    assert position.closed_quantity == 5


def test_position_can_close() -> None:
    position = make_position()

    result = synchronize_position_quantity(
        position,
        0,
    )

    assert result.new_state == PositionState.CLOSED
    assert position.quantity == 0
    assert position.closed_at is not None


def test_closed_position_cannot_reopen() -> None:
    position = make_position(
        quantity=0,
        state=PositionState.CLOSED,
    )

    with pytest.raises(
        InvalidPositionTransition,
        match="CLOSED -> OPEN",
    ):
        transition_position(
            position,
            PositionState.OPEN,
        )


def test_same_state_transition_is_idempotent() -> None:
    position = make_position()

    result = transition_position(
        position,
        PositionState.OPEN,
    )

    assert result.previous_state == PositionState.OPEN
    assert result.new_state == PositionState.OPEN


@pytest.mark.parametrize(
    (
        "current_quantity",
        "opened_quantity",
        "expected",
    ),
    [
        (10, 10, PositionState.OPEN),
        (5, 10, PositionState.PARTIALLY_CLOSED),
        (0, 10, PositionState.CLOSED),
        (-10, 10, PositionState.OPEN),
        (-5, 10, PositionState.PARTIALLY_CLOSED),
    ],
)
def test_state_is_derived_from_quantity(
    current_quantity: float,
    opened_quantity: float,
    expected: PositionState,
) -> None:
    assert (
        state_for_position_quantity(
            current_quantity=current_quantity,
            opened_quantity=opened_quantity,
        )
        == expected
    )


def test_transition_validation_helper() -> None:
    assert can_transition_position(
        PositionState.OPEN,
        PositionState.CLOSED,
    )

    assert not can_transition_position(
        PositionState.CLOSED,
        PositionState.OPEN,
    )


def test_position_to_dict_contains_calculated_values() -> None:
    position = make_position()
    position.update_market_price(105)

    result = position.to_dict()

    assert result["symbol"] == "AAPL"
    assert result["side"] == "LONG"
    assert result["market_value"] == 1050
    assert result["unrealized_pnl"] == 50
    assert result["state"] == "OPEN"
 
   