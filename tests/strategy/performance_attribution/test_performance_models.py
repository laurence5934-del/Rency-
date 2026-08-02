from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.strategy.performance_attribution.performance_models import (
    AttributionSummary,
    ContributionType,
    PerformanceAttributionStatus,
    PerformanceContribution,
    PortfolioPerformanceReport,
)


def contribution(
    contributor_id: str = "strategy-alpha",
    *,
    contribution_type: ContributionType = (
        ContributionType.STRATEGY
    ),
    contribution_return: str = "0.06",
    profit_loss: str = "6000",
) -> PerformanceContribution:
    return PerformanceContribution(
        contributor_id=contributor_id,
        name=contributor_id,
        contribution_type=contribution_type,
        weight=Decimal("0.50"),
        return_rate=Decimal("0.12"),
        contribution_return=Decimal(
            contribution_return
        ),
        profit_loss=Decimal(profit_loss),
        risk_contribution=Decimal("0.30"),
        observations=10,
    )


def summary() -> AttributionSummary:
    return AttributionSummary(
        contribution_type=ContributionType.STRATEGY,
        total_return_contribution=Decimal("0.10"),
        total_profit_loss=Decimal("10000"),
        total_risk_contribution=Decimal("0.60"),
        contributor_count=2,
        top_contributor_id="strategy-alpha",
        bottom_contributor_id="strategy-beta",
    )


def report() -> PortfolioPerformanceReport:
    contributions = (
        contribution(),
        contribution(
            "strategy-beta",
            contribution_return="0.04",
            profit_loss="4000",
        ),
    )

    return PortfolioPerformanceReport(
        status=PerformanceAttributionStatus.COMPLETED,
        initial_value=Decimal("100000"),
        ending_value=Decimal("110000"),
        net_profit_loss=Decimal("10000"),
        total_return=Decimal("0.10"),
        contributions=contributions,
        summaries=(summary(),),
        top_contributor_id="strategy-alpha",
        bottom_contributor_id="strategy-beta",
        concentration_score=Decimal("0.52"),
        risk_adjusted_score=Decimal("0.80"),
        recommendation=(
            "Maintain the current allocation while "
            "monitoring concentration."
        ),
    )


def test_performance_contribution() -> None:
    value = contribution()

    assert value.contributor_id == "strategy-alpha"
    assert (
        value.contribution_type
        is ContributionType.STRATEGY
    )
    assert value.profit_loss == Decimal("6000")


def test_contribution_text_is_normalized() -> None:
    value = PerformanceContribution(
        contributor_id="  strategy-alpha  ",
        name="  Strategy Alpha  ",
        contribution_type=ContributionType.STRATEGY,
        weight=Decimal("0.50"),
        return_rate=Decimal("0.12"),
        contribution_return=Decimal("0.06"),
        profit_loss=Decimal("6000"),
    )

    assert value.contributor_id == "strategy-alpha"
    assert value.name == "Strategy Alpha"


@pytest.mark.parametrize(
    ("field_name", "message"),
    [
        (
            "contributor_id",
            "contributor_id must not be empty",
        ),
        (
            "name",
            "name must not be empty",
        ),
    ],
)
def test_contribution_text_fields_must_not_be_empty(
    field_name: str,
    message: str,
) -> None:
    arguments = {
        "contributor_id": "strategy-alpha",
        "name": "Strategy Alpha",
        "contribution_type": ContributionType.STRATEGY,
        "weight": Decimal("0.50"),
        "return_rate": Decimal("0.12"),
        "contribution_return": Decimal("0.06"),
        "profit_loss": Decimal("6000"),
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=message,
    ):
        PerformanceContribution(**arguments)


@pytest.mark.parametrize(
    "weight",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_weight_must_be_valid(
    weight: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="weight must be between 0 and 1",
    ):
        PerformanceContribution(
            contributor_id="strategy-alpha",
            name="Strategy Alpha",
            contribution_type=ContributionType.STRATEGY,
            weight=weight,
            return_rate=Decimal("0.12"),
            contribution_return=Decimal("0.06"),
            profit_loss=Decimal("6000"),
        )


@pytest.mark.parametrize(
    "risk_contribution",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_risk_contribution_must_be_valid(
    risk_contribution: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "risk_contribution must be between 0 and 1"
        ),
    ):
        PerformanceContribution(
            contributor_id="strategy-alpha",
            name="Strategy Alpha",
            contribution_type=ContributionType.STRATEGY,
            weight=Decimal("0.50"),
            return_rate=Decimal("0.12"),
            contribution_return=Decimal("0.06"),
            profit_loss=Decimal("6000"),
            risk_contribution=risk_contribution,
        )


def test_observations_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="observations must not be negative",
    ):
        PerformanceContribution(
            contributor_id="strategy-alpha",
            name="Strategy Alpha",
            contribution_type=ContributionType.STRATEGY,
            weight=Decimal("0.50"),
            return_rate=Decimal("0.12"),
            contribution_return=Decimal("0.06"),
            profit_loss=Decimal("6000"),
            observations=-1,
        )


def test_contribution_warnings_are_tuples() -> None:
    value = PerformanceContribution(
        contributor_id="strategy-alpha",
        name="Strategy Alpha",
        contribution_type=ContributionType.STRATEGY,
        weight=Decimal("0.50"),
        return_rate=Decimal("0.12"),
        contribution_return=Decimal("0.06"),
        profit_loss=Decimal("6000"),
        warnings=["Concentration elevated."],
    )

    assert value.warnings == (
        "Concentration elevated.",
    )


def test_attribution_summary() -> None:
    value = summary()

    assert value.contributor_count == 2
    assert value.top_contributor_id == "strategy-alpha"
    assert value.bottom_contributor_id == "strategy-beta"


def test_summary_identifiers_are_normalized() -> None:
    value = AttributionSummary(
        contribution_type=ContributionType.SYMBOL,
        total_return_contribution=Decimal("0.05"),
        total_profit_loss=Decimal("5000"),
        total_risk_contribution=Decimal("0.40"),
        contributor_count=2,
        top_contributor_id="  NVDA  ",
        bottom_contributor_id="  TSLA  ",
    )

    assert value.top_contributor_id == "NVDA"
    assert value.bottom_contributor_id == "TSLA"


def test_empty_summary_cannot_identify_contributor() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "empty summaries must not identify contributors"
        ),
    ):
        AttributionSummary(
            contribution_type=ContributionType.SYMBOL,
            total_return_contribution=Decimal("0"),
            total_profit_loss=Decimal("0"),
            total_risk_contribution=Decimal("0"),
            contributor_count=0,
            top_contributor_id="NVDA",
        )


def test_portfolio_performance_report() -> None:
    value = report()

    assert (
        value.status
        is PerformanceAttributionStatus.COMPLETED
    )
    assert value.net_profit_loss == Decimal("10000")
    assert value.total_return == Decimal("0.10")
    assert len(value.contributions) == 2


def test_report_collections_are_tuples() -> None:
    value = PortfolioPerformanceReport(
        status=PerformanceAttributionStatus.COMPLETED,
        initial_value=Decimal("100000"),
        ending_value=Decimal("106000"),
        net_profit_loss=Decimal("6000"),
        total_return=Decimal("0.06"),
        contributions=[contribution()],
        summaries=[
            AttributionSummary(
                contribution_type=ContributionType.STRATEGY,
                total_return_contribution=Decimal("0.06"),
                total_profit_loss=Decimal("6000"),
                total_risk_contribution=Decimal("0.30"),
                contributor_count=1,
                top_contributor_id="strategy-alpha",
                bottom_contributor_id="strategy-alpha",
            )
        ],
        top_contributor_id="strategy-alpha",
        bottom_contributor_id="strategy-alpha",
        recommendation="Maintain strategy exposure.",
        warnings=["Attribution warning."],
    )

    assert value.contributions == (contribution(),)
    assert isinstance(value.summaries, tuple)
    assert value.warnings == (
        "Attribution warning.",
    )


def test_initial_value_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="initial_value must be greater than zero",
    ):
        PortfolioPerformanceReport(
            status=PerformanceAttributionStatus.PENDING,
            initial_value=Decimal("0"),
            ending_value=Decimal("0"),
            net_profit_loss=Decimal("0"),
            total_return=Decimal("0"),
        )


def test_net_profit_loss_must_match_values() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "net_profit_loss must equal ending_value "
            "minus initial_value"
        ),
    ):
        PortfolioPerformanceReport(
            status=PerformanceAttributionStatus.COMPLETED,
            initial_value=Decimal("100000"),
            ending_value=Decimal("110000"),
            net_profit_loss=Decimal("9000"),
            total_return=Decimal("0.09"),
            recommendation="Review attribution.",
        )


def test_total_return_must_match_profit_loss() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "total_return must equal net_profit_loss "
            "divided by initial_value"
        ),
    ):
        PortfolioPerformanceReport(
            status=PerformanceAttributionStatus.COMPLETED,
            initial_value=Decimal("100000"),
            ending_value=Decimal("110000"),
            net_profit_loss=Decimal("10000"),
            total_return=Decimal("0.09"),
            recommendation="Review attribution.",
        )


def test_contributor_ids_must_be_unique() -> None:
    duplicate = contribution()

    with pytest.raises(
        ValueError,
        match="contributor_id values must be unique",
    ):
        PortfolioPerformanceReport(
            status=PerformanceAttributionStatus.COMPLETED,
            initial_value=Decimal("100000"),
            ending_value=Decimal("112000"),
            net_profit_loss=Decimal("12000"),
            total_return=Decimal("0.12"),
            contributions=(
                duplicate,
                duplicate,
            ),
            recommendation="Review duplicate contributors.",
        )


def test_summary_types_must_be_unique() -> None:
    first = summary()
    second = summary()

    with pytest.raises(
        ValueError,
        match=(
            "summary contribution types must be unique"
        ),
    ):
        PortfolioPerformanceReport(
            status=PerformanceAttributionStatus.COMPLETED,
            initial_value=Decimal("100000"),
            ending_value=Decimal("110000"),
            net_profit_loss=Decimal("10000"),
            total_return=Decimal("0.10"),
            summaries=(first, second),
            recommendation="Review duplicate summaries.",
        )


def test_top_contributor_must_exist() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "top_contributor_id must identify "
            "a contribution"
        ),
    ):
        PortfolioPerformanceReport(
            status=PerformanceAttributionStatus.COMPLETED,
            initial_value=Decimal("100000"),
            ending_value=Decimal("106000"),
            net_profit_loss=Decimal("6000"),
            total_return=Decimal("0.06"),
            contributions=(contribution(),),
            top_contributor_id="missing",
            recommendation="Review attribution.",
        )


@pytest.mark.parametrize(
    "score_name",
    [
        "concentration_score",
        "risk_adjusted_score",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_report_scores_must_be_valid(
    score_name: str,
    value: Decimal,
) -> None:
    arguments = {
        "status": PerformanceAttributionStatus.COMPLETED,
        "initial_value": Decimal("100000"),
        "ending_value": Decimal("110000"),
        "net_profit_loss": Decimal("10000"),
        "total_return": Decimal("0.10"),
        "concentration_score": Decimal("0.50"),
        "risk_adjusted_score": Decimal("0.80"),
        "recommendation": "Maintain allocation.",
    }
    arguments[score_name] = value

    with pytest.raises(
        ValueError,
        match=f"{score_name} must be between 0 and 1",
    ):
        PortfolioPerformanceReport(**arguments)


def test_completed_report_requires_recommendation() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed reports must include a recommendation"
        ),
    ):
        PortfolioPerformanceReport(
            status=PerformanceAttributionStatus.COMPLETED,
            initial_value=Decimal("100000"),
            ending_value=Decimal("110000"),
            net_profit_loss=Decimal("10000"),
            total_return=Decimal("0.10"),
            recommendation="   ",
        )


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        PortfolioPerformanceReport(
            status=PerformanceAttributionStatus.FAILED,
            initial_value=Decimal("100000"),
            ending_value=Decimal("100000"),
            net_profit_loss=Decimal("0"),
            total_return=Decimal("0"),
        )


def test_completed_report_cannot_include_error() -> None:
    with pytest.raises(
        ValueError,
        match="only failed reports may include an error",
    ):
        PortfolioPerformanceReport(
            status=PerformanceAttributionStatus.COMPLETED,
            initial_value=Decimal("100000"),
            ending_value=Decimal("100000"),
            net_profit_loss=Decimal("0"),
            total_return=Decimal("0"),
            recommendation="No change.",
            error="Unexpected failure.",
        )


def test_models_are_immutable() -> None:
    value = contribution()

    with pytest.raises(FrozenInstanceError):
        value.name = "Changed"