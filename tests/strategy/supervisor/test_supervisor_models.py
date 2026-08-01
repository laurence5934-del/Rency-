from decimal import Decimal

from app.strategy.analytics import StrategyEvaluation
from app.strategy.decision import (
    Decision,
    DecisionAction,
)
from app.strategy.supervisor.supervisor_models import (
    CapitalAllocation,
    DeploymentPlan,
    RankedStrategy,
    StrategyCandidate,
)


def evaluation(score=90):
    return StrategyEvaluation(
        score=score,
        grade="A",
        recommendation="READY",
        strengths=(),
        concerns=(),
    )


def decision():
    return Decision(
        action=DecisionAction.PAPER_TRADE,
        confidence=Decimal("0.90"),
        reason="Approved",
    )


def test_strategy_candidate():
    candidate = StrategyCandidate(
        strategy_id="mean_reversion",
        evaluation=evaluation(),
        decision=decision(),
    )

    assert candidate.strategy_id == "mean_reversion"


def test_ranked_strategy():
    ranked = RankedStrategy(
        strategy=StrategyCandidate(
            strategy_id="breakout",
            evaluation=evaluation(),
            decision=decision(),
        ),
        rank=1,
        score=Decimal("95"),
    )

    assert ranked.rank == 1


def test_capital_allocation():
    allocation = CapitalAllocation(
        strategy_id="trend",
        allocation=Decimal("25000"),
        weight=Decimal("0.25"),
    )

    assert allocation.allocation == Decimal("25000")


def test_deployment_plan():
    plan = DeploymentPlan(
        allocations=(
            CapitalAllocation(
                strategy_id="trend",
                allocation=Decimal("50000"),
                weight=Decimal("0.50"),
            ),
        ),
        total_capital=Decimal("50000"),
    )

    assert len(plan.allocations) == 1
    assert plan.total_capital == Decimal("50000")


def test_plan_warnings_are_tuple():
    plan = DeploymentPlan(
        warnings=["Drawdown warning"],
    )

    assert plan.warnings == (
        "Drawdown warning",
    )