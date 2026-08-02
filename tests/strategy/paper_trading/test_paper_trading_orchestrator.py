from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.strategy.decision import (
    Decision,
    DecisionAction,
)
from app.strategy.paper_trading.orchestrator_models import (
    OrchestratorStatus,
    PaperTradeRequest,
    PaperTradeSide,
    TradeApproval,
)
from app.strategy.paper_trading.paper_trading_orchestrator import (
    PaperBrokerReceipt,
    PaperTradingOrchestrator,
)
from app.strategy.regime import (
    MarketRegime,
    MarketRegimeReport,
    MarketRegimeSignal,
    RegimeConfidence,
    RegimeDetectionStatus,
)
from app.strategy.risk_dashboard import (
    DeploymentReadiness,
    InstitutionalRiskDashboard,
    PortfolioHealth,
)


NOW = datetime(
    2026,
    8,
    2,
    17,
    0,
    tzinfo=timezone.utc,
)


class RecordingBroker:
    def __init__(self) -> None:
        self.requests: list[
            PaperTradeRequest
        ] = []

    def submit(
        self,
        request: PaperTradeRequest,
    ) -> PaperBrokerReceipt:
        self.requests.append(request)

        return PaperBrokerReceipt(
            order_id="PAPER-ORDER-001",
            execution_price=Decimal("199.50"),
            executed_quantity=request.quantity,
        )


class FailingBroker:
    def submit(
        self,
        request: PaperTradeRequest,
    ) -> PaperBrokerReceipt:
        del request
        raise RuntimeError(
            "paper broker unavailable"
        )


def request() -> PaperTradeRequest:
    return PaperTradeRequest(
        request_id="paper-001",
        symbol="AAPL",
        side=PaperTradeSide.BUY,
        quantity=Decimal("10"),
        strategy_id="trend-001",
        submitted_at=NOW,
    )


def decision(
    action: DecisionAction = (
        DecisionAction.PAPER_TRADE
    ),
) -> Decision:
    return Decision(
        action=action,
        confidence=Decimal("0.90"),
        reason="Strategy passed evaluation.",
    )


def dashboard(
    readiness: DeploymentReadiness = (
        DeploymentReadiness.PAPER_READY
    ),
    *,
    warnings=(),
) -> InstitutionalRiskDashboard:
    return InstitutionalRiskDashboard(
        overall_risk_score=Decimal("0.20"),
        confidence_score=Decimal("0.90"),
        capital_preservation_score=Decimal("0.85"),
        health=PortfolioHealth.HEALTHY,
        readiness=readiness,
        recommendation="Proceed carefully.",
        warnings=tuple(warnings),
    )


def regime_report(
    regime: MarketRegime = MarketRegime.BULL,
    *,
    status: RegimeDetectionStatus = (
        RegimeDetectionStatus.COMPLETED
    ),
    warnings=(),
    error=None,
) -> MarketRegimeReport:
    return MarketRegimeReport(
        status=status,
        regime=regime,
        confidence=RegimeConfidence.HIGH,
        overall_score=Decimal("0.75"),
        signal=MarketRegimeSignal(
            signal_id="market-001",
            trend_score=Decimal("0.75"),
            volatility_score=Decimal("0.30"),
            breadth_score=Decimal("0.70"),
            momentum_score=Decimal("0.72"),
            liquidity_score=Decimal("0.80"),
        ),
        recommendation="Maintain constructive exposure.",
        warnings=tuple(warnings),
        error=error,
    )


def orchestrator(
    broker=None,
) -> PaperTradingOrchestrator:
    return PaperTradingOrchestrator(
        broker=broker or RecordingBroker(),
        clock=lambda: NOW,
    )


def test_approved_trade_reaches_broker() -> None:
    broker = RecordingBroker()

    report = orchestrator(broker).execute(
        request=request(),
        decision=decision(),
        risk_dashboard=dashboard(),
        regime_report=regime_report(),
    )

    assert report.status is OrchestratorStatus.COMPLETED
    assert report.approval is TradeApproval.APPROVED
    assert report.result.submitted is True
    assert report.result.order_id == "PAPER-ORDER-001"
    assert len(broker.requests) == 1


def test_live_trade_decision_is_accepted_for_paper_execution() -> None:
    report = orchestrator().execute(
        request=request(),
        decision=decision(
            DecisionAction.LIVE_TRADE
        ),
        risk_dashboard=dashboard(),
        regime_report=regime_report(),
    )

    assert report.approval is TradeApproval.APPROVED
    assert report.result.submitted is True


def test_rejected_decision_never_reaches_broker() -> None:
    broker = RecordingBroker()

    report = orchestrator(broker).execute(
        request=request(),
        decision=decision(
            DecisionAction.REJECT
        ),
        risk_dashboard=dashboard(),
        regime_report=regime_report(),
    )

    assert report.approval is TradeApproval.REJECTED
    assert report.result.submitted is False
    assert broker.requests == []


def test_improve_decision_requires_review() -> None:
    broker = RecordingBroker()

    report = orchestrator(broker).execute(
        request=request(),
        decision=decision(
            DecisionAction.IMPROVE
        ),
        risk_dashboard=dashboard(),
        regime_report=regime_report(),
    )

    assert (
        report.approval
        is TradeApproval.REVIEW_REQUIRED
    )
    assert report.result.submitted is False
    assert broker.requests == []


def test_blocked_risk_dashboard_rejects_trade() -> None:
    broker = RecordingBroker()

    report = orchestrator(broker).execute(
        request=request(),
        decision=decision(),
        risk_dashboard=dashboard(
            DeploymentReadiness.BLOCKED
        ),
        regime_report=regime_report(),
    )

    assert report.approval is TradeApproval.REJECTED
    assert report.result.submitted is False
    assert broker.requests == []


def test_review_risk_dashboard_requires_review() -> None:
    report = orchestrator().execute(
        request=request(),
        decision=decision(),
        risk_dashboard=dashboard(
            DeploymentReadiness.REVIEW_REQUIRED
        ),
        regime_report=regime_report(),
    )

    assert (
        report.approval
        is TradeApproval.REVIEW_REQUIRED
    )


@pytest.mark.parametrize(
    "regime",
    [
        MarketRegime.RISK_OFF,
        MarketRegime.STRONG_BEAR,
    ],
)
def test_dangerous_regime_rejects_trade(
    regime: MarketRegime,
) -> None:
    report = orchestrator().execute(
        request=request(),
        decision=decision(),
        risk_dashboard=dashboard(),
        regime_report=regime_report(regime),
    )

    assert report.approval is TradeApproval.REJECTED
    assert report.result.submitted is False


@pytest.mark.parametrize(
    "regime",
    [
        MarketRegime.UNKNOWN,
        MarketRegime.CORRECTION,
        MarketRegime.HIGH_VOLATILITY,
    ],
)
def test_uncertain_regime_requires_review(
    regime: MarketRegime,
) -> None:
    report = orchestrator().execute(
        request=request(),
        decision=decision(),
        risk_dashboard=dashboard(),
        regime_report=regime_report(regime),
    )

    assert (
        report.approval
        is TradeApproval.REVIEW_REQUIRED
    )
    assert report.result.submitted is False


def test_failed_regime_report_rejects_trade() -> None:
    report = orchestrator().execute(
        request=request(),
        decision=decision(),
        risk_dashboard=dashboard(),
        regime_report=regime_report(
            MarketRegime.UNKNOWN,
            status=RegimeDetectionStatus.FAILED,
            error="regime detection failed",
        ),
    )

    assert report.approval is TradeApproval.REJECTED


def test_rejection_has_precedence_over_review() -> None:
    report = orchestrator().execute(
        request=request(),
        decision=decision(
            DecisionAction.IMPROVE
        ),
        risk_dashboard=dashboard(
            DeploymentReadiness.BLOCKED
        ),
        regime_report=regime_report(
            MarketRegime.CORRECTION
        ),
    )

    assert report.approval is TradeApproval.REJECTED


def test_review_has_precedence_over_approval() -> None:
    report = orchestrator().execute(
        request=request(),
        decision=decision(),
        risk_dashboard=dashboard(),
        regime_report=regime_report(
            MarketRegime.CORRECTION
        ),
    )

    assert (
        report.approval
        is TradeApproval.REVIEW_REQUIRED
    )


def test_broker_receipt_populates_result() -> None:
    report = orchestrator().execute(
        request=request(),
        decision=decision(),
        risk_dashboard=dashboard(),
        regime_report=regime_report(),
    )

    assert (
        report.result.execution_price
        == Decimal("199.50")
    )
    assert (
        report.result.executed_quantity
        == Decimal("10")
    )


def test_broker_failure_returns_failed_report() -> None:
    report = orchestrator(
        FailingBroker()
    ).execute(
        request=request(),
        decision=decision(),
        risk_dashboard=dashboard(),
        regime_report=regime_report(),
    )

    assert report.status is OrchestratorStatus.FAILED
    assert report.approval is TradeApproval.REJECTED
    assert report.result.submitted is False
    assert report.error == "paper broker unavailable"


def test_invalid_broker_response_returns_failed_report() -> None:
    class InvalidBroker:
        def submit(self, request):
            del request
            return object()

    report = orchestrator(
        InvalidBroker()
    ).execute(
        request=request(),
        decision=decision(),
        risk_dashboard=dashboard(),
        regime_report=regime_report(),
    )

    assert report.status is OrchestratorStatus.FAILED
    assert (
        report.error
        == "broker submit must return PaperBrokerReceipt"
    )


def test_overfill_returns_failed_report() -> None:
    class OverfillingBroker:
        def submit(self, request):
            return PaperBrokerReceipt(
                order_id="OVERFILL",
                execution_price=Decimal("200"),
                executed_quantity=(
                    request.quantity
                    + Decimal("1")
                ),
            )

    report = orchestrator(
        OverfillingBroker()
    ).execute(
        request=request(),
        decision=decision(),
        risk_dashboard=dashboard(),
        regime_report=regime_report(),
    )

    assert report.status is OrchestratorStatus.FAILED
    assert "must not exceed" in report.error


def test_warnings_are_aggregated() -> None:
    report = orchestrator().execute(
        request=request(),
        decision=decision(),
        risk_dashboard=dashboard(
            warnings=("Risk warning.",)
        ),
        regime_report=regime_report(
            warnings=("Regime warning.",)
        ),
    )

    assert report.warnings == (
        "Risk warning.",
        "Regime warning.",
    )


def test_report_contains_summaries() -> None:
    report = orchestrator().execute(
        request=request(),
        decision=decision(),
        risk_dashboard=dashboard(),
        regime_report=regime_report(),
    )

    assert "PAPER_TRADE" in report.decision_summary
    assert "PAPER_READY" in report.risk_summary
    assert "BULL" in report.regime_summary


@pytest.mark.parametrize(
    (
        "argument_name",
        "invalid_value",
        "message",
    ),
    [
        (
            "request",
            object(),
            "request must be a PaperTradeRequest",
        ),
        (
            "decision",
            object(),
            "decision must be a Decision",
        ),
        (
            "risk_dashboard",
            object(),
            "risk_dashboard must be an "
            "InstitutionalRiskDashboard",
        ),
        (
            "regime_report",
            object(),
            "regime_report must be a "
            "MarketRegimeReport",
        ),
    ],
)
def test_inputs_are_validated(
    argument_name,
    invalid_value,
    message,
) -> None:
    values = {
        "request": request(),
        "decision": decision(),
        "risk_dashboard": dashboard(),
        "regime_report": regime_report(),
    }
    values[argument_name] = invalid_value

    with pytest.raises(
        TypeError,
        match=message,
    ):
        orchestrator().execute(**values)


def test_broker_must_have_submit_method() -> None:
    with pytest.raises(
        TypeError,
        match="broker must provide a submit method",
    ):
        PaperTradingOrchestrator(
            broker=object()
        )


def test_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        PaperTradingOrchestrator(
            broker=RecordingBroker(),
            clock=NOW,
        )


def test_clock_must_return_datetime() -> None:
    engine = PaperTradingOrchestrator(
        broker=RecordingBroker(),
        clock=lambda: "now",
    )

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        engine.execute(
            request=request(),
            decision=decision(),
            risk_dashboard=dashboard(),
            regime_report=regime_report(),
        )


def test_clock_must_return_timezone_aware_datetime() -> None:
    engine = PaperTradingOrchestrator(
        broker=RecordingBroker(),
        clock=lambda: datetime(2026, 8, 2),
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        engine.execute(
            request=request(),
            decision=decision(),
            risk_dashboard=dashboard(),
            regime_report=regime_report(),
        )