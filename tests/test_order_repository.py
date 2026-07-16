import sqlite3

import pytest

from app.db.order_repository import (
    OrderRepository,
)
from app.models.order_models import (
    OrderState,
)


def make_order_request(
    *,
    symbol: str = "AAPL",
    action: str = "BUY",
    quantity: int = 10,
    order_type: str = "MKT",
    limit_price: float | None = None,
) -> dict:
    return {
        "symbol": symbol,
        "action": action,
        "quantity": quantity,
        "order_type": order_type,
        "limit_price": limit_price,
        "paper_only": True,
        "transmit": False,
    }


@pytest.fixture
def repository(
    tmp_path,
) -> OrderRepository:
    return OrderRepository(
        tmp_path / "oms_test.db"
    )


def test_initializes_order_tables(
    repository,
):
    with sqlite3.connect(
        repository.db_path
    ) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

    assert "managed_orders" in tables
    assert "order_events" in tables


def test_creates_managed_order(
    repository,
):
    order = repository.create_order(
        make_order_request(),
        candidate_id=101,
        strategy="MOMENTUM",
    )

    assert order.local_order_id is not None
    assert order.broker_order_id is None
    assert order.candidate_id == 101
    assert order.symbol == "AAPL"
    assert order.action == "BUY"
    assert order.quantity == 10
    assert order.state == OrderState.CREATED
    assert order.remaining_quantity == 10
    assert order.paper_only is True


def test_creation_records_initial_event(
    repository,
):
    order = repository.create_order(
        make_order_request()
    )

    events = repository.list_order_events(
        order.local_order_id
    )

    assert len(events) == 1
    assert events[0].previous_state is None
    assert (
        events[0].new_state
        == OrderState.CREATED
    )
    assert events[0].source == "OMS"


def test_retrieves_order_by_local_id(
    repository,
):
    created = repository.create_order(
        make_order_request(
            symbol="NVDA",
        )
    )

    loaded = repository.get_order(
        created.local_order_id
    )

    assert loaded is not None
    assert loaded.symbol == "NVDA"
    assert (
        loaded.local_order_id
        == created.local_order_id
    )


def test_sets_and_finds_broker_order_id(
    repository,
):
    created = repository.create_order(
        make_order_request()
    )

    updated = repository.set_broker_order_id(
        created.local_order_id,
        5001,
    )

    assert updated.broker_order_id == 5001

    loaded = repository.get_order_by_broker_id(
        5001
    )

    assert loaded is not None
    assert (
        loaded.local_order_id
        == created.local_order_id
    )


def test_prevents_active_duplicate_order(
    repository,
):
    repository.create_order(
        make_order_request(),
        strategy="BREAKOUT",
    )

    with pytest.raises(
        ValueError,
        match="active duplicate order",
    ):
        repository.create_order(
            make_order_request(),
            strategy="BREAKOUT",
        )


def test_allows_different_strategy_duplicate(
    repository,
):
    repository.create_order(
        make_order_request(),
        strategy="BREAKOUT",
    )

    second = repository.create_order(
        make_order_request(),
        strategy="MEAN_REVERSION",
    )

    assert second.local_order_id is not None


def test_allows_opposite_action_for_same_symbol(
    repository,
):
    repository.create_order(
        make_order_request(
            action="BUY",
        ),
        strategy="REVERSAL",
    )

    sell_order = repository.create_order(
        make_order_request(
            action="SELL",
        ),
        strategy="REVERSAL",
    )

    assert sell_order.action == "SELL"


def test_rejects_non_paper_order(
    repository,
):
    request = make_order_request()
    request["paper_only"] = False

    with pytest.raises(
        ValueError,
        match="paper-only",
    ):
        repository.create_order(request)


def test_rejects_invalid_limit_order(
    repository,
):
    with pytest.raises(
        ValueError,
        match="positive limit price",
    ):
        repository.create_order(
            make_order_request(
                order_type="LMT",
                limit_price=None,
            )
        )


def test_transitions_order_and_records_event(
    repository,
):
    created = repository.create_order(
        make_order_request()
    )

    validated = repository.transition_order(
        created.local_order_id,
        OrderState.VALIDATED,
        source="RISK_MANAGER",
        message="Validation passed.",
    )

    assert (
        validated.state
        == OrderState.VALIDATED
    )

    events = repository.list_order_events(
        created.local_order_id
    )

    assert len(events) == 2
    assert (
        events[-1].previous_state
        == OrderState.CREATED
    )
    assert (
        events[-1].new_state
        == OrderState.VALIDATED
    )
    assert (
        events[-1].source
        == "RISK_MANAGER"
    )


def test_rejects_invalid_state_transition(
    repository,
):
    created = repository.create_order(
        make_order_request()
    )

    with pytest.raises(
        ValueError,
        match="Invalid order-state transition",
    ):
        repository.transition_order(
            created.local_order_id,
            OrderState.FILLED,
            source="TEST",
        )


def test_lists_active_orders(
    repository,
):
    first = repository.create_order(
        make_order_request(
            symbol="AAPL",
        )
    )

    second = repository.create_order(
        make_order_request(
            symbol="MSFT",
        )
    )

    repository.transition_order(
        first.local_order_id,
        OrderState.REJECTED,
        source="TEST",
    )

    active_orders = repository.list_orders(
        active_only=True
    )

    active_ids = {
        order.local_order_id
        for order in active_orders
    }

    assert first.local_order_id not in active_ids
    assert second.local_order_id in active_ids


def test_updates_partial_fill(
    repository,
):
    order = repository.create_order(
        make_order_request()
    )

    repository.transition_order(
        order.local_order_id,
        OrderState.VALIDATED,
        source="TEST",
    )
    repository.transition_order(
        order.local_order_id,
        OrderState.APPROVED,
        source="TEST",
    )
    repository.transition_order(
        order.local_order_id,
        OrderState.SUBMITTING,
        source="TEST",
    )
    repository.transition_order(
        order.local_order_id,
        OrderState.SUBMITTED,
        source="IBKR",
    )

    updated = repository.update_execution(
        order.local_order_id,
        filled_quantity=4,
        remaining_quantity=6,
        average_fill_price=199.50,
        last_fill_price=199.75,
    )

    assert (
        updated.state
        == OrderState.PARTIALLY_FILLED
    )
    assert updated.filled_quantity == 4
    assert updated.remaining_quantity == 6
    assert (
        updated.average_fill_price
        == 199.50
    )


def test_updates_completed_fill(
    repository,
):
    order = repository.create_order(
        make_order_request()
    )

    repository.transition_order(
        order.local_order_id,
        OrderState.VALIDATED,
        source="TEST",
    )
    repository.transition_order(
        order.local_order_id,
        OrderState.APPROVED,
        source="TEST",
    )
    repository.transition_order(
        order.local_order_id,
        OrderState.SUBMITTING,
        source="TEST",
    )
    repository.transition_order(
        order.local_order_id,
        OrderState.SUBMITTED,
        source="IBKR",
    )

    updated = repository.update_execution(
        order.local_order_id,
        filled_quantity=10,
        remaining_quantity=0,
        average_fill_price=200.10,
        last_fill_price=200.10,
    )

    assert updated.state == OrderState.FILLED
    assert updated.is_terminal is True
    assert updated.filled_quantity == 10
    assert updated.remaining_quantity == 0


def test_stores_broker_payload_in_event(
    repository,
):
    order = repository.create_order(
        make_order_request()
    )

    repository.transition_order(
        order.local_order_id,
        OrderState.VALIDATED,
        source="IBKR",
        broker_payload={
            "status": "Validated",
            "request_id": 77,
        },
    )

    events = repository.list_order_events(
        order.local_order_id
    )

    assert events[-1].broker_payload == {
        "status": "Validated",
        "request_id": 77,
    }


def test_missing_order_transition_raises_key_error(
    repository,
):
    with pytest.raises(
        KeyError,
        match="does not exist",
    ):
        repository.transition_order(
            99999,
            OrderState.VALIDATED,
            source="TEST",
        )