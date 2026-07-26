from app.strategy.evaluation import StrategyEvaluationDashboardAPI, StrategyEvaluationEngine, StrategyEvidence


def main() -> None:
    engine = StrategyEvaluationEngine()
    evidence = StrategyEvidence(
        strategy_id="momentum",
        strategy_version="1.0.0",
        net_return_pct=28.0,
        annualized_return_pct=22.0,
        win_rate_pct=61.0,
        profit_factor=1.7,
        expectancy=1.1,
        max_drawdown_pct=11.0,
        annualized_volatility_pct=18.0,
        monthly_returns_pct=(2.0, 1.0, -0.5, 3.0, 2.5, 1.5),
        trade_count=120,
        profitable_period_ratio=5 / 6,
        execution_success_rate_pct=99.0,
        average_slippage_bps=2.0,
        order_failure_rate_pct=0.5,
    )
    result = engine.evaluate(evidence)
    assert result.scores.overall > 70.0
    assert StrategyEvaluationDashboardAPI(engine).health()["status"] == "healthy"


if __name__ == "__main__":
    main()
