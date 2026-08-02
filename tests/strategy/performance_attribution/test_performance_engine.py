from decimal import Decimal

import pytest

from app.strategy.performance_attribution.performance_engine import (
    PerformanceAttributionEngine,
    PerformanceObservation,
)
from app.strategy.performance_attribution.performance_models import (
    ContributionType,
    PerformanceAttributionStatus,
)


def observation(
    observation_id: str,
    contributor_id: str,
    *,
    contribution_type: ContributionType = (
        ContributionType.STRATEGY
    ),
    weight: str = "0.50",
    return_rate: str = "0.10",
    profit_loss: str = "5000",
    risk_contribution: str = "0.20",
    warnings=(),
) -> PerformanceObservation:
    return PerformanceObservation(
        observation_id=observation_id,
        contributor_id=contributor_id,
        contributor_name=contributor_id,
        contribution_type=contribution_type,
        capital_weight=Decimal(weight),
        return_rate=Decimal(return_rate),
        profit_loss=Decimal(profit_loss),
        risk_contribution=Decimal(
            risk_contribution
        ),
        warnings=tuple(warnings),
    )


def test_observation_text_is_normalized() -> None:
    value = PerformanceObservation(
        observation_id="  obs-001  ",
        contributor_id="  alpha  ",
        contributor_name="  Strategy Alpha  ",
        contribution_type=ContributionType.STRATEGY,
        capital_weight=Decimal("0.50"),
        return_rate=Decimal("0.10"),
        profit_loss=Decimal("5000"),
    )

    assert value.observation_id == "obs-001"
    assert value.contributor_id == "alpha"
    assert value.contributor_name == "Strategy Alpha"


def test_observation_weight_must_be_valid() -> None:
    with pytest.raises(
        ValueError,
        match="capital_weight must be between 0 and 1",
    ):
        observation(
            "obs-001",
            "alpha",
            weight="1.01",
        )


def test_analyze_completed_report() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("110000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="6000",
            ),
            observation(
                "obs-002",
                "beta",
                profit_loss="4000",
            ),
        ),
    )

    assert (
        report.status
        is PerformanceAttributionStatus.COMPLETED
    )
    assert report.net_profit_loss == Decimal("10000")
    assert report.total_return == Decimal("0.10")
    assert len(report.contributions) == 2
    assert report.error is None


def test_groups_observations_by_contributor() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("110000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                weight="0.30",
                return_rate="0.10",
                profit_loss="3000",
            ),
            observation(
                "obs-002",
                "alpha",
                weight="0.20",
                return_rate="0.15",
                profit_loss="2000",
            ),
            observation(
                "obs-003",
                "beta",
                weight="0.50",
                profit_loss="5000",
            ),
        ),
    )

    alpha = next(
        item
        for item in report.contributions
        if item.contributor_id == "alpha"
    )

    assert alpha.weight == Decimal("0.50")
    assert alpha.profit_loss == Decimal("5000")
    assert alpha.contribution_return == Decimal(
        "0.05"
    )
    assert alpha.observations == 2


def test_grouped_return_rate_is_weighted() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("105000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                weight="0.25",
                return_rate="0.10",
                profit_loss="2500",
            ),
            observation(
                "obs-002",
                "alpha",
                weight="0.75",
                return_rate="0.20",
                profit_loss="2500",
            ),
        ),
    )

    contribution = report.contributions[0]

    expected = (
        Decimal("0.10") * Decimal("0.25")
        + Decimal("0.20") * Decimal("0.75")
    )

    assert contribution.return_rate == expected


def test_risk_contribution_is_capped_at_one() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("110000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="5000",
                risk_contribution="0.70",
            ),
            observation(
                "obs-002",
                "alpha",
                profit_loss="5000",
                risk_contribution="0.60",
            ),
        ),
    )

    assert (
        report.contributions[0].risk_contribution
        == Decimal("1")
    )


def test_creates_summary_per_contribution_type() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("110000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                contribution_type=(
                    ContributionType.STRATEGY
                ),
                profit_loss="6000",
            ),
            observation(
                "obs-002",
                "AAPL",
                contribution_type=ContributionType.SYMBOL,
                profit_loss="4000",
            ),
        ),
    )

    assert len(report.summaries) == 2

    assert {
        summary.contribution_type
        for summary in report.summaries
    } == {
        ContributionType.STRATEGY,
        ContributionType.SYMBOL,
    }


def test_summary_totals_are_calculated() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("110000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="6000",
                risk_contribution="0.20",
            ),
            observation(
                "obs-002",
                "beta",
                profit_loss="4000",
                risk_contribution="0.30",
            ),
        ),
    )

    summary = report.summaries[0]

    assert (
        summary.total_return_contribution
        == Decimal("0.10")
    )
    assert summary.total_profit_loss == Decimal(
        "10000"
    )
    assert (
        summary.total_risk_contribution
        == Decimal("0.50")
    )


def test_identifies_top_contributor() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("110000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="8000",
            ),
            observation(
                "obs-002",
                "beta",
                profit_loss="2000",
            ),
        ),
    )

    assert report.top_contributor_id == "alpha"


def test_identifies_bottom_contributor() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("105000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="7000",
            ),
            observation(
                "obs-002",
                "beta",
                profit_loss="-2000",
                return_rate="-0.04",
            ),
        ),
    )

    assert report.bottom_contributor_id == "beta"


def test_empty_observations_are_supported() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("100000"),
        observations=(),
    )

    assert (
        report.status
        is PerformanceAttributionStatus.COMPLETED
    )
    assert report.contributions == ()
    assert report.summaries == ()
    assert report.top_contributor_id is None
    assert report.bottom_contributor_id is None
    assert report.concentration_score == Decimal("0")


def test_concentration_score() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("110000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="8000",
            ),
            observation(
                "obs-002",
                "beta",
                profit_loss="2000",
            ),
        ),
    )

    assert (
        report.concentration_score
        == Decimal("0.8")
    )


def test_zero_contributions_have_zero_concentration() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("100000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="0",
                return_rate="0",
            ),
        ),
    )

    assert report.concentration_score == Decimal("0")


def test_positive_return_without_risk_scores_one() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("110000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="10000",
                risk_contribution="0",
            ),
        ),
    )

    assert report.risk_adjusted_score == Decimal("1")


def test_negative_return_has_zero_risk_adjusted_score() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("90000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="-10000",
                return_rate="-0.10",
                risk_contribution="0.20",
            ),
        ),
    )

    assert report.risk_adjusted_score == Decimal("0")


def test_risk_adjusted_score_is_calculated() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("110000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="10000",
                risk_contribution="0.50",
            ),
        ),
    )

    assert (
        report.risk_adjusted_score
        == Decimal("0.2")
    )


def test_concentration_warning() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("110000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="9000",
            ),
            observation(
                "obs-002",
                "beta",
                profit_loss="1000",
            ),
        ),
    )

    assert (
        "Portfolio performance is highly concentrated."
        in report.warnings
    )


def test_negative_contributor_warning() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("105000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="7000",
            ),
            observation(
                "obs-002",
                "beta",
                profit_loss="-2000",
                return_rate="-0.04",
            ),
        ),
    )

    assert (
        "1 contributors produced negative performance."
        in report.warnings
    )


def test_observation_warnings_are_aggregated() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("105000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="5000",
                warnings=("Input warning.",),
            ),
        ),
    )

    assert "Input warning." in report.warnings


def test_negative_return_recommendation() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("90000"),
        observations=(),
    )

    assert "Review losing contributors" in (
        report.recommendation
    )


def test_high_concentration_recommendation() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("110000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="9000",
            ),
            observation(
                "obs-002",
                "beta",
                profit_loss="1000",
            ),
        ),
    )

    assert "Reduce contributor concentration" in (
        report.recommendation
    )


def test_high_risk_adjusted_recommendation() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("110000"),
        observations=(
            observation(
                "obs-001",
                "alpha",
                profit_loss="5000",
                risk_contribution="0.05",
            ),
            observation(
                "obs-002",
                "beta",
                profit_loss="5000",
                risk_contribution="0.05",
            ),
        ),
    )

    assert "Maintain the current allocation" in (
        report.recommendation
    )


def test_duplicate_observation_ids_return_failed_report() -> None:
    duplicate = observation(
        "duplicate",
        "alpha",
    )

    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("110000"),
        observations=(
            duplicate,
            duplicate,
        ),
    )

    assert (
        report.status
        is PerformanceAttributionStatus.FAILED
    )
    assert (
        report.error
        == "observation_id values must be unique"
    )


def test_invalid_observation_returns_failed_report() -> None:
    report = PerformanceAttributionEngine().analyze(
        initial_value=Decimal("100000"),
        ending_value=Decimal("100000"),
        observations=(object(),),
    )

    assert (
        report.status
        is PerformanceAttributionStatus.FAILED
    )
    assert (
        report.error
        == "every observation must be a "
        "PerformanceObservation"
    )


def test_non_iterable_observations_raise_type_error() -> None:
    with pytest.raises(
        TypeError,
        match="observations must be iterable",
    ):
        PerformanceAttributionEngine().analyze(
            initial_value=Decimal("100000"),
            ending_value=Decimal("100000"),
            observations=None,
        )


def test_initial_value_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="initial_value must be a Decimal",
    ):
        PerformanceAttributionEngine().analyze(
            initial_value=100000,
            ending_value=Decimal("100000"),
            observations=(),
        )


@pytest.mark.parametrize(
    "initial_value",
    [
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_initial_value_must_be_positive(
    initial_value: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="initial_value must be greater than zero",
    ):
        PerformanceAttributionEngine().analyze(
            initial_value=initial_value,
            ending_value=Decimal("100000"),
            observations=(),
        )


def test_ending_value_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="ending_value must be a Decimal",
    ):
        PerformanceAttributionEngine().analyze(
            initial_value=Decimal("100000"),
            ending_value=100000,
            observations=(),
        )


def test_ending_value_cannot_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="ending_value must not be negative",
    ):
        PerformanceAttributionEngine().analyze(
            initial_value=Decimal("100000"),
            ending_value=Decimal("-1"),
            observations=(),
        )