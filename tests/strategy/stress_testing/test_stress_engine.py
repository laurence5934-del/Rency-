from decimal import Decimal

import pytest

from app.strategy.stress_testing.stress_engine import (
    StressTestEngine,
)
from app.strategy.stress_testing.stress_models import (
    StressScenario,
    StressScenarioType,
    StressTestStatus,
)


def scenario(
    scenario_id: str,
    *,
    market_return_shock: str = "0",
    volatility_multiplier: str = "1",
    liquidity_haircut: str = "0",
) -> StressScenario:
    return StressScenario(
        scenario_id=scenario_id,
        name=scenario_id,
        scenario_type=StressScenarioType.CUSTOM,
        market_return_shock=Decimal(
            market_return_shock
        ),
        volatility_multiplier=Decimal(
            volatility_multiplier
        ),
        liquidity_haircut=Decimal(
            liquidity_haircut
        ),
    )


def test_run_completes_all_scenarios() -> None:
    report = StressTestEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "crash",
                market_return_shock="-0.20",
            ),
            scenario(
                "liquidity",
                liquidity_haircut="0.10",
            ),
        ),
    )

    assert report.status is StressTestStatus.COMPLETED
    assert len(report.results) == 2
    assert report.error is None


def test_market_shock_reduces_equity() -> None:
    report = StressTestEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "crash",
                market_return_shock="-0.20",
            ),
        ),
    )

    result = report.results[0]

    assert result.stressed_equity == Decimal("80000.00")
    assert result.loss_amount == Decimal("20000.00")
    assert result.loss_percent == Decimal("0.20")


def test_liquidity_haircut_reduces_equity() -> None:
    report = StressTestEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "liquidity",
                liquidity_haircut="0.10",
            ),
        ),
    )

    result = report.results[0]

    assert result.stressed_equity == Decimal("90000.00")
    assert result.loss_percent == Decimal("0.10")


def test_combined_shock_is_compounded() -> None:
    report = StressTestEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "combined",
                market_return_shock="-0.20",
                liquidity_haircut="0.10",
            ),
        ),
    )

    result = report.results[0]

    assert result.stressed_equity == Decimal("72000.000")
    assert result.loss_percent == Decimal("0.28")


def test_positive_market_shock_does_not_create_loss() -> None:
    report = StressTestEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "rally",
                market_return_shock="0.10",
            ),
        ),
    )

    result = report.results[0]

    assert result.stressed_equity == Decimal("110000.00")
    assert result.loss_amount == Decimal("0")
    assert result.loss_percent == Decimal("0")


def test_loss_limit_breach_is_detected() -> None:
    report = StressTestEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "crash",
                market_return_shock="-0.25",
            ),
        ),
        loss_limit=Decimal("0.20"),
    )

    result = report.results[0]

    assert result.breached_limit is True
    assert report.breach_count == 1


def test_loss_equal_to_limit_is_a_breach() -> None:
    report = StressTestEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "crash",
                market_return_shock="-0.20",
            ),
        ),
        loss_limit=Decimal("0.20"),
    )

    assert report.results[0].breached_limit is True


def test_worst_case_loss_is_calculated() -> None:
    report = StressTestEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "mild",
                market_return_shock="-0.10",
            ),
            scenario(
                "severe",
                market_return_shock="-0.35",
            ),
        ),
    )

    assert (
        report.worst_case_loss_percent
        == Decimal("0.35")
    )


def test_average_loss_is_calculated() -> None:
    report = StressTestEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "one",
                market_return_shock="-0.10",
            ),
            scenario(
                "two",
                market_return_shock="-0.30",
            ),
        ),
    )

    assert (
        report.average_loss_percent
        == Decimal("0.20")
    )


def test_elevated_volatility_adds_warning() -> None:
    report = StressTestEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "volatility",
                volatility_multiplier="2",
            ),
        ),
    )

    assert report.results[0].warnings == (
        "volatility includes elevated volatility.",
    )


def test_breach_warning_is_aggregated() -> None:
    report = StressTestEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "crash",
                market_return_shock="-0.30",
            ),
        ),
        loss_limit=Decimal("0.20"),
    )

    assert report.warnings == (
        "crash breached the loss limit.",
    )


def test_empty_scenarios_return_completed_report() -> None:
    report = StressTestEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(),
    )

    assert report.status is StressTestStatus.COMPLETED
    assert report.results == ()
    assert report.worst_case_loss_percent == Decimal(
        "0"
    )
    assert report.average_loss_percent == Decimal(
        "0"
    )
    assert report.breach_count == 0
    assert report.warnings == (
        "No stress scenarios were supplied.",
    )


def test_invalid_scenario_returns_failed_report() -> None:
    report = StressTestEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "valid",
                market_return_shock="-0.10",
            ),
            object(),
        ),
    )

    assert report.status is StressTestStatus.FAILED
    assert len(report.results) == 1
    assert (
        report.error
        == "every scenario must be a StressScenario"
    )


@pytest.mark.parametrize(
    "initial_equity",
    [
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_initial_equity_must_be_positive(
    initial_equity: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be greater than zero",
    ):
        StressTestEngine().run(
            initial_equity=initial_equity,
            scenarios=(),
        )


def test_initial_equity_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="initial_equity must be a Decimal",
    ):
        StressTestEngine().run(
            initial_equity=100000,
            scenarios=(),
        )


@pytest.mark.parametrize(
    "loss_limit",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_loss_limit_must_be_valid(
    loss_limit: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="loss_limit must be between 0 and 1",
    ):
        StressTestEngine().run(
            initial_equity=Decimal("100000"),
            scenarios=(),
            loss_limit=loss_limit,
        )


def test_loss_limit_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="loss_limit must be a Decimal",
    ):
        StressTestEngine().run(
            initial_equity=Decimal("100000"),
            scenarios=(),
            loss_limit=0.20,
        )