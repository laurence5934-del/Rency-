from decimal import Decimal

import pytest

from app.strategy.rebalancing.rebalancing_engine import (
    PortfolioRebalancingEngine,
)
from app.strategy.rebalancing.rebalancing_models import (
    PortfolioAllocation,
    RebalanceSide,
    RebalancingDecision,
    RebalancingStatus,
)


def allocation(
    symbol: str,
    *,
    current_value: str,
    current_weight: str,
    target_weight: str,
    market_price: str | None,
    warnings=(),
) -> PortfolioAllocation:
    return PortfolioAllocation(
        symbol=symbol,
        current_value=Decimal(current_value),
        current_weight=Decimal(current_weight),
        target_weight=Decimal(target_weight),
        market_price=(
            Decimal(market_price)
            if market_price is not None
            else None
        ),
        warnings=tuple(warnings),
    )


def balanced_allocations():
    return (
        allocation(
            "AAPL",
            current_value="50000",
            current_weight="0.50",
            target_weight="0.50",
            market_price="200",
        ),
        allocation(
            "MSFT",
            current_value="50000",
            current_weight="0.50",
            target_weight="0.50",
            market_price="400",
        ),
    )


def drifting_allocations():
    return (
        allocation(
            "AAPL",
            current_value="40000",
            current_weight="0.40",
            target_weight="0.50",
            market_price="200",
        ),
        allocation(
            "MSFT",
            current_value="60000",
            current_weight="0.60",
            target_weight="0.50",
            market_price="400",
        ),
    )


def build(
    *,
    allocations=None,
    portfolio_value: str = "100000",
    available_cash: str = "0",
    drift_threshold: str = "0.02",
    minimum_trade_value: str = "100",
    maximum_turnover: str = "0.30",
):
    return PortfolioRebalancingEngine().build_plan(
        plan_id="plan-001",
        portfolio_value=Decimal(portfolio_value),
        available_cash=Decimal(available_cash),
        allocations=(
            allocations
            if allocations is not None
            else drifting_allocations()
        ),
        drift_threshold=Decimal(drift_threshold),
        minimum_trade_value=Decimal(
            minimum_trade_value
        ),
        maximum_turnover=Decimal(
            maximum_turnover
        ),
    )


def test_valid_rebalance_is_approved() -> None:
    report = build()

    assert report.status is RebalancingStatus.COMPLETED
    assert report.decision is RebalancingDecision.APPROVE
    assert report.plan is not None
    assert report.error is None


def test_builds_buy_and_sell_instructions() -> None:
    report = build()
    assert report.plan is not None

    sides = {
        instruction.symbol: instruction.side
        for instruction in report.plan.instructions
    }

    assert sides["AAPL"] is RebalanceSide.BUY
    assert sides["MSFT"] is RebalanceSide.SELL


def test_sell_is_ordered_before_buy() -> None:
    report = build()
    assert report.plan is not None

    assert tuple(
        instruction.side
        for instruction in report.plan.instructions
    ) == (
        RebalanceSide.SELL,
        RebalanceSide.BUY,
    )


def test_trade_values_are_based_on_drift() -> None:
    report = build()
    assert report.plan is not None

    aapl = next(
        instruction
        for instruction in report.plan.instructions
        if instruction.symbol == "AAPL"
    )

    assert (
        aapl.estimated_trade_value
        == Decimal("10000")
    )
    assert aapl.quantity == Decimal("50")


def test_plan_totals_are_calculated() -> None:
    report = build()
    assert report.plan is not None

    assert report.plan.total_buy_value == Decimal(
        "10000"
    )
    assert report.plan.total_sell_value == Decimal(
        "10000"
    )
    assert report.plan.projected_cash == Decimal("0")
    assert report.plan.turnover_ratio == Decimal(
        "0.20"
    )


def test_no_drift_produces_hold_instructions() -> None:
    report = build(
        allocations=balanced_allocations()
    )
    assert report.plan is not None

    assert report.decision is RebalancingDecision.APPROVE
    assert all(
        instruction.side is RebalanceSide.HOLD
        for instruction in report.plan.instructions
    )
    assert report.plan.turnover_ratio == Decimal("0")


def test_no_drift_recommendation() -> None:
    report = build(
        allocations=balanced_allocations()
    )

    assert "No meaningful portfolio drift" in (
        report.recommendation
    )


def test_drift_below_threshold_is_held() -> None:
    allocations = (
        allocation(
            "AAPL",
            current_value="49000",
            current_weight="0.49",
            target_weight="0.50",
            market_price="200",
        ),
        allocation(
            "MSFT",
            current_value="51000",
            current_weight="0.51",
            target_weight="0.50",
            market_price="400",
        ),
    )

    report = build(
        allocations=allocations,
        drift_threshold="0.02",
    )
    assert report.plan is not None

    assert all(
        item.side is RebalanceSide.HOLD
        for item in report.plan.instructions
    )


def test_drift_equal_to_threshold_trades() -> None:
    allocations = (
        allocation(
            "AAPL",
            current_value="48000",
            current_weight="0.48",
            target_weight="0.50",
            market_price="200",
        ),
        allocation(
            "MSFT",
            current_value="52000",
            current_weight="0.52",
            target_weight="0.50",
            market_price="400",
        ),
    )

    report = build(
        allocations=allocations,
        drift_threshold="0.02",
    )
    assert report.plan is not None

    assert any(
        item.side is RebalanceSide.BUY
        for item in report.plan.instructions
    )


def test_trade_below_minimum_is_held() -> None:
    allocations = (
        allocation(
            "AAPL",
            current_value="49950",
            current_weight="0.4995",
            target_weight="0.50",
            market_price="200",
        ),
        allocation(
            "MSFT",
            current_value="50050",
            current_weight="0.5005",
            target_weight="0.50",
            market_price="400",
        ),
    )

    report = build(
        allocations=allocations,
        drift_threshold="0",
        minimum_trade_value="100",
    )
    assert report.plan is not None

    assert all(
        item.side is RebalanceSide.HOLD
        for item in report.plan.instructions
    )


def test_missing_price_requires_review() -> None:
    allocations = (
        allocation(
            "AAPL",
            current_value="40000",
            current_weight="0.40",
            target_weight="0.50",
            market_price=None,
        ),
        allocation(
            "MSFT",
            current_value="60000",
            current_weight="0.60",
            target_weight="0.50",
            market_price="400",
        ),
    )

    report = build(allocations=allocations)

    assert (
        report.decision
        is RebalancingDecision.REVIEW_REQUIRED
    )
    assert "Missing market prices" in report.warnings[0]


def test_missing_price_instruction_is_hold() -> None:
    allocations = (
        allocation(
            "AAPL",
            current_value="40000",
            current_weight="0.40",
            target_weight="0.50",
            market_price=None,
        ),
        allocation(
            "MSFT",
            current_value="60000",
            current_weight="0.60",
            target_weight="0.50",
            market_price="400",
        ),
    )

    report = build(allocations=allocations)
    assert report.plan is not None

    aapl = next(
        item
        for item in report.plan.instructions
        if item.symbol == "AAPL"
    )

    assert aapl.side is RebalanceSide.HOLD


def test_sells_fund_buys() -> None:
    report = build(
        available_cash="0"
    )

    assert report.decision is RebalancingDecision.APPROVE
    assert report.plan is not None
    assert report.plan.projected_cash == Decimal("0")


def test_insufficient_cash_requires_review() -> None:
    allocations = (
        allocation(
            "AAPL",
            current_value="20000",
            current_weight="0.20",
            target_weight="0.60",
            market_price="200",
        ),
        allocation(
            "MSFT",
            current_value="80000",
            current_weight="0.80",
            target_weight="0.40",
            market_price=None,
        ),
    )

    report = build(
        allocations=allocations,
        available_cash="0",
    )

    assert (
        report.decision
        is RebalancingDecision.REVIEW_REQUIRED
    )


def test_unfunded_buy_is_converted_to_hold() -> None:
    allocations = (
        allocation(
            "AAPL",
            current_value="20000",
            current_weight="0.20",
            target_weight="0.60",
            market_price="200",
        ),
        allocation(
            "MSFT",
            current_value="80000",
            current_weight="0.80",
            target_weight="0.40",
            market_price=None,
        ),
    )

    report = build(
        allocations=allocations,
        available_cash="0",
    )
    assert report.plan is not None

    aapl = next(
        item
        for item in report.plan.instructions
        if item.symbol == "AAPL"
    )

    assert aapl.side is RebalanceSide.HOLD
    assert report.plan.projected_cash >= Decimal("0")


def test_turnover_above_maximum_is_rejected() -> None:
    report = build(
        maximum_turnover="0.10"
    )

    assert report.decision is RebalancingDecision.REJECT
    assert "turnover" in report.recommendation.lower()


def test_turnover_equal_to_maximum_is_approved() -> None:
    report = build(
        maximum_turnover="0.20"
    )

    assert report.decision is RebalancingDecision.APPROVE


def test_allocation_warnings_are_preserved() -> None:
    allocations = (
        allocation(
            "AAPL",
            current_value="40000",
            current_weight="0.40",
            target_weight="0.50",
            market_price="200",
            warnings=("Allocation warning.",),
        ),
        allocation(
            "MSFT",
            current_value="60000",
            current_weight="0.60",
            target_weight="0.50",
            market_price="400",
        ),
    )

    report = build(allocations=allocations)

    assert "Allocation warning." in report.warnings


def test_duplicate_symbols_return_failed_report() -> None:
    duplicate = allocation(
        "AAPL",
        current_value="50000",
        current_weight="0.50",
        target_weight="0.50",
        market_price="200",
    )

    report = build(
        allocations=(duplicate, duplicate)
    )

    assert report.status is RebalancingStatus.FAILED
    assert (
        report.error
        == "allocation symbols must be unique"
    )


def test_target_weights_must_sum_to_one() -> None:
    allocations = (
        allocation(
            "AAPL",
            current_value="50000",
            current_weight="0.50",
            target_weight="0.40",
            market_price="200",
        ),
        allocation(
            "MSFT",
            current_value="50000",
            current_weight="0.50",
            target_weight="0.40",
            market_price="400",
        ),
    )

    report = build(allocations=allocations)

    assert report.status is RebalancingStatus.FAILED
    assert (
        report.error
        == "target allocation weights must sum to 1"
    )


def test_current_values_cannot_exceed_portfolio() -> None:
    allocations = (
        allocation(
            "AAPL",
            current_value="70000",
            current_weight="0.50",
            target_weight="0.50",
            market_price="200",
        ),
        allocation(
            "MSFT",
            current_value="70000",
            current_weight="0.50",
            target_weight="0.50",
            market_price="400",
        ),
    )

    report = build(allocations=allocations)

    assert report.status is RebalancingStatus.FAILED
    assert "must not exceed" in report.error


def test_empty_allocations_return_failed_report() -> None:
    report = build(allocations=())

    assert report.status is RebalancingStatus.FAILED
    assert report.error == "allocations must not be empty"


def test_invalid_allocation_returns_failed_report() -> None:
    report = build(
        allocations=(object(),)
    )

    assert report.status is RebalancingStatus.FAILED
    assert (
        report.error
        == "every allocation must be a PortfolioAllocation"
    )


def test_non_iterable_allocations_raise_type_error() -> None:
    with pytest.raises(
        TypeError,
        match="allocations must be iterable",
    ):
        PortfolioRebalancingEngine().build_plan(
            plan_id="plan-001",
            portfolio_value=Decimal("100000"),
            available_cash=Decimal("0"),
            allocations=None,
        )


def test_portfolio_value_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="portfolio_value must be a Decimal",
    ):
        PortfolioRebalancingEngine().build_plan(
            plan_id="plan-001",
            portfolio_value=100000,
            available_cash=Decimal("0"),
            allocations=balanced_allocations(),
        )


def test_portfolio_value_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "portfolio_value must be greater than zero"
        ),
    ):
        PortfolioRebalancingEngine().build_plan(
            plan_id="plan-001",
            portfolio_value=Decimal("0"),
            available_cash=Decimal("0"),
            allocations=balanced_allocations(),
        )


def test_available_cash_cannot_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="available_cash must not be negative",
    ):
        PortfolioRebalancingEngine().build_plan(
            plan_id="plan-001",
            portfolio_value=Decimal("100000"),
            available_cash=Decimal("-1"),
            allocations=balanced_allocations(),
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "drift_threshold",
        "maximum_turnover",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_normalized_configuration_must_be_valid(
    field_name: str,
    value: Decimal,
) -> None:
    arguments = {
        "plan_id": "plan-001",
        "portfolio_value": Decimal("100000"),
        "available_cash": Decimal("0"),
        "allocations": balanced_allocations(),
        "drift_threshold": Decimal("0.02"),
        "minimum_trade_value": Decimal("100"),
        "maximum_turnover": Decimal("0.30"),
    }
    arguments[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be between 0 and 1",
    ):
        PortfolioRebalancingEngine().build_plan(
            **arguments
        )


def test_minimum_trade_value_cannot_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "minimum_trade_value must not be negative"
        ),
    ):
        PortfolioRebalancingEngine().build_plan(
            plan_id="plan-001",
            portfolio_value=Decimal("100000"),
            available_cash=Decimal("0"),
            allocations=balanced_allocations(),
            minimum_trade_value=Decimal("-1"),
        )