from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.strategy.rebalancing.rebalancing_models import (
    PortfolioAllocation,
    RebalanceInstruction,
    RebalancePlan,
    RebalanceSide,
    RebalancingDecision,
    RebalancingReport,
    RebalancingStatus,
)


def allocation(
    symbol: str = "AAPL",
    *,
    current_value: str = "40000",
    current_weight: str = "0.40",
    target_weight: str = "0.50",
    market_price: str | None = "200",
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
        asset_class="Equity",
        sector="Technology",
    )


def buy_instruction() -> RebalanceInstruction:
    return RebalanceInstruction(
        instruction_id="instruction-aapl",
        symbol="AAPL",
        side=RebalanceSide.BUY,
        current_weight=Decimal("0.40"),
        target_weight=Decimal("0.50"),
        drift=Decimal("0.10"),
        quantity=Decimal("50"),
        estimated_price=Decimal("200"),
        estimated_trade_value=Decimal("10000"),
        priority=1,
        reason="Increase AAPL to target allocation.",
    )


def sell_instruction() -> RebalanceInstruction:
    return RebalanceInstruction(
        instruction_id="instruction-msft",
        symbol="MSFT",
        side=RebalanceSide.SELL,
        current_weight=Decimal("0.60"),
        target_weight=Decimal("0.50"),
        drift=Decimal("-0.10"),
        quantity=Decimal("25"),
        estimated_price=Decimal("400"),
        estimated_trade_value=Decimal("10000"),
        priority=0,
        reason="Reduce MSFT to target allocation.",
    )


def rebalance_plan() -> RebalancePlan:
    allocations = (
        allocation(),
        allocation(
            "MSFT",
            current_value="60000",
            current_weight="0.60",
            target_weight="0.50",
            market_price="400",
        ),
    )

    instructions = (
        sell_instruction(),
        buy_instruction(),
    )

    return RebalancePlan(
        plan_id="rebalance-001",
        portfolio_value=Decimal("100000"),
        available_cash=Decimal("5000"),
        allocations=allocations,
        instructions=instructions,
        total_buy_value=Decimal("10000"),
        total_sell_value=Decimal("10000"),
        projected_cash=Decimal("5000"),
        turnover_ratio=Decimal("0.20"),
        drift_threshold=Decimal("0.02"),
        minimum_trade_value=Decimal("500"),
        maximum_turnover=Decimal("0.30"),
    )


def test_portfolio_allocation() -> None:
    value = allocation()

    assert value.symbol == "AAPL"
    assert value.current_weight == Decimal("0.40")
    assert value.target_weight == Decimal("0.50")
    assert value.drift == Decimal("0.10")


def test_allocation_text_is_normalized() -> None:
    value = PortfolioAllocation(
        symbol="  aapl  ",
        current_value=Decimal("40000"),
        current_weight=Decimal("0.40"),
        target_weight=Decimal("0.50"),
        asset_class="  Equity  ",
        sector="  Technology  ",
    )

    assert value.symbol == "AAPL"
    assert value.asset_class == "Equity"
    assert value.sector == "Technology"


def test_allocation_symbol_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="symbol must not be empty",
    ):
        allocation("   ")


@pytest.mark.parametrize(
    "field_name",
    [
        "current_weight",
        "target_weight",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_allocation_weights_must_be_valid(
    field_name: str,
    value: Decimal,
) -> None:
    arguments = {
        "symbol": "AAPL",
        "current_value": Decimal("40000"),
        "current_weight": Decimal("0.40"),
        "target_weight": Decimal("0.50"),
    }
    arguments[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be between 0 and 1",
    ):
        PortfolioAllocation(**arguments)


def test_market_price_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="market_price must be greater than zero",
    ):
        allocation(
            market_price="0"
        )


def test_allocation_warnings_are_tuples() -> None:
    value = PortfolioAllocation(
        symbol="AAPL",
        current_value=Decimal("40000"),
        current_weight=Decimal("0.40"),
        target_weight=Decimal("0.50"),
        warnings=["Allocation warning."],
    )

    assert value.warnings == (
        "Allocation warning.",
    )


def test_buy_instruction() -> None:
    value = buy_instruction()

    assert value.side is RebalanceSide.BUY
    assert value.quantity == Decimal("50")
    assert value.estimated_trade_value == Decimal("10000")


def test_sell_instruction() -> None:
    value = sell_instruction()

    assert value.side is RebalanceSide.SELL
    assert value.drift == Decimal("-0.10")


def test_instruction_text_is_normalized() -> None:
    value = RebalanceInstruction(
        instruction_id="  instruction-aapl  ",
        symbol="  aapl  ",
        side=RebalanceSide.BUY,
        current_weight=Decimal("0.40"),
        target_weight=Decimal("0.50"),
        drift=Decimal("0.10"),
        quantity=Decimal("50"),
        estimated_price=Decimal("200"),
        estimated_trade_value=Decimal("10000"),
        reason="  Increase allocation.  ",
    )

    assert value.instruction_id == "instruction-aapl"
    assert value.symbol == "AAPL"
    assert value.reason == "Increase allocation."


def test_instruction_drift_must_match_weights() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "drift must equal target_weight minus current_weight"
        ),
    ):
        RebalanceInstruction(
            instruction_id="instruction-aapl",
            symbol="AAPL",
            side=RebalanceSide.BUY,
            current_weight=Decimal("0.40"),
            target_weight=Decimal("0.50"),
            drift=Decimal("0.05"),
            quantity=Decimal("50"),
            estimated_price=Decimal("200"),
            estimated_trade_value=Decimal("10000"),
            reason="Increase allocation.",
        )


def test_buy_requires_positive_drift() -> None:
    with pytest.raises(
        ValueError,
        match="buy instructions require positive drift",
    ):
        RebalanceInstruction(
            instruction_id="instruction-aapl",
            symbol="AAPL",
            side=RebalanceSide.BUY,
            current_weight=Decimal("0.50"),
            target_weight=Decimal("0.40"),
            drift=Decimal("-0.10"),
            quantity=Decimal("50"),
            estimated_price=Decimal("200"),
            estimated_trade_value=Decimal("10000"),
            reason="Invalid buy.",
        )


def test_sell_requires_negative_drift() -> None:
    with pytest.raises(
        ValueError,
        match="sell instructions require negative drift",
    ):
        RebalanceInstruction(
            instruction_id="instruction-msft",
            symbol="MSFT",
            side=RebalanceSide.SELL,
            current_weight=Decimal("0.40"),
            target_weight=Decimal("0.50"),
            drift=Decimal("0.10"),
            quantity=Decimal("25"),
            estimated_price=Decimal("400"),
            estimated_trade_value=Decimal("10000"),
            reason="Invalid sell.",
        )


def test_trade_value_must_match_quantity_and_price() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "estimated_trade_value must equal quantity "
            "times estimated_price"
        ),
    ):
        RebalanceInstruction(
            instruction_id="instruction-aapl",
            symbol="AAPL",
            side=RebalanceSide.BUY,
            current_weight=Decimal("0.40"),
            target_weight=Decimal("0.50"),
            drift=Decimal("0.10"),
            quantity=Decimal("50"),
            estimated_price=Decimal("200"),
            estimated_trade_value=Decimal("9000"),
            reason="Increase allocation.",
        )


def test_hold_instruction_requires_zero_quantity() -> None:
    with pytest.raises(
        ValueError,
        match="hold instructions must have zero quantity",
    ):
        RebalanceInstruction(
            instruction_id="instruction-aapl",
            symbol="AAPL",
            side=RebalanceSide.HOLD,
            current_weight=Decimal("0.50"),
            target_weight=Decimal("0.50"),
            drift=Decimal("0"),
            quantity=Decimal("1"),
            estimated_price=None,
            estimated_trade_value=Decimal("0"),
            reason="Hold allocation.",
        )


def test_rebalance_plan() -> None:
    value = rebalance_plan()

    assert value.plan_id == "rebalance-001"
    assert len(value.allocations) == 2
    assert len(value.instructions) == 2
    assert value.projected_cash == Decimal("5000")


def test_plan_collections_are_tuples() -> None:
    value = rebalance_plan()

    assert isinstance(value.allocations, tuple)
    assert isinstance(value.instructions, tuple)


def test_allocation_symbols_must_be_unique() -> None:
    duplicate = allocation()

    with pytest.raises(
        ValueError,
        match="allocation symbols must be unique",
    ):
        RebalancePlan(
            plan_id="rebalance-001",
            portfolio_value=Decimal("100000"),
            available_cash=Decimal("0"),
            allocations=(duplicate, duplicate),
            instructions=(),
            total_buy_value=Decimal("0"),
            total_sell_value=Decimal("0"),
            projected_cash=Decimal("0"),
            turnover_ratio=Decimal("0"),
            drift_threshold=Decimal("0.02"),
            minimum_trade_value=Decimal("500"),
            maximum_turnover=Decimal("0.30"),
        )


def test_target_weights_must_sum_to_one() -> None:
    with pytest.raises(
        ValueError,
        match="target allocation weights must sum to 1",
    ):
        RebalancePlan(
            plan_id="rebalance-001",
            portfolio_value=Decimal("100000"),
            available_cash=Decimal("0"),
            allocations=(
                allocation(
                    target_weight="0.40"
                ),
                allocation(
                    "MSFT",
                    current_weight="0.60",
                    target_weight="0.40",
                ),
            ),
            instructions=(),
            total_buy_value=Decimal("0"),
            total_sell_value=Decimal("0"),
            projected_cash=Decimal("0"),
            turnover_ratio=Decimal("0"),
            drift_threshold=Decimal("0.02"),
            minimum_trade_value=Decimal("500"),
            maximum_turnover=Decimal("0.30"),
        )


def test_instruction_must_reference_allocation() -> None:
    unknown_instruction = RebalanceInstruction(
        instruction_id="instruction-nvda",
        symbol="NVDA",
        side=RebalanceSide.HOLD,
        current_weight=Decimal("0"),
        target_weight=Decimal("0"),
        drift=Decimal("0"),
        quantity=Decimal("0"),
        estimated_price=None,
        estimated_trade_value=Decimal("0"),
        reason="No action.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "every instruction must reference an allocation"
        ),
    ):
        RebalancePlan(
            plan_id="rebalance-001",
            portfolio_value=Decimal("100000"),
            available_cash=Decimal("0"),
            allocations=(
                allocation(),
                allocation(
                    "MSFT",
                    current_weight="0.60",
                    target_weight="0.50",
                ),
            ),
            instructions=(unknown_instruction,),
            total_buy_value=Decimal("0"),
            total_sell_value=Decimal("0"),
            projected_cash=Decimal("0"),
            turnover_ratio=Decimal("0"),
            drift_threshold=Decimal("0.02"),
            minimum_trade_value=Decimal("500"),
            maximum_turnover=Decimal("0.30"),
        )


def test_projected_cash_must_match_plan_values() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "projected_cash must equal available_cash plus "
            "sells minus buys"
        ),
    ):
        RebalancePlan(
            plan_id="rebalance-001",
            portfolio_value=Decimal("100000"),
            available_cash=Decimal("5000"),
            allocations=rebalance_plan().allocations,
            instructions=rebalance_plan().instructions,
            total_buy_value=Decimal("10000"),
            total_sell_value=Decimal("10000"),
            projected_cash=Decimal("4000"),
            turnover_ratio=Decimal("0.20"),
            drift_threshold=Decimal("0.02"),
            minimum_trade_value=Decimal("500"),
            maximum_turnover=Decimal("0.30"),
        )


def test_turnover_ratio_must_match_trade_values() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "turnover_ratio must equal total trade value "
            "divided by portfolio_value"
        ),
    ):
        RebalancePlan(
            plan_id="rebalance-001",
            portfolio_value=Decimal("100000"),
            available_cash=Decimal("5000"),
            allocations=rebalance_plan().allocations,
            instructions=rebalance_plan().instructions,
            total_buy_value=Decimal("10000"),
            total_sell_value=Decimal("10000"),
            projected_cash=Decimal("5000"),
            turnover_ratio=Decimal("0.10"),
            drift_threshold=Decimal("0.02"),
            minimum_trade_value=Decimal("500"),
            maximum_turnover=Decimal("0.30"),
        )


def test_rebalancing_report() -> None:
    value = RebalancingReport(
        status=RebalancingStatus.COMPLETED,
        decision=RebalancingDecision.APPROVE,
        plan=rebalance_plan(),
        recommendation="Execute the approved rebalance plan.",
    )

    assert value.status is RebalancingStatus.COMPLETED
    assert value.decision is RebalancingDecision.APPROVE
    assert value.plan == rebalance_plan()


def test_completed_report_requires_plan() -> None:
    with pytest.raises(
        ValueError,
        match="completed reports must include a plan",
    ):
        RebalancingReport(
            status=RebalancingStatus.COMPLETED,
            decision=RebalancingDecision.REVIEW_REQUIRED,
            plan=None,
            recommendation="Review required.",
        )


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        RebalancingReport(
            status=RebalancingStatus.FAILED,
            decision=RebalancingDecision.REJECT,
            plan=None,
            recommendation="Rebalancing failed.",
        )


def test_completed_report_cannot_include_error() -> None:
    with pytest.raises(
        ValueError,
        match="only failed reports may include an error",
    ):
        RebalancingReport(
            status=RebalancingStatus.COMPLETED,
            decision=RebalancingDecision.APPROVE,
            plan=rebalance_plan(),
            recommendation="Approved.",
            error="Unexpected error.",
        )


def test_report_warnings_are_tuples() -> None:
    value = RebalancingReport(
        status=RebalancingStatus.COMPLETED,
        decision=RebalancingDecision.APPROVE,
        plan=rebalance_plan(),
        recommendation="Approved.",
        warnings=["Turnover warning."],
    )

    assert value.warnings == (
        "Turnover warning.",
    )


def test_models_are_immutable() -> None:
    value = allocation()

    with pytest.raises(FrozenInstanceError):
        value.symbol = "MSFT"