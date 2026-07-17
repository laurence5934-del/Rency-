import pytest

from app.broker.order_manager import (
    OrderManager,
)
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
        tmp_path / "order_manager_test.db"
    )


def test_submits_and_persists_order(
    repository,
):
    def fake_submitter(
        order_request,
        *,
        paper_account_confirmed,
        wait_seconds,
    ):
        assert paper_account_confirmed is True
        assert wait_seconds == 2.0

        return {
            "submitted": True,
            "status": "Submitted",
            "order_id": 5001,
            "statuses": [
                {
                    "orderId": 5001,
                    "status": "Submitted",
                    "filled": 0,
                    "remaining": 10,
                    "avgFillPrice": 0,
                    "lastFillPrice": 0,
                }
            ],
            "fills": [],
            "errors": [],
        }

    manager = OrderManager(
        repository,
        broker_submitter=fake_submitter,
    )

    result = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=True,
        candidate_id=101,
        strategy="BREAKOUT",
        wait_seconds=2.0,
    )

    assert result["submitted"] is True
    assert result["broker_order_id"] == 5001
    assert result["state"] == "SUBMITTED"

    stored = repository.get_order(
        result["local_order_id"]
    )

    assert stored is not None
    assert stored.broker_order_id == 5001
    assert stored.candidate_id == 101
    assert stored.strategy == "BREAKOUT"
    assert stored.state == OrderState.SUBMITTED


def test_records_complete_lifecycle_events(
    repository,
):
    def fake_submitter(*args, **kwargs):
        return {
            "submitted": True,
            "status": "Submitted",
            "order_id": 5002,
            "statuses": [
                {
                    "orderId": 5002,
                    "status": "Submitted",
                    "filled": 0,
                    "remaining": 10,
                }
            ],
        }

    manager = OrderManager(
        repository,
        broker_submitter=fake_submitter,
    )

    result = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=True,
    )

    events = repository.list_order_events(
        result["local_order_id"]
    )

    assert [
        event.new_state
        for event in events
    ] == [
        OrderState.CREATED,
        OrderState.VALIDATED,
        OrderState.APPROVED,
        OrderState.SUBMITTING,
        OrderState.SUBMITTED,
    ]


def test_handles_presubmitted_status(
    repository,
):
    def fake_submitter(*args, **kwargs):
        return {
            "submitted": True,
            "status": "PreSubmitted",
            "order_id": 5003,
            "statuses": [
                {
                    "orderId": 5003,
                    "status": "PreSubmitted",
                    "filled": 0,
                    "remaining": 10,
                }
            ],
        }

    manager = OrderManager(
        repository,
        broker_submitter=fake_submitter,
    )

    result = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=True,
    )

    assert result["state"] == "PRESUBMITTED"


def test_handles_awaiting_status_as_submitted(
    repository,
):
    def fake_submitter(*args, **kwargs):
        return {
            "submitted": True,
            "status": "AWAITING_STATUS",
            "order_id": 5004,
            "statuses": [],
        }

    manager = OrderManager(
        repository,
        broker_submitter=fake_submitter,
    )

    result = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=True,
    )

    assert result["submitted"] is True
    assert result["state"] == "SUBMITTED"


def test_records_partial_fill(
    repository,
):
    def fake_submitter(*args, **kwargs):
        return {
            "submitted": True,
            "status": "Submitted",
            "order_id": 5005,
            "statuses": [
                {
                    "orderId": 5005,
                    "status": "Submitted",
                    "filled": 4,
                    "remaining": 6,
                    "avgFillPrice": 199.50,
                    "lastFillPrice": 199.75,
                }
            ],
        }

    manager = OrderManager(
        repository,
        broker_submitter=fake_submitter,
    )

    result = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=True,
    )

    assert result["state"] == "PARTIALLY_FILLED"

    order = repository.get_order(
        result["local_order_id"]
    )

    assert order is not None
    assert order.filled_quantity == 4
    assert order.remaining_quantity == 6
    assert order.average_fill_price == 199.50
    assert order.last_fill_price == 199.75


def test_records_complete_fill(
    repository,
):
    def fake_submitter(*args, **kwargs):
        return {
            "submitted": True,
            "status": "Filled",
            "order_id": 5006,
            "statuses": [
                {
                    "orderId": 5006,
                    "status": "Filled",
                    "filled": 10,
                    "remaining": 0,
                    "avgFillPrice": 200.10,
                    "lastFillPrice": 200.10,
                }
            ],
        }

    manager = OrderManager(
        repository,
        broker_submitter=fake_submitter,
    )

    result = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=True,
    )

    assert result["state"] == "FILLED"

    order = repository.get_order(
        result["local_order_id"]
    )

    assert order is not None
    assert order.is_terminal is True
    assert order.filled_quantity == 10


def test_maps_cancelled_submission(
    repository,
):
    def fake_submitter(*args, **kwargs):
        return {
            "submitted": False,
            "status": "Cancelled",
            "order_id": 5007,
            "statuses": [],
        }

    manager = OrderManager(
        repository,
        broker_submitter=fake_submitter,
    )

    result = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=True,
    )

    assert result["submitted"] is False
    assert result["state"] == "CANCELLED"


def test_maps_inactive_submission(
    repository,
):
    def fake_submitter(*args, **kwargs):
        return {
            "submitted": False,
            "status": "Inactive",
            "order_id": 5008,
            "statuses": [],
        }

    manager = OrderManager(
        repository,
        broker_submitter=fake_submitter,
    )

    result = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=True,
    )

    assert result["state"] == "INACTIVE"


def test_maps_guard_rejection(
    repository,
):
    def fake_submitter(*args, **kwargs):
        return {
            "submitted": False,
            "status": "PAPER_CONFIRMATION_REQUIRED",
        }

    manager = OrderManager(
        repository,
        broker_submitter=fake_submitter,
    )

    result = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=False,
    )

    assert result["state"] == "REJECTED"


def test_maps_unexpected_failure_to_error(
    repository,
):
    def fake_submitter(*args, **kwargs):
        return {
            "submitted": False,
            "status": "BROKER_FAILURE",
        }

    manager = OrderManager(
        repository,
        broker_submitter=fake_submitter,
    )

    result = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=True,
    )

    assert result["state"] == "ERROR"


def test_handles_broker_exception(
    repository,
):
    def fake_submitter(*args, **kwargs):
        raise ConnectionError(
            "TWS connection failed."
        )

    manager = OrderManager(
        repository,
        broker_submitter=fake_submitter,
    )

    result = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=True,
    )

    assert result["submitted"] is False
    assert result["state"] == "ERROR"
    assert "TWS connection failed" in (
        result["message"]
    )

    order = repository.get_order(
        result["local_order_id"]
    )

    assert order is not None
    assert order.state == OrderState.ERROR


def test_prevents_duplicate_active_submission(
    repository,
):
    calls = 0

    def fake_submitter(*args, **kwargs):
        nonlocal calls
        calls += 1

        return {
            "submitted": True,
            "status": "Submitted",
            "order_id": 6000 + calls,
            "statuses": [
                {
                    "orderId": 6000 + calls,
                    "status": "Submitted",
                    "filled": 0,
                    "remaining": 10,
                }
            ],
        }

    manager = OrderManager(
        repository,
        broker_submitter=fake_submitter,
    )

    first = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=True,
        strategy="MOMENTUM",
    )

    second = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=True,
        strategy="MOMENTUM",
    )

    assert first["submitted"] is True
    assert second["submitted"] is False
    assert "active duplicate order" in (
        second["message"]
    )
    assert calls == 1


def test_allows_new_order_after_terminal_order(
    repository,
):
    calls = 0

    def fake_submitter(*args, **kwargs):
        nonlocal calls
        calls += 1

        return {
            "submitted": True,
            "status": "Filled",
            "order_id": 7000 + calls,
            "statuses": [
                {
                    "orderId": 7000 + calls,
                    "status": "Filled",
                    "filled": 10,
                    "remaining": 0,
                    "avgFillPrice": 200,
                    "lastFillPrice": 200,
                }
            ],
        }

    manager = OrderManager(
        repository,
        broker_submitter=fake_submitter,
    )

    first = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=True,
        strategy="MOMENTUM",
    )

    second = manager.submit_prepared_order(
        make_order_request(),
        paper_account_confirmed=True,
        strategy="MOMENTUM",
    )

    assert first["state"] == "FILLED"
    assert second["submitted"] is True
    assert calls == 2


def test_rejects_unsafe_transmitting_preview(
    repository,
):
    request = make_order_request()
    request["transmit"] = True

    def fake_submitter(*args, **kwargs):
        pytest.fail(
            "Broker submitter should not be called."
        )

    manager = OrderManager(
        repository,
        broker_submitter=fake_submitter,
    )

    result = manager.submit_prepared_order(
        request,
        paper_account_confirmed=True,
    )

    # Repository currently validates paper_only but the broker
    # adapter is responsible for rejecting transmit=True.
    # This test confirms the broker result is recorded safely
    # when the submitter is replaced in future integration tests.
    assert result["submitted"] is False