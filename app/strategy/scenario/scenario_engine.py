from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from .scenario_models import (
    PortfolioScenarioReport,
    ScenarioAnalysisStatus,
    ScenarioDefinition,
    ScenarioResult,
)

_ZERO = Decimal("0")
_ONE = Decimal("1")


class ScenarioAnalysisEngine:
    """Evaluates a portfolio across multiple market scenarios."""

    def run(
        self,
        *,
        initial_equity: Decimal,
        scenarios: Iterable[ScenarioDefinition],
        maximum_risk_score: Decimal = Decimal("0.50"),
    ) -> PortfolioScenarioReport:
        scenario_list = tuple(scenarios)

        self._validate_inputs(
            initial_equity=initial_equity,
            maximum_risk_score=maximum_risk_score,
        )

        if not scenario_list:
            return PortfolioScenarioReport(
                status=ScenarioAnalysisStatus.COMPLETED,
                results=(),
                weighted_return=_ZERO,
                weighted_drawdown=_ZERO,
                weighted_risk_score=_ZERO,
                recommendation="NO_SCENARIOS",
                warnings=(
                    "No scenarios were supplied.",
                ),
            )

        results: list[ScenarioResult] = []

        try:
            for scenario in scenario_list:
                results.append(
                    self._evaluate_scenario(
                        scenario=scenario,
                        initial_equity=initial_equity,
                        maximum_risk_score=maximum_risk_score,
                    )
                )

        except Exception as exc:
            return PortfolioScenarioReport(
                status=ScenarioAnalysisStatus.FAILED,
                results=tuple(results),
                weighted_return=self._weighted_return(results),
                weighted_drawdown=self._weighted_drawdown(results),
                weighted_risk_score=self._weighted_risk(results),
                recommendation="FAILED",
                warnings=(
                    "Scenario analysis terminated early.",
                ),
                error=str(exc),
            )

        best = max(
            results,
            key=lambda result: result.projected_return,
        )

        worst = min(
            results,
            key=lambda result: result.projected_return,
        )

        recommendation = (
            "APPROVE"
            if self._weighted_risk(results)
            <= maximum_risk_score
            else "REVIEW"
        )

        warnings = tuple(
            warning
            for result in results
            for warning in result.warnings
        )

        return PortfolioScenarioReport(
            status=ScenarioAnalysisStatus.COMPLETED,
            results=tuple(results),
            weighted_return=self._weighted_return(results),
            weighted_drawdown=self._weighted_drawdown(results),
            weighted_risk_score=self._weighted_risk(results),
            best_scenario_id=best.scenario.scenario_id,
            worst_scenario_id=worst.scenario.scenario_id,
            recommendation=recommendation,
            warnings=warnings,
        )

    @staticmethod
    def _evaluate_scenario(
        *,
        scenario: ScenarioDefinition,
        initial_equity: Decimal,
        maximum_risk_score: Decimal,
    ) -> ScenarioResult:

        projected_equity = (
            initial_equity
            * (Decimal("1") + scenario.expected_return)
        )

        if projected_equity < _ZERO:
            projected_equity = _ZERO

        projected_drawdown = min(
            scenario.expected_volatility,
            _ONE,
        )

        risk_score = min(
            scenario.expected_volatility,
            _ONE,
        )

        passed = risk_score <= maximum_risk_score

        warnings = []

        if not passed:
            warnings.append(
                f"{scenario.scenario_id} exceeded risk limit."
            )

        return ScenarioResult(
            scenario=scenario,
            initial_equity=initial_equity,
            projected_equity=projected_equity,
            projected_return=scenario.expected_return,
            projected_drawdown=projected_drawdown,
            risk_score=risk_score,
            passed=passed,
            warnings=tuple(warnings),
        )

    @staticmethod
    def _weighted_return(
        results: Iterable[ScenarioResult],
    ) -> Decimal:
        results = tuple(results)

        if not results:
            return _ZERO

        total = sum(
            (
                r.projected_return
                * r.scenario.probability_weight
                for r in results
            ),
            _ZERO,
        )

        weight = sum(
            (
                r.scenario.probability_weight
                for r in results
            ),
            _ZERO,
        )

        return total / weight if weight else _ZERO

    @staticmethod
    def _weighted_drawdown(
        results: Iterable[ScenarioResult],
    ) -> Decimal:
        results = tuple(results)

        if not results:
            return _ZERO

        total = sum(
            (
                r.projected_drawdown
                * r.scenario.probability_weight
                for r in results
            ),
            _ZERO,
        )

        weight = sum(
            (
                r.scenario.probability_weight
                for r in results
            ),
            _ZERO,
        )

        return total / weight if weight else _ZERO

    @staticmethod
    def _weighted_risk(
        results: Iterable[ScenarioResult],
    ) -> Decimal:
        results = tuple(results)

        if not results:
            return _ZERO

        total = sum(
            (
                r.risk_score
                * r.scenario.probability_weight
                for r in results
            ),
            _ZERO,
        )

        weight = sum(
            (
                r.scenario.probability_weight
                for r in results
            ),
            _ZERO,
        )

        return total / weight if weight else _ZERO

    @staticmethod
    def _validate_inputs(
        *,
        initial_equity: Decimal,
        maximum_risk_score: Decimal,
    ) -> None:

        if not isinstance(
            initial_equity,
            Decimal,
        ):
            raise TypeError(
                "initial_equity must be a Decimal"
            )

        if initial_equity <= _ZERO:
            raise ValueError(
                "initial_equity must be greater than zero"
            )

        if not isinstance(
            maximum_risk_score,
            Decimal,
        ):
            raise TypeError(
                "maximum_risk_score must be a Decimal"
            )

        if not (
            _ZERO
            <= maximum_risk_score
            <= _ONE
        ):
            raise ValueError(
                "maximum_risk_score must be between 0 and 1"
            )