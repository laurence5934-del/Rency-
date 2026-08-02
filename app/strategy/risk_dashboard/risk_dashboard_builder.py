from __future__ import annotations

from decimal import Decimal

from app.strategy.monte_carlo import (
    MonteCarloReport,
    MonteCarloStatus,
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

from .risk_dashboard_models import (
    DeploymentReadiness,
    InstitutionalRiskDashboard,
    PortfolioHealth,
    RiskDashboardSection,
)


_ZERO = Decimal("0")
_ONE = Decimal("1")
_TWO = Decimal("2")
_THREE = Decimal("3")
_FOUR = Decimal("4")


class InstitutionalRiskDashboardBuilder:
    """Combines institutional risk reports into one dashboard."""

    def build(
        self,
        *,
        walk_forward: WalkForwardReport,
        monte_carlo: MonteCarloReport,
        stress_testing: StressTestReport,
        scenario_analysis: PortfolioScenarioReport,
    ) -> InstitutionalRiskDashboard:
        self._validate_reports(
            walk_forward=walk_forward,
            monte_carlo=monte_carlo,
            stress_testing=stress_testing,
            scenario_analysis=scenario_analysis,
        )

        sections = (
            self._walk_forward_section(walk_forward),
            self._monte_carlo_section(monte_carlo),
            self._stress_testing_section(stress_testing),
            self._scenario_analysis_section(
                scenario_analysis
            ),
        )

        failed_reports = self._failed_report_names(
            walk_forward=walk_forward,
            monte_carlo=monte_carlo,
            stress_testing=stress_testing,
            scenario_analysis=scenario_analysis,
        )

        overall_risk_score = self._overall_risk_score(
            walk_forward=walk_forward,
            monte_carlo=monte_carlo,
            stress_testing=stress_testing,
            scenario_analysis=scenario_analysis,
        )

        confidence_score = self._confidence_score(
            walk_forward=walk_forward,
            monte_carlo=monte_carlo,
        )

        capital_preservation_score = (
            self._capital_preservation_score(
                monte_carlo=monte_carlo,
                stress_testing=stress_testing,
                scenario_analysis=scenario_analysis,
            )
        )

        health = self._health(overall_risk_score)

        readiness = self._readiness(
            health=health,
            confidence_score=confidence_score,
            failed_reports=failed_reports,
        )

        warnings = self._aggregate_warnings(
            sections=sections,
            failed_reports=failed_reports,
        )

        return InstitutionalRiskDashboard(
            overall_risk_score=overall_risk_score,
            confidence_score=confidence_score,
            capital_preservation_score=(
                capital_preservation_score
            ),
            health=health,
            readiness=readiness,
            recommendation=self._recommendation(
                readiness
            ),
            sections=sections,
            warnings=warnings,
        )

    @staticmethod
    def _walk_forward_section(
        report: WalkForwardReport,
    ) -> RiskDashboardSection:
        score = (
            report.robustness_score
            + report.pass_rate
        ) / _TWO

        return RiskDashboardSection(
            section_id="walk-forward",
            title="Walk-Forward Validation",
            score=score,
            status=report.status.value,
            metrics=(
                (
                    "Robustness Score",
                    str(report.robustness_score),
                ),
                (
                    "Pass Rate",
                    str(report.pass_rate),
                ),
                (
                    "Window Count",
                    str(len(report.windows)),
                ),
            ),
            warnings=report.warnings,
        )

    @staticmethod
    def _monte_carlo_section(
        report: MonteCarloReport,
    ) -> RiskDashboardSection:
        score = _ONE - (
            report.ruin_probability
            + report.median_max_drawdown
        ) / _TWO

        return RiskDashboardSection(
            section_id="monte-carlo",
            title="Monte Carlo Simulation",
            score=InstitutionalRiskDashboardBuilder._clamp(
                score
            ),
            status=report.status.value,
            metrics=(
                (
                    "Ruin Probability",
                    str(report.ruin_probability),
                ),
                (
                    "Median Final Equity",
                    str(report.median_final_equity),
                ),
                (
                    "Median Maximum Drawdown",
                    str(report.median_max_drawdown),
                ),
                (
                    "Simulation Count",
                    str(len(report.paths)),
                ),
            ),
            warnings=report.warnings,
        )

    @staticmethod
    def _stress_testing_section(
        report: StressTestReport,
    ) -> RiskDashboardSection:
        score = _ONE - (
            report.worst_case_loss_percent
            + report.average_loss_percent
        ) / _TWO

        return RiskDashboardSection(
            section_id="stress-testing",
            title="Stress Testing",
            score=InstitutionalRiskDashboardBuilder._clamp(
                score
            ),
            status=report.status.value,
            metrics=(
                (
                    "Worst-Case Loss",
                    str(report.worst_case_loss_percent),
                ),
                (
                    "Average Loss",
                    str(report.average_loss_percent),
                ),
                (
                    "Breach Count",
                    str(report.breach_count),
                ),
                (
                    "Scenario Count",
                    str(len(report.results)),
                ),
            ),
            warnings=report.warnings,
        )

    @staticmethod
    def _scenario_analysis_section(
        report: PortfolioScenarioReport,
    ) -> RiskDashboardSection:
        score = _ONE - report.weighted_risk_score

        return RiskDashboardSection(
            section_id="scenario-analysis",
            title="Portfolio Scenario Analysis",
            score=InstitutionalRiskDashboardBuilder._clamp(
                score
            ),
            status=report.status.value,
            metrics=(
                (
                    "Weighted Return",
                    str(report.weighted_return),
                ),
                (
                    "Weighted Drawdown",
                    str(report.weighted_drawdown),
                ),
                (
                    "Weighted Risk Score",
                    str(report.weighted_risk_score),
                ),
                (
                    "Recommendation",
                    report.recommendation,
                ),
            ),
            warnings=report.warnings,
        )

    @classmethod
    def _overall_risk_score(
        cls,
        *,
        walk_forward: WalkForwardReport,
        monte_carlo: MonteCarloReport,
        stress_testing: StressTestReport,
        scenario_analysis: PortfolioScenarioReport,
    ) -> Decimal:
        walk_forward_strength = (
            walk_forward.robustness_score
            + walk_forward.pass_rate
        ) / _TWO

        walk_forward_risk = (
            _ONE - walk_forward_strength
        )

        monte_carlo_risk = (
            monte_carlo.ruin_probability
            + monte_carlo.median_max_drawdown
        ) / _TWO

        stress_risk = (
            stress_testing.worst_case_loss_percent
            + stress_testing.average_loss_percent
        ) / _TWO

        scenario_risk = (
            scenario_analysis.weighted_risk_score
        )

        return cls._clamp(
            (
                walk_forward_risk
                + monte_carlo_risk
                + stress_risk
                + scenario_risk
            )
            / _FOUR
        )

    @classmethod
    def _confidence_score(
        cls,
        *,
        walk_forward: WalkForwardReport,
        monte_carlo: MonteCarloReport,
    ) -> Decimal:
        monte_carlo_survival = (
            _ONE - monte_carlo.ruin_probability
        )

        return cls._clamp(
            (
                walk_forward.robustness_score
                + walk_forward.pass_rate
                + monte_carlo_survival
            )
            / _THREE
        )

    @classmethod
    def _capital_preservation_score(
        cls,
        *,
        monte_carlo: MonteCarloReport,
        stress_testing: StressTestReport,
        scenario_analysis: PortfolioScenarioReport,
    ) -> Decimal:
        average_capital_risk = (
            monte_carlo.median_max_drawdown
            + stress_testing.worst_case_loss_percent
            + scenario_analysis.weighted_drawdown
        ) / _THREE

        return cls._clamp(
            _ONE - average_capital_risk
        )

    @staticmethod
    def _health(
        overall_risk_score: Decimal,
    ) -> PortfolioHealth:
        if overall_risk_score <= Decimal("0.10"):
            return PortfolioHealth.EXCELLENT

        if overall_risk_score <= Decimal("0.25"):
            return PortfolioHealth.HEALTHY

        if overall_risk_score <= Decimal("0.40"):
            return PortfolioHealth.CAUTION

        if overall_risk_score <= Decimal("0.60"):
            return PortfolioHealth.HIGH_RISK

        return PortfolioHealth.CRITICAL

    @staticmethod
    def _readiness(
        *,
        health: PortfolioHealth,
        confidence_score: Decimal,
        failed_reports: tuple[str, ...],
    ) -> DeploymentReadiness:
        if failed_reports:
            return DeploymentReadiness.BLOCKED

        if (
            health is PortfolioHealth.EXCELLENT
            and confidence_score >= Decimal("0.90")
        ):
            return DeploymentReadiness.LIVE_READY

        if (
            health
            in {
                PortfolioHealth.EXCELLENT,
                PortfolioHealth.HEALTHY,
            }
            and confidence_score >= Decimal("0.70")
        ):
            return DeploymentReadiness.PAPER_READY

        if health in {
            PortfolioHealth.CAUTION,
            PortfolioHealth.HEALTHY,
        }:
            return DeploymentReadiness.REVIEW_REQUIRED

        return DeploymentReadiness.BLOCKED

    @staticmethod
    def _recommendation(
        readiness: DeploymentReadiness,
    ) -> str:
        recommendations = {
            DeploymentReadiness.LIVE_READY: (
                "Portfolio satisfies institutional live "
                "deployment requirements."
            ),
            DeploymentReadiness.PAPER_READY: (
                "Proceed to controlled paper trading."
            ),
            DeploymentReadiness.REVIEW_REQUIRED: (
                "Review portfolio risk before deployment."
            ),
            DeploymentReadiness.BLOCKED: (
                "Deployment is blocked until material risk "
                "issues are resolved."
            ),
        }

        return recommendations[readiness]

    @staticmethod
    def _failed_report_names(
        *,
        walk_forward: WalkForwardReport,
        monte_carlo: MonteCarloReport,
        stress_testing: StressTestReport,
        scenario_analysis: PortfolioScenarioReport,
    ) -> tuple[str, ...]:
        failed: list[str] = []

        if (
            walk_forward.status
            is WalkForwardStatus.FAILED
        ):
            failed.append("Walk-Forward Validation")

        if (
            monte_carlo.status
            is MonteCarloStatus.FAILED
        ):
            failed.append("Monte Carlo Simulation")

        if (
            stress_testing.status
            is StressTestStatus.FAILED
        ):
            failed.append("Stress Testing")

        if (
            scenario_analysis.status
            is ScenarioAnalysisStatus.FAILED
        ):
            failed.append("Scenario Analysis")

        return tuple(failed)

    @staticmethod
    def _aggregate_warnings(
        *,
        sections: tuple[RiskDashboardSection, ...],
        failed_reports: tuple[str, ...],
    ) -> tuple[str, ...]:
        warnings = [
            warning
            for section in sections
            for warning in section.warnings
        ]

        warnings.extend(
            f"{report_name} report failed."
            for report_name in failed_reports
        )

        return tuple(warnings)

    @staticmethod
    def _validate_reports(
        *,
        walk_forward: WalkForwardReport,
        monte_carlo: MonteCarloReport,
        stress_testing: StressTestReport,
        scenario_analysis: PortfolioScenarioReport,
    ) -> None:
        expected = (
            (
                walk_forward,
                WalkForwardReport,
                "walk_forward",
            ),
            (
                monte_carlo,
                MonteCarloReport,
                "monte_carlo",
            ),
            (
                stress_testing,
                StressTestReport,
                "stress_testing",
            ),
            (
                scenario_analysis,
                PortfolioScenarioReport,
                "scenario_analysis",
            ),
        )

        for value, expected_type, name in expected:
            if not isinstance(value, expected_type):
                raise TypeError(
                    f"{name} must be a "
                    f"{expected_type.__name__}"
                )

    @staticmethod
    def _clamp(value: Decimal) -> Decimal:
        return min(
            max(value, _ZERO),
            _ONE,
        )