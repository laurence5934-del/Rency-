from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.broker_gateway import (
    BrokerEnvironment,
    BrokerOrderRequest,
)
from app.strategy.execution_coordinator import (
    EnterpriseExecutionCoordinator,
    ExecutionDecision,
    ExecutionRequest,
    ExecutionStage,
    ExecutionStatus,
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
    15,
    0,
    tzinfo=timezone.utc,
)

SESSION_TIME = NOW - timedelta(minutes=5)
ORDER_TIME = NOW - timedelta(minutes=4)
RISK_TIME = NOW - timedelta(minutes=2)
BROKER_TIME = NOW - timedelta(minutes=1)


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
        opened_at=SESSION_TIME - timedelta(minutes=30),
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
        created_at=NOW,
        risk_request=risk_request(order),
        broker_request=broker_request(order),
        requested_by="strategy-orchestrator",
    )


def coordinator(
    current_time: datetime = NOW,
) -> EnterpriseExecutionCoordinator:
    return EnterpriseExecutionCoordinator(
        clock=FixedClock(current_time)
    )


def registered_coordinator() -> EnterpriseExecutionCoordinator:
    value = coordinator()
    value.register_request(execution_request())
    return value


def started_coordinator() -> EnterpriseExecutionCoordinator:
    value = registered_coordinator()
    value.start_execution("execution-001")
    return value


def test_create_coordinator() -> None:
    value = coordinator()

    assert value.execution_ids == ()
    assert value.report_history == ()


def test_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterpriseExecutionCoordinator(
            clock=NOW
        )


def test_register_request() -> None:
    value = coordinator()
    request = execution_request()

    result = value.register_request(request)

    assert result == request
    assert value.execution_ids == (
        "execution-001",
    )


def test_register_requires_request_model() -> None:
    with pytest.raises(
        TypeError,
        match="request must be an ExecutionRequest",
    ):
        coordinator().register_request(object())


def test_duplicate_execution_id_is_rejected() -> None:
    value = registered_coordinator()

    with pytest.raises(
        ValueError,
        match="execution_id is already registered",
    ):
        value.register_request(
            execution_request(
                correlation_id="correlation-002",
            )
        )


def test_duplicate_correlation_id_is_rejected() -> None:
    value = registered_coordinator()

    with pytest.raises(
        ValueError,
        match="correlation_id is already registered",
    ):
        value.register_request(
            execution_request(
                execution_id="execution-002",
                order_id="order-002",
                client_order_id="client-order-002",
            )
        )


def test_register_multiple_requests() -> None:
    value = coordinator()

    value.register_request(
        execution_request()
    )

    value.register_request(
        execution_request(
            execution_id="execution-002",
            correlation_id="correlation-002",
            order_id="order-002",
            client_order_id="client-order-002",
            symbol="AAPL",
        )
    )

    assert value.execution_ids == (
        "execution-001",
        "execution-002",
    )


def test_unregister_request() -> None:
    value = registered_coordinator()

    removed = value.unregister_request(
        "execution-001"
    )

    assert removed.execution_id == "execution-001"
    assert value.execution_ids == ()


def test_unregister_unknown_request_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="execution request not found",
    ):
        coordinator().unregister_request(
            "missing"
        )


def test_unregister_started_execution_is_rejected() -> None:
    value = started_coordinator()

    with pytest.raises(
        RuntimeError,
        match=(
            "started executions cannot be unregistered"
        ),
    ):
        value.unregister_request(
            "execution-001"
        )


def test_get_request() -> None:
    value = registered_coordinator()

    result = value.get_request(
        "execution-001"
    )

    assert result.execution_id == "execution-001"
    assert result.order_request.order_id == "order-001"


def test_get_request_normalizes_identifier() -> None:
    value = registered_coordinator()

    result = value.get_request(
        "  execution-001  "
    )

    assert result.execution_id == "execution-001"


def test_get_unknown_request_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="execution request not found",
    ):
        coordinator().get_request("missing")


def test_request_for_correlation() -> None:
    value = registered_coordinator()

    result = value.request_for_correlation(
        "correlation-001"
    )

    assert result.execution_id == "execution-001"


def test_request_for_correlation_normalizes_identifier() -> None:
    value = registered_coordinator()

    result = value.request_for_correlation(
        "  correlation-001  "
    )

    assert result.correlation_id == "correlation-001"


def test_unknown_correlation_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "execution request not found for "
            "correlation_id"
        ),
    ):
        coordinator().request_for_correlation(
            "missing"
        )


def test_start_execution() -> None:
    value = registered_coordinator()

    report = value.start_execution(
        "execution-001"
    )

    assert report.result.status is (
        ExecutionStatus.EXECUTING
    )
    assert report.result.decision is (
        ExecutionDecision.PROCEED
    )
    assert report.result.steps == ()
    assert report.result.started_at == NOW
    assert report.result.updated_at == NOW


def test_start_execution_is_idempotent() -> None:
    value = registered_coordinator()

    first = value.start_execution(
        "execution-001"
    )
    second = value.start_execution(
        "execution-001"
    )

    assert first == second
    assert len(value.report_history) == 1
    assert len(
        value.results_for_execution(
            "execution-001"
        )
    ) == 1


def test_start_unknown_execution_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="execution request not found",
    ):
        coordinator().start_execution(
            "missing"
        )


def test_start_time_must_not_precede_request() -> None:
    value = coordinator(
        NOW - timedelta(seconds=1)
    )
    value.register_request(
        execution_request()
    )

    with pytest.raises(
        ValueError,
        match=(
            "execution start time must not be earlier "
            "than request created_at"
        ),
    ):
        value.start_execution(
            "execution-001"
        )


def test_get_result() -> None:
    value = started_coordinator()

    result = value.get_result(
        "execution-001"
    )

    assert result.status is ExecutionStatus.EXECUTING
    assert result.execution_id == "execution-001"


def test_get_result_before_start_is_rejected() -> None:
    value = registered_coordinator()

    with pytest.raises(
        KeyError,
        match="execution has no result state",
    ):
        value.get_result(
            "execution-001"
        )


def test_get_report() -> None:
    value = started_coordinator()

    report = value.get_report(
        "execution-001"
    )

    assert report.request.execution_id == (
        "execution-001"
    )
    assert report.result.status is (
        ExecutionStatus.EXECUTING
    )


def test_get_report_before_start_is_rejected() -> None:
    value = registered_coordinator()

    with pytest.raises(
        KeyError,
        match="execution has no report",
    ):
        value.get_report(
            "execution-001"
        )


def test_latest_report() -> None:
    value = started_coordinator()

    report = value.latest_report()

    assert report.request.execution_id == (
        "execution-001"
    )


def test_latest_report_without_history_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "execution coordinator has no reports"
        ),
    ):
        coordinator().latest_report()


def test_results_for_execution() -> None:
    value = started_coordinator()

    results = value.results_for_execution(
        "execution-001"
    )

    assert len(results) == 1
    assert results[0].status is (
        ExecutionStatus.EXECUTING
    )


def test_results_for_unstarted_execution_returns_empty() -> None:
    value = registered_coordinator()

    assert value.results_for_execution(
        "execution-001"
    ) == ()


def test_reports_for_order() -> None:
    value = started_coordinator()

    reports = value.reports_for_order(
        "order-001"
    )

    assert len(reports) == 1
    assert (
        reports[0].request.order_request.order_id
        == "order-001"
    )


def test_reports_for_unknown_order_returns_empty() -> None:
    value = started_coordinator()

    assert value.reports_for_order(
        "missing-order"
    ) == ()


def test_reports_for_portfolio() -> None:
    value = started_coordinator()

    reports = value.reports_for_portfolio(
        "portfolio-001"
    )

    assert len(reports) == 1
    assert reports[0].request.portfolio_id == (
        "portfolio-001"
    )


def test_reports_for_unknown_portfolio_returns_empty() -> None:
    value = started_coordinator()

    assert value.reports_for_portfolio(
        "missing-portfolio"
    ) == ()


def test_report_history_property() -> None:
    value = started_coordinator()

    assert len(value.report_history) == 1
    assert value.report_history[0].report_id == (
        "execution-report-000001"
    )


def test_report_ids_continue_across_executions() -> None:
    value = coordinator()

    value.register_request(
        execution_request()
    )

    value.register_request(
        execution_request(
            execution_id="execution-002",
            correlation_id="correlation-002",
            order_id="order-002",
            client_order_id="client-order-002",
            symbol="AAPL",
        )
    )

    first = value.start_execution(
        "execution-001"
    )
    second = value.start_execution(
        "execution-002"
    )

    assert first.report_id == (
        "execution-report-000001"
    )
    assert second.report_id == (
        "execution-report-000002"
    )


def test_report_contains_correlation_metadata() -> None:
    value = started_coordinator()

    report = value.get_report(
        "execution-001"
    )

    assert report.metadata == (
        ("correlation_id", "correlation-001"),
        ("order_id", "order-001"),
    )


def test_execution_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="execution_id must not be empty",
    ):
        coordinator().get_request("   ")


def test_execution_identifier_must_be_string() -> None:
    with pytest.raises(
        TypeError,
        match="execution_id must be a string",
    ):
        coordinator().get_request(123)


def test_correlation_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="correlation_id must not be empty",
    ):
        coordinator().request_for_correlation(
            "   "
        )


def test_order_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="order_id must not be empty",
    ):
        coordinator().reports_for_order("   ")


def test_portfolio_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="portfolio_id must not be empty",
    ):
        coordinator().reports_for_portfolio(
            "   "
        )


def test_clock_must_return_datetime() -> None:
    value = EnterpriseExecutionCoordinator(
        clock=lambda: "now"
    )
    value.register_request(
        execution_request()
    )

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        value.start_execution(
            "execution-001"
        )


def test_clock_must_return_timezone_aware_datetime() -> None:
    value = EnterpriseExecutionCoordinator(
        clock=lambda: datetime(
            2026,
            8,
            5,
            15,
            0,
        )
    )
    value.register_request(
        execution_request()
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        value.start_execution(
            "execution-001"
        )
def test_record_session_step() -> None:
    value = started_coordinator()

    report = value.record_step(
        "execution-001",
        stage=ExecutionStage.SESSION,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Trading session validated.",
        reference_id="session-001",
    )

    assert report.result.status is (
        ExecutionStatus.EXECUTING
    )
    assert len(report.result.steps) == 1

    step = report.result.steps[0]

    assert step.step_id == (
        "execution-step-000001"
    )
    assert step.stage is ExecutionStage.SESSION
    assert step.successful is True
    assert step.reference_id == "session-001"


def test_record_multiple_ordered_steps() -> None:
    value = started_coordinator()

    value.record_step(
        "execution-001",
        stage=ExecutionStage.SESSION,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Session approved.",
    )

    value.record_step(
        "execution-001",
        stage=ExecutionStage.ORDER,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Order prepared.",
    )

    value.record_step(
        "execution-001",
        stage=ExecutionStage.RISK,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Risk approved.",
    )

    result = value.get_result(
        "execution-001"
    )

    assert tuple(
        step.stage
        for step in result.steps
    ) == (
        ExecutionStage.SESSION,
        ExecutionStage.ORDER,
        ExecutionStage.RISK,
    )


def test_record_step_requires_stage_enum() -> None:
    value = started_coordinator()

    with pytest.raises(
        TypeError,
        match="stage must be an ExecutionStage",
    ):
        value.record_step(
            "execution-001",
            stage="SESSION",
            decision=ExecutionDecision.PROCEED,
            successful=True,
            message="Invalid stage.",
        )


def test_record_step_requires_decision_enum() -> None:
    value = started_coordinator()

    with pytest.raises(
        TypeError,
        match=(
            "decision must be an ExecutionDecision"
        ),
    ):
        value.record_step(
            "execution-001",
            stage=ExecutionStage.SESSION,
            decision="PROCEED",
            successful=True,
            message="Invalid decision.",
        )


def test_record_step_requires_success_bool() -> None:
    value = started_coordinator()

    with pytest.raises(
        TypeError,
        match="successful must be a bool",
    ):
        value.record_step(
            "execution-001",
            stage=ExecutionStage.SESSION,
            decision=ExecutionDecision.PROCEED,
            successful="yes",
            message="Invalid success flag.",
        )


def test_duplicate_stage_is_rejected() -> None:
    value = started_coordinator()

    value.record_step(
        "execution-001",
        stage=ExecutionStage.SESSION,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Session approved.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "execution stage is already recorded"
        ),
    ):
        value.record_step(
            "execution-001",
            stage=ExecutionStage.SESSION,
            decision=ExecutionDecision.PROCEED,
            successful=True,
            message="Duplicate session stage.",
        )


def test_stages_must_be_recorded_in_order() -> None:
    value = started_coordinator()

    value.record_step(
        "execution-001",
        stage=ExecutionStage.RISK,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Risk approved.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "execution stages must be recorded "
            "in pipeline order"
        ),
    ):
        value.record_step(
            "execution-001",
            stage=ExecutionStage.ORDER,
            decision=ExecutionDecision.PROCEED,
            successful=True,
            message="Order prepared too late.",
        )


def test_steps_may_skip_optional_stages() -> None:
    value = started_coordinator()

    value.record_step(
        "execution-001",
        stage=ExecutionStage.SESSION,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Session approved.",
    )

    value.record_step(
        "execution-001",
        stage=ExecutionStage.RISK,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Risk approved.",
    )

    result = value.get_result(
        "execution-001"
    )

    assert tuple(
        step.stage
        for step in result.steps
    ) == (
        ExecutionStage.SESSION,
        ExecutionStage.RISK,
    )


def test_step_ids_are_deterministic() -> None:
    value = started_coordinator()

    first = value.record_step(
        "execution-001",
        stage=ExecutionStage.SESSION,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Session approved.",
    )

    second = value.record_step(
        "execution-001",
        stage=ExecutionStage.ORDER,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Order prepared.",
    )

    assert first.result.steps[-1].step_id == (
        "execution-step-000001"
    )
    assert second.result.steps[-1].step_id == (
        "execution-step-000002"
    )


def test_step_ids_continue_across_executions() -> None:
    value = coordinator()

    value.register_request(
        execution_request()
    )
    value.register_request(
        execution_request(
            execution_id="execution-002",
            correlation_id="correlation-002",
            order_id="order-002",
            client_order_id="client-order-002",
            symbol="AAPL",
        )
    )

    value.start_execution("execution-001")
    value.start_execution("execution-002")

    first = value.record_step(
        "execution-001",
        stage=ExecutionStage.SESSION,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="First session approved.",
    )

    second = value.record_step(
        "execution-002",
        stage=ExecutionStage.SESSION,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Second session approved.",
    )

    assert first.result.steps[-1].step_id == (
        "execution-step-000001"
    )
    assert second.result.steps[-1].step_id == (
        "execution-step-000002"
    )


def test_step_warnings_are_accumulated() -> None:
    value = started_coordinator()

    value.record_step(
        "execution-001",
        stage=ExecutionStage.SESSION,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Session approved.",
        warnings=("Session warning.",),
    )

    report = value.record_step(
        "execution-001",
        stage=ExecutionStage.ORDER,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Order prepared.",
        warnings=("Order warning.",),
    )

    assert report.result.warnings == (
        "Session warning.",
        "Order warning.",
    )
    assert report.warnings == (
        "Session warning.",
        "Order warning.",
    )


def test_duplicate_warnings_are_removed() -> None:
    value = started_coordinator()

    value.record_step(
        "execution-001",
        stage=ExecutionStage.SESSION,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Session approved.",
        warnings=("Shared warning.",),
    )

    report = value.record_step(
        "execution-001",
        stage=ExecutionStage.ORDER,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Order prepared.",
        warnings=("Shared warning.",),
    )

    assert report.result.warnings == (
        "Shared warning.",
    )


def test_result_history_records_each_transition() -> None:
    value = started_coordinator()

    value.record_step(
        "execution-001",
        stage=ExecutionStage.SESSION,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Session approved.",
    )

    value.record_step(
        "execution-001",
        stage=ExecutionStage.ORDER,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Order prepared.",
    )

    history = value.results_for_execution(
        "execution-001"
    )

    assert len(history) == 3
    assert tuple(
        len(result.steps)
        for result in history
    ) == (0, 1, 2)


def test_report_history_records_each_transition() -> None:
    value = started_coordinator()

    value.record_step(
        "execution-001",
        stage=ExecutionStage.SESSION,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Session approved.",
    )

    value.record_step(
        "execution-001",
        stage=ExecutionStage.ORDER,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Order prepared.",
    )

    assert len(value.report_history) == 3
    assert tuple(
        report.report_id
        for report in value.report_history
    ) == (
        "execution-report-000001",
        "execution-report-000002",
        "execution-report-000003",
    )


def broker_ready_coordinator(
) -> EnterpriseExecutionCoordinator:
    value = started_coordinator()

    value.record_step(
        "execution-001",
        stage=ExecutionStage.SESSION,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Session approved.",
        reference_id="session-001",
    )

    value.record_step(
        "execution-001",
        stage=ExecutionStage.ORDER,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Order prepared.",
        reference_id="order-001",
    )

    value.record_step(
        "execution-001",
        stage=ExecutionStage.RISK,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Risk approved.",
        reference_id="risk-order-001",
    )

    value.record_step(
        "execution-001",
        stage=ExecutionStage.BROKER,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Broker acknowledged the order.",
        reference_id="broker-order-001",
    )

    return value


def test_complete_execution() -> None:
    value = broker_ready_coordinator()

    report = value.complete_execution(
        "execution-001",
        final_order_id="order-001",
        broker_order_id="broker-order-001",
    )

    assert report.result.status is (
        ExecutionStatus.COMPLETED
    )
    assert report.result.decision is (
        ExecutionDecision.PROCEED
    )
    assert report.result.final_order_id == (
        "order-001"
    )
    assert report.result.broker_order_id == (
        "broker-order-001"
    )
    assert report.result.is_terminal is True


def test_completion_identifiers_are_normalized() -> None:
    value = broker_ready_coordinator()

    report = value.complete_execution(
        "execution-001",
        final_order_id="  order-001  ",
        broker_order_id="  broker-order-001  ",
    )

    assert report.result.final_order_id == (
        "order-001"
    )
    assert report.result.broker_order_id == (
        "broker-order-001"
    )


def test_completion_requires_matching_order_id() -> None:
    value = broker_ready_coordinator()

    with pytest.raises(
        ValueError,
        match=(
            "final_order_id must match "
            "the execution order_id"
        ),
    ):
        value.complete_execution(
            "execution-001",
            final_order_id="different-order",
            broker_order_id="broker-order-001",
        )


def test_completion_requires_steps() -> None:
    value = started_coordinator()

    with pytest.raises(
        RuntimeError,
        match=(
            "execution cannot complete without steps"
        ),
    ):
        value.complete_execution(
            "execution-001",
            final_order_id="order-001",
            broker_order_id="broker-order-001",
        )


def test_completion_requires_broker_stage() -> None:
    value = started_coordinator()

    value.record_step(
        "execution-001",
        stage=ExecutionStage.SESSION,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Session approved.",
    )

    value.record_step(
        "execution-001",
        stage=ExecutionStage.RISK,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Risk approved.",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "execution must reach the broker or "
            "execution stage before completion"
        ),
    ):
        value.complete_execution(
            "execution-001",
            final_order_id="order-001",
            broker_order_id="broker-order-001",
        )


def test_hold_execution() -> None:
    value = started_coordinator()

    report = value.hold_execution(
        "execution-001",
        stage=ExecutionStage.SESSION,
        reason="Trading session is temporarily unavailable.",
        reference_id="session-001",
    )

    assert report.result.status is (
        ExecutionStatus.HELD
    )
    assert report.result.decision is (
        ExecutionDecision.HOLD
    )
    assert report.result.is_terminal is True
    assert report.result.failed_step is not None
    assert (
        report.result.failed_step.stage
        is ExecutionStage.SESSION
    )


def test_reject_execution() -> None:
    value = started_coordinator()

    report = value.reject_execution(
        "execution-001",
        stage=ExecutionStage.RISK,
        reason="Risk gateway rejected the order.",
        reference_id="risk-order-001",
    )

    assert report.result.status is (
        ExecutionStatus.REJECTED
    )
    assert report.result.decision is (
        ExecutionDecision.REJECT
    )
    assert report.result.is_terminal is True


def test_cancel_execution() -> None:
    value = started_coordinator()

    report = value.cancel_execution(
        "execution-001",
        stage=ExecutionStage.ORDER,
        reason="Execution was cancelled by the operator.",
        reference_id="order-001",
    )

    assert report.result.status is (
        ExecutionStatus.CANCELLED
    )
    assert report.result.decision is (
        ExecutionDecision.CANCEL
    )
    assert report.result.is_terminal is True


def test_fail_execution() -> None:
    value = started_coordinator()

    report = value.fail_execution(
        "execution-001",
        stage=ExecutionStage.BROKER,
        error="Broker connection failed.",
        reference_id="account-001",
    )

    assert report.result.status is (
        ExecutionStatus.FAILED
    )
    assert report.result.decision is (
        ExecutionDecision.NO_ACTION
    )
    assert report.result.error == (
        "Broker connection failed."
    )
    assert report.result.is_terminal is True


@pytest.mark.parametrize(
    ("method_name", "keyword_name"),
    [
        ("hold_execution", "reason"),
        ("reject_execution", "reason"),
        ("cancel_execution", "reason"),
        ("fail_execution", "error"),
    ],
)
def test_terminal_reason_must_not_be_empty(
    method_name: str,
    keyword_name: str,
) -> None:
    value = started_coordinator()
    method = getattr(value, method_name)

    arguments = {
        "execution_id": "execution-001",
        "stage": ExecutionStage.RISK,
        keyword_name: "   ",
    }

    with pytest.raises(
        ValueError,
        match=(
            f"{keyword_name} must not be empty"
        ),
    ):
        method(**arguments)


def test_terminal_stage_must_be_enum() -> None:
    value = started_coordinator()

    with pytest.raises(
        TypeError,
        match="stage must be an ExecutionStage",
    ):
        value.reject_execution(
            "execution-001",
            stage="RISK",
            reason="Invalid stage.",
        )


def test_terminal_transition_respects_stage_order() -> None:
    value = started_coordinator()

    value.record_step(
        "execution-001",
        stage=ExecutionStage.RISK,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Risk approved.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "execution stages must be recorded "
            "in pipeline order"
        ),
    ):
        value.reject_execution(
            "execution-001",
            stage=ExecutionStage.ORDER,
            reason="Late order rejection.",
        )


def test_terminal_transition_rejects_duplicate_stage() -> None:
    value = started_coordinator()

    value.record_step(
        "execution-001",
        stage=ExecutionStage.RISK,
        decision=ExecutionDecision.PROCEED,
        successful=True,
        message="Risk approved.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "execution stage is already recorded"
        ),
    ):
        value.reject_execution(
            "execution-001",
            stage=ExecutionStage.RISK,
            reason="Duplicate risk stage.",
        )


@pytest.mark.parametrize(
    "terminal_action",
    [
        "hold_execution",
        "reject_execution",
        "cancel_execution",
        "fail_execution",
    ],
)
def test_terminal_execution_cannot_be_modified(
    terminal_action: str,
) -> None:
    value = started_coordinator()

    if terminal_action == "fail_execution":
        value.fail_execution(
            "execution-001",
            stage=ExecutionStage.RISK,
            error="Risk service failed.",
        )
    else:
        method = getattr(
            value,
            terminal_action,
        )
        method(
            "execution-001",
            stage=ExecutionStage.RISK,
            reason="Terminal transition.",
        )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal executions cannot be modified"
        ),
    ):
        value.record_step(
            "execution-001",
            stage=ExecutionStage.BROKER,
            decision=ExecutionDecision.PROCEED,
            successful=True,
            message="Invalid terminal update.",
        )


def test_completed_execution_cannot_be_modified() -> None:
    value = broker_ready_coordinator()

    value.complete_execution(
        "execution-001",
        final_order_id="order-001",
        broker_order_id="broker-order-001",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal executions cannot be modified"
        ),
    ):
        value.record_step(
            "execution-001",
            stage=ExecutionStage.EXECUTION,
            decision=ExecutionDecision.PROCEED,
            successful=True,
            message="Invalid post-completion step.",
        )


def test_latest_report_tracks_terminal_result() -> None:
    value = started_coordinator()

    expected = value.reject_execution(
        "execution-001",
        stage=ExecutionStage.RISK,
        reason="Risk rejected the order.",
    )

    assert value.latest_report() == expected
    assert value.get_report(
        "execution-001"
    ) == expected


def test_reports_for_order_include_full_history() -> None:
    value = broker_ready_coordinator()

    value.complete_execution(
        "execution-001",
        final_order_id="order-001",
        broker_order_id="broker-order-001",
    )

    reports = value.reports_for_order(
        "order-001"
    )

    assert len(reports) == 6
    assert reports[-1].result.status is (
        ExecutionStatus.COMPLETED
    )


def test_completion_report_ids_are_deterministic() -> None:
    value = broker_ready_coordinator()

    report = value.complete_execution(
        "execution-001",
        final_order_id="order-001",
        broker_order_id="broker-order-001",
    )

    assert report.report_id == (
        "execution-report-000006"
    )    