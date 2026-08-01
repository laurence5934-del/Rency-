from decimal import Decimal

import pytest

from app.strategy.scenario.scenario_engine import (
    ScenarioAnalysisEngine,
)
from app.strategy.scenario.scenario_models import (
    ScenarioAnalysisStatus,
    ScenarioDefinition,
    ScenarioType,
)


def scenario(
    scenario_id: str,
    *,
    expected_return: str,
    expected_volatility: str,
    probability_weight: str,
) -> ScenarioDefinition:
    return ScenarioDefinition(
        scenario_id=scenario_id,
        name=scenario_id,
        scenario_type=ScenarioType.CUSTOM,
        expected_return=Decimal(expected_return),
        expected_volatility=Decimal(
            expected_volatility
        ),
        probability_weight=Decimal(
            probability_weight
        ),
    )


def test_run_completes_all_scenarios() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "bull",
                expected_return="0.20",
                expected_volatility="0.10",
                probability_weight="0.60",
            ),
            scenario(
                "bear",
                expected_return="-0.15",
                expected_volatility="0.30",
                probability_weight="0.40",
            ),
        ),
    )

    assert (
        report.status
        is ScenarioAnalysisStatus.COMPLETED
    )
    assert len(report.results) == 2
    assert report.error is None


def test_projected_equity_is_calculated() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "bull",
                expected_return="0.15",
                expected_volatility="0.10",
                probability_weight="1",
            ),
        ),
    )

    result = report.results[0]

    assert (
        result.projected_equity
        == Decimal("115000.00")
    )
    assert (
        result.projected_return
        == Decimal("0.15")
    )


def test_negative_return_reduces_equity() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "bear",
                expected_return="-0.25",
                expected_volatility="0.30",
                probability_weight="1",
            ),
        ),
    )

    result = report.results[0]

    assert (
        result.projected_equity
        == Decimal("75000.00")
    )
    assert (
        result.projected_return
        == Decimal("-0.25")
    )


def test_total_loss_reaches_zero_equity() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "collapse",
                expected_return="-1",
                expected_volatility="1",
                probability_weight="1",
            ),
        ),
    )

    result = report.results[0]

    assert result.projected_equity == Decimal("0")
    assert result.projected_return == Decimal("-1")


def test_projected_drawdown_uses_volatility() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "volatile",
                expected_return="0.05",
                expected_volatility="0.40",
                probability_weight="1",
            ),
        ),
    )

    assert (
        report.results[0].projected_drawdown
        == Decimal("0.40")
    )


def test_projected_drawdown_is_capped_at_one() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "extreme-volatility",
                expected_return="0",
                expected_volatility="1.50",
                probability_weight="1",
            ),
        ),
    )

    assert (
        report.results[0].projected_drawdown
        == Decimal("1")
    )


def test_risk_score_uses_volatility() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "risk",
                expected_return="0",
                expected_volatility="0.35",
                probability_weight="1",
            ),
        ),
    )

    assert (
        report.results[0].risk_score
        == Decimal("0.35")
    )


def test_risk_score_is_capped_at_one() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "extreme-risk",
                expected_return="0",
                expected_volatility="2",
                probability_weight="1",
            ),
        ),
    )

    assert report.results[0].risk_score == Decimal("1")


def test_scenario_passes_within_risk_limit() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "acceptable",
                expected_return="0.10",
                expected_volatility="0.40",
                probability_weight="1",
            ),
        ),
        maximum_risk_score=Decimal("0.50"),
    )

    assert report.results[0].passed is True


def test_scenario_fails_above_risk_limit() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "too-risky",
                expected_return="0.10",
                expected_volatility="0.60",
                probability_weight="1",
            ),
        ),
        maximum_risk_score=Decimal("0.50"),
    )

    assert report.results[0].passed is False


def test_score_equal_to_limit_passes() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "boundary",
                expected_return="0.10",
                expected_volatility="0.50",
                probability_weight="1",
            ),
        ),
        maximum_risk_score=Decimal("0.50"),
    )

    assert report.results[0].passed is True


def test_failed_scenario_adds_warning() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "too-risky",
                expected_return="0.10",
                expected_volatility="0.75",
                probability_weight="1",
            ),
        ),
        maximum_risk_score=Decimal("0.50"),
    )

    assert report.results[0].warnings == (
        "too-risky exceeded risk limit.",
    )


def test_warnings_are_aggregated() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "risk-one",
                expected_return="0",
                expected_volatility="0.70",
                probability_weight="0.50",
            ),
            scenario(
                "risk-two",
                expected_return="0",
                expected_volatility="0.80",
                probability_weight="0.50",
            ),
        ),
        maximum_risk_score=Decimal("0.50"),
    )

    assert report.warnings == (
        "risk-one exceeded risk limit.",
        "risk-two exceeded risk limit.",
    )


def test_weighted_return_is_calculated() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "bull",
                expected_return="0.20",
                expected_volatility="0.10",
                probability_weight="0.75",
            ),
            scenario(
                "bear",
                expected_return="-0.20",
                expected_volatility="0.30",
                probability_weight="0.25",
            ),
        ),
    )

    assert report.weighted_return == Decimal("0.10")


def test_weighted_drawdown_is_calculated() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "low-risk",
                expected_return="0.10",
                expected_volatility="0.10",
                probability_weight="0.75",
            ),
            scenario(
                "high-risk",
                expected_return="-0.10",
                expected_volatility="0.50",
                probability_weight="0.25",
            ),
        ),
    )

    assert (
        report.weighted_drawdown
        == Decimal("0.20")
    )


def test_weighted_risk_is_calculated() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "one",
                expected_return="0",
                expected_volatility="0.20",
                probability_weight="0.50",
            ),
            scenario(
                "two",
                expected_return="0",
                expected_volatility="0.60",
                probability_weight="0.50",
            ),
        ),
    )

    assert (
        report.weighted_risk_score
        == Decimal("0.40")
    )


def test_weights_are_normalized() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "one",
                expected_return="0.20",
                expected_volatility="0.10",
                probability_weight="0.50",
            ),
            scenario(
                "two",
                expected_return="0",
                expected_volatility="0.30",
                probability_weight="0.25",
            ),
        ),
    )

    expected_return = (
        Decimal("0.20")
        * Decimal("0.50")
        / Decimal("0.75")
    )

    assert report.weighted_return == expected_return


def test_zero_total_weight_returns_zero_aggregates() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "one",
                expected_return="0.20",
                expected_volatility="0.10",
                probability_weight="0",
            ),
            scenario(
                "two",
                expected_return="-0.20",
                expected_volatility="0.30",
                probability_weight="0",
            ),
        ),
    )

    assert report.weighted_return == Decimal("0")
    assert report.weighted_drawdown == Decimal("0")
    assert report.weighted_risk_score == Decimal("0")


def test_best_scenario_is_selected() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "middle",
                expected_return="0.10",
                expected_volatility="0.20",
                probability_weight="0.30",
            ),
            scenario(
                "best",
                expected_return="0.25",
                expected_volatility="0.20",
                probability_weight="0.30",
            ),
            scenario(
                "worst",
                expected_return="-0.15",
                expected_volatility="0.20",
                probability_weight="0.40",
            ),
        ),
    )

    assert report.best_scenario_id == "best"


def test_worst_scenario_is_selected() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "middle",
                expected_return="0.10",
                expected_volatility="0.20",
                probability_weight="0.30",
            ),
            scenario(
                "best",
                expected_return="0.25",
                expected_volatility="0.20",
                probability_weight="0.30",
            ),
            scenario(
                "worst",
                expected_return="-0.15",
                expected_volatility="0.20",
                probability_weight="0.40",
            ),
        ),
    )

    assert report.worst_scenario_id == "worst"


def test_approve_recommendation_when_risk_is_acceptable() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "safe",
                expected_return="0.10",
                expected_volatility="0.20",
                probability_weight="1",
            ),
        ),
        maximum_risk_score=Decimal("0.50"),
    )

    assert report.recommendation == "APPROVE"


def test_review_recommendation_when_risk_is_high() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "risky",
                expected_return="0.10",
                expected_volatility="0.70",
                probability_weight="1",
            ),
        ),
        maximum_risk_score=Decimal("0.50"),
    )

    assert report.recommendation == "REVIEW"


def test_empty_scenarios_return_completed_report() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(),
    )

    assert (
        report.status
        is ScenarioAnalysisStatus.COMPLETED
    )
    assert report.results == ()
    assert report.weighted_return == Decimal("0")
    assert report.weighted_drawdown == Decimal("0")
    assert report.weighted_risk_score == Decimal("0")
    assert report.recommendation == "NO_SCENARIOS"
    assert report.warnings == (
        "No scenarios were supplied.",
    )


def test_invalid_scenario_returns_failed_report() -> None:
    report = ScenarioAnalysisEngine().run(
        initial_equity=Decimal("100000"),
        scenarios=(
            scenario(
                "valid",
                expected_return="0.10",
                expected_volatility="0.20",
                probability_weight="1",
            ),
            object(),
        ),
    )

    assert (
        report.status
        is ScenarioAnalysisStatus.FAILED
    )
    assert len(report.results) == 1
    assert report.recommendation == "FAILED"


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
        ScenarioAnalysisEngine().run(
            initial_equity=initial_equity,
            scenarios=(),
        )


def test_initial_equity_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="initial_equity must be a Decimal",
    ):
        ScenarioAnalysisEngine().run(
            initial_equity=100000,
            scenarios=(),
        )


@pytest.mark.parametrize(
    "maximum_risk_score",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_maximum_risk_score_must_be_valid(
    maximum_risk_score: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="maximum_risk_score must be between 0 and 1",
    ):
        ScenarioAnalysisEngine().run(
            initial_equity=Decimal("100000"),
            scenarios=(),
            maximum_risk_score=maximum_risk_score,
        )


def test_maximum_risk_score_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="maximum_risk_score must be a Decimal",
    ):
        ScenarioAnalysisEngine().run(
            initial_equity=Decimal("100000"),
            scenarios=(),
            maximum_risk_score=0.50,
        )