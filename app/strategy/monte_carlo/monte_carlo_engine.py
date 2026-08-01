from __future__ import annotations

from decimal import Decimal
from random import Random
from typing import Iterable

from .monte_carlo_models import (
    MonteCarloPathResult,
    MonteCarloReport,
    MonteCarloStatus,
)


_ZERO = Decimal("0")
_ONE = Decimal("1")
_ONE_HUNDRED = Decimal("100")


class MonteCarloEngine:
    """Runs reproducible bootstrap simulations of strategy returns."""

    def run(
        self,
        *,
        trade_returns: Iterable[Decimal],
        initial_capital: Decimal,
        simulations: int,
        seed: int = 42,
        ruin_threshold: Decimal = Decimal("0.50"),
    ) -> MonteCarloReport:
        returns = tuple(trade_returns)

        self._validate_inputs(
            trade_returns=returns,
            initial_capital=initial_capital,
            simulations=simulations,
            seed=seed,
            ruin_threshold=ruin_threshold,
        )

        if not returns:
            return MonteCarloReport(
                status=MonteCarloStatus.COMPLETED,
                paths=(),
                ruin_probability=_ZERO,
                median_final_equity=initial_capital,
                percentile_05_final_equity=initial_capital,
                percentile_95_final_equity=initial_capital,
                median_max_drawdown=_ZERO,
                warnings=(
                    "No trade returns were supplied.",
                ),
            )

        random_generator = Random(seed)
        paths: list[MonteCarloPathResult] = []

        try:
            for path_id in range(1, simulations + 1):
                sampled_returns = tuple(
                    random_generator.choice(returns)
                    for _ in range(len(returns))
                )

                paths.append(
                    self._simulate_path(
                        path_id=path_id,
                        sampled_returns=sampled_returns,
                        initial_capital=initial_capital,
                        ruin_threshold=ruin_threshold,
                    )
                )
        except Exception as exc:
            return MonteCarloReport(
                status=MonteCarloStatus.FAILED,
                paths=tuple(paths),
                ruin_probability=self._ruin_probability(paths),
                median_final_equity=self._median(
                    tuple(
                        path.final_equity
                        for path in paths
                    )
                ),
                percentile_05_final_equity=self._percentile(
                    tuple(
                        path.final_equity
                        for path in paths
                    ),
                    Decimal("0.05"),
                ),
                percentile_95_final_equity=self._percentile(
                    tuple(
                        path.final_equity
                        for path in paths
                    ),
                    Decimal("0.95"),
                ),
                median_max_drawdown=self._median(
                    tuple(
                        path.max_drawdown
                        for path in paths
                    )
                ),
                warnings=(
                    "Monte Carlo execution stopped before all "
                    "simulation paths completed.",
                ),
                error=str(exc),
            )

        final_equities = tuple(
            path.final_equity
            for path in paths
        )
        maximum_drawdowns = tuple(
            path.max_drawdown
            for path in paths
        )

        warnings: list[str] = []

        ruin_probability = self._ruin_probability(paths)

        if ruin_probability > _ZERO:
            warnings.append(
                "One or more simulation paths reached the ruin threshold."
            )

        return MonteCarloReport(
            status=MonteCarloStatus.COMPLETED,
            paths=tuple(paths),
            ruin_probability=ruin_probability,
            median_final_equity=self._median(
                final_equities
            ),
            percentile_05_final_equity=self._percentile(
                final_equities,
                Decimal("0.05"),
            ),
            percentile_95_final_equity=self._percentile(
                final_equities,
                Decimal("0.95"),
            ),
            median_max_drawdown=self._median(
                maximum_drawdowns
            ),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _simulate_path(
        *,
        path_id: int,
        sampled_returns: tuple[Decimal, ...],
        initial_capital: Decimal,
        ruin_threshold: Decimal,
    ) -> MonteCarloPathResult:
        equity = initial_capital
        peak_equity = initial_capital
        maximum_drawdown = _ZERO

        ruin_equity = (
            initial_capital
            * ruin_threshold
        )
        ruined = False

        for trade_return in sampled_returns:
            equity *= _ONE + trade_return

            if equity < _ZERO:
                equity = _ZERO

            if equity > peak_equity:
                peak_equity = equity

            if peak_equity > _ZERO:
                drawdown = (
                    peak_equity - equity
                ) / peak_equity
            else:
                drawdown = _ZERO

            if drawdown > maximum_drawdown:
                maximum_drawdown = drawdown

            if equity <= ruin_equity:
                ruined = True

        total_return = (
            equity - initial_capital
        ) / initial_capital

        return MonteCarloPathResult(
            path_id=path_id,
            final_equity=equity,
            total_return=total_return,
            max_drawdown=maximum_drawdown,
            ruined=ruined,
        )

    @staticmethod
    def _ruin_probability(
        paths: Iterable[MonteCarloPathResult],
    ) -> Decimal:
        completed = tuple(paths)

        if not completed:
            return _ZERO

        ruined_count = sum(
            1
            for path in completed
            if path.ruined
        )

        return (
            Decimal(ruined_count)
            / Decimal(len(completed))
        )

    @classmethod
    def _median(
        cls,
        values: tuple[Decimal, ...],
    ) -> Decimal:
        if not values:
            return _ZERO

        ordered = tuple(sorted(values))
        count = len(ordered)
        midpoint = count // 2

        if count % 2 == 1:
            return ordered[midpoint]

        return (
            ordered[midpoint - 1]
            + ordered[midpoint]
        ) / Decimal("2")

    @staticmethod
    def _percentile(
        values: tuple[Decimal, ...],
        percentile: Decimal,
    ) -> Decimal:
        if not values:
            return _ZERO

        ordered = tuple(sorted(values))

        if len(ordered) == 1:
            return ordered[0]

        position = (
            Decimal(len(ordered) - 1)
            * percentile
        )

        lower_index = int(position)
        upper_index = min(
            lower_index + 1,
            len(ordered) - 1,
        )

        fraction = (
            position
            - Decimal(lower_index)
        )

        lower_value = ordered[lower_index]
        upper_value = ordered[upper_index]

        return (
            lower_value
            + (upper_value - lower_value)
            * fraction
        )

    @staticmethod
    def _validate_inputs(
        *,
        trade_returns: tuple[Decimal, ...],
        initial_capital: Decimal,
        simulations: int,
        seed: int,
        ruin_threshold: Decimal,
    ) -> None:
        if not isinstance(initial_capital, Decimal):
            raise TypeError(
                "initial_capital must be a Decimal"
            )

        if initial_capital <= _ZERO:
            raise ValueError(
                "initial_capital must be greater than zero"
            )

        if not isinstance(simulations, int):
            raise TypeError(
                "simulations must be an integer"
            )

        if simulations <= 0:
            raise ValueError(
                "simulations must be greater than zero"
            )

        if not isinstance(seed, int):
            raise TypeError(
                "seed must be an integer"
            )

        if not isinstance(ruin_threshold, Decimal):
            raise TypeError(
                "ruin_threshold must be a Decimal"
            )

        if not _ZERO <= ruin_threshold <= _ONE:
            raise ValueError(
                "ruin_threshold must be between 0 and 1"
            )

        for trade_return in trade_returns:
            if not isinstance(trade_return, Decimal):
                raise TypeError(
                    "every trade return must be a Decimal"
                )

            if trade_return < -_ONE:
                raise ValueError(
                    "trade returns must not be less than -1"
                )