from decimal import Decimal

from app.strategy.analytics import StrategyEvaluation
from app.strategy.decision.decision_models import DecisionAction
from app.strategy.decision.decision_policy import (
    AggressivePolicy,
    BalancedPolicy,
    ConservativePolicy,
)


def evaluation(
    *,
    score=100,
    grade="A",
    concerns=(),
):
    return StrategyEvaluation(
        score=score,
        grade=grade,
        recommendation="READY",
        strengths=(),
        concerns=tuple(concerns),
    )


def test_conservative_live_trade():
    decision = ConservativePolicy().decide(
        evaluation(
            score=100,
            grade="A",
        )
    )

    assert decision.action is DecisionAction.LIVE_TRADE
    assert decision.approved


def test_conservative_requires_improvement():
    decision = ConservativePolicy().decide(
        evaluation(
            score=90,
            grade="A",
        )
    )

    assert decision.action is DecisionAction.IMPROVE


def test_balanced_policy():
    decision = BalancedPolicy().decide(
        evaluation(
            score=88,
            grade="B",
        )
    )

    assert decision.action is DecisionAction.PAPER_TRADE


def test_balanced_rejects_low_score():
    decision = BalancedPolicy().decide(
        evaluation(
            score=70,
            grade="C",
        )
    )

    assert decision.action is DecisionAction.IMPROVE


def test_aggressive_policy():
    decision = AggressivePolicy().decide(
        evaluation(
            score=78,
            grade="B",
        )
    )

    assert decision.action is DecisionAction.PAPER_TRADE


def test_aggressive_reject():
    decision = AggressivePolicy().decide(
        evaluation(
            score=60,
            grade="D",
        )
    )

    assert decision.action is DecisionAction.REJECT


def test_concerns_are_preserved():
    decision = BalancedPolicy().decide(
        evaluation(
            score=88,
            grade="A",
            concerns=("Drawdown",),
        )
    )

    assert decision.warnings == ("Drawdown",)