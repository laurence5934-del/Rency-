from decimal import Decimal

import pytest

from app.strategy.analytics import StrategyEvaluation
from app.strategy.decision import (
    Decision,
    DecisionAction,
)
from app.strategy.supervisor.allocation import (
    ConfidenceWeightedAllocator,
    EqualWeightAllocator,
    ScoreWeightedAllocator,
)
from app.strategy.supervisor.supervisor_models import (
    RankedStrategy,
    StrategyCandidate,
)


def ranked_strategy(
    strategy_id: str,
    *,
    rank: int,
    score: str,
    confidence: str,
) -> RankedStrategy:
    candidate = StrategyCandidate(
        strategy_id=strategy_id,
        evaluation=StrategyEvaluation(
            score=int(Decimal(score)),
            grade="A",
            recommendation="READY",
            strengths=(),
            concerns=(),
        ),
        decision=Decision(
            action=DecisionAction.PAPER_TRADE,
            confidence=Decimal(confidence),
            reason="Allocation test.",
        ),
    )

    return RankedStrategy(
        strategy=candidate,
        rank=rank,
        score=Decimal(score),
    )


def test_equal_weight_allocator() -> None:
    allocator = EqualWeightAllocator()

    allocations = allocator.allocate(
        (
            ranked_strategy(
                "trend",
                rank=1,
                score="90",
                confidence="0.90",
            ),
            ranked_strategy(
                "breakout",
                rank=2,
                score="80",
                confidence="0.80",
            ),
        ),
        capital=Decimal("100000"),
    )

    assert allocations[0].allocation == Decimal("50000")
    assert allocations[1].allocation == Decimal("50000")
    assert allocations[0].weight == Decimal("0.5")
    assert allocations[1].weight == Decimal("0.5")


def test_score_weighted_allocator() -> None:
    allocator = ScoreWeightedAllocator()

    allocations = allocator.allocate(
        (
            ranked_strategy(
                "higher",
                rank=1,
                score="75",
                confidence="0.80",
            ),
            ranked_strategy(
                "lower",
                rank=2,
                score="25",
                confidence="0.80",
            ),
        ),
        capital=Decimal("100000"),
    )

    assert allocations[0].allocation == Decimal("75000")
    assert allocations[1].allocation == Decimal("25000")
    assert allocations[0].weight == Decimal("0.75")
    assert allocations[1].weight == Decimal("0.25")


def test_confidence_weighted_allocator() -> None:
    allocator = ConfidenceWeightedAllocator()

    allocations = allocator.allocate(
        (
            ranked_strategy(
                "higher-confidence",
                rank=1,
                score="90",
                confidence="0.75",
            ),
            ranked_strategy(
                "lower-confidence",
                rank=2,
                score="90",
                confidence="0.25",
            ),
        ),
        capital=Decimal("80000"),
    )

    assert allocations[0].allocation == Decimal("60000")
    assert allocations[1].allocation == Decimal("20000")
    assert allocations[0].weight == Decimal("0.75")
    assert allocations[1].weight == Decimal("0.25")


@pytest.mark.parametrize(
    "allocator",
    [
        EqualWeightAllocator(),
        ScoreWeightedAllocator(),
        ConfidenceWeightedAllocator(),
    ],
)
def test_empty_ranked_strategies_return_no_allocations(
    allocator,
) -> None:
    assert (
        allocator.allocate(
            (),
            capital=Decimal("100000"),
        )
        == ()
    )


@pytest.mark.parametrize(
    "allocator",
    [
        EqualWeightAllocator(),
        ScoreWeightedAllocator(),
        ConfidenceWeightedAllocator(),
    ],
)
def test_zero_capital_produces_zero_allocations(
    allocator,
) -> None:
    allocations = allocator.allocate(
        (
            ranked_strategy(
                "trend",
                rank=1,
                score="90",
                confidence="0.90",
            ),
        ),
        capital=Decimal("0"),
    )

    assert allocations[0].allocation == Decimal("0")


def test_zero_scores_fall_back_to_equal_weight() -> None:
    allocator = ScoreWeightedAllocator()

    allocations = allocator.allocate(
        (
            ranked_strategy(
                "one",
                rank=1,
                score="0",
                confidence="0.80",
            ),
            ranked_strategy(
                "two",
                rank=2,
                score="0",
                confidence="0.70",
            ),
        ),
        capital=Decimal("100000"),
    )

    assert allocations[0].allocation == Decimal("50000")
    assert allocations[1].allocation == Decimal("50000")


def test_zero_confidences_fall_back_to_equal_weight() -> None:
    allocator = ConfidenceWeightedAllocator()

    allocations = allocator.allocate(
        (
            ranked_strategy(
                "one",
                rank=1,
                score="90",
                confidence="0",
            ),
            ranked_strategy(
                "two",
                rank=2,
                score="80",
                confidence="0",
            ),
        ),
        capital=Decimal("100000"),
    )

    assert allocations[0].allocation == Decimal("50000")
    assert allocations[1].allocation == Decimal("50000")


@pytest.mark.parametrize(
    "allocator",
    [
        EqualWeightAllocator(),
        ScoreWeightedAllocator(),
        ConfidenceWeightedAllocator(),
    ],
)
def test_negative_capital_is_rejected(
    allocator,
) -> None:
    with pytest.raises(
        ValueError,
        match="must not be negative",
    ):
        allocator.allocate(
            (),
            capital=Decimal("-1"),
        )


@pytest.mark.parametrize(
    "allocator",
    [
        EqualWeightAllocator(),
        ScoreWeightedAllocator(),
        ConfidenceWeightedAllocator(),
    ],
)
def test_capital_must_be_decimal(
    allocator,
) -> None:
    with pytest.raises(
        TypeError,
        match="capital must be a Decimal",
    ):
        allocator.allocate(
            (),
            capital=100000,
        )