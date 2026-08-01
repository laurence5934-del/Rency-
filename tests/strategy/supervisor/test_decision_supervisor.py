from decimal import Decimal

import pytest

from app.strategy.analytics import StrategyEvaluation
from app.strategy.decision import (
    Decision,
    DecisionAction,
)
from app.strategy.supervisor.decision_supervisor import (
    DecisionSupervisor,
)
from app.strategy.supervisor.supervisor_models import (
    StrategyCandidate,
)


def candidate(
    strategy_id: str,
    *,
    score: int,
    confidence: str,
    action: DecisionAction,
) -> StrategyCandidate:
    return StrategyCandidate(
        strategy_id=strategy_id,
        evaluation=StrategyEvaluation(
            score=score,
            grade="A",
            recommendation="READY",
            strengths=(),
            concerns=(),
        ),
        decision=Decision(
            action=action,
            confidence=Decimal(confidence),
            reason="Supervisor test decision.",
        ),
    )


def test_create_plan_allocates_capital_equally() -> None:
    supervisor = DecisionSupervisor()

    plan = supervisor.create_plan(
        (
            candidate(
                "trend",
                score=95,
                confidence="0.95",
                action=DecisionAction.LIVE_TRADE,
            ),
            candidate(
                "breakout",
                score=90,
                confidence="0.90",
                action=DecisionAction.PAPER_TRADE,
            ),
        ),
        capital=Decimal("100000"),
    )

    assert len(plan.allocations) == 2

    assert plan.allocations[0].allocation == Decimal(
        "50000"
    )
    assert plan.allocations[1].allocation == Decimal(
        "50000"
    )

    assert plan.allocations[0].weight == Decimal(
        "0.5"
    )
    assert plan.allocations[1].weight == Decimal(
        "0.5"
    )

    assert plan.total_capital == Decimal("100000")


def test_rejected_candidates_are_excluded() -> None:
    supervisor = DecisionSupervisor()

    plan = supervisor.create_plan(
        (
            candidate(
                "approved",
                score=90,
                confidence="0.90",
                action=DecisionAction.PAPER_TRADE,
            ),
            candidate(
                "rejected",
                score=99,
                confidence="0.99",
                action=DecisionAction.REJECT,
            ),
        ),
        capital=Decimal("50000"),
    )

    assert len(plan.allocations) == 1
    assert (
        plan.allocations[0].strategy_id
        == "approved"
    )
    assert (
        plan.allocations[0].allocation
        == Decimal("50000")
    )


def test_improve_candidates_are_excluded() -> None:
    supervisor = DecisionSupervisor()

    plan = supervisor.create_plan(
        (
            candidate(
                "needs-work",
                score=85,
                confidence="0.85",
                action=DecisionAction.IMPROVE,
            ),
        ),
        capital=Decimal("50000"),
    )

    assert plan.allocations == ()
    assert plan.total_capital == Decimal("0")


def test_candidates_are_ranked_by_score() -> None:
    supervisor = DecisionSupervisor()

    plan = supervisor.create_plan(
        (
            candidate(
                "lower",
                score=80,
                confidence="0.90",
                action=DecisionAction.PAPER_TRADE,
            ),
            candidate(
                "higher",
                score=95,
                confidence="0.80",
                action=DecisionAction.PAPER_TRADE,
            ),
        ),
        capital=Decimal("100000"),
    )

    assert (
        plan.allocations[0].strategy_id
        == "higher"
    )
    assert (
        plan.allocations[1].strategy_id
        == "lower"
    )


def test_confidence_breaks_score_ties() -> None:
    supervisor = DecisionSupervisor()

    plan = supervisor.create_plan(
        (
            candidate(
                "lower-confidence",
                score=90,
                confidence="0.80",
                action=DecisionAction.PAPER_TRADE,
            ),
            candidate(
                "higher-confidence",
                score=90,
                confidence="0.95",
                action=DecisionAction.PAPER_TRADE,
            ),
        ),
        capital=Decimal("100000"),
    )

    assert (
        plan.allocations[0].strategy_id
        == "higher-confidence"
    )


def test_no_approved_strategies_returns_warning() -> None:
    supervisor = DecisionSupervisor()

    plan = supervisor.create_plan(
        (
            candidate(
                "rejected",
                score=50,
                confidence="0.50",
                action=DecisionAction.REJECT,
            ),
        ),
        capital=Decimal("100000"),
    )

    assert plan.allocations == ()
    assert plan.total_capital == Decimal("0")
    assert plan.warnings == (
        "No approved strategies were available for deployment.",
    )


def test_zero_capital_returns_zero_allocations() -> None:
    supervisor = DecisionSupervisor()

    plan = supervisor.create_plan(
        (
            candidate(
                "trend",
                score=90,
                confidence="0.90",
                action=DecisionAction.PAPER_TRADE,
            ),
        ),
        capital=Decimal("0"),
    )

    assert plan.allocations[0].allocation == Decimal("0")
    assert plan.total_capital == Decimal("0")
    assert plan.warnings == (
        "Available capital is zero.",
    )


def test_negative_capital_is_rejected() -> None:
    supervisor = DecisionSupervisor()

    with pytest.raises(
        ValueError,
        match="must not be negative",
    ):
        supervisor.create_plan(
            (),
            capital=Decimal("-1"),
        )


def test_capital_must_be_decimal() -> None:
    supervisor = DecisionSupervisor()

    with pytest.raises(
        TypeError,
        match="capital must be a Decimal",
    ):
        supervisor.create_plan(
            (),
            capital=100000,
        )