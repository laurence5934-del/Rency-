from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.strategy.agent_coordinator import (
    AgentCoordinatorStatus,
    AgentOpinion,
    AgentRecommendation,
    AgentRole,
    AgentVoteSummary,
    CoordinatedAction,
    CoordinationReport,
)
from app.strategy.execution import (
    ExecutionGateway,
    SimulatorBrokerAdapter,
    UnavailableBrokerAdapter,
)
from app.strategy.live_trading.live_trading_models import (
    ExecutionPlanStatus,
    LiveOrderType,
    LiveTradeDecision,
    LiveTradeRequest,
    LiveTradeSide,
    LiveTradingStatus,
    TradingEnvironment,
    TradingSession,
    TradingSessionStatus,
)
from app.strategy.live_trading.live_trading_orchestrator import (
    LiveTradingOrchestrator,
)
from app.strategy.portfolio_risk import (
    PortfolioRiskDecision,
    PortfolioRiskLimit,
    PortfolioRiskMetrics,
    PortfolioRiskReport,
    PortfolioRiskStatus,
    RiskLimitBreach,
    RiskLimitSeverity,
    RiskLimitType,
)


NOW = datetime(
    2026,
    8,
    2,
    19,
    0,
    tzinfo=timezone.utc,
)


def session(
    *,
    environment: TradingEnvironment = (
        TradingEnvironment.PAPER
    ),
    status: TradingSessionStatus = (
        TradingSessionStatus.ACTIVE
    ),
    max_order_value: str = "25000",
) -> TradingSession:
    return TradingSession(
        session_id="session-001",
        environment=environment,
        status=status,
        started_at=NOW,
        account_id="account-001",
        max_order_value=Decimal(
            max_order_value
        ),
        max_session_loss=Decimal("5000"),
        live_trading_confirmed=(
            environment is TradingEnvironment.LIVE
        ),
    )


def request(
    *,
    quantity: str = "10",
    estimated_price: str | None = "200",
    session_id: str = "session-001",
) -> LiveTradeRequest:
    return LiveTradeRequest(
        request_id="trade-001",
        session_id=session_id,
        symbol="AAPL",
        side=LiveTradeSide.BUY,
        quantity=Decimal(quantity),
        order_type=LiveOrderType.MARKET,
        submitted_at=NOW,
        strategy_id="trend-001",
        estimated_price=(
            Decimal(estimated_price)
            if estimated_price is not None
            else None
        ),
    )


def opinion(role: AgentRole) -> AgentOpinion:
    return AgentOpinion(
        agent_id=f"{role.value.lower()}-agent",
        role=role,
        recommendation=AgentRecommendation.APPROVE,
        confidence=Decimal("0.90"),
        weight=Decimal("0.20"),
        reason="Agent approved execution.",
    )


def coordination_report(
    *,
    status: AgentCoordinatorStatus = (
        AgentCoordinatorStatus.COMPLETED
    ),
    action: CoordinatedAction = (
        CoordinatedAction.EXECUTE
    ),
    warnings=(),
    error: str | None = None,
) -> CoordinationReport:
    return CoordinationReport(
        status=status,
        action=action,
        confidence=Decimal("0.90"),
        opinions=tuple(
            opinion(role)
            for role in AgentRole
        ),
        vote_summary=AgentVoteSummary(
            approval_score=Decimal("1"),
            review_score=Decimal("0"),
            rejection_score=Decimal("0"),
            participating_agents=5,
        ),
        rationale="Agent coordination completed.",
        warnings=tuple(warnings),
        error=error,
    )


def risk_metrics() -> PortfolioRiskMetrics:
    return PortfolioRiskMetrics(
        portfolio_value=Decimal("100000"),
        cash_value=Decimal("20000"),
        gross_exposure=Decimal("0.80"),
        net_exposure=Decimal("0.70"),
        leverage_ratio=Decimal("1"),
        concentration_score=Decimal("0.25"),
        diversification_score=Decimal("0.75"),
        volatility=Decimal("0.15"),
        maximum_drawdown=Decimal("0.10"),
        value_at_risk=Decimal("0.03"),
        expected_shortfall=Decimal("0.05"),
        risk_budget_used=Decimal("0.40"),
        liquidity_score=Decimal("0.90"),
    )


def risk_report(
    *,
    status: PortfolioRiskStatus = (
        PortfolioRiskStatus.COMPLETED
    ),
    decision: PortfolioRiskDecision = (
        PortfolioRiskDecision.APPROVE
    ),
    warnings=(),
    error: str | None = None,
) -> PortfolioRiskReport:
    return PortfolioRiskReport(
        status=status,
        decision=decision,
        metrics=risk_metrics(),
        recommendation="Portfolio risk reviewed.",
        warnings=tuple(warnings),
        error=error,
    )


def gateway(
    *,
    price: str = "200",
) -> ExecutionGateway:
    return ExecutionGateway(
        adapter=SimulatorBrokerAdapter(
            price_provider=lambda symbol: Decimal(
                price
            ),
            clock=lambda: NOW,
        )
    )


def orchestrator(
    execution_gateway: ExecutionGateway | None = None,
) -> LiveTradingOrchestrator:
    return LiveTradingOrchestrator(
        execution_gateway=(
            execution_gateway or gateway()
        ),
        clock=lambda: NOW,
    )


def test_approved_trade_executes() -> None:
    report = orchestrator().orchestrate(
        session=session(),
        request=request(),
        coordination_report=coordination_report(),
        risk_report=risk_report(),
    )

    assert report.status is LiveTradingStatus.COMPLETED
    assert report.plan.decision is LiveTradeDecision.EXECUTE
    assert report.plan.status is ExecutionPlanStatus.READY
    assert report.result.submitted is True
    assert report.result.order_id == "SIM-000001"
    assert report.audit_id == "audit-trade-001"


def test_execution_result_contains_fill() -> None:
    report = orchestrator().orchestrate(
        session=session(),
        request=request(),
        coordination_report=coordination_report(),
        risk_report=risk_report(),
    )

    assert report.result.filled_quantity == Decimal("10")
    assert report.result.average_price == Decimal("200")
    assert report.result.broker_name == "SIMULATOR"


def test_live_session_marks_manual_confirmation() -> None:
    report = orchestrator().orchestrate(
        session=session(
            environment=TradingEnvironment.LIVE
        ),
        request=request(),
        coordination_report=coordination_report(),
        risk_report=risk_report(),
    )

    assert (
        report.plan.requires_manual_confirmation
        is True
    )
    assert report.result.submitted is True


def test_inactive_session_rejects_trade() -> None:
    report = orchestrator().orchestrate(
        session=session(
            status=TradingSessionStatus.HALTED
        ),
        request=request(),
        coordination_report=coordination_report(),
        risk_report=risk_report(),
    )

    assert report.plan.decision is LiveTradeDecision.REJECT
    assert report.result.submitted is False
    assert "not active" in report.plan.reason


def test_session_mismatch_is_rejected_before_orchestration() -> None:
    with pytest.raises(
        ValueError,
        match="request session_id must match the session",
    ):
        orchestrator().orchestrate(
            session=session(),
            request=request(
                session_id="different-session"
            ),
            coordination_report=coordination_report(),
            risk_report=risk_report(),
        )

        assert report.plan.decision is LiveTradeDecision.REJECT
        assert report.result.submitted is False


def test_failed_coordination_rejects_trade() -> None:
    report = orchestrator().orchestrate(
        session=session(),
        request=request(),
        coordination_report=coordination_report(
            status=AgentCoordinatorStatus.FAILED,
            action=CoordinatedAction.BLOCK,
            error="coordination failed",
        ),
        risk_report=risk_report(),
    )

    assert report.plan.decision is LiveTradeDecision.REJECT
    assert "coordination failed" in (
        report.plan.reason.lower()
    )


def test_blocked_coordination_rejects_trade() -> None:
    report = orchestrator().orchestrate(
        session=session(),
        request=request(),
        coordination_report=coordination_report(
            action=CoordinatedAction.BLOCK
        ),
        risk_report=risk_report(),
    )

    assert report.plan.decision is LiveTradeDecision.REJECT


def test_failed_risk_report_rejects_trade() -> None:
    report = orchestrator().orchestrate(
        session=session(),
        request=request(),
        coordination_report=coordination_report(),
        risk_report=risk_report(
            status=PortfolioRiskStatus.FAILED,
            decision=(
                PortfolioRiskDecision.REVIEW_REQUIRED
            ),
            error="risk assessment failed",
        ),
    )

    assert report.plan.decision is LiveTradeDecision.REJECT


def test_rejected_risk_report_rejects_trade() -> None:
    report = orchestrator().orchestrate(
        session=session(),
        request=request(),
        coordination_report=coordination_report(),
        risk_report=rejected_risk_report(),
    )

    assert report.plan.decision is LiveTradeDecision.REJECT
    assert report.result.submitted is False


@pytest.mark.parametrize(
    ("coordination_action", "risk_decision"),
    [
        (
            CoordinatedAction.REVIEW_REQUIRED,
            PortfolioRiskDecision.APPROVE,
        ),
        (
            CoordinatedAction.EXECUTE,
            PortfolioRiskDecision.REVIEW_REQUIRED,
        ),
    ],
)
def test_review_gate_requires_manual_review(
    coordination_action,
    risk_decision,
) -> None:
    report = orchestrator().orchestrate(
        session=session(),
        request=request(),
        coordination_report=coordination_report(
            action=coordination_action
        ),
        risk_report=risk_report(
            decision=risk_decision
        ),
    )

    assert (
        report.plan.decision
        is LiveTradeDecision.REVIEW_REQUIRED
    )
    assert report.result.submitted is False


def test_missing_estimated_price_requires_review() -> None:
    report = orchestrator().orchestrate(
        session=session(),
        request=request(
            estimated_price=None
        ),
        coordination_report=coordination_report(),
        risk_report=risk_report(),
    )

    assert (
        report.plan.decision
        is LiveTradeDecision.REVIEW_REQUIRED
    )


def test_order_above_session_limit_is_rejected() -> None:
    report = orchestrator().orchestrate(
        session=session(
            max_order_value="1000"
        ),
        request=request(
            quantity="10",
            estimated_price="200",
        ),
        coordination_report=coordination_report(),
        risk_report=risk_report(),
    )

    assert report.plan.decision is LiveTradeDecision.REJECT
    assert "exceeds" in report.plan.reason


def test_order_equal_to_session_limit_executes() -> None:
    report = orchestrator().orchestrate(
        session=session(
            max_order_value="2000"
        ),
        request=request(
            quantity="10",
            estimated_price="200",
        ),
        coordination_report=coordination_report(),
        risk_report=risk_report(),
    )

    assert report.plan.decision is LiveTradeDecision.EXECUTE
    assert report.result.submitted is True


def test_gateway_failure_returns_failed_report() -> None:
    failed_gateway = ExecutionGateway(
        adapter=UnavailableBrokerAdapter(
            broker_name="TEST_BROKER"
        )
    )

    report = orchestrator(
        failed_gateway
    ).orchestrate(
        session=session(),
        request=request(),
        coordination_report=coordination_report(),
        risk_report=risk_report(),
    )

    assert report.status is LiveTradingStatus.FAILED
    assert report.plan.decision is LiveTradeDecision.EXECUTE
    assert report.result.submitted is False
    assert "not configured" in report.error


def test_partial_fill_warning_is_preserved() -> None:
    from app.strategy.execution import (
        ExecutionReceipt,
    )

    class PartialAdapter:
        name = "PARTIAL"

        def execute(self, value):
            return ExecutionReceipt(
                execution_id=value.execution_id,
                broker_name=self.name,
                order_id="PARTIAL-001",
                filled_quantity=Decimal("5"),
                average_price=Decimal("200"),
                commission=Decimal("0"),
                executed_at=NOW,
            )

    report = orchestrator(
        ExecutionGateway(
            adapter=PartialAdapter()
        )
    ).orchestrate(
        session=session(),
        request=request(),
        coordination_report=coordination_report(),
        risk_report=risk_report(),
    )

    assert report.result.submitted is True
    assert (
        "The execution was partially filled."
        in report.warnings
    )


def test_coordination_and_risk_warnings_are_aggregated() -> None:
    report = orchestrator().orchestrate(
        session=session(),
        request=request(),
        coordination_report=coordination_report(
            warnings=("Coordinator warning.",)
        ),
        risk_report=risk_report(
            warnings=("Risk warning.",)
        ),
    )

    assert report.warnings == (
        "Coordinator warning.",
        "Risk warning.",
    )


@pytest.mark.parametrize(
    (
        "argument_name",
        "invalid_value",
        "message",
    ),
    [
        (
            "session",
            object(),
            "session must be a TradingSession",
        ),
        (
            "request",
            object(),
            "request must be a LiveTradeRequest",
        ),
        (
            "coordination_report",
            object(),
            "coordination_report must be a "
            "CoordinationReport",
        ),
        (
            "risk_report",
            object(),
            "risk_report must be a PortfolioRiskReport",
        ),
    ],
)
def test_inputs_are_validated(
    argument_name,
    invalid_value,
    message,
) -> None:
    values = {
        "session": session(),
        "request": request(),
        "coordination_report": (
            coordination_report()
        ),
        "risk_report": risk_report(),
    }
    values[argument_name] = invalid_value

    with pytest.raises(
        TypeError,
        match=message,
    ):
        orchestrator().orchestrate(**values)


def test_gateway_type_is_validated() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "execution_gateway must be an "
            "ExecutionGateway"
        ),
    ):
        LiveTradingOrchestrator(
            execution_gateway=object()
        )


def test_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        LiveTradingOrchestrator(
            execution_gateway=gateway(),
            clock=NOW,
        )


def test_clock_must_return_datetime() -> None:
    engine = LiveTradingOrchestrator(
        execution_gateway=gateway(),
        clock=lambda: "now",
    )

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        engine.orchestrate(
            session=session(),
            request=request(),
            coordination_report=coordination_report(),
            risk_report=risk_report(),
        )


def test_clock_must_return_timezone_aware_datetime() -> None:
    engine = LiveTradingOrchestrator(
        execution_gateway=gateway(),
        clock=lambda: datetime(2026, 8, 2),
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        engine.orchestrate(
            session=session(),
            request=request(),
            coordination_report=coordination_report(),
            risk_report=risk_report(),
        )
def rejected_risk_report() -> PortfolioRiskReport:
    critical_limit = PortfolioRiskLimit(
        limit_id="leverage-limit",
        name="Maximum leverage",
        limit_type=RiskLimitType.LEVERAGE,
        threshold=Decimal("1.50"),
        severity=RiskLimitSeverity.CRITICAL,
    )

    critical_breach = RiskLimitBreach(
        limit=critical_limit,
        observed_value=Decimal("2.00"),
        exceeded_by=Decimal("0.50"),
        message="Maximum leverage was breached.",
    )

    return PortfolioRiskReport(
        status=PortfolioRiskStatus.COMPLETED,
        decision=PortfolioRiskDecision.REJECT,
        metrics=risk_metrics(),
        limits=(critical_limit,),
        breaches=(critical_breach,),
        recommendation=(
            "Reject new exposure until the critical "
            "breach is resolved."
        ),
    )