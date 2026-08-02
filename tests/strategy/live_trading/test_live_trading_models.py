from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.live_trading.live_trading_models import (
    ExecutionPlanStatus,
    LiveOrderType,
    LiveTradeDecision,
    LiveTradeExecutionResult,
    LiveTradeRequest,
    LiveTradeSide,
    LiveTradingReport,
    LiveTradingStatus,
    TradeExecutionPlan,
    TradingEnvironment,
    TradingSession,
    TradingSessionStatus,
)


NOW = datetime(
    2026,
    8,
    2,
    18,
    0,
    tzinfo=timezone.utc,
)


def paper_session() -> TradingSession:
    return TradingSession(
        session_id="session-001",
        environment=TradingEnvironment.PAPER,
        status=TradingSessionStatus.ACTIVE,
        started_at=NOW,
        account_id="paper-account",
        max_order_value=Decimal("25000"),
        max_session_loss=Decimal("5000"),
    )


def live_session() -> TradingSession:
    return TradingSession(
        session_id="session-live",
        environment=TradingEnvironment.LIVE,
        status=TradingSessionStatus.ACTIVE,
        started_at=NOW,
        account_id="live-account",
        max_order_value=Decimal("10000"),
        max_session_loss=Decimal("2000"),
        live_trading_confirmed=True,
    )


def request() -> LiveTradeRequest:
    return LiveTradeRequest(
        request_id="trade-001",
        session_id="session-001",
        symbol="AAPL",
        side=LiveTradeSide.BUY,
        quantity=Decimal("10"),
        order_type=LiveOrderType.MARKET,
        submitted_at=NOW,
        strategy_id="trend-001",
        estimated_price=Decimal("200"),
    )


def ready_plan() -> TradeExecutionPlan:
    return TradeExecutionPlan(
        plan_id="plan-001",
        request_id="trade-001",
        environment=TradingEnvironment.PAPER,
        status=ExecutionPlanStatus.READY,
        decision=LiveTradeDecision.EXECUTE,
        approved_quantity=Decimal("10"),
        estimated_order_value=Decimal("2000"),
        reason="All execution gates passed.",
        risk_checks_passed=True,
        coordinator_approved=True,
    )


def execution_result() -> LiveTradeExecutionResult:
    return LiveTradeExecutionResult(
        request_id="trade-001",
        plan_id="plan-001",
        decision=LiveTradeDecision.EXECUTE,
        submitted=True,
        broker_name="SIMULATOR",
        order_id="SIM-000001",
        filled_quantity=Decimal("10"),
        average_price=Decimal("199.50"),
        commission=Decimal("1"),
        executed_at=NOW + timedelta(seconds=1),
        reason="Order executed.",
    )


def completed_report() -> LiveTradingReport:
    return LiveTradingReport(
        status=LiveTradingStatus.COMPLETED,
        session=paper_session(),
        request=request(),
        plan=ready_plan(),
        result=execution_result(),
        completed_at=NOW + timedelta(seconds=2),
        audit_id="audit-001",
    )


def test_paper_session() -> None:
    value = paper_session()

    assert value.session_id == "session-001"
    assert value.environment is TradingEnvironment.PAPER
    assert value.status is TradingSessionStatus.ACTIVE


def test_live_session_requires_confirmation() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "live sessions require explicit "
            "live-trading confirmation"
        ),
    ):
        TradingSession(
            session_id="session-live",
            environment=TradingEnvironment.LIVE,
            status=TradingSessionStatus.ACTIVE,
            started_at=NOW,
            account_id="live-account",
            max_order_value=Decimal("10000"),
            max_session_loss=Decimal("2000"),
        )


def test_confirmed_live_session() -> None:
    value = live_session()

    assert value.live_trading_confirmed is True


def test_session_text_is_normalized() -> None:
    value = TradingSession(
        session_id="  session-001  ",
        environment=TradingEnvironment.PAPER,
        status=TradingSessionStatus.ACTIVE,
        started_at=NOW,
        account_id="  paper-account  ",
        max_order_value=Decimal("25000"),
        max_session_loss=Decimal("5000"),
    )

    assert value.session_id == "session-001"
    assert value.account_id == "paper-account"


@pytest.mark.parametrize(
    "field_name",
    [
        "session_id",
        "account_id",
    ],
)
def test_session_identifiers_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "session_id": "session-001",
        "environment": TradingEnvironment.PAPER,
        "status": TradingSessionStatus.ACTIVE,
        "started_at": NOW,
        "account_id": "paper-account",
        "max_order_value": Decimal("25000"),
        "max_session_loss": Decimal("5000"),
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        TradingSession(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "max_order_value",
        "max_session_loss",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_session_limits_must_be_positive(
    field_name: str,
    value: Decimal,
) -> None:
    arguments = {
        "session_id": "session-001",
        "environment": TradingEnvironment.PAPER,
        "status": TradingSessionStatus.ACTIVE,
        "started_at": NOW,
        "account_id": "paper-account",
        "max_order_value": Decimal("25000"),
        "max_session_loss": Decimal("5000"),
    }
    arguments[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be greater than zero",
    ):
        TradingSession(**arguments)


def test_closed_session_requires_closed_at() -> None:
    with pytest.raises(
        ValueError,
        match="closed sessions must include closed_at",
    ):
        TradingSession(
            session_id="session-001",
            environment=TradingEnvironment.PAPER,
            status=TradingSessionStatus.CLOSED,
            started_at=NOW,
            account_id="paper-account",
            max_order_value=Decimal("25000"),
            max_session_loss=Decimal("5000"),
        )


def test_non_closed_session_rejects_closed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only closed sessions may include closed_at"
        ),
    ):
        TradingSession(
            session_id="session-001",
            environment=TradingEnvironment.PAPER,
            status=TradingSessionStatus.ACTIVE,
            started_at=NOW,
            account_id="paper-account",
            max_order_value=Decimal("25000"),
            max_session_loss=Decimal("5000"),
            closed_at=NOW + timedelta(hours=1),
        )


def test_live_trade_request() -> None:
    value = request()

    assert value.symbol == "AAPL"
    assert value.quantity == Decimal("10")
    assert (
        value.estimated_order_value
        == Decimal("2000")
    )


def test_request_text_is_normalized() -> None:
    value = LiveTradeRequest(
        request_id="  trade-001  ",
        session_id="  session-001  ",
        symbol="  aapl  ",
        side=LiveTradeSide.BUY,
        quantity=Decimal("10"),
        order_type=LiveOrderType.MARKET,
        submitted_at=NOW,
        strategy_id="  trend-001  ",
    )

    assert value.request_id == "trade-001"
    assert value.session_id == "session-001"
    assert value.symbol == "AAPL"
    assert value.strategy_id == "trend-001"


def test_quantity_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="quantity must be greater than zero",
    ):
        LiveTradeRequest(
            request_id="trade-001",
            session_id="session-001",
            symbol="AAPL",
            side=LiveTradeSide.BUY,
            quantity=Decimal("0"),
            order_type=LiveOrderType.MARKET,
            submitted_at=NOW,
            strategy_id="trend-001",
        )


def test_limit_order_requires_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match="limit orders must include a limit_price",
    ):
        LiveTradeRequest(
            request_id="trade-001",
            session_id="session-001",
            symbol="AAPL",
            side=LiveTradeSide.BUY,
            quantity=Decimal("10"),
            order_type=LiveOrderType.LIMIT,
            submitted_at=NOW,
            strategy_id="trend-001",
        )


def test_market_order_rejects_limit_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "market orders must not include a limit_price"
        ),
    ):
        LiveTradeRequest(
            request_id="trade-001",
            session_id="session-001",
            symbol="AAPL",
            side=LiveTradeSide.BUY,
            quantity=Decimal("10"),
            order_type=LiveOrderType.MARKET,
            submitted_at=NOW,
            strategy_id="trend-001",
            limit_price=Decimal("200"),
        )


def test_request_without_price_has_no_estimated_value() -> None:
    value = LiveTradeRequest(
        request_id="trade-001",
        session_id="session-001",
        symbol="AAPL",
        side=LiveTradeSide.BUY,
        quantity=Decimal("10"),
        order_type=LiveOrderType.MARKET,
        submitted_at=NOW,
        strategy_id="trend-001",
    )

    assert value.estimated_order_value is None


def test_ready_execution_plan() -> None:
    value = ready_plan()

    assert value.decision is LiveTradeDecision.EXECUTE
    assert value.status is ExecutionPlanStatus.READY


def test_execute_plan_requires_ready_status() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "executable plans must have READY status"
        ),
    ):
        TradeExecutionPlan(
            plan_id="plan-001",
            request_id="trade-001",
            environment=TradingEnvironment.PAPER,
            status=ExecutionPlanStatus.BLOCKED,
            decision=LiveTradeDecision.EXECUTE,
            approved_quantity=Decimal("10"),
            estimated_order_value=Decimal("2000"),
            reason="Approved.",
            risk_checks_passed=True,
            coordinator_approved=True,
        )


def test_execute_plan_requires_passed_risk() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "executable plans require passed risk checks"
        ),
    ):
        TradeExecutionPlan(
            plan_id="plan-001",
            request_id="trade-001",
            environment=TradingEnvironment.PAPER,
            status=ExecutionPlanStatus.READY,
            decision=LiveTradeDecision.EXECUTE,
            approved_quantity=Decimal("10"),
            estimated_order_value=Decimal("2000"),
            reason="Approved.",
            risk_checks_passed=False,
            coordinator_approved=True,
        )


def test_execute_plan_requires_coordinator_approval() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "executable plans require coordinator approval"
        ),
    ):
        TradeExecutionPlan(
            plan_id="plan-001",
            request_id="trade-001",
            environment=TradingEnvironment.PAPER,
            status=ExecutionPlanStatus.READY,
            decision=LiveTradeDecision.EXECUTE,
            approved_quantity=Decimal("10"),
            estimated_order_value=Decimal("2000"),
            reason="Approved.",
            risk_checks_passed=True,
            coordinator_approved=False,
        )


def test_rejected_plan_requires_zero_quantity() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "rejected plans must approve zero quantity"
        ),
    ):
        TradeExecutionPlan(
            plan_id="plan-001",
            request_id="trade-001",
            environment=TradingEnvironment.PAPER,
            status=ExecutionPlanStatus.BLOCKED,
            decision=LiveTradeDecision.REJECT,
            approved_quantity=Decimal("1"),
            estimated_order_value=Decimal("0"),
            reason="Rejected.",
            risk_checks_passed=False,
            coordinator_approved=False,
        )


def test_submitted_execution_result() -> None:
    value = execution_result()

    assert value.submitted is True
    assert value.order_id == "SIM-000001"
    assert value.filled_quantity == Decimal("10")


def test_submitted_result_requires_broker() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "submitted results must include broker_name"
        ),
    ):
        LiveTradeExecutionResult(
            request_id="trade-001",
            plan_id="plan-001",
            decision=LiveTradeDecision.EXECUTE,
            submitted=True,
            broker_name=None,
            order_id="SIM-000001",
            filled_quantity=Decimal("10"),
            average_price=Decimal("200"),
            commission=Decimal("0"),
            executed_at=NOW,
            reason="Executed.",
        )


def test_non_submitted_result_has_zero_fill() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-submitted results must have zero "
            "filled_quantity"
        ),
    ):
        LiveTradeExecutionResult(
            request_id="trade-001",
            plan_id="plan-001",
            decision=LiveTradeDecision.REJECT,
            submitted=False,
            broker_name=None,
            order_id=None,
            filled_quantity=Decimal("1"),
            average_price=None,
            commission=Decimal("0"),
            executed_at=None,
            reason="Rejected.",
        )


def test_completed_live_trading_report() -> None:
    value = completed_report()

    assert value.status is LiveTradingStatus.COMPLETED
    assert value.audit_id == "audit-001"
    assert value.result.submitted is True


def test_report_session_ids_must_match() -> None:
    bad_request = LiveTradeRequest(
        request_id="trade-001",
        session_id="different-session",
        symbol="AAPL",
        side=LiveTradeSide.BUY,
        quantity=Decimal("10"),
        order_type=LiveOrderType.MARKET,
        submitted_at=NOW,
        strategy_id="trend-001",
        estimated_price=Decimal("200"),
    )

    with pytest.raises(
        ValueError,
        match=(
            "request session_id must match the session"
        ),
    ):
        LiveTradingReport(
            status=LiveTradingStatus.COMPLETED,
            session=paper_session(),
            request=bad_request,
            plan=ready_plan(),
            result=execution_result(),
            completed_at=NOW + timedelta(seconds=2),
        )


def test_report_plan_request_id_must_match() -> None:
    bad_plan = TradeExecutionPlan(
        plan_id="plan-001",
        request_id="different-request",
        environment=TradingEnvironment.PAPER,
        status=ExecutionPlanStatus.READY,
        decision=LiveTradeDecision.EXECUTE,
        approved_quantity=Decimal("10"),
        estimated_order_value=Decimal("2000"),
        reason="Approved.",
        risk_checks_passed=True,
        coordinator_approved=True,
    )

    with pytest.raises(
        ValueError,
        match=(
            "plan request_id must match the request"
        ),
    ):
        LiveTradingReport(
            status=LiveTradingStatus.COMPLETED,
            session=paper_session(),
            request=request(),
            plan=bad_plan,
            result=execution_result(),
            completed_at=NOW + timedelta(seconds=2),
        )


def test_failed_report_requires_error() -> None:
    rejected_plan = TradeExecutionPlan(
        plan_id="plan-001",
        request_id="trade-001",
        environment=TradingEnvironment.PAPER,
        status=ExecutionPlanStatus.BLOCKED,
        decision=LiveTradeDecision.REJECT,
        approved_quantity=Decimal("0"),
        estimated_order_value=Decimal("0"),
        reason="Execution failed.",
        risk_checks_passed=False,
        coordinator_approved=False,
    )

    rejected_result = LiveTradeExecutionResult(
        request_id="trade-001",
        plan_id="plan-001",
        decision=LiveTradeDecision.REJECT,
        submitted=False,
        broker_name=None,
        order_id=None,
        filled_quantity=Decimal("0"),
        average_price=None,
        commission=Decimal("0"),
        executed_at=None,
        reason="Execution failed.",
    )

    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        LiveTradingReport(
            status=LiveTradingStatus.FAILED,
            session=paper_session(),
            request=request(),
            plan=rejected_plan,
            result=rejected_result,
            completed_at=NOW,
        )


def test_completed_report_cannot_include_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only failed reports may include an error"
        ),
    ):
        LiveTradingReport(
            status=LiveTradingStatus.COMPLETED,
            session=paper_session(),
            request=request(),
            plan=ready_plan(),
            result=execution_result(),
            completed_at=NOW + timedelta(seconds=2),
            error="Unexpected error.",
        )


def test_report_collections_are_tuples() -> None:
    value = LiveTradingReport(
        status=LiveTradingStatus.COMPLETED,
        session=paper_session(),
        request=request(),
        plan=ready_plan(),
        result=execution_result(),
        completed_at=NOW + timedelta(seconds=2),
        warnings=["Execution warning."],
    )

    assert value.warnings == (
        "Execution warning.",
    )


def test_models_are_immutable() -> None:
    value = paper_session()

    with pytest.raises(FrozenInstanceError):
        value.account_id = "changed"