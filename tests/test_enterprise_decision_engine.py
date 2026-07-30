from app.ai.decision_engine import (
    DecisionAction,
    DecisionContext,
    DecisionStatus,
    EnterpriseDecisionEngine,
    MarketDecisionContext,
    PortfolioDecisionContext,
    PositionDecisionContext,
    RiskDecisionContext,
    StrategyDecisionContext,
)


def make_context(**overrides):
    values = dict(
        symbol="NVDA",
        side="BUY",
        requested_quantity=50,
        consensus_score=0.82,
        confidence_score=0.83,
        validation_score=0.90,
        strategy=StrategyDecisionContext(
            strategy_name="trend",
            desired_action=DecisionAction.BUY,
            signal_strength=0.85,
        ),
        risk=RiskDecisionContext(
            decision="APPROVE",
            risk_score=0.20,
            approved_quantity=50,
            maximum_allowed_quantity=100,
        ),
        portfolio=PortfolioDecisionContext(
            portfolio_value=100000.0,
            cash_available=50000.0,
            gross_exposure=50000.0,
            net_exposure=50000.0,
        ),
        position=PositionDecisionContext(),
        market=MarketDecisionContext(),
    )
    values.update(overrides)
    return DecisionContext(**values)


def test_approves_valid_buy():
    report = EnterpriseDecisionEngine().decide(make_context())
    assert report.action == DecisionAction.BUY
    assert report.status == DecisionStatus.APPROVED


def test_rejects_risk_rejection():
    context = make_context(
        risk=RiskDecisionContext(
            decision="REJECT",
            risk_score=0.90,
            approved_quantity=0,
            maximum_allowed_quantity=0,
            violations=("MAXIMUM_DRAWDOWN_REACHED",),
        )
    )
    report = EnterpriseDecisionEngine().decide(context)
    assert report.action == DecisionAction.CANCEL
    assert report.status == DecisionStatus.REJECTED


def test_defers_when_market_closed():
    context = make_context(
        market=MarketDecisionContext(market_open=False)
    )
    report = EnterpriseDecisionEngine().decide(context)
    assert report.action == DecisionAction.DEFER
    assert report.status == DecisionStatus.DEFERRED


def test_buy_becomes_scale_in_with_open_position():
    context = make_context(
        position=PositionDecisionContext(
            current_quantity=25,
            average_price=100.0,
            has_open_position=True,
        )
    )
    report = EnterpriseDecisionEngine().decide(context)
    assert report.action in {DecisionAction.BUY, DecisionAction.SCALE_IN}
