from __future__ import annotations

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
from app.strategy.risk_gateway import (
    RiskEvaluationRequest,
)
from app.strategy.trading_orchestrator import (
    EnterpriseTradingOrchestrator,
    TradingWorkflowRequest,
    WorkflowDecision,
    WorkflowStage,
    WorkflowStatus,
)
from app.strategy.trading_session import (
    SessionState,
    SessionType,
    TradingSession,
)


NOW = datetime(
    2026,
    8,
    5,
    20,
    0,
    tzinfo=timezone.utc,
)

SESSION_TIME = NOW - timedelta(minutes=10)
ORDER_TIME = NOW - timedelta(minutes=8)
RISK_TIME = NOW - timedelta(minutes=5)
BROKER_TIME = NOW - timedelta(minutes=3)
EXECUTION_TIME = NOW - timedelta(minutes=1)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def trading_session() -> TradingSession:
    return TradingSession(
        session_id="session-001",
        calendar_id="calendar-001",
        market="NYSE",
        trading_date=date(2026, 8, 5),
        state=SessionState.OPEN,
        session_type=SessionType.REGULAR,
        opened_at=(
            SESSION_TIME - timedelta(minutes=30)
        ),
        closed_at=None,
        evaluated_at=SESSION_TIME,
        trading_allowed=True,
        reason="Regular trading session is open.",
    )


def order_request(
    *,
    order_id: str = "order-001",
    client_order_id: str = "client-order-001",
    portfolio_id: str = "portfolio-001",
    strategy_id: str = "strategy-001",
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
        quantity=Decimal("10"),
        created_at=ORDER_TIME,
        strategy_id=strategy_id,
    )


def risk_request(
    order: OrderRequest,
) -> RiskEvaluationRequest:
    return RiskEvaluationRequest(
        evaluation_id=f"risk-{order.order_id}",
        request=order,
        account_id="account-001",
        portfolio_id=order.portfolio_id,
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
    order: OrderRequest,
) -> BrokerOrderRequest:
    return BrokerOrderRequest(
        gateway_order_id=f"gateway-{order.order_id}",
        order_id=order.order_id,
        client_order_id=order.client_order_id,
        broker_name="Interactive Brokers",
        account_id="account-001",
        environment=BrokerEnvironment.PAPER,
        symbol=order.symbol,
        asset_class=order.asset_class,
        side=order.side,
        order_type=order.order_type,
        time_in_force=order.time_in_force,
        quantity=order.quantity,
        submitted_at=BROKER_TIME,
        limit_price=order.limit_price,
        stop_price=order.stop_price,
    )


def execution_request(
    *,
    execution_id: str = "execution-001",
    correlation_id: str = "correlation-001",
    order_id: str = "order-001",
    client_order_id: str = "client-order-001",
    portfolio_id: str = "portfolio-001",
    strategy_id: str = "strategy-001",
    symbol: str = "NVDA",
) -> ExecutionRequest:
    order = order_request(
        order_id=order_id,
        client_order_id=client_order_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        symbol=symbol,
    )

    return ExecutionRequest(
        execution_id=execution_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        session=trading_session(),
        order_request=order,
        created_at=EXECUTION_TIME,
        risk_request=risk_request(order),
        broker_request=broker_request(order),
        requested_by="strategy-orchestrator",
    )


def workflow_request(
    *,
    workflow_id: str = "workflow-001",
    correlation_id: str = "correlation-001",
    execution_id: str = "execution-001",
    order_id: str = "order-001",
    client_order_id: str = "client-order-001",
    portfolio_id: str = "portfolio-001",
    strategy_id: str = "strategy-001",
    symbol: str = "NVDA",
) -> TradingWorkflowRequest:
    execution = execution_request(
        execution_id=execution_id,
        correlation_id=correlation_id,
        order_id=order_id,
        client_order_id=client_order_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        symbol=symbol,
    )

    return TradingWorkflowRequest(
        workflow_id=workflow_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        execution_request=execution,
        created_at=NOW,
        requested_by="strategy-orchestrator",
    )


def orchestrator(
    *,
    current_time: datetime = NOW,
) -> EnterpriseTradingOrchestrator:
    return EnterpriseTradingOrchestrator(
        clock=FixedClock(current_time)
    )


def registered_orchestrator(
) -> EnterpriseTradingOrchestrator:
    value = orchestrator()
    value.register_workflow(
        workflow_request()
    )
    return value


def started_orchestrator(
) -> EnterpriseTradingOrchestrator:
    value = registered_orchestrator()
    value.start_workflow("workflow-001")
    return value


def test_create_orchestrator() -> None:
    value = orchestrator()

    assert value.workflow_ids == ()
    assert value.report_history == ()


def test_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterpriseTradingOrchestrator(
            clock=NOW
        )


def test_register_workflow() -> None:
    value = orchestrator()
    request = workflow_request()

    result = value.register_workflow(request)

    assert result == request
    assert value.workflow_ids == (
        "workflow-001",
    )


def test_register_requires_workflow_request() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "request must be a TradingWorkflowRequest"
        ),
    ):
        orchestrator().register_workflow(
            object()
        )


def test_duplicate_workflow_id_is_rejected() -> None:
    value = registered_orchestrator()

    with pytest.raises(
        ValueError,
        match="workflow_id is already registered",
    ):
        value.register_workflow(
            workflow_request(
                correlation_id="correlation-002",
                execution_id="execution-002",
                order_id="order-002",
                client_order_id="client-order-002",
            )
        )


def test_duplicate_correlation_id_is_rejected() -> None:
    value = registered_orchestrator()

    with pytest.raises(
        ValueError,
        match=(
            "correlation_id is already registered"
        ),
    ):
        value.register_workflow(
            workflow_request(
                workflow_id="workflow-002",
                execution_id="execution-002",
                order_id="order-002",
                client_order_id="client-order-002",
            )
        )


def test_duplicate_execution_id_is_rejected() -> None:
    value = registered_orchestrator()

    with pytest.raises(
        ValueError,
        match="execution_id is already registered",
    ):
        value.register_workflow(
            workflow_request(
                workflow_id="workflow-002",
                correlation_id="correlation-002",
                order_id="order-002",
                client_order_id="client-order-002",
            )
        )


def test_register_multiple_workflows() -> None:
    value = orchestrator()

    value.register_workflow(
        workflow_request()
    )

    value.register_workflow(
        workflow_request(
            workflow_id="workflow-002",
            correlation_id="correlation-002",
            execution_id="execution-002",
            order_id="order-002",
            client_order_id="client-order-002",
            symbol="AAPL",
        )
    )

    assert value.workflow_ids == (
        "workflow-001",
        "workflow-002",
    )


def test_unregister_workflow() -> None:
    value = registered_orchestrator()

    removed = value.unregister_workflow(
        "workflow-001"
    )

    assert removed.workflow_id == "workflow-001"
    assert value.workflow_ids == ()


def test_unregister_unknown_workflow_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "trading workflow request not found"
        ),
    ):
        orchestrator().unregister_workflow(
            "missing"
        )


def test_unregister_started_workflow_is_rejected() -> None:
    value = started_orchestrator()

    with pytest.raises(
        RuntimeError,
        match=(
            "started workflows cannot be unregistered"
        ),
    ):
        value.unregister_workflow(
            "workflow-001"
        )


def test_get_request() -> None:
    value = registered_orchestrator()

    request = value.get_request(
        "workflow-001"
    )

    assert request.workflow_id == "workflow-001"
    assert request.execution_id == "execution-001"


def test_get_request_normalizes_identifier() -> None:
    value = registered_orchestrator()

    request = value.get_request(
        "  workflow-001  "
    )

    assert request.workflow_id == "workflow-001"


def test_get_unknown_request_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "trading workflow request not found"
        ),
    ):
        orchestrator().get_request("missing")


def test_request_for_correlation() -> None:
    value = registered_orchestrator()

    request = value.request_for_correlation(
        "correlation-001"
    )

    assert request.workflow_id == "workflow-001"


def test_request_for_correlation_normalizes_identifier(
) -> None:
    value = registered_orchestrator()

    request = value.request_for_correlation(
        "  correlation-001  "
    )

    assert request.correlation_id == (
        "correlation-001"
    )


def test_unknown_correlation_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "trading workflow not found for "
            "correlation_id"
        ),
    ):
        orchestrator().request_for_correlation(
            "missing"
        )


def test_request_for_execution() -> None:
    value = registered_orchestrator()

    request = value.request_for_execution(
        "execution-001"
    )

    assert request.workflow_id == "workflow-001"


def test_request_for_execution_normalizes_identifier(
) -> None:
    value = registered_orchestrator()

    request = value.request_for_execution(
        "  execution-001  "
    )

    assert request.execution_id == "execution-001"


def test_unknown_execution_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "trading workflow not found for "
            "execution_id"
        ),
    ):
        orchestrator().request_for_execution(
            "missing"
        )


def test_start_workflow() -> None:
    value = registered_orchestrator()

    report = value.start_workflow(
        "workflow-001"
    )

    assert report.result.status is (
        WorkflowStatus.RUNNING
    )
    assert report.result.decision is (
        WorkflowDecision.PROCEED
    )
    assert report.result.checkpoints == ()
    assert report.result.started_at == NOW
    assert report.result.updated_at == NOW


def test_start_workflow_is_idempotent() -> None:
    value = registered_orchestrator()

    first = value.start_workflow(
        "workflow-001"
    )
    second = value.start_workflow(
        "workflow-001"
    )

    assert first == second
    assert len(value.report_history) == 1
    assert len(
        value.results_for_workflow(
            "workflow-001"
        )
    ) == 1


def test_start_unknown_workflow_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "trading workflow request not found"
        ),
    ):
        orchestrator().start_workflow(
            "missing"
        )


def test_start_time_must_not_precede_request() -> None:
    value = orchestrator(
        current_time=NOW - timedelta(seconds=1)
    )
    value.register_workflow(
        workflow_request()
    )

    with pytest.raises(
        ValueError,
        match=(
            "workflow start time must not be earlier "
            "than request created_at"
        ),
    ):
        value.start_workflow(
            "workflow-001"
        )


def test_get_result() -> None:
    value = started_orchestrator()

    result = value.get_result(
        "workflow-001"
    )

    assert result.status is WorkflowStatus.RUNNING
    assert result.workflow_id == "workflow-001"


def test_get_result_before_start_is_rejected() -> None:
    value = registered_orchestrator()

    with pytest.raises(
        KeyError,
        match=(
            "trading workflow has no result state"
        ),
    ):
        value.get_result(
            "workflow-001"
        )


def test_get_report() -> None:
    value = started_orchestrator()

    report = value.get_report(
        "workflow-001"
    )

    assert report.request.workflow_id == (
        "workflow-001"
    )
    assert report.result.status is (
        WorkflowStatus.RUNNING
    )


def test_get_report_before_start_is_rejected() -> None:
    value = registered_orchestrator()

    with pytest.raises(
        KeyError,
        match=(
            "trading workflow has no report"
        ),
    ):
        value.get_report(
            "workflow-001"
        )


def test_results_for_workflow() -> None:
    value = started_orchestrator()

    results = value.results_for_workflow(
        "workflow-001"
    )

    assert len(results) == 1
    assert results[0].status is (
        WorkflowStatus.RUNNING
    )


def test_results_for_unstarted_workflow_returns_empty(
) -> None:
    value = registered_orchestrator()

    assert value.results_for_workflow(
        "workflow-001"
    ) == ()


def test_reports_for_order() -> None:
    value = started_orchestrator()

    reports = value.reports_for_order(
        "order-001"
    )

    assert len(reports) == 1
    assert reports[0].request.order_id == (
        "order-001"
    )


def test_reports_for_unknown_order_returns_empty() -> None:
    value = started_orchestrator()

    assert value.reports_for_order(
        "missing-order"
    ) == ()


def test_reports_for_portfolio() -> None:
    value = started_orchestrator()

    reports = value.reports_for_portfolio(
        "portfolio-001"
    )

    assert len(reports) == 1
    assert reports[0].request.portfolio_id == (
        "portfolio-001"
    )


def test_reports_for_unknown_portfolio_returns_empty(
) -> None:
    value = started_orchestrator()

    assert value.reports_for_portfolio(
        "missing-portfolio"
    ) == ()


def test_reports_for_strategy() -> None:
    value = started_orchestrator()

    reports = value.reports_for_strategy(
        "strategy-001"
    )

    assert len(reports) == 1
    assert reports[0].request.strategy_id == (
        "strategy-001"
    )


def test_reports_for_unknown_strategy_returns_empty(
) -> None:
    value = started_orchestrator()

    assert value.reports_for_strategy(
        "missing-strategy"
    ) == ()


def test_latest_report() -> None:
    value = started_orchestrator()

    report = value.latest_report()

    assert report.request.workflow_id == (
        "workflow-001"
    )


def test_latest_report_without_history_is_rejected(
) -> None:
    with pytest.raises(
        KeyError,
        match=(
            "trading orchestrator has no reports"
        ),
    ):
        orchestrator().latest_report()


def test_report_history_property() -> None:
    value = started_orchestrator()

    assert len(value.report_history) == 1
    assert value.report_history[0].report_id == (
        "workflow-report-000001"
    )


def test_report_ids_continue_across_workflows() -> None:
    value = orchestrator()

    value.register_workflow(
        workflow_request()
    )

    value.register_workflow(
        workflow_request(
            workflow_id="workflow-002",
            correlation_id="correlation-002",
            execution_id="execution-002",
            order_id="order-002",
            client_order_id="client-order-002",
            symbol="AAPL",
        )
    )

    first = value.start_workflow(
        "workflow-001"
    )
    second = value.start_workflow(
        "workflow-002"
    )

    assert first.report_id == (
        "workflow-report-000001"
    )
    assert second.report_id == (
        "workflow-report-000002"
    )


def test_report_contains_workflow_metadata() -> None:
    value = started_orchestrator()

    report = value.get_report(
        "workflow-001"
    )

    assert report.metadata == (
        ("correlation_id", "correlation-001"),
        ("execution_id", "execution-001"),
        ("order_id", "order-001"),
    )


def test_workflow_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="workflow_id must not be empty",
    ):
        orchestrator().get_request("   ")


def test_workflow_identifier_must_be_string() -> None:
    with pytest.raises(
        TypeError,
        match="workflow_id must be a string",
    ):
        orchestrator().get_request(123)


def test_correlation_identifier_must_not_be_empty(
) -> None:
    with pytest.raises(
        ValueError,
        match="correlation_id must not be empty",
    ):
        orchestrator().request_for_correlation(
            "   "
        )


def test_execution_identifier_must_not_be_empty(
) -> None:
    with pytest.raises(
        ValueError,
        match="execution_id must not be empty",
    ):
        orchestrator().request_for_execution(
            "   "
        )


def test_order_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="order_id must not be empty",
    ):
        orchestrator().reports_for_order(
            "   "
        )


def test_portfolio_identifier_must_not_be_empty(
) -> None:
    with pytest.raises(
        ValueError,
        match="portfolio_id must not be empty",
    ):
        orchestrator().reports_for_portfolio(
            "   "
        )


def test_strategy_identifier_must_not_be_empty(
) -> None:
    with pytest.raises(
        ValueError,
        match="strategy_id must not be empty",
    ):
        orchestrator().reports_for_strategy(
            "   "
        )


def test_clock_must_return_datetime() -> None:
    value = EnterpriseTradingOrchestrator(
        clock=lambda: "now"
    )
    value.register_workflow(
        workflow_request()
    )

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        value.start_workflow(
            "workflow-001"
        )


def test_clock_must_return_timezone_aware_datetime(
) -> None:
    value = EnterpriseTradingOrchestrator(
        clock=lambda: datetime(
            2026,
            8,
            5,
            20,
            0,
        )
    )
    value.register_workflow(
        workflow_request()
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        value.start_workflow(
            "workflow-001"
        )
def completed_execution_report(
    *,
    request: ExecutionRequest | None = None,
    execution_id: str = "execution-001",
    order_id: str = "order-001",
    client_order_id: str = "client-order-001",
) -> ExecutionReport:
    effective_request = request or execution_request(
        execution_id=execution_id,
        order_id=order_id,
        client_order_id=client_order_id,
    )

    step_time = NOW - timedelta(seconds=20)

    step = ExecutionStep(
        step_id="execution-step-001",
        execution_id=effective_request.execution_id,
        stage=ExecutionStage.BROKER,
        decision=ExecutionDecision.PROCEED,
        started_at=step_time,
        completed_at=step_time,
        successful=True,
        message="Broker execution completed.",
        reference_id="broker-order-001",
    )

    result = ExecutionResult(
        execution_id=effective_request.execution_id,
        status=ExecutionStatus.COMPLETED,
        decision=ExecutionDecision.PROCEED,
        started_at=step_time,
        updated_at=(
            NOW - timedelta(seconds=10)
        ),
        completed_at=(
            NOW - timedelta(seconds=10)
        ),
        steps=(step,),
        final_order_id=(
            effective_request.order_request.order_id
        ),
        broker_order_id="broker-order-001",
    )

    return ExecutionReport(
        report_id="execution-report-001",
        request=effective_request,
        result=result,
        reported_at=(
            NOW - timedelta(seconds=5)
        ),
        message="Execution completed successfully.",
    )


def test_record_strategy_checkpoint() -> None:
    value = started_orchestrator()

    report = value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.STRATEGY,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Strategy signal validated.",
        reference_id="strategy-001",
    )

    assert report.result.status is (
        WorkflowStatus.RUNNING
    )
    assert len(report.result.checkpoints) == 1

    checkpoint = report.result.checkpoints[0]

    assert checkpoint.checkpoint_id == (
        "workflow-checkpoint-000001"
    )
    assert checkpoint.stage is (
        WorkflowStage.STRATEGY
    )
    assert checkpoint.decision is (
        WorkflowDecision.PROCEED
    )
    assert checkpoint.successful is True
    assert checkpoint.reference_id == (
        "strategy-001"
    )


def test_record_multiple_ordered_checkpoints() -> None:
    value = started_orchestrator()

    stages = (
        WorkflowStage.STRATEGY,
        WorkflowStage.SESSION,
        WorkflowStage.PORTFOLIO,
        WorkflowStage.ORDER,
        WorkflowStage.RISK,
        WorkflowStage.BROKER,
        WorkflowStage.EXECUTION,
    )

    for stage in stages:
        value.record_checkpoint(
            "workflow-001",
            stage=stage,
            decision=WorkflowDecision.PROCEED,
            successful=True,
            message=f"{stage.value} completed.",
        )

    result = value.get_result(
        "workflow-001"
    )

    assert tuple(
        checkpoint.stage
        for checkpoint in result.checkpoints
    ) == stages


def test_record_checkpoint_requires_stage_enum() -> None:
    value = started_orchestrator()

    with pytest.raises(
        TypeError,
        match="stage must be a WorkflowStage",
    ):
        value.record_checkpoint(
            "workflow-001",
            stage="STRATEGY",
            decision=WorkflowDecision.PROCEED,
            successful=True,
            message="Invalid stage.",
        )


def test_record_checkpoint_requires_decision_enum(
) -> None:
    value = started_orchestrator()

    with pytest.raises(
        TypeError,
        match=(
            "decision must be a WorkflowDecision"
        ),
    ):
        value.record_checkpoint(
            "workflow-001",
            stage=WorkflowStage.STRATEGY,
            decision="PROCEED",
            successful=True,
            message="Invalid decision.",
        )


def test_record_checkpoint_requires_success_bool(
) -> None:
    value = started_orchestrator()

    with pytest.raises(
        TypeError,
        match="successful must be a bool",
    ):
        value.record_checkpoint(
            "workflow-001",
            stage=WorkflowStage.STRATEGY,
            decision=WorkflowDecision.PROCEED,
            successful="yes",
            message="Invalid success value.",
        )


def test_duplicate_workflow_stage_is_rejected() -> None:
    value = started_orchestrator()

    value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.STRATEGY,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Strategy validated.",
    )

    with pytest.raises(
        ValueError,
        match="workflow stage is already recorded",
    ):
        value.record_checkpoint(
            "workflow-001",
            stage=WorkflowStage.STRATEGY,
            decision=WorkflowDecision.PROCEED,
            successful=True,
            message="Duplicate strategy checkpoint.",
        )


def test_workflow_stages_must_be_recorded_in_order(
) -> None:
    value = started_orchestrator()

    value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.RISK,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Risk approved.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "workflow stages must be recorded "
            "in pipeline order"
        ),
    ):
        value.record_checkpoint(
            "workflow-001",
            stage=WorkflowStage.ORDER,
            decision=WorkflowDecision.PROCEED,
            successful=True,
            message="Order recorded too late.",
        )


def test_workflow_may_skip_optional_stages() -> None:
    value = started_orchestrator()

    value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.STRATEGY,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Strategy validated.",
    )

    value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.RISK,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Risk approved.",
    )

    result = value.get_result(
        "workflow-001"
    )

    assert tuple(
        checkpoint.stage
        for checkpoint in result.checkpoints
    ) == (
        WorkflowStage.STRATEGY,
        WorkflowStage.RISK,
    )


def test_checkpoint_ids_are_deterministic() -> None:
    value = started_orchestrator()

    first = value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.STRATEGY,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Strategy validated.",
    )

    second = value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.SESSION,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Session validated.",
    )

    assert (
        first.result
        .checkpoints[-1]
        .checkpoint_id
        == "workflow-checkpoint-000001"
    )

    assert (
        second.result
        .checkpoints[-1]
        .checkpoint_id
        == "workflow-checkpoint-000002"
    )


def test_checkpoint_ids_continue_across_workflows(
) -> None:
    value = orchestrator()

    value.register_workflow(
        workflow_request()
    )

    value.register_workflow(
        workflow_request(
            workflow_id="workflow-002",
            correlation_id="correlation-002",
            execution_id="execution-002",
            order_id="order-002",
            client_order_id="client-order-002",
            symbol="AAPL",
        )
    )

    value.start_workflow("workflow-001")
    value.start_workflow("workflow-002")

    first = value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.STRATEGY,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="First strategy validated.",
    )

    second = value.record_checkpoint(
        "workflow-002",
        stage=WorkflowStage.STRATEGY,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Second strategy validated.",
    )

    assert (
        first.result
        .checkpoints[-1]
        .checkpoint_id
        == "workflow-checkpoint-000001"
    )

    assert (
        second.result
        .checkpoints[-1]
        .checkpoint_id
        == "workflow-checkpoint-000002"
    )


def test_checkpoint_warnings_are_accumulated() -> None:
    value = started_orchestrator()

    value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.STRATEGY,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Strategy validated.",
        warnings=("Strategy warning.",),
    )

    report = value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.SESSION,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Session validated.",
        warnings=("Session warning.",),
    )

    assert report.result.warnings == (
        "Strategy warning.",
        "Session warning.",
    )

    assert report.warnings == (
        "Strategy warning.",
        "Session warning.",
    )


def test_duplicate_checkpoint_warnings_are_removed(
) -> None:
    value = started_orchestrator()

    value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.STRATEGY,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Strategy validated.",
        warnings=("Shared warning.",),
    )

    report = value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.SESSION,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Session validated.",
        warnings=("Shared warning.",),
    )

    assert report.result.warnings == (
        "Shared warning.",
    )


def test_result_history_records_every_transition(
) -> None:
    value = started_orchestrator()

    value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.STRATEGY,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Strategy validated.",
    )

    value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.SESSION,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Session validated.",
    )

    history = value.results_for_workflow(
        "workflow-001"
    )

    assert len(history) == 3

    assert tuple(
        len(result.checkpoints)
        for result in history
    ) == (0, 1, 2)


def test_report_history_records_every_transition(
) -> None:
    value = started_orchestrator()

    value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.STRATEGY,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Strategy validated.",
    )

    value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.SESSION,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Session validated.",
    )

    assert tuple(
        report.report_id
        for report in value.report_history
    ) == (
        "workflow-report-000001",
        "workflow-report-000002",
        "workflow-report-000003",
    )


def execution_ready_orchestrator(
) -> EnterpriseTradingOrchestrator:
    value = started_orchestrator()

    stages = (
        WorkflowStage.STRATEGY,
        WorkflowStage.SESSION,
        WorkflowStage.PORTFOLIO,
        WorkflowStage.ORDER,
        WorkflowStage.RISK,
        WorkflowStage.BROKER,
        WorkflowStage.EXECUTION,
    )

    for stage in stages:
        value.record_checkpoint(
            "workflow-001",
            stage=stage,
            decision=WorkflowDecision.PROCEED,
            successful=True,
            message=f"{stage.value} completed.",
            reference_id=(
                f"reference-{stage.value.lower()}"
            ),
        )

    return value


def test_complete_workflow() -> None:
    value = execution_ready_orchestrator()

    report = value.complete_workflow(
        "workflow-001",
        execution_report=(
            completed_execution_report()
        ),
    )

    assert report.result.status is (
        WorkflowStatus.COMPLETED
    )
    assert report.result.decision is (
        WorkflowDecision.PROCEED
    )
    assert report.result.is_terminal is True
    assert report.result.execution_report is not None
    assert len(report.result.checkpoints) == 7


def test_complete_workflow_requires_execution_report(
) -> None:
    value = execution_ready_orchestrator()

    with pytest.raises(
        TypeError,
        match=(
            "execution_report must be an "
            "ExecutionReport"
        ),
    ):
        value.complete_workflow(
            "workflow-001",
            execution_report=object(),
        )


def test_execution_report_execution_id_must_match(
) -> None:
    value = execution_ready_orchestrator()

    report = completed_execution_report(
        execution_id="different-execution",
        order_id="order-001",
    )

    with pytest.raises(
        ValueError,
        match=(
            "execution_report execution_id must match "
            "workflow execution_id"
        ),
    ):
        value.complete_workflow(
            "workflow-001",
            execution_report=report,
        )


def test_execution_report_order_id_must_match() -> None:
    value = execution_ready_orchestrator()

    report = completed_execution_report(
        execution_id="execution-001",
        order_id="different-order",
        client_order_id="different-client-order",
    )

    with pytest.raises(
        ValueError,
        match=(
            "execution_report order_id must match "
            "workflow order_id"
        ),
    ):
        value.complete_workflow(
            "workflow-001",
            execution_report=report,
        )


def test_completion_requires_checkpoints() -> None:
    value = started_orchestrator()

    with pytest.raises(
        RuntimeError,
        match=(
            "workflow cannot complete without checkpoints"
        ),
    ):
        value.complete_workflow(
            "workflow-001",
            execution_report=(
                completed_execution_report()
            ),
        )


def test_completion_requires_execution_stage() -> None:
    value = started_orchestrator()

    value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.STRATEGY,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Strategy validated.",
    )

    value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.RISK,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Risk approved.",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "workflow must reach the execution stage "
            "before completion"
        ),
    ):
        value.complete_workflow(
            "workflow-001",
            execution_report=(
                completed_execution_report()
            ),
        )


def test_completion_time_must_follow_execution_report(
) -> None:
    value = execution_ready_orchestrator()

    future_request = execution_request()

    step = ExecutionStep(
        step_id="execution-step-future",
        execution_id="execution-001",
        stage=ExecutionStage.BROKER,
        decision=ExecutionDecision.PROCEED,
        started_at=NOW,
        completed_at=NOW,
        successful=True,
        message="Execution completed.",
    )

    future_result = ExecutionResult(
        execution_id="execution-001",
        status=ExecutionStatus.COMPLETED,
        decision=ExecutionDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW + timedelta(seconds=1),
        completed_at=NOW + timedelta(seconds=1),
        steps=(step,),
        final_order_id="order-001",
        broker_order_id="broker-order-001",
    )

    future_report = ExecutionReport(
        report_id="execution-report-future",
        request=future_request,
        result=future_result,
        reported_at=NOW + timedelta(seconds=1),
        message="Future execution report.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "workflow completion time must not be "
            "earlier than execution report time"
        ),
    ):
        value.complete_workflow(
            "workflow-001",
            execution_report=future_report,
        )


def test_hold_workflow() -> None:
    value = started_orchestrator()

    report = value.hold_workflow(
        "workflow-001",
        stage=WorkflowStage.SESSION,
        reason="Trading session is unavailable.",
        reference_id="session-001",
    )

    assert report.result.status is (
        WorkflowStatus.HELD
    )
    assert report.result.decision is (
        WorkflowDecision.HOLD
    )
    assert report.result.is_terminal is True
    assert report.result.failed_checkpoint is not None


def test_reject_workflow() -> None:
    value = started_orchestrator()

    report = value.reject_workflow(
        "workflow-001",
        stage=WorkflowStage.RISK,
        reason="Risk gateway rejected the trade.",
        reference_id="risk-001",
    )

    assert report.result.status is (
        WorkflowStatus.REJECTED
    )
    assert report.result.decision is (
        WorkflowDecision.REJECT
    )
    assert report.result.is_terminal is True


def test_cancel_workflow() -> None:
    value = started_orchestrator()

    report = value.cancel_workflow(
        "workflow-001",
        stage=WorkflowStage.ORDER,
        reason="Workflow cancelled by operator.",
        reference_id="order-001",
    )

    assert report.result.status is (
        WorkflowStatus.CANCELLED
    )
    assert report.result.decision is (
        WorkflowDecision.CANCEL
    )
    assert report.result.is_terminal is True


def test_fail_workflow() -> None:
    value = started_orchestrator()

    report = value.fail_workflow(
        "workflow-001",
        stage=WorkflowStage.BROKER,
        error="Broker connection failed.",
        reference_id="account-001",
    )

    assert report.result.status is (
        WorkflowStatus.FAILED
    )
    assert report.result.decision is (
        WorkflowDecision.NO_ACTION
    )
    assert report.result.error == (
        "Broker connection failed."
    )
    assert report.result.is_terminal is True


@pytest.mark.parametrize(
    ("method_name", "argument_name"),
    [
        ("hold_workflow", "reason"),
        ("reject_workflow", "reason"),
        ("cancel_workflow", "reason"),
        ("fail_workflow", "error"),
    ],
)
def test_terminal_message_must_not_be_empty(
    method_name: str,
    argument_name: str,
) -> None:
    value = started_orchestrator()
    method = getattr(value, method_name)

    arguments = {
        "workflow_id": "workflow-001",
        "stage": WorkflowStage.RISK,
        argument_name: "   ",
    }

    with pytest.raises(
        ValueError,
        match=f"{argument_name} must not be empty",
    ):
        method(**arguments)


def test_terminal_stage_must_be_enum() -> None:
    value = started_orchestrator()

    with pytest.raises(
        TypeError,
        match="stage must be a WorkflowStage",
    ):
        value.reject_workflow(
            "workflow-001",
            stage="RISK",
            reason="Invalid stage.",
        )


def test_terminal_transition_respects_stage_order(
) -> None:
    value = started_orchestrator()

    value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.RISK,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Risk approved.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "workflow stages must be recorded "
            "in pipeline order"
        ),
    ):
        value.reject_workflow(
            "workflow-001",
            stage=WorkflowStage.ORDER,
            reason="Late order rejection.",
        )


def test_terminal_transition_rejects_duplicate_stage(
) -> None:
    value = started_orchestrator()

    value.record_checkpoint(
        "workflow-001",
        stage=WorkflowStage.RISK,
        decision=WorkflowDecision.PROCEED,
        successful=True,
        message="Risk approved.",
    )

    with pytest.raises(
        ValueError,
        match="workflow stage is already recorded",
    ):
        value.reject_workflow(
            "workflow-001",
            stage=WorkflowStage.RISK,
            reason="Duplicate risk stage.",
        )


@pytest.mark.parametrize(
    "terminal_action",
    [
        "hold_workflow",
        "reject_workflow",
        "cancel_workflow",
        "fail_workflow",
    ],
)
def test_terminal_workflow_cannot_be_modified(
    terminal_action: str,
) -> None:
    value = started_orchestrator()

    if terminal_action == "fail_workflow":
        value.fail_workflow(
            "workflow-001",
            stage=WorkflowStage.RISK,
            error="Risk service failed.",
        )
    else:
        method = getattr(value, terminal_action)

        method(
            "workflow-001",
            stage=WorkflowStage.RISK,
            reason="Terminal workflow transition.",
        )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal workflows cannot be modified"
        ),
    ):
        value.record_checkpoint(
            "workflow-001",
            stage=WorkflowStage.BROKER,
            decision=WorkflowDecision.PROCEED,
            successful=True,
            message="Invalid terminal update.",
        )


def test_completed_workflow_cannot_be_modified() -> None:
    value = execution_ready_orchestrator()

    value.complete_workflow(
        "workflow-001",
        execution_report=(
            completed_execution_report()
        ),
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal workflows cannot be modified"
        ),
    ):
        value.record_checkpoint(
            "workflow-001",
            stage=WorkflowStage.EXECUTION,
            decision=WorkflowDecision.PROCEED,
            successful=True,
            message="Invalid post-completion update.",
        )


def test_latest_report_tracks_terminal_result() -> None:
    value = started_orchestrator()

    expected = value.reject_workflow(
        "workflow-001",
        stage=WorkflowStage.RISK,
        reason="Risk rejected the workflow.",
    )

    assert value.latest_report() == expected
    assert value.get_report(
        "workflow-001"
    ) == expected


def test_reports_for_order_include_full_history(
) -> None:
    value = execution_ready_orchestrator()

    value.complete_workflow(
        "workflow-001",
        execution_report=(
            completed_execution_report()
        ),
    )

    reports = value.reports_for_order(
        "order-001"
    )

    assert len(reports) == 9
    assert reports[-1].result.status is (
        WorkflowStatus.COMPLETED
    )


def test_completion_report_id_is_deterministic(
) -> None:
    value = execution_ready_orchestrator()

    report = value.complete_workflow(
        "workflow-001",
        execution_report=(
            completed_execution_report()
        ),
    )

    assert report.report_id == (
        "workflow-report-000009"
    )