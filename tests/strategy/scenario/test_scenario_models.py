from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.strategy.scenario.scenario_models import (
    PortfolioScenarioReport,
    ScenarioAnalysisStatus,
    ScenarioDefinition,
    ScenarioResult,
    ScenarioType,
)


def scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        scenario_id="bull-001",
        name="Bull market",
        scenario_type=ScenarioType.BULL_MARKET,
        expected_return=Decimal("0.15"),
        expected_volatility=Decimal("0.12"),
        probability_weight=Decimal("0.40"),
        description="Strong economic expansion.",
    )


def result() -> ScenarioResult:
    return ScenarioResult(
        scenario=scenario(),
        initial_equity=Decimal("100000"),
        projected_equity=Decimal("115000"),
        projected_return=Decimal("0.15"),
        projected_drawdown=Decimal("0.05"),
        risk_score=Decimal("0.20"),
        passed=True,
    )


def test_scenario_definition() -> None:
    value = scenario()

    assert value.scenario_id == "bull-001"
    assert value.scenario_type is ScenarioType.BULL_MARKET
    assert value.expected_return == Decimal("0.15")


def test_scenario_text_is_normalized() -> None:
    value = ScenarioDefinition(
        scenario_id="  bull-001  ",
        name="  Bull market  ",
        scenario_type=ScenarioType.BULL_MARKET,
        expected_return=Decimal("0.15"),
        expected_volatility=Decimal("0.12"),
        probability_weight=Decimal("0.40"),
        description="  Expansion scenario.  ",
    )

    assert value.scenario_id == "bull-001"
    assert value.name == "Bull market"
    assert value.description == "Expansion scenario."


def test_scenario_id_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="scenario_id must not be empty",
    ):
        ScenarioDefinition(
            scenario_id="   ",
            name="Bull market",
            scenario_type=ScenarioType.BULL_MARKET,
            expected_return=Decimal("0.15"),
            expected_volatility=Decimal("0.12"),
            probability_weight=Decimal("0.40"),
        )


def test_name_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="name must not be empty",
    ):
        ScenarioDefinition(
            scenario_id="bull-001",
            name="   ",
            scenario_type=ScenarioType.BULL_MARKET,
            expected_return=Decimal("0.15"),
            expected_volatility=Decimal("0.12"),
            probability_weight=Decimal("0.40"),
        )


def test_expected_return_cannot_be_less_than_negative_one() -> None:
    with pytest.raises(
        ValueError,
        match="expected_return must not be less than -1",
    ):
        ScenarioDefinition(
            scenario_id="bear-001",
            name="Bear market",
            scenario_type=ScenarioType.BEAR_MARKET,
            expected_return=Decimal("-1.01"),
            expected_volatility=Decimal("0.30"),
            probability_weight=Decimal("0.20"),
        )


def test_expected_volatility_cannot_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="expected_volatility must not be negative",
    ):
        ScenarioDefinition(
            scenario_id="vol-001",
            name="Volatility",
            scenario_type=ScenarioType.HIGH_VOLATILITY,
            expected_return=Decimal("0"),
            expected_volatility=Decimal("-0.01"),
            probability_weight=Decimal("0.20"),
        )


@pytest.mark.parametrize(
    "weight",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_probability_weight_must_be_valid(
    weight: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="probability_weight must be between 0 and 1",
    ):
        ScenarioDefinition(
            scenario_id="custom-001",
            name="Custom",
            scenario_type=ScenarioType.CUSTOM,
            expected_return=Decimal("0"),
            expected_volatility=Decimal("0.10"),
            probability_weight=weight,
        )


def test_scenario_result() -> None:
    value = result()

    assert value.projected_equity == Decimal("115000")
    assert value.projected_return == Decimal("0.15")
    assert value.passed is True


def test_initial_equity_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="initial_equity must be greater than zero",
    ):
        ScenarioResult(
            scenario=scenario(),
            initial_equity=Decimal("0"),
            projected_equity=Decimal("0"),
            projected_return=Decimal("0"),
            projected_drawdown=Decimal("0"),
            risk_score=Decimal("0"),
            passed=False,
        )


@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_projected_drawdown_must_be_valid(
    value: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="projected_drawdown must be between 0 and 1",
    ):
        ScenarioResult(
            scenario=scenario(),
            initial_equity=Decimal("100000"),
            projected_equity=Decimal("90000"),
            projected_return=Decimal("-0.10"),
            projected_drawdown=value,
            risk_score=Decimal("0.50"),
            passed=False,
        )


@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_risk_score_must_be_valid(
    value: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="risk_score must be between 0 and 1",
    ):
        ScenarioResult(
            scenario=scenario(),
            initial_equity=Decimal("100000"),
            projected_equity=Decimal("90000"),
            projected_return=Decimal("-0.10"),
            projected_drawdown=Decimal("0.10"),
            risk_score=value,
            passed=False,
        )


def test_result_warnings_are_normalized() -> None:
    value = ScenarioResult(
        scenario=scenario(),
        initial_equity=Decimal("100000"),
        projected_equity=Decimal("115000"),
        projected_return=Decimal("0.15"),
        projected_drawdown=Decimal("0.05"),
        risk_score=Decimal("0.20"),
        passed=True,
        warnings=["Scenario warning."],
    )

    assert value.warnings == ("Scenario warning.",)


def test_report_normalizes_collections() -> None:
    report = PortfolioScenarioReport(
        status=ScenarioAnalysisStatus.COMPLETED,
        results=[result()],
        weighted_return=Decimal("0.15"),
        weighted_drawdown=Decimal("0.05"),
        weighted_risk_score=Decimal("0.20"),
        best_scenario_id="  bull-001  ",
        worst_scenario_id="  bear-001  ",
        recommendation="  APPROVE  ",
        warnings=["Portfolio warning."],
    )

    assert report.results == (result(),)
    assert report.best_scenario_id == "bull-001"
    assert report.worst_scenario_id == "bear-001"
    assert report.recommendation == "APPROVE"
    assert report.warnings == ("Portfolio warning.",)


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        PortfolioScenarioReport(
            status=ScenarioAnalysisStatus.FAILED,
        )


def test_completed_report_cannot_include_error() -> None:
    with pytest.raises(
        ValueError,
        match="only failed reports may include an error",
    ):
        PortfolioScenarioReport(
            status=ScenarioAnalysisStatus.COMPLETED,
            error="Unexpected failure.",
        )


@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_weighted_drawdown_must_be_valid(
    value: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="weighted_drawdown must be between 0 and 1",
    ):
        PortfolioScenarioReport(
            status=ScenarioAnalysisStatus.COMPLETED,
            weighted_drawdown=value,
        )


@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_weighted_risk_score_must_be_valid(
    value: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="weighted_risk_score must be between 0 and 1",
    ):
        PortfolioScenarioReport(
            status=ScenarioAnalysisStatus.COMPLETED,
            weighted_risk_score=value,
        )


def test_models_are_immutable() -> None:
    value = scenario()

    with pytest.raises(FrozenInstanceError):
        value.name = "Changed"