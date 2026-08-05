from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.broker_gateway import (
    BrokerEnvironment,
    BrokerOrderRequest,
)
from app.strategy.execution_coordinator import (
    ExecutionDecision,
    ExecutionReport,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStage,
    ExecutionStatus,
    ExecutionStep,
)
from app.strategy.order_manager import (
    OrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)
from app.strategy.portfolio_manager import AssetClass
from app.strategy.risk_gateway import RiskEvaluationRequest
from app.strategy.trading_session import (
    SessionState,
    SessionType,
    TradingSession,
)


NOW = datetime(
    2026,
    8,
    5,
    14,
    0,
    tzinfo=timezone.utc,
)

SESSION_TIME = NOW - timedelta(minutes=5)
ORDER_TIME = NOW - timedelta(minutes=4)
RISK_TIME = NOW - timedelta(minutes=2)
BROKER_TIME = NOW - timedelta(minutes=1)


def trading_session(
    *,
    session_id: str = "session-001",
    evaluated_at: datetime = SESSION_TIME,
    trading_allowed: bool = True,
) -> TradingSession:
    return TradingSession(
        session_id=session_id,
        calendar_id="calendar-001",
        market="NYSE",
        trading_date=date(2026, 8, 5),
        state=SessionState.OPEN,
        session_type=SessionType.REGULAR,
        opened_at=SESSION_TIME - timedelta(minutes=30),
        closed_at=None,
        evaluated_at=evaluated_at,
        trading_allowed=trading_allowed,
        reason="Regular trading session is open.",
    )


def order_request(
    *,
    order_id: str = "order-001",
    client_order_id: str = "client-order-001",
    portfolio_id: str = "portfolio-001",
    strategy_id: str = "strategy-001",
    quantity: str = "10",
    symbol: str = "NVDA",
) -> OrderRequest:
    return OrderRequest(
        order_id=order_id,
        client_order_id=client_order_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        asset_class=AssetClass.EQUITY,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal(quantity),
        created_at=ORDER_TIME,
        strategy_id=strategy_id,
    )


def risk_request(
    *,
    evaluation_id: str = "evaluation-001",
    order: OrderRequest | None = None,
) -> RiskEvaluationRequest:
    effective_order = order or order_request()

    return RiskEvaluationRequest(
        evaluation_id=evaluation_id,
        request=effective_order,
        account_id="account-001",
        portfolio_id=effective_order.portfolio_id,
        requested_at=RISK_TIME,
        market_price=Decimal("125"),
        current_position_quantity=Decimal("20"),
        current_position_notional=Decimal("2500"),
        available_buying_power=Decimal("50000"),
        available_margin=Decimal("25000"),
        gross_exposure=Decimal("100000"),
        net_exposure=Decimal("60000"),
        daily_realized_pnl=Decimal("500"),
        daily_unrealized_pnl=Decimal("-100"),
        trading_session_allowed=True,
        short_selling_allowed=True,
    )


def broker_request(
    *,
    order: OrderRequest | None = None,
    gateway_order_id: str = "gateway-order-001",
) -> BrokerOrderRequest:
    effective_order = order or order_request()

    return BrokerOrderRequest(
        gateway_order_id=gateway_order_id,
        order_id=effective_order.order_id,
        client_order_id=effective_order.client_order_id,
        broker_name="Interactive Brokers",
        account_id="account-001",
        environment=BrokerEnvironment.PAPER,
        symbol=effective_order.symbol,
        asset_class=effective_order.asset_class,
        side=effective_order.side,
        order_type=effective_order.order_type,
        time_in_force=effective_order.time_in_force,
        quantity=effective_order.quantity,
        submitted_at=BROKER_TIME,
        limit_price=effective_order.limit_price,
        stop_price=effective_order.stop_price,
    )


def execution_request(
    *,
    execution_id: str = "execution-001",
    correlation_id: str = "correlation-001",
    strategy_id: str = "strategy-001",
    portfolio_id: str = "portfolio-001",
    session: TradingSession | None = None,
    order: OrderRequest | None = None,
    include_risk: bool = True,
    include_broker: bool = True,
    created_at: datetime = NOW,
) -> ExecutionRequest:
    effective_order = order or order_request(
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
    )

    return ExecutionRequest(
        execution_id=execution_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        session=session or trading_session(),
        order_request=effective_order,
        created_at=created_at,
        risk_request=(
            risk_request(order=effective_order)
            if include_risk
            else None
        ),
        broker_request=(
            broker_request(order=effective_order)
            if include_broker
            else None
        ),
        requested_by="strategy-orchestrator",
        metadata=(("source", "ai-strategy"),),
    )


def successful_step(
    *,
    step_id: str = "step-001",
    stage: ExecutionStage = ExecutionStage.SESSION,
    started_at: datetime = NOW,
    completed_at: datetime = NOW,
    reference_id: str = "reference-001",
) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        execution_id="execution-001",
        stage=stage,
        decision=ExecutionDecision.PROCEED,
        started_at=started_at,
        completed_at=completed_at,
        successful=True,
        message="Execution stage completed successfully.",
        reference_id=reference_id,
    )


def failed_step(
    *,
    step_id: str = "step-002",
    stage: ExecutionStage = ExecutionStage.RISK,
    decision: ExecutionDecision = ExecutionDecision.REJECT,
) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        execution_id="execution-001",
        stage=stage,
        decision=decision,
        started_at=NOW,
        completed_at=NOW,
        successful=False,
        message="Execution stage did not complete.",
        error="Stage validation failed.",
    )


def completed_result() -> ExecutionResult:
    return ExecutionResult(
        execution_id="execution-001",
        status=ExecutionStatus.COMPLETED,
        decision=ExecutionDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW + timedelta(seconds=3),
        completed_at=NOW + timedelta(seconds=3),
        steps=(
            successful_step(
                step_id="step-001",
                stage=ExecutionStage.SESSION,
                started_at=NOW,
                completed_at=NOW,
            ),
            successful_step(
                step_id="step-002",
                stage=ExecutionStage.ORDER,
                started_at=NOW + timedelta(seconds=1),
                completed_at=NOW + timedelta(seconds=1),
            ),
            successful_step(
                step_id="step-003",
                stage=ExecutionStage.RISK,
                started_at=NOW + timedelta(seconds=2),
                completed_at=NOW + timedelta(seconds=2),
            ),
            successful_step(
                step_id="step-004",
                stage=ExecutionStage.BROKER,
                started_at=NOW + timedelta(seconds=3),
                completed_at=NOW + timedelta(seconds=3),
            ),
        ),
        final_order_id="order-001",
        broker_order_id="broker-order-001",
    )


def test_execution_request() -> None:
    value = execution_request()

    assert value.execution_id == "execution-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.order_request.order_id == "order-001"
    assert value.risk_request is not None
    assert value.broker_request is not None


def test_execution_request_allows_optional_requests() -> None:
    value = execution_request(
        include_risk=False,
        include_broker=False,
    )

    assert value.risk_request is None
    assert value.broker_request is None


def test_request_text_is_normalized() -> None:
    order = order_request()

    value = ExecutionRequest(
        execution_id="  execution-001  ",
        correlation_id="  correlation-001  ",
        strategy_id="  strategy-001  ",
        portfolio_id="  portfolio-001  ",
        session=trading_session(),
        order_request=order,
        created_at=NOW,
        requested_by="  strategy-orchestrator  ",
        metadata=[("  source  ", "  strategy  ")],
    )

    assert value.execution_id == "execution-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.requested_by == "strategy-orchestrator"
    assert value.metadata == (("source", "strategy"),)


@pytest.mark.parametrize(
    "field_name",
    [
        "execution_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "requested_by",
    ],
)
def test_request_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "execution_id": "execution-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "session": trading_session(),
        "order_request": order_request(),
        "created_at": NOW,
        "requested_by": "strategy-orchestrator",
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        ExecutionRequest(**arguments)


def test_request_requires_trading_session() -> None:
    with pytest.raises(
        TypeError,
        match="session must be a TradingSession",
    ):
        ExecutionRequest(
            execution_id="execution-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            session=object(),
            order_request=order_request(),
            created_at=NOW,
        )


def test_request_requires_order_request() -> None:
    with pytest.raises(
        TypeError,
        match="order_request must be an OrderRequest",
    ):
        ExecutionRequest(
            execution_id="execution-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            session=trading_session(),
            order_request=object(),
            created_at=NOW,
        )


def test_risk_request_requires_correct_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "risk_request must be a "
            "RiskEvaluationRequest or None"
        ),
    ):
        ExecutionRequest(
            execution_id="execution-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            session=trading_session(),
            order_request=order_request(),
            created_at=NOW,
            risk_request=object(),
        )


def test_broker_request_requires_correct_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "broker_request must be a "
            "BrokerOrderRequest or None"
        ),
    ):
        ExecutionRequest(
            execution_id="execution-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            session=trading_session(),
            order_request=order_request(),
            created_at=NOW,
            broker_request=object(),
        )


def test_request_created_at_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="created_at must be timezone-aware",
    ):
        execution_request(
            created_at=datetime(2026, 8, 5, 14, 0)
        )


def test_portfolio_id_must_match_order() -> None:
    order = order_request(
        portfolio_id="different-portfolio"
    )

    with pytest.raises(
        ValueError,
        match=(
            "portfolio_id must match "
            "order_request portfolio_id"
        ),
    ):
        execution_request(order=order)


def test_strategy_id_must_match_order() -> None:
    order = order_request(
        strategy_id="different-strategy"
    )

    with pytest.raises(
        ValueError,
        match=(
            "strategy_id must match "
            "order_request strategy_id"
        ),
    ):
        execution_request(order=order)


def test_order_creation_must_not_follow_execution() -> None:
    order = OrderRequest(
        order_id="order-001",
        client_order_id="client-order-001",
        portfolio_id="portfolio-001",
        symbol="NVDA",
        asset_class=AssetClass.EQUITY,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal("10"),
        created_at=NOW + timedelta(seconds=1),
        strategy_id="strategy-001",
    )

    with pytest.raises(
        ValueError,
        match=(
            "order_request created_at must not be later "
            "than execution created_at"
        ),
    ):
        execution_request(
            order=order,
            created_at=NOW,
            include_risk=False,
            include_broker=False,
        )


def test_session_evaluation_must_not_follow_execution() -> None:
    session = trading_session(
        evaluated_at=NOW + timedelta(seconds=1)
    )

    with pytest.raises(
        ValueError,
        match=(
            "session evaluated_at must not be later "
            "than execution created_at"
        ),
    ):
        execution_request(session=session)


def test_risk_order_must_match_order_request() -> None:
    primary_order = order_request()
    different_order = order_request(
        order_id="order-002",
        client_order_id="client-order-002",
    )

    with pytest.raises(
        ValueError,
        match=(
            "risk_request order must match "
            "order_request"
        ),
    ):
        ExecutionRequest(
            execution_id="execution-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            session=trading_session(),
            order_request=primary_order,
            created_at=NOW,
            risk_request=risk_request(
                order=different_order
            ),
        )


def test_broker_order_id_must_match_order_request() -> None:
    primary_order = order_request()
    different_order = order_request(
        order_id="order-002",
        client_order_id="client-order-002",
    )

    with pytest.raises(
        ValueError,
        match=(
            "broker_request order_id must match "
            "order_request order_id"
        ),
    ):
        ExecutionRequest(
            execution_id="execution-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            session=trading_session(),
            order_request=primary_order,
            created_at=NOW,
            broker_request=broker_request(
                order=different_order
            ),
        )


def test_successful_execution_step() -> None:
    value = successful_step()

    assert value.successful is True
    assert value.is_complete is True
    assert value.stage_position == 1
    assert value.error is None


def test_unsuccessful_execution_step() -> None:
    value = failed_step()

    assert value.successful is False
    assert value.is_complete is True
    assert value.error == "Stage validation failed."


def test_step_text_is_normalized() -> None:
    value = ExecutionStep(
        step_id="  step-001  ",
        execution_id="  execution-001  ",
        stage=ExecutionStage.ORDER,
        decision=ExecutionDecision.PROCEED,
        started_at=NOW,
        completed_at=NOW,
        successful=True,
        message="  Order validated.  ",
        reference_id="  order-001  ",
        warnings=["  Review order.  "],
        metadata=[("  source  ", "  oms  ")],
    )

    assert value.step_id == "step-001"
    assert value.execution_id == "execution-001"
    assert value.message == "Order validated."
    assert value.reference_id == "order-001"
    assert value.warnings == ("Review order.",)
    assert value.metadata == (("source", "oms"),)


def test_step_requires_stage_enum() -> None:
    with pytest.raises(
        TypeError,
        match="stage must be an ExecutionStage",
    ):
        ExecutionStep(
            step_id="step-001",
            execution_id="execution-001",
            stage="ORDER",
            decision=ExecutionDecision.PROCEED,
            started_at=NOW,
            successful=True,
            message="Order validated.",
        )


def test_step_requires_decision_enum() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "decision must be an ExecutionDecision"
        ),
    ):
        ExecutionStep(
            step_id="step-001",
            execution_id="execution-001",
            stage=ExecutionStage.ORDER,
            decision="PROCEED",
            started_at=NOW,
            successful=True,
            message="Order validated.",
        )


def test_step_successful_must_be_bool() -> None:
    with pytest.raises(
        TypeError,
        match="successful must be a bool",
    ):
        ExecutionStep(
            step_id="step-001",
            execution_id="execution-001",
            stage=ExecutionStage.ORDER,
            decision=ExecutionDecision.PROCEED,
            started_at=NOW,
            successful="yes",
            message="Order validated.",
        )


def test_step_completion_must_follow_start() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed_at must not be earlier "
            "than started_at"
        ),
    ):
        successful_step(
            started_at=NOW,
            completed_at=NOW - timedelta(seconds=1),
        )


def test_successful_step_rejects_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "successful steps must not include an error"
        ),
    ):
        ExecutionStep(
            step_id="step-001",
            execution_id="execution-001",
            stage=ExecutionStage.ORDER,
            decision=ExecutionDecision.PROCEED,
            started_at=NOW,
            successful=True,
            message="Order validated.",
            error="Unexpected error.",
        )


@pytest.mark.parametrize(
    "decision",
    [
        ExecutionDecision.REJECT,
        ExecutionDecision.CANCEL,
    ],
)
def test_successful_step_rejects_terminal_decision(
    decision: ExecutionDecision,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "successful steps must not have "
            "a reject or cancel decision"
        ),
    ):
        ExecutionStep(
            step_id="step-001",
            execution_id="execution-001",
            stage=ExecutionStage.ORDER,
            decision=decision,
            started_at=NOW,
            successful=True,
            message="Invalid successful step.",
        )


def test_unsuccessful_step_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "unsuccessful steps must include an error"
        ),
    ):
        ExecutionStep(
            step_id="step-001",
            execution_id="execution-001",
            stage=ExecutionStage.RISK,
            decision=ExecutionDecision.REJECT,
            started_at=NOW,
            successful=False,
            message="Risk rejected the order.",
        )


def test_completed_execution_result() -> None:
    value = completed_result()

    assert value.status is ExecutionStatus.COMPLETED
    assert value.decision is ExecutionDecision.PROCEED
    assert value.is_terminal is True
    assert value.successful_step_count == 4
    assert value.failed_step is None


def test_executing_result() -> None:
    value = ExecutionResult(
        execution_id="execution-001",
        status=ExecutionStatus.EXECUTING,
        decision=ExecutionDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW,
        steps=(),
    )

    assert value.is_terminal is False
    assert value.completed_at is None


def test_rejected_result() -> None:
    step = failed_step()

    value = ExecutionResult(
        execution_id="execution-001",
        status=ExecutionStatus.REJECTED,
        decision=ExecutionDecision.REJECT,
        started_at=NOW,
        updated_at=NOW,
        completed_at=NOW,
        steps=(step,),
    )

    assert value.is_terminal is True
    assert value.failed_step == step


def test_failed_result() -> None:
    step = failed_step(
        decision=ExecutionDecision.NO_ACTION
    )

    value = ExecutionResult(
        execution_id="execution-001",
        status=ExecutionStatus.FAILED,
        decision=ExecutionDecision.NO_ACTION,
        started_at=NOW,
        updated_at=NOW,
        completed_at=NOW,
        steps=(step,),
        error="Coordinator processing failed.",
    )

    assert value.is_terminal is True
    assert value.error == "Coordinator processing failed."


def test_result_updated_at_must_follow_start() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "updated_at must not be earlier "
            "than started_at"
        ),
    ):
        ExecutionResult(
            execution_id="execution-001",
            status=ExecutionStatus.EXECUTING,
            decision=ExecutionDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW - timedelta(seconds=1),
        )


def test_step_execution_id_must_match_result() -> None:
    step = ExecutionStep(
        step_id="step-001",
        execution_id="different-execution",
        stage=ExecutionStage.SESSION,
        decision=ExecutionDecision.PROCEED,
        started_at=NOW,
        completed_at=NOW,
        successful=True,
        message="Session validated.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "step execution_id must match result"
        ),
    ):
        ExecutionResult(
            execution_id="execution-001",
            status=ExecutionStatus.EXECUTING,
            decision=ExecutionDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            steps=(step,),
        )


def test_step_ids_must_be_unique() -> None:
    step = successful_step()

    with pytest.raises(
        ValueError,
        match="step_id values must be unique",
    ):
        ExecutionResult(
            execution_id="execution-001",
            status=ExecutionStatus.EXECUTING,
            decision=ExecutionDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            steps=(step, step),
        )


def test_steps_must_be_ordered_by_stage() -> None:
    risk_step = successful_step(
        step_id="step-001",
        stage=ExecutionStage.RISK,
    )
    order_step = successful_step(
        step_id="step-002",
        stage=ExecutionStage.ORDER,
    )

    with pytest.raises(
        ValueError,
        match=(
            "steps must be ordered by execution stage"
        ),
    ):
        ExecutionResult(
            execution_id="execution-001",
            status=ExecutionStatus.EXECUTING,
            decision=ExecutionDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            steps=(risk_step, order_step),
        )


def test_execution_stages_must_be_unique() -> None:
    first = successful_step(
        step_id="step-001",
        stage=ExecutionStage.ORDER,
    )
    second = successful_step(
        step_id="step-002",
        stage=ExecutionStage.ORDER,
    )

    with pytest.raises(
        ValueError,
        match="execution stages must be unique",
    ):
        ExecutionResult(
            execution_id="execution-001",
            status=ExecutionStatus.EXECUTING,
            decision=ExecutionDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            steps=(first, second),
        )


def test_terminal_result_requires_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "terminal execution results must include "
            "completed_at"
        ),
    ):
        ExecutionResult(
            execution_id="execution-001",
            status=ExecutionStatus.REJECTED,
            decision=ExecutionDecision.REJECT,
            started_at=NOW,
            updated_at=NOW,
        )


def test_non_terminal_result_rejects_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-terminal execution results must not "
            "include completed_at"
        ),
    ):
        ExecutionResult(
            execution_id="execution-001",
            status=ExecutionStatus.EXECUTING,
            decision=ExecutionDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            completed_at=NOW,
        )


def test_completed_result_requires_final_order_id() -> None:
    value = completed_result()

    with pytest.raises(
        ValueError,
        match=(
            "completed executions must include "
            "final_order_id"
        ),
    ):
        ExecutionResult(
            execution_id=value.execution_id,
            status=value.status,
            decision=value.decision,
            started_at=value.started_at,
            updated_at=value.updated_at,
            completed_at=value.completed_at,
            steps=value.steps,
            broker_order_id=value.broker_order_id,
        )


def test_completed_result_requires_broker_order_id() -> None:
    value = completed_result()

    with pytest.raises(
        ValueError,
        match=(
            "completed executions must include "
            "broker_order_id"
        ),
    ):
        ExecutionResult(
            execution_id=value.execution_id,
            status=value.status,
            decision=value.decision,
            started_at=value.started_at,
            updated_at=value.updated_at,
            completed_at=value.completed_at,
            steps=value.steps,
            final_order_id=value.final_order_id,
        )


def test_failed_result_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed executions must include an error"
        ),
    ):
        ExecutionResult(
            execution_id="execution-001",
            status=ExecutionStatus.FAILED,
            decision=ExecutionDecision.NO_ACTION,
            started_at=NOW,
            updated_at=NOW,
            completed_at=NOW,
        )


def test_non_failed_result_rejects_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only failed executions may include an error"
        ),
    ):
        ExecutionResult(
            execution_id="execution-001",
            status=ExecutionStatus.REJECTED,
            decision=ExecutionDecision.REJECT,
            started_at=NOW,
            updated_at=NOW,
            completed_at=NOW,
            error="Unexpected error.",
        )


def test_execution_report() -> None:
    request = execution_request()
    result = completed_result()

    report = ExecutionReport(
        report_id="report-001",
        request=request,
        result=result,
        reported_at=NOW + timedelta(seconds=4),
        message="Execution completed successfully.",
    )

    assert report.request == request
    assert report.result == result
    assert report.report_id == "report-001"


def test_report_text_is_normalized() -> None:
    report = ExecutionReport(
        report_id="  report-001  ",
        request=execution_request(),
        result=completed_result(),
        reported_at=NOW + timedelta(seconds=4),
        message="  Execution completed.  ",
        metadata=[("  source  ", "  coordinator  ")],
        warnings=["  Review commission.  "],
    )

    assert report.report_id == "report-001"
    assert report.message == "Execution completed."
    assert report.metadata == (
        ("source", "coordinator"),
    )
    assert report.warnings == (
        "Review commission.",
    )


def test_report_execution_ids_must_match() -> None:
    result = ExecutionResult(
        execution_id="different-execution",
        status=ExecutionStatus.EXECUTING,
        decision=ExecutionDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result execution_id values "
            "must match"
        ),
    ):
        ExecutionReport(
            report_id="report-001",
            request=execution_request(),
            result=result,
            reported_at=NOW,
            message="Execution report.",
        )


def test_report_result_must_not_precede_request() -> None:
    result = ExecutionResult(
        execution_id="execution-001",
        status=ExecutionStatus.EXECUTING,
        decision=ExecutionDecision.PROCEED,
        started_at=NOW - timedelta(seconds=1),
        updated_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match=(
            "result started_at must not be earlier "
            "than request created_at"
        ),
    ):
        ExecutionReport(
            report_id="report-001",
            request=execution_request(),
            result=result,
            reported_at=NOW,
            message="Execution report.",
        )


def test_reported_at_must_follow_result_update() -> None:
    result = completed_result()

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier than "
            "result updated_at"
        ),
    ):
        ExecutionReport(
            report_id="report-001",
            request=execution_request(),
            result=result,
            reported_at=NOW,
            message="Execution report.",
        )


def test_models_are_immutable() -> None:
    value = execution_request()

    with pytest.raises(FrozenInstanceError):
        value.execution_id = "changed"