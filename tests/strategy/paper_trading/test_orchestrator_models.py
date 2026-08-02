from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.strategy.paper_trading.orchestrator_models import (
    OrchestratorReport,
    OrchestratorStatus,
    PaperTradeRequest,
    PaperTradeResult,
    PaperTradeSide,
    TradeApproval,
)


NOW = datetime(
    2026,
    8,
    2,
    13,
    0,
    tzinfo=timezone.utc,
)


def request() -> PaperTradeRequest:
    return PaperTradeRequest(
        request_id="paper-001",
        symbol="AAPL",
        side=PaperTradeSide.BUY,
        quantity=Decimal("10"),
        strategy_id="trend-001",
        submitted_at=NOW,
        limit_price=Decimal("200"),
    )


def approved_result() -> PaperTradeResult:
    return PaperTradeResult(
        request_id="paper-001",
        approval=TradeApproval.APPROVED,
        submitted=True,
        reason="All orchestration gates passed.",
        order_id="PAPER-ORDER-001",
        execution_price=Decimal("199.50"),
        executed_quantity=Decimal("10"),
    )


def completed_report() -> OrchestratorReport:
    return OrchestratorReport(
        status=OrchestratorStatus.COMPLETED,
        request=request(),
        approval=TradeApproval.APPROVED,
        result=approved_result(),
        decision_summary="Decision approved.",
        risk_summary="Portfolio is paper ready.",
        regime_summary="Market regime is bullish.",
        completed_at=NOW,
    )


def test_paper_trade_request() -> None:
    value = request()

    assert value.request_id == "paper-001"
    assert value.symbol == "AAPL"
    assert value.side is PaperTradeSide.BUY
    assert value.quantity == Decimal("10")


def test_request_text_is_normalized() -> None:
    value = PaperTradeRequest(
        request_id="  paper-001  ",
        symbol="  aapl  ",
        side=PaperTradeSide.BUY,
        quantity=Decimal("10"),
        strategy_id="  trend-001  ",
        submitted_at=NOW,
    )

    assert value.request_id == "paper-001"
    assert value.symbol == "AAPL"
    assert value.strategy_id == "trend-001"


@pytest.mark.parametrize(
    ("field_name", "message"),
    [
        (
            "request_id",
            "request_id must not be empty",
        ),
        (
            "symbol",
            "symbol must not be empty",
        ),
        (
            "strategy_id",
            "strategy_id must not be empty",
        ),
    ],
)
def test_request_text_fields_must_not_be_empty(
    field_name: str,
    message: str,
) -> None:
    arguments = {
        "request_id": "paper-001",
        "symbol": "AAPL",
        "side": PaperTradeSide.BUY,
        "quantity": Decimal("10"),
        "strategy_id": "trend-001",
        "submitted_at": NOW,
    }

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=message,
    ):
        PaperTradeRequest(**arguments)


def test_request_side_must_be_enum() -> None:
    with pytest.raises(
        TypeError,
        match="side must be a PaperTradeSide",
    ):
        PaperTradeRequest(
            request_id="paper-001",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("10"),
            strategy_id="trend-001",
            submitted_at=NOW,
        )


def test_quantity_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="quantity must be a Decimal",
    ):
        PaperTradeRequest(
            request_id="paper-001",
            symbol="AAPL",
            side=PaperTradeSide.BUY,
            quantity=10,
            strategy_id="trend-001",
            submitted_at=NOW,
        )


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
        PaperTradeRequest(
            request_id="paper-001",
            symbol="AAPL",
            side=PaperTradeSide.BUY,
            quantity=quantity,
            strategy_id="trend-001",
            submitted_at=NOW,
        )


def test_submitted_at_must_be_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="submitted_at must be a datetime",
    ):
        PaperTradeRequest(
            request_id="paper-001",
            symbol="AAPL",
            side=PaperTradeSide.BUY,
            quantity=Decimal("10"),
            strategy_id="trend-001",
            submitted_at="2026-08-02",
        )


def test_submitted_at_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="submitted_at must be timezone-aware",
    ):
        PaperTradeRequest(
            request_id="paper-001",
            symbol="AAPL",
            side=PaperTradeSide.BUY,
            quantity=Decimal("10"),
            strategy_id="trend-001",
            submitted_at=datetime(2026, 8, 2),
        )


@pytest.mark.parametrize(
    "limit_price",
    [
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_limit_price_must_be_positive(
    limit_price: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="limit_price must be greater than zero",
    ):
        PaperTradeRequest(
            request_id="paper-001",
            symbol="AAPL",
            side=PaperTradeSide.BUY,
            quantity=Decimal("10"),
            strategy_id="trend-001",
            submitted_at=NOW,
            limit_price=limit_price,
        )


def test_metadata_is_normalized() -> None:
    value = PaperTradeRequest(
        request_id="paper-001",
        symbol="AAPL",
        side=PaperTradeSide.BUY,
        quantity=Decimal("10"),
        strategy_id="trend-001",
        submitted_at=NOW,
        metadata=[
            (
                "  source  ",
                "  decision-engine  ",
            ),
        ],
    )

    assert value.metadata == (
        (
            "source",
            "decision-engine",
        ),
    )


def test_metadata_must_have_two_items() -> None:
    with pytest.raises(
        TypeError,
        match="two-item tuple",
    ):
        PaperTradeRequest(
            request_id="paper-001",
            symbol="AAPL",
            side=PaperTradeSide.BUY,
            quantity=Decimal("10"),
            strategy_id="trend-001",
            submitted_at=NOW,
            metadata=(
                ("invalid",),
            ),
        )


def test_approved_result() -> None:
    value = approved_result()

    assert value.approval is TradeApproval.APPROVED
    assert value.submitted is True
    assert value.order_id == "PAPER-ORDER-001"


def test_submitted_result_requires_order_id() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "submitted results must include an order_id"
        ),
    ):
        PaperTradeResult(
            request_id="paper-001",
            approval=TradeApproval.APPROVED,
            submitted=True,
            reason="Approved.",
        )


def test_non_submitted_result_cannot_have_order_id() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-submitted results must not include "
            "an order_id"
        ),
    ):
        PaperTradeResult(
            request_id="paper-001",
            approval=TradeApproval.REJECTED,
            submitted=False,
            reason="Rejected.",
            order_id="INVALID",
        )


def test_only_approved_result_may_be_submitted() -> None:
    with pytest.raises(
        ValueError,
        match="only approved results may be submitted",
    ):
        PaperTradeResult(
            request_id="paper-001",
            approval=TradeApproval.REVIEW_REQUIRED,
            submitted=True,
            reason="Review required.",
            order_id="PAPER-ORDER-001",
        )


def test_non_submitted_result_has_zero_quantity() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-submitted results must have zero "
            "executed_quantity"
        ),
    ):
        PaperTradeResult(
            request_id="paper-001",
            approval=TradeApproval.REJECTED,
            submitted=False,
            reason="Rejected.",
            executed_quantity=Decimal("1"),
        )


def test_result_warnings_are_converted_to_tuple() -> None:
    value = PaperTradeResult(
        request_id="paper-001",
        approval=TradeApproval.REVIEW_REQUIRED,
        submitted=False,
        reason="Review required.",
        warnings=["Market regime is uncertain."],
    )

    assert value.warnings == (
        "Market regime is uncertain.",
    )


def test_completed_orchestrator_report() -> None:
    value = completed_report()

    assert value.status is OrchestratorStatus.COMPLETED
    assert value.approval is TradeApproval.APPROVED
    assert value.result == approved_result()
    assert value.completed_at == NOW


def test_report_request_ids_must_match() -> None:
    mismatched_result = PaperTradeResult(
        request_id="different",
        approval=TradeApproval.REJECTED,
        submitted=False,
        reason="Rejected.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result request_id values "
            "must match"
        ),
    ):
        OrchestratorReport(
            status=OrchestratorStatus.COMPLETED,
            request=request(),
            approval=TradeApproval.REJECTED,
            result=mismatched_result,
            decision_summary="Rejected.",
            risk_summary="Risk failed.",
            regime_summary="Regime blocked.",
            completed_at=NOW,
        )


def test_report_approval_values_must_match() -> None:
    result = PaperTradeResult(
        request_id="paper-001",
        approval=TradeApproval.REJECTED,
        submitted=False,
        reason="Rejected.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "report and result approval values must match"
        ),
    ):
        OrchestratorReport(
            status=OrchestratorStatus.COMPLETED,
            request=request(),
            approval=TradeApproval.APPROVED,
            result=result,
            decision_summary="Decision approved.",
            risk_summary="Risk failed.",
            regime_summary="Regime blocked.",
            completed_at=NOW,
        )


@pytest.mark.parametrize(
    ("field_name", "message"),
    [
        (
            "decision_summary",
            "decision_summary must not be empty",
        ),
        (
            "risk_summary",
            "risk_summary must not be empty",
        ),
        (
            "regime_summary",
            "regime_summary must not be empty",
        ),
    ],
)
def test_report_summaries_must_not_be_empty(
    field_name: str,
    message: str,
) -> None:
    arguments = {
        "status": OrchestratorStatus.COMPLETED,
        "request": request(),
        "approval": TradeApproval.APPROVED,
        "result": approved_result(),
        "decision_summary": "Decision approved.",
        "risk_summary": "Portfolio is ready.",
        "regime_summary": "Regime is bullish.",
        "completed_at": NOW,
    }

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=message,
    ):
        OrchestratorReport(**arguments)


def test_completed_report_requires_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed reports must include completed_at"
        ),
    ):
        OrchestratorReport(
            status=OrchestratorStatus.COMPLETED,
            request=request(),
            approval=TradeApproval.APPROVED,
            result=approved_result(),
            decision_summary="Decision approved.",
            risk_summary="Portfolio is ready.",
            regime_summary="Regime is bullish.",
        )


def test_failed_report_requires_error() -> None:
    rejected_result = PaperTradeResult(
        request_id="paper-001",
        approval=TradeApproval.REJECTED,
        submitted=False,
        reason="Workflow failed.",
    )

    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        OrchestratorReport(
            status=OrchestratorStatus.FAILED,
            request=request(),
            approval=TradeApproval.REJECTED,
            result=rejected_result,
            decision_summary="Decision unavailable.",
            risk_summary="Risk unavailable.",
            regime_summary="Regime unavailable.",
        )


def test_completed_report_cannot_include_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only failed reports may include an error"
        ),
    ):
        OrchestratorReport(
            status=OrchestratorStatus.COMPLETED,
            request=request(),
            approval=TradeApproval.APPROVED,
            result=approved_result(),
            decision_summary="Decision approved.",
            risk_summary="Portfolio is ready.",
            regime_summary="Regime is bullish.",
            completed_at=NOW,
            error="Unexpected error.",
        )


def test_report_collections_are_tuples() -> None:
    value = OrchestratorReport(
        status=OrchestratorStatus.COMPLETED,
        request=request(),
        approval=TradeApproval.APPROVED,
        result=approved_result(),
        decision_summary="Decision approved.",
        risk_summary="Portfolio is ready.",
        regime_summary="Regime is bullish.",
        completed_at=NOW,
        warnings=["Paper execution warning."],
    )

    assert value.warnings == (
        "Paper execution warning.",
    )


def test_models_are_immutable() -> None:
    value = request()

    with pytest.raises(FrozenInstanceError):
        value.symbol = "MSFT"