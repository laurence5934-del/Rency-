from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.strategy.risk_dashboard.risk_dashboard_models import (
    DeploymentReadiness,
    InstitutionalRiskDashboard,
    PortfolioHealth,
    RiskDashboardSection,
)


def section() -> RiskDashboardSection:
    return RiskDashboardSection(
        section_id="monte-carlo",
        title="Monte Carlo",
        score=Decimal("0.85"),
        status="HEALTHY",
        metrics=(
            ("Ruin Probability", "0.02"),
            ("Median Drawdown", "0.12"),
        ),
    )


def dashboard() -> InstitutionalRiskDashboard:
    return InstitutionalRiskDashboard(
        overall_risk_score=Decimal("0.20"),
        confidence_score=Decimal("0.90"),
        capital_preservation_score=Decimal("0.88"),
        health=PortfolioHealth.HEALTHY,
        readiness=DeploymentReadiness.PAPER_READY,
        recommendation="Proceed to controlled paper trading.",
        sections=(section(),),
    )


def test_risk_dashboard_section() -> None:
    value = section()

    assert value.section_id == "monte-carlo"
    assert value.title == "Monte Carlo"
    assert value.score == Decimal("0.85")


def test_section_text_is_normalized() -> None:
    value = RiskDashboardSection(
        section_id="  stress-testing  ",
        title="  Stress Testing  ",
        score=Decimal("0.75"),
        status="  CAUTION  ",
    )

    assert value.section_id == "stress-testing"
    assert value.title == "Stress Testing"
    assert value.status == "CAUTION"


def test_section_id_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="section_id must not be empty",
    ):
        RiskDashboardSection(
            section_id="   ",
            title="Stress Testing",
            score=Decimal("0.50"),
            status="CAUTION",
        )


def test_section_title_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="title must not be empty",
    ):
        RiskDashboardSection(
            section_id="stress",
            title="   ",
            score=Decimal("0.50"),
            status="CAUTION",
        )


def test_section_status_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="status must not be empty",
    ):
        RiskDashboardSection(
            section_id="stress",
            title="Stress Testing",
            score=Decimal("0.50"),
            status="   ",
        )


@pytest.mark.parametrize(
    "score",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_section_score_must_be_valid(
    score: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="score must be between 0 and 1",
    ):
        RiskDashboardSection(
            section_id="stress",
            title="Stress Testing",
            score=score,
            status="CAUTION",
        )


def test_section_score_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="score must be a Decimal",
    ):
        RiskDashboardSection(
            section_id="stress",
            title="Stress Testing",
            score=0.50,
            status="CAUTION",
        )


def test_section_metrics_are_normalized() -> None:
    value = RiskDashboardSection(
        section_id="stress",
        title="Stress Testing",
        score=Decimal("0.50"),
        status="CAUTION",
        metrics=[
            (
                "  Worst Loss  ",
                "  0.25  ",
            ),
        ],
    )

    assert value.metrics == (
        (
            "Worst Loss",
            "0.25",
        ),
    )


def test_metric_must_have_two_items() -> None:
    with pytest.raises(
        TypeError,
        match="two-item tuple",
    ):
        RiskDashboardSection(
            section_id="stress",
            title="Stress Testing",
            score=Decimal("0.50"),
            status="CAUTION",
            metrics=(
                ("Invalid",),
            ),
        )


def test_metric_name_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="metric names must not be empty",
    ):
        RiskDashboardSection(
            section_id="stress",
            title="Stress Testing",
            score=Decimal("0.50"),
            status="CAUTION",
            metrics=(
                ("   ", "0.20"),
            ),
        )


def test_section_warnings_are_converted_to_tuple() -> None:
    value = RiskDashboardSection(
        section_id="stress",
        title="Stress Testing",
        score=Decimal("0.50"),
        status="CAUTION",
        warnings=["Risk limit approached."],
    )

    assert value.warnings == (
        "Risk limit approached.",
    )


def test_institutional_dashboard() -> None:
    value = dashboard()

    assert value.health is PortfolioHealth.HEALTHY
    assert (
        value.readiness
        is DeploymentReadiness.PAPER_READY
    )
    assert value.sections == (section(),)


@pytest.mark.parametrize(
    "field_name",
    [
        "overall_risk_score",
        "confidence_score",
        "capital_preservation_score",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_dashboard_scores_must_be_valid(
    field_name: str,
    value: Decimal,
) -> None:
    arguments = {
        "overall_risk_score": Decimal("0.20"),
        "confidence_score": Decimal("0.90"),
        "capital_preservation_score": Decimal(
            "0.88"
        ),
        "health": PortfolioHealth.HEALTHY,
        "readiness": DeploymentReadiness.PAPER_READY,
        "recommendation": "Paper trade.",
    }

    arguments[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be between 0 and 1",
    ):
        InstitutionalRiskDashboard(**arguments)


def test_health_must_be_portfolio_health() -> None:
    with pytest.raises(
        TypeError,
        match="health must be a PortfolioHealth",
    ):
        InstitutionalRiskDashboard(
            overall_risk_score=Decimal("0.20"),
            confidence_score=Decimal("0.90"),
            capital_preservation_score=Decimal("0.88"),
            health="HEALTHY",
            readiness=DeploymentReadiness.PAPER_READY,
            recommendation="Paper trade.",
        )


def test_readiness_must_be_deployment_readiness() -> None:
    with pytest.raises(
        TypeError,
        match="readiness must be a DeploymentReadiness",
    ):
        InstitutionalRiskDashboard(
            overall_risk_score=Decimal("0.20"),
            confidence_score=Decimal("0.90"),
            capital_preservation_score=Decimal("0.88"),
            health=PortfolioHealth.HEALTHY,
            readiness="PAPER_READY",
            recommendation="Paper trade.",
        )


def test_recommendation_is_normalized() -> None:
    value = InstitutionalRiskDashboard(
        overall_risk_score=Decimal("0.20"),
        confidence_score=Decimal("0.90"),
        capital_preservation_score=Decimal("0.88"),
        health=PortfolioHealth.HEALTHY,
        readiness=DeploymentReadiness.PAPER_READY,
        recommendation="  Paper trade.  ",
    )

    assert value.recommendation == "Paper trade."


def test_recommendation_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="recommendation must not be empty",
    ):
        InstitutionalRiskDashboard(
            overall_risk_score=Decimal("0.20"),
            confidence_score=Decimal("0.90"),
            capital_preservation_score=Decimal("0.88"),
            health=PortfolioHealth.HEALTHY,
            readiness=DeploymentReadiness.PAPER_READY,
            recommendation="   ",
        )


def test_dashboard_collections_are_tuples() -> None:
    value = InstitutionalRiskDashboard(
        overall_risk_score=Decimal("0.20"),
        confidence_score=Decimal("0.90"),
        capital_preservation_score=Decimal("0.88"),
        health=PortfolioHealth.HEALTHY,
        readiness=DeploymentReadiness.PAPER_READY,
        recommendation="Paper trade.",
        sections=[section()],
        warnings=["Portfolio warning."],
    )

    assert value.sections == (section(),)
    assert value.warnings == (
        "Portfolio warning.",
    )


def test_models_are_immutable() -> None:
    value = dashboard()

    with pytest.raises(FrozenInstanceError):
        value.recommendation = "Changed"