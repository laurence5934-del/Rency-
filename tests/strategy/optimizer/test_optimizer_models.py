from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.strategy.optimizer.optimizer_models import (
    OptimizationObjective,
    OptimizationResult,
)
from app.strategy.supervisor import CapitalAllocation


def allocation() -> CapitalAllocation:
    return CapitalAllocation(
        strategy_id="trend",
        allocation=Decimal("50000"),
        weight=Decimal("0.50"),
    )


def test_optimization_result() -> None:
    result = OptimizationResult(
        objective=OptimizationObjective.BALANCED,
        selected_policy="EqualWeightAllocator",
        allocations=(allocation(),),
        total_capital=Decimal("50000"),
        portfolio_score=Decimal("0.90"),
    )

    assert result.objective is OptimizationObjective.BALANCED
    assert result.selected_policy == "EqualWeightAllocator"
    assert result.allocations == (allocation(),)
    assert result.total_capital == Decimal("50000")
    assert result.portfolio_score == Decimal("0.90")


def test_allocations_are_converted_to_tuple() -> None:
    result = OptimizationResult(
        objective=OptimizationObjective.MAXIMIZE_SCORE,
        selected_policy="ScoreWeightedAllocator",
        allocations=[allocation()],
        total_capital=Decimal("50000"),
        portfolio_score=Decimal("0.95"),
    )

    assert result.allocations == (allocation(),)


def test_warnings_are_converted_to_tuple() -> None:
    result = OptimizationResult(
        objective=OptimizationObjective.BALANCED,
        selected_policy="EqualWeightAllocator",
        warnings=["No approved strategies."],
    )

    assert result.warnings == (
        "No approved strategies.",
    )


def test_selected_policy_is_normalized() -> None:
    result = OptimizationResult(
        objective=OptimizationObjective.BALANCED,
        selected_policy="  EqualWeightAllocator  ",
    )

    assert result.selected_policy == "EqualWeightAllocator"


def test_selected_policy_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="selected_policy must not be empty",
    ):
        OptimizationResult(
            objective=OptimizationObjective.BALANCED,
            selected_policy="   ",
        )


def test_total_capital_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="total_capital must be a Decimal",
    ):
        OptimizationResult(
            objective=OptimizationObjective.BALANCED,
            selected_policy="EqualWeightAllocator",
            total_capital=50000,
        )


def test_total_capital_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="total_capital must not be negative",
    ):
        OptimizationResult(
            objective=OptimizationObjective.BALANCED,
            selected_policy="EqualWeightAllocator",
            total_capital=Decimal("-1"),
        )


@pytest.mark.parametrize(
    "portfolio_score",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_portfolio_score_must_be_between_zero_and_one(
    portfolio_score: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="portfolio_score must be between 0 and 1",
    ):
        OptimizationResult(
            objective=OptimizationObjective.BALANCED,
            selected_policy="EqualWeightAllocator",
            portfolio_score=portfolio_score,
        )


def test_result_is_immutable() -> None:
    result = OptimizationResult(
        objective=OptimizationObjective.BALANCED,
        selected_policy="EqualWeightAllocator",
    )

    with pytest.raises(FrozenInstanceError):
        result.selected_policy = "ScoreWeightedAllocator"