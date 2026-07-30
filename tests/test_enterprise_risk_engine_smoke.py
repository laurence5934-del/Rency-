from app.ai.risk_engine import (
    EnterpriseRiskEngine,
    MarketRiskContext,
    PortfolioRiskContext,
    RiskDecision,
    RiskEvaluationInput,
    TradeRiskContext,
)


def test_enterprise_risk_engine_smoke() -> None:
    portfolio = PortfolioRiskContext(
        100000,
        40000,
        60000,
        60000,
        daily_pnl=500,
        weekly_pnl=1200,
        monthly_pnl=3000,
        current_drawdown=0.02,
        leverage=1.0,
        sector_exposure={"Technology": 0.12},
    )

    trade = TradeRiskContext(
        "PLTR",
        "BUY",
        25,
        100,
        "Technology",
        0.84,
        0.79,
        0.12,
        0.28,
        20000000,
    )

    market = MarketRiskContext(
        18,
        False,
        False,
        10,
        0.20,
        0.95,
    )

    historical_returns = (
        0.010,
        -0.008,
        0.006,
        -0.004,
        0.012,
        -0.015,
        0.004,
        0.008,
        -0.006,
        0.009,
    )

    source = RiskEvaluationInput(
        portfolio=portfolio,
        trade=trade,
        market=market,
        historical_returns=historical_returns,
    )

    engine = EnterpriseRiskEngine()
    report = engine.evaluate(source)

    assert report.decision in {
        RiskDecision.APPROVE,
        RiskDecision.REDUCE,
    }
    assert report.maximum_allowed_quantity > 0
    assert report.suggested_stop_loss < source.trade.price
    assert report.suggested_take_profit > source.trade.price
    assert report.risk_reward_ratio >= 2.0
    assert engine.metrics()["evaluations"] == 1
