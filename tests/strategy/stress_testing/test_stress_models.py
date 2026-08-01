from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.strategy.stress_testing.stress_models import (
    StressScenario,
    StressScenarioResult,
    StressScenarioType,
    StressTestReport,
    StressTestStatus,
)


def scenario() -> StressScenario:
    return StressScenario(
        scenario_id="crash-001",
        name="Market crash",
        scenario_type=StressScenarioType.MARKET_CRASH,
        market_return_shock=Decimal("-0.20"),
        volatility_multiplier=Decimal("2"),
        liquidity_haircut=Decimal("0.05"),
    )


def scenario_result() -> StressScenarioResult:
    return StressScenarioResult(
        scenario=scenario(),
        initial_equity=Decimal("100000"),
        stressed_equity=Decimal("75000"),
        loss_amount=Decimal("25000"),
        loss_percent=Decimal("0.25"),
        breached_limit=True,
    )


def test_stress_scenario() -> None:
    result = scenario()

    assert result.scenario_id == "crash-001"
    assert result.market_return_shock == Decimal("-0.20")


def test_scenario_text_is_normalized() -> None:
    result = StressScenario(
        scenario_id="  crash-001  ",
        name="  Market crash  ",
        scenario_type=StressScenarioType.MARKET_CRASH,
    )

    assert result.scenario_id == "crash-001"
    assert result.name == "Market crash"


def test_scenario_id_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="scenario_id must not be empty",
    ):
        StressScenario(
            scenario_id="   ",
            name="Crash",
            scenario_type=StressScenarioType.MARKET_CRASH,
        )


def test_name_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="name must not be empty",
    ):
        StressScenario(
            scenario_id="crash",
            name="   ",
            scenario_type=StressScenarioType.MARKET_CRASH,
        )


def test_market_return_cannot_be_less_than_negative_one() -> None:
    with pytest.raises(
        ValueError,
        match="must not be less than -1",
    ):
        StressScenario(
            scenario_id="crash",
            name="Crash",
            scenario_type=StressScenarioType.MARKET_CRASH,
            market_return_shock=Decimal("-1.01"),
        )


def test_volatility_multiplier_cannot_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="must not be negative",
    ):
        StressScenario(
            scenario_id="volatility",
            name="Volatility spike",
            scenario_type=StressScenarioType.VOLATILITY_SPIKE,
            volatility_multiplier=Decimal("-1"),
        )


@pytest.mark.parametrize(
    "haircut",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_liquidity_haircut_must_be_valid(
    haircut: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be between 0 and 1",
    ):
        StressScenario(
            scenario_id="liquidity",
            name="Liquidity shock",
            scenario_type=StressScenarioType.LIQUIDITY_SHOCK,
            liquidity_haircut=haircut,
        )


def test_scenario_result() -> None:
    result = scenario_result()

    assert result.loss_amount == Decimal("25000")
    assert result.loss_percent == Decimal("0.25")
    assert result.breached_limit is True


def test_initial_equity_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="initial_equity must be greater than zero",
    ):
        StressScenarioResult(
            scenario=scenario(),
            initial_equity=Decimal("0"),
            stressed_equity=Decimal("0"),
            loss_amount=Decimal("0"),
            loss_percent=Decimal("0"),
        )


def test_result_warnings_are_normalized() -> None:
    result = StressScenarioResult(
        scenario=scenario(),
        initial_equity=Decimal("100000"),
        stressed_equity=Decimal("90000"),
        loss_amount=Decimal("10000"),
        loss_percent=Decimal("0.10"),
        warnings=["Loss limit approached."],
    )

    assert result.warnings == (
        "Loss limit approached.",
    )


def test_report_normalizes_collections() -> None:
    report = StressTestReport(
        status=StressTestStatus.COMPLETED,
        results=[scenario_result()],
        worst_case_loss_percent=Decimal("0.25"),
        average_loss_percent=Decimal("0.25"),
        breach_count=1,
        warnings=["Stress limit breached."],
    )

    assert report.results == (scenario_result(),)
    assert report.warnings == (
        "Stress limit breached.",
    )


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        StressTestReport(
            status=StressTestStatus.FAILED,
        )


def test_completed_report_cannot_include_error() -> None:
    with pytest.raises(
        ValueError,
        match="only failed reports may include an error",
    ):
        StressTestReport(
            status=StressTestStatus.COMPLETED,
            error="Unexpected failure.",
        )


@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_report_loss_percentages_must_be_valid(
    value: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be between 0 and 1",
    ):
        StressTestReport(
            status=StressTestStatus.COMPLETED,
            worst_case_loss_percent=value,
        )


def test_breach_count_cannot_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="breach_count must not be negative",
    ):
        StressTestReport(
            status=StressTestStatus.COMPLETED,
            breach_count=-1,
        )


def test_models_are_immutable() -> None:
    result = scenario()

    with pytest.raises(FrozenInstanceError):
        result.name = "Changed"