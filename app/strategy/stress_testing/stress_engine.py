from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from .stress_models import (
    StressScenario,
    StressScenarioResult,
    StressTestReport,
    StressTestStatus,
)


_ZERO = Decimal("0")
_ONE = Decimal("1")


class StressTestEngine:
    """Executes deterministic portfolio stress scenarios."""

    def run(
        self,
        *,
        initial_equity: Decimal,
        scenarios: Iterable[StressScenario],
        loss_limit: Decimal = Decimal("0.20"),
    ) -> StressTestReport:
        scenario_list = tuple(scenarios)

        self._validate_inputs(
            initial_equity=initial_equity,
            loss_limit=loss_limit,
        )

        if not scenario_list:
            return StressTestReport(
                status=StressTestStatus.COMPLETED,
                results=(),
                worst_case_loss_percent=_ZERO,
                average_loss_percent=_ZERO,
                breach_count=0,
                warnings=(
                    "No stress scenarios were supplied.",
                ),
            )

        results: list[StressScenarioResult] = []

        try:
            for scenario in scenario_list:
                if not isinstance(
                    scenario,
                    StressScenario,
                ):
                    raise TypeError(
                        "every scenario must be a StressScenario"
                    )

                results.append(
                    self._apply_scenario(
                        scenario=scenario,
                        initial_equity=initial_equity,
                        loss_limit=loss_limit,
                    )
                )

        except Exception as exc:
            return StressTestReport(
                status=StressTestStatus.FAILED,
                results=tuple(results),
                worst_case_loss_percent=(
                    self._worst_case_loss(results)
                ),
                average_loss_percent=(
                    self._average_loss(results)
                ),
                breach_count=self._breach_count(results),
                warnings=(
                    "Stress-test execution stopped before all "
                    "scenarios completed.",
                ),
                error=str(exc),
            )

        warnings = tuple(
            warning
            for result in results
            for warning in result.warnings
        )

        return StressTestReport(
            status=StressTestStatus.COMPLETED,
            results=tuple(results),
            worst_case_loss_percent=(
                self._worst_case_loss(results)
            ),
            average_loss_percent=(
                self._average_loss(results)
            ),
            breach_count=self._breach_count(results),
            warnings=warnings,
        )

    @staticmethod
    def _apply_scenario(
        *,
        scenario: StressScenario,
        initial_equity: Decimal,
        loss_limit: Decimal,
    ) -> StressScenarioResult:
        market_factor = _ONE + scenario.market_return_shock
        liquidity_factor = _ONE - scenario.liquidity_haircut

        stressed_equity = (
            initial_equity
            * market_factor
            * liquidity_factor
        )

        if stressed_equity < _ZERO:
            stressed_equity = _ZERO

        loss_amount = max(
            initial_equity - stressed_equity,
            _ZERO,
        )

        loss_percent = (
            loss_amount / initial_equity
        )

        breached_limit = (
            loss_percent >= loss_limit
        )

        warnings: list[str] = []

        if breached_limit:
            warnings.append(
                f"{scenario.scenario_id} breached the loss limit."
            )

        if scenario.volatility_multiplier > _ONE:
            warnings.append(
                f"{scenario.scenario_id} includes elevated volatility."
            )

        return StressScenarioResult(
            scenario=scenario,
            initial_equity=initial_equity,
            stressed_equity=stressed_equity,
            loss_amount=loss_amount,
            loss_percent=loss_percent,
            breached_limit=breached_limit,
            warnings=tuple(warnings),
        )

    @staticmethod
    def _worst_case_loss(
        results: Iterable[StressScenarioResult],
    ) -> Decimal:
        completed = tuple(results)

        if not completed:
            return _ZERO

        return max(
            result.loss_percent
            for result in completed
        )

    @staticmethod
    def _average_loss(
        results: Iterable[StressScenarioResult],
    ) -> Decimal:
        completed = tuple(results)

        if not completed:
            return _ZERO

        return (
            sum(
                (
                    result.loss_percent
                    for result in completed
                ),
                _ZERO,
            )
            / Decimal(len(completed))
        )

    @staticmethod
    def _breach_count(
        results: Iterable[StressScenarioResult],
    ) -> int:
        return sum(
            1
            for result in results
            if result.breached_limit
        )

    @staticmethod
    def _validate_inputs(
        *,
        initial_equity: Decimal,
        loss_limit: Decimal,
    ) -> None:
        if not isinstance(initial_equity, Decimal):
            raise TypeError(
                "initial_equity must be a Decimal"
            )

        if initial_equity <= _ZERO:
            raise ValueError(
                "initial_equity must be greater than zero"
            )

        if not isinstance(loss_limit, Decimal):
            raise TypeError(
                "loss_limit must be a Decimal"
            )

        if not _ZERO <= loss_limit <= _ONE:
            raise ValueError(
                "loss_limit must be between 0 and 1"
            )