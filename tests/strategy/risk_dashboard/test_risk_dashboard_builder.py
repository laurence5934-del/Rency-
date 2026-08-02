from decimal import Decimal

import pytest

from app.strategy.monte_carlo import (
    MonteCarloReport,
    MonteCarloStatus,
)
from app.strategy.risk_dashboard.risk_dashboard_builder import (
    InstitutionalRiskDashboardBuilder,
)
from app.strategy.risk_dashboard.risk_dashboard_models import (
    DeploymentReadiness,
    PortfolioHealth,
)
from app.strategy.scenario import (
    PortfolioScenarioReport,
    ScenarioAnalysisStatus,
)
from app.strategy.stress_testing import (
    StressTestReport,
    StressTestStatus,
)
from app.strategy.walk_forward import (
    WalkForwardReport,
    WalkForwardStatus,
)


def walk_forward_report(
    *,
    robustness_score: str = "0.90",
    pass_rate: str = "0.90",
    status: WalkForwardStatus = (
        WalkForwardStatus.COMPLETED
    ),
    warnings=(),
    error=None,
) -> WalkForwardReport:
    return WalkForwardReport(
        status=status,
        robustness_score=Decimal(
            robustness_score
        ),
        pass_rate=Decimal(pass_rate),
        warnings=tuple(warnings),
        error=error,
    )


def monte_carlo_report(
    *,
    ruin_probability: str = "0.02",
    median_drawdown: str = "0.10",
    status: MonteCarloStatus = (
        MonteCarloStatus.COMPLETED
    ),
    warnings=(),
    error=None,
) -> MonteCarloReport:
    return MonteCarloReport(
        status=status,
        ruin_probability=Decimal(
            ruin_probability
        ),
        median_final_equity=Decimal("110000"),
        percentile_05_final_equity=Decimal(
            "90000"
        ),
        percentile_95_final_equity=Decimal(
            "130000"
        ),
        median_max_drawdown=Decimal(
            median_drawdown
        ),
        warnings=tuple(warnings),
        error=error,
    )


def stress_report(
    *,
    worst_loss: str = "0.15",
    average_loss: str = "0.08",
    breach_count: int = 0,
    status: StressTestStatus = (
        StressTestStatus.COMPLETED
    ),
    warnings=(),
    error=None,
) -> StressTestReport:
    return StressTestReport(
        status=status,
        worst_case_loss_percent=Decimal(
            worst_loss
        ),
        average_loss_percent=Decimal(
            average_loss
        ),
        breach_count=breach_count,
        warnings=tuple(warnings),
        error=error,
    )


def scenario_report(
    *,
    weighted_return: str = "0.08",
    weighted_drawdown: str = "0.10",
    weighted_risk: str = "0.15",
    status: ScenarioAnalysisStatus = (
        ScenarioAnalysisStatus.COMPLETED
    ),
    warnings=(),
    error=None,
) -> PortfolioScenarioReport:
    return PortfolioScenarioReport(
        status=status,
        weighted_return=Decimal(
            weighted_return
        ),
        weighted_drawdown=Decimal(
            weighted_drawdown
        ),
        weighted_risk_score=Decimal(
            weighted_risk
        ),
        recommendation="APPROVE",
        warnings=tuple(warnings),
        error=error,
    )


def build_dashboard(**overrides):
    values = {
        "walk_forward": walk_forward_report(),
        "monte_carlo": monte_carlo_report(),
        "stress_testing": stress_report(),
        "scenario_analysis": scenario_report(),
    }
    values.update(overrides)

    return InstitutionalRiskDashboardBuilder().build(
        **values
    )


def test_build_creates_four_sections() -> None:
    dashboard = build_dashboard()

    assert len(dashboard.sections) == 4

    assert tuple(
        section.section_id
        for section in dashboard.sections
    ) == (
        "walk-forward",
        "monte-carlo",
        "stress-testing",
        "scenario-analysis",
    )


def test_walk_forward_section_score() -> None:
    dashboard = build_dashboard(
        walk_forward=walk_forward_report(
            robustness_score="0.80",
            pass_rate="0.60",
        )
    )

    assert (
        dashboard.sections[0].score
        == Decimal("0.70")
    )


def test_monte_carlo_section_score() -> None:
    dashboard = build_dashboard(
        monte_carlo=monte_carlo_report(
            ruin_probability="0.10",
            median_drawdown="0.20",
        )
    )

    assert (
        dashboard.sections[1].score
        == Decimal("0.85")
    )


def test_stress_section_score() -> None:
    dashboard = build_dashboard(
        stress_testing=stress_report(
            worst_loss="0.30",
            average_loss="0.10",
        )
    )

    assert (
        dashboard.sections[2].score
        == Decimal("0.80")
    )


def test_scenario_section_score() -> None:
    dashboard = build_dashboard(
        scenario_analysis=scenario_report(
            weighted_risk="0.25",
        )
    )

    assert (
        dashboard.sections[3].score
        == Decimal("0.75")
    )


def test_overall_risk_score_is_calculated() -> None:
    dashboard = build_dashboard(
        walk_forward=walk_forward_report(
            robustness_score="0.80",
            pass_rate="0.80",
        ),
        monte_carlo=monte_carlo_report(
            ruin_probability="0.10",
            median_drawdown="0.20",
        ),
        stress_testing=stress_report(
            worst_loss="0.30",
            average_loss="0.10",
        ),
        scenario_analysis=scenario_report(
            weighted_risk="0.25",
        ),
    )

    expected = (
        Decimal("0.20")
        + Decimal("0.15")
        + Decimal("0.20")
        + Decimal("0.25")
    ) / Decimal("4")

    assert dashboard.overall_risk_score == expected


def test_confidence_score_is_calculated() -> None:
    dashboard = build_dashboard(
        walk_forward=walk_forward_report(
            robustness_score="0.90",
            pass_rate="0.80",
        ),
        monte_carlo=monte_carlo_report(
            ruin_probability="0.10",
        ),
    )

    expected = (
        Decimal("0.90")
        + Decimal("0.80")
        + Decimal("0.90")
    ) / Decimal("3")

    assert dashboard.confidence_score == expected


def test_capital_preservation_is_calculated() -> None:
    dashboard = build_dashboard(
        monte_carlo=monte_carlo_report(
            median_drawdown="0.10",
        ),
        stress_testing=stress_report(
            worst_loss="0.20",
        ),
        scenario_analysis=scenario_report(
            weighted_drawdown="0.15",
        ),
    )

    expected = Decimal("1") - (
        Decimal("0.10")
        + Decimal("0.20")
        + Decimal("0.15")
    ) / Decimal("3")

    assert (
        dashboard.capital_preservation_score
        == expected
    )


@pytest.mark.parametrize(
    ("risk_score", "expected_health"),
    [
        ("0.10", PortfolioHealth.EXCELLENT),
        ("0.11", PortfolioHealth.HEALTHY),
        ("0.25", PortfolioHealth.HEALTHY),
        ("0.26", PortfolioHealth.CAUTION),
        ("0.40", PortfolioHealth.CAUTION),
        ("0.41", PortfolioHealth.HIGH_RISK),
        ("0.60", PortfolioHealth.HIGH_RISK),
        ("0.61", PortfolioHealth.CRITICAL),
    ],
)
def test_health_boundaries(
    risk_score: str,
    expected_health: PortfolioHealth,
) -> None:
    assert (
        InstitutionalRiskDashboardBuilder._health(
            Decimal(risk_score)
        )
        is expected_health
    )


def test_excellent_high_confidence_is_live_ready() -> None:
    readiness = (
        InstitutionalRiskDashboardBuilder._readiness(
            health=PortfolioHealth.EXCELLENT,
            confidence_score=Decimal("0.90"),
            failed_reports=(),
        )
    )

    assert readiness is DeploymentReadiness.LIVE_READY


def test_healthy_confident_portfolio_is_paper_ready() -> None:
    readiness = (
        InstitutionalRiskDashboardBuilder._readiness(
            health=PortfolioHealth.HEALTHY,
            confidence_score=Decimal("0.80"),
            failed_reports=(),
        )
    )

    assert readiness is DeploymentReadiness.PAPER_READY


def test_caution_requires_review() -> None:
    readiness = (
        InstitutionalRiskDashboardBuilder._readiness(
            health=PortfolioHealth.CAUTION,
            confidence_score=Decimal("0.80"),
            failed_reports=(),
        )
    )

    assert (
        readiness
        is DeploymentReadiness.REVIEW_REQUIRED
    )


def test_high_risk_is_blocked() -> None:
    readiness = (
        InstitutionalRiskDashboardBuilder._readiness(
            health=PortfolioHealth.HIGH_RISK,
            confidence_score=Decimal("0.90"),
            failed_reports=(),
        )
    )

    assert readiness is DeploymentReadiness.BLOCKED


def test_failed_report_blocks_deployment() -> None:
    dashboard = build_dashboard(
        monte_carlo=monte_carlo_report(
            status=MonteCarloStatus.FAILED,
            error="simulation failed",
        )
    )

    assert (
        dashboard.readiness
        is DeploymentReadiness.BLOCKED
    )
    assert (
        "Monte Carlo Simulation report failed."
        in dashboard.warnings
    )


def test_report_warnings_are_aggregated() -> None:
    dashboard = build_dashboard(
        walk_forward=walk_forward_report(
            warnings=("Walk-forward warning.",),
        ),
        monte_carlo=monte_carlo_report(
            warnings=("Monte Carlo warning.",),
        ),
        stress_testing=stress_report(
            warnings=("Stress warning.",),
        ),
        scenario_analysis=scenario_report(
            warnings=("Scenario warning.",),
        ),
    )

    assert dashboard.warnings == (
        "Walk-forward warning.",
        "Monte Carlo warning.",
        "Stress warning.",
        "Scenario warning.",
    )


@pytest.mark.parametrize(
    ("argument_name", "invalid_value", "type_name"),
    [
        (
            "walk_forward",
            object(),
            "WalkForwardReport",
        ),
        (
            "monte_carlo",
            object(),
            "MonteCarloReport",
        ),
        (
            "stress_testing",
            object(),
            "StressTestReport",
        ),
        (
            "scenario_analysis",
            object(),
            "PortfolioScenarioReport",
        ),
    ],
)
def test_report_types_are_validated(
    argument_name,
    invalid_value,
    type_name,
) -> None:
    values = {
        "walk_forward": walk_forward_report(),
        "monte_carlo": monte_carlo_report(),
        "stress_testing": stress_report(),
        "scenario_analysis": scenario_report(),
    }
    values[argument_name] = invalid_value

    with pytest.raises(
        TypeError,
        match=type_name,
    ):
        InstitutionalRiskDashboardBuilder().build(
            **values
        )


def test_recommendations_are_not_empty() -> None:
    for readiness in DeploymentReadiness:
        recommendation = (
            InstitutionalRiskDashboardBuilder
            ._recommendation(readiness)
        )

        assert recommendation.strip()