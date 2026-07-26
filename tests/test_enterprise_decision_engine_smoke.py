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

context = DecisionContext(
    symbol="PLTR",
    side="BUY",
    requested_quantity=100,
    consensus_score=0.82,
    confidence_score=0.84,
    validation_score=0.90,
    strategy=StrategyDecisionContext(
        strategy_name="momentum_growth",
        desired_action=DecisionAction.BUY,
        signal_strength=0.86,
        expected_return_pct=0.12,
        time_horizon="SWING",
        rationale="Strong multi-timeframe momentum",
    ),
    risk=RiskDecisionContext(
        decision="APPROVE",
        risk_score=0.20,
        approved_quantity=100,
        maximum_allowed_quantity=250,
    ),
    portfolio=PortfolioDecisionContext(
        portfolio_value=100000.0,
        cash_available=40000.0,
        gross_exposure=60000.0,
        net_exposure=60000.0,
        open_positions=5,
    ),
    position=PositionDecisionContext(
        current_quantity=0,
        average_price=0.0,
        unrealized_pnl_pct=0.0,
        has_open_position=False,
    ),
    market=MarketDecisionContext(
        market_open=True,
        trading_halted=False,
        volatility_regime="NORMAL",
        liquidity_score=0.95,
        market_trend="BULLISH",
    ),
)

engine = EnterpriseDecisionEngine()
report = engine.decide(context, correlation_id="smoke-test-001")

assert report.symbol == "PLTR"
assert report.action == DecisionAction.BUY
assert report.status == DecisionStatus.APPROVED
assert report.approved_quantity == 100
assert report.decision_score >= 0.70
assert engine.metrics()["total"] == 1
assert engine.health()["status"] == "HEALTHY"
assert len(engine.recent_decisions()) == 1
