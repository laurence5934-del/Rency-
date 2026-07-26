from app.analytics import (
    AIDecisionObservation,
    ClosedTrade,
    EnterprisePerformanceAnalyticsEngine,
    IncomeEvent,
    IncomeType,
    PortfolioObservation,
)


def test_trade_and_risk_statistics():
    engine = EnterprisePerformanceAnalyticsEngine()
    engine.record_portfolio(PortfolioObservation(5000.0, 5000.0, 10000.0))
    engine.record_portfolio(PortfolioObservation(5000.0, 5000.0, 8000.0))
    engine.record_portfolio(PortfolioObservation(5000.0, 5000.0, 9000.0))
    engine.record_trade(ClosedTrade("AAA", 300.0))
    engine.record_trade(ClosedTrade("BBB", -100.0))
    snapshot = engine.snapshot()
    assert snapshot.trades["win_rate"] == 0.5
    assert snapshot.trades["profit_factor"] == 3.0
    assert snapshot.trades["expectancy"] == 100.0
    assert snapshot.risk["maximum_drawdown"] == 0.2


def test_income_ai_benchmark_and_attribution():
    engine = EnterprisePerformanceAnalyticsEngine()
    engine.record_portfolio(PortfolioObservation(1000.0, 1000.0, 10000.0))
    engine.record_portfolio(PortfolioObservation(1000.0, 1000.0, 11000.0))
    engine.record_benchmark_value(10000.0)
    engine.record_benchmark_value(10500.0)
    engine.record_income(IncomeEvent(120.0, IncomeType.DIVIDEND, "AAA", "2026-01-15T00:00:00+00:00"))
    engine.record_trade(ClosedTrade("AAA", 200.0, strategy="TREND", broker="PAPER"))
    engine.record_ai_decision(AIDecisionObservation(0.9, True, model="MODEL_A"))
    engine.record_ai_decision(AIDecisionObservation(0.7, False, model="MODEL_A"))
    snapshot = engine.snapshot(invested_capital=10000.0)
    assert snapshot.income["yield_on_cost"] == 0.012
    assert snapshot.ai["decision_accuracy"] == 0.5
    assert snapshot.benchmark["excess_return"] == 0.05
    assert snapshot.attribution["by_strategy"]["TREND"] == 200.0
