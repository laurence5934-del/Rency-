from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.strategy.execution.execution_models import (
    ExecutionOrderType,
    ExecutionReceipt,
    ExecutionReport,
    ExecutionRequest,
    ExecutionSide,
    ExecutionStatus,
)


NOW = datetime(
    2026,
    8,
    2,
    17,
    0,
    tzinfo=timezone.utc,
)


def market_request() -> ExecutionRequest:
    return ExecutionRequest(
        execution_id="execution-001",
        symbol="AAPL",
        side=ExecutionSide.BUY,
        quantity=Decimal("10"),
        order_type=ExecutionOrderType.MARKET,
        submitted_at=NOW,
        strategy_id="trend-001",
    )


def receipt() -> ExecutionReceipt:
    return ExecutionReceipt(
        execution_id="execution-001",
        broker_name="SIMULATOR",
        order_id="SIM-000001",
        filled_quantity=Decimal("10"),
        average_price=Decimal("200"),
        commission=Decimal("1"),
        executed_at=NOW,
    )


def test_execution_request() -> None:
    value = market_request()

    assert value.symbol == "AAPL"
    assert value.quantity == Decimal("10")
    assert value.side is ExecutionSide.BUY


def test_request_text_is_normalized() -> None:
    value = ExecutionRequest(
        execution_id="  execution-001  ",
        symbol="  aapl  ",
        side=ExecutionSide.BUY,
        quantity=Decimal("10"),
        order_type=ExecutionOrderType.MARKET,
        submitted_at=NOW,
        strategy_id="  trend-001  ",
    )

    assert value.execution_id == "execution-001"
    assert value.symbol == "AAPL"
    assert value.strategy_id == "trend-001"


@pytest.mark.parametrize(
    "quantity",
    [
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_quantity_must_be_positive(
    quantity: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="quantity must be greater than zero",
    ):
        ExecutionRequest(
            execution_id="execution-001",
            symbol="AAPL",
            side=ExecutionSide.BUY,
            quantity=quantity,
            order_type=ExecutionOrderType.MARKET,
            submitted_at=NOW,
        )


def test_limit_order_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="limit orders must include a limit_price",
    ):
        ExecutionRequest(
            execution_id="execution-001",
            symbol="AAPL",
            side=ExecutionSide.BUY,
            quantity=Decimal("10"),
            order_type=ExecutionOrderType.LIMIT,
            submitted_at=NOW,
        )


def test_market_order_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="market orders must not include a limit_price",
    ):
        ExecutionRequest(
            execution_id="execution-001",
            symbol="AAPL",
            side=ExecutionSide.BUY,
            quantity=Decimal("10"),
            order_type=ExecutionOrderType.MARKET,
            submitted_at=NOW,
            limit_price=Decimal("200"),
        )


def test_submitted_at_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="submitted_at must be timezone-aware",
    ):
        ExecutionRequest(
            execution_id="execution-001",
            symbol="AAPL",
            side=ExecutionSide.BUY,
            quantity=Decimal("10"),
            order_type=ExecutionOrderType.MARKET,
            submitted_at=datetime(2026, 8, 2),
        )


def test_metadata_is_normalized() -> None:
    value = ExecutionRequest(
        execution_id="execution-001",
        symbol="AAPL",
        side=ExecutionSide.BUY,
        quantity=Decimal("10"),
        order_type=ExecutionOrderType.MARKET,
        submitted_at=NOW,
        metadata=[
            (
                "  source  ",
                "  paper-orchestrator  ",
            ),
        ],
    )

    assert value.metadata == (
        (
            "source",
            "paper-orchestrator",
        ),
    )


def test_execution_receipt() -> None:
    value = receipt()

    assert value.order_id == "SIM-000001"
    assert value.average_price == Decimal("200")


def test_receipt_quantity_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="filled_quantity must be greater than zero",
    ):
        ExecutionReceipt(
            execution_id="execution-001",
            broker_name="SIMULATOR",
            order_id="SIM-000001",
            filled_quantity=Decimal("0"),
            average_price=Decimal("200"),
            commission=Decimal("0"),
            executed_at=NOW,
        )


def test_commission_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="commission must not be negative",
    ):
        ExecutionReceipt(
            execution_id="execution-001",
            broker_name="SIMULATOR",
            order_id="SIM-000001",
            filled_quantity=Decimal("10"),
            average_price=Decimal("200"),
            commission=Decimal("-1"),
            executed_at=NOW,
        )


def test_completed_report() -> None:
    report = ExecutionReport(
        status=ExecutionStatus.COMPLETED,
        request=market_request(),
        receipt=receipt(),
    )

    assert report.status is ExecutionStatus.COMPLETED
    assert report.receipt == receipt()


def test_completed_report_requires_receipt() -> None:
    with pytest.raises(
        ValueError,
        match="completed reports must include a receipt",
    ):
        ExecutionReport(
            status=ExecutionStatus.COMPLETED,
            request=market_request(),
        )


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        ExecutionReport(
            status=ExecutionStatus.FAILED,
            request=market_request(),
        )


def test_request_and_receipt_ids_must_match() -> None:
    invalid_receipt = ExecutionReceipt(
        execution_id="different",
        broker_name="SIMULATOR",
        order_id="SIM-000001",
        filled_quantity=Decimal("10"),
        average_price=Decimal("200"),
        commission=Decimal("0"),
        executed_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match="execution_id values must match",
    ):
        ExecutionReport(
            status=ExecutionStatus.COMPLETED,
            request=market_request(),
            receipt=invalid_receipt,
        )


def test_models_are_immutable() -> None:
    value = market_request()

    with pytest.raises(FrozenInstanceError):
        value.symbol = "MSFT"