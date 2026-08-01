from decimal import Decimal

from app.strategy.analytics import StrategyEvaluation
from app.strategy.decision import (
    Decision,
    DecisionAction,
)
from app.strategy.optimizer import (
    OptimizationObjective,
    PortfolioOptimizer,
)
from app.strategy.supervisor import (
    RankedStrategy,
    StrategyCandidate,
)


def ranked(
    strategy_id: str,
    score: int,
    confidence: str,
):
    return RankedStrategy(
        strategy=StrategyCandidate(
            strategy_id=strategy_id,
            evaluation=StrategyEvaluation(
                score=score,
                grade="A",
                recommendation="READY",
                strengths=(),
                concerns=(),
            ),
            decision=Decision(
                action=DecisionAction.PAPER_TRADE,
                confidence=Decimal(confidence),
                reason="optimizer",
            ),
        ),
        rank=1,
        score=Decimal(score),
    )


def test_balanced_selects_equal_allocator():

    optimizer = PortfolioOptimizer()

    result = optimizer.optimize(
        (
            ranked("A", 90, "0.9"),
            ranked("B", 80, "0.8"),
        ),
        objective=OptimizationObjective.BALANCED,
        capital=Decimal("100000"),
    )

    assert result.selected_policy == "EqualWeightAllocator"

    assert result.allocations[0].allocation == Decimal("50000")


def test_score_optimizer():

    optimizer = PortfolioOptimizer()

    result = optimizer.optimize(
        (
            ranked("A", 75, "0.8"),
            ranked("B", 25, "0.8"),
        ),
        objective=OptimizationObjective.MAXIMIZE_SCORE,
        capital=Decimal("100000"),
    )

    assert result.selected_policy == "ScoreWeightedAllocator"

    assert result.allocations[0].allocation == Decimal("75000")


def test_confidence_optimizer():

    optimizer = PortfolioOptimizer()

    result = optimizer.optimize(
        (
            ranked("A", 90, "0.75"),
            ranked("B", 90, "0.25"),
        ),
        objective=OptimizationObjective.MAXIMIZE_CONFIDENCE,
        capital=Decimal("80000"),
    )

    assert result.selected_policy == "ConfidenceWeightedAllocator"

    assert result.allocations[0].allocation == Decimal("60000")


def test_portfolio_score():

    optimizer = PortfolioOptimizer()

    result = optimizer.optimize(
        (
            ranked("A", 100, "1"),
            ranked("B", 80, "1"),
        ),
        objective=OptimizationObjective.BALANCED,
        capital=Decimal("100000"),
    )

    assert result.portfolio_score == Decimal("0.9")


def test_empty_portfolio():

    optimizer = PortfolioOptimizer()

    result = optimizer.optimize(
        (),
        objective=OptimizationObjective.BALANCED,
        capital=Decimal("100000"),
    )

    assert result.allocations == ()
    assert result.portfolio_score == Decimal("0")