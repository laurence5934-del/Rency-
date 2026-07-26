from app.analytics import (
    AIDecisionObservation,
    ClosedTrade,
    EnterprisePerformanceAnalyticsEngine,
    IncomeEvent,
    IncomeType,
    PortfolioObservation,
)


def main() -> None:
    engine = EnterprisePerformanceAnalyticsEngine()
    engine.record_portfolio(PortfolioObservation(5000.0, 5000.0, 10000.0))
    engine.record_portfolio(PortfolioObservation(5100.0, 5100.0, 10200.0, realized_pnl=100.0, unrealized_pnl=100.0))
    engine.record_trade(ClosedTrade("ABC", 250.0, strategy="MOMENTUM", broker="PAPER"))
    engine.record_trade(ClosedTrade("XYZ", -100.0, strategy="MEAN_REVERSION", broker="PAPER"))
    engine.record_income(IncomeEvent(50.0, IncomeType.DIVIDEND, "ABC"))
    engine.record_ai_decision(AIDecisionObservation(0.85, True, model="CONSENSUS"))
    engine.record_benchmark_value(10000.0)
    engine.record_benchmark_value(10100.0)
    snapshot = engine.snapshot(invested_capital=10000.0)
    assert snapshot.portfolio["portfolio_value"] == 10200.0
    assert snapshot.trades["total_trades"] == 2
    assert snapshot.income["total_income"] == 50.0
    assert snapshot.ai["decision_accuracy"] == 1.0
    assert engine.health()["status"] == "HEALTHY"


if __name__ == "__main__":
    main()
