import pytest

from app.strategy.evaluation import (
    EvaluationWeights,
    Recommendation,
    StrategyEvaluationEngine,
    StrategyEvidence,
    StrategyRankingEngine,
)


def evidence(strategy_id: str, annualized_return: float, drawdown: float, trades: int = 100) -> StrategyEvidence:
    return StrategyEvidence(
        strategy_id=strategy_id,
        strategy_version="1.0.0",
        net_return_pct=annualized_return * 1.4,
        annualized_return_pct=annualized_return,
        win_rate_pct=62.0,
        profit_factor=1.8,
        expectancy=1.2,
        max_drawdown_pct=drawdown,
        annualized_volatility_pct=17.0,
        monthly_returns_pct=(2.0, 1.5, -0.2, 2.1, 1.1, 2.4),
        trade_count=trades,
        profitable_period_ratio=5 / 6,
        execution_success_rate_pct=99.5,
        average_slippage_bps=1.5,
        order_failure_rate_pct=0.2,
    )


def test_evaluation_and_ranking_are_explainable() -> None:
    engine = StrategyEvaluationEngine()
    stronger = engine.evaluate(evidence("stronger", 24.0, 9.0))
    weaker = engine.evaluate(evidence("weaker", 8.0, 28.0))
    ranked = StrategyRankingEngine().rank([weaker, stronger])
    assert ranked[0].strategy_id == "stronger"
    assert stronger.recommendation in {Recommendation.PROMOTE_TO_PAPER, Recommendation.PROMOTE_TO_LIVE_REVIEW}
    assert stronger.reasons
    assert engine.metrics.snapshot()["evaluations_total"] == 2


def test_weight_validation_and_small_sample_recommendation() -> None:
    with pytest.raises(ValueError):
        EvaluationWeights(performance=0.5)
    result = StrategyEvaluationEngine().evaluate(evidence("small", 20.0, 10.0, trades=12))
    assert result.recommendation is Recommendation.NEEDS_MORE_DATA
