from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Iterable


_ZERO = Decimal("0")
_ONE = Decimal("1")


class StrategyQualityAnalyzer:
    """Calculates advanced strategy-quality metrics."""

    @staticmethod
    def system_quality_number(
        trade_results: Iterable[Decimal],
    ) -> Decimal:
        results = tuple(trade_results)

        if len(results) < 2:
            return _ZERO

        count = Decimal(len(results))
        mean_result = sum(results, _ZERO) / count

        squared_deviations = [
            (result - mean_result) ** 2
            for result in results
        ]

        sample_variance = (
            sum(squared_deviations, _ZERO)
            / Decimal(len(results) - 1)
        )

        if sample_variance == _ZERO:
            return _ZERO

        with localcontext() as context:
            context.prec = 28
            standard_deviation = sample_variance.sqrt()
            return count.sqrt() * mean_result / standard_deviation

    @staticmethod
    def kelly_criterion(
        *,
        win_rate: Decimal,
        payoff_ratio: Decimal,
    ) -> Decimal:
        if payoff_ratio <= _ZERO:
            return _ZERO

        loss_rate = _ONE - win_rate

        return win_rate - (loss_rate / payoff_ratio)

    @staticmethod
    def gain_to_pain_ratio(
        returns: Iterable[Decimal],
    ) -> Decimal:
        values = tuple(returns)

        total_gain = sum(
            (
                value
                for value in values
                if value > _ZERO
            ),
            _ZERO,
        )

        total_pain = abs(
            sum(
                (
                    value
                    for value in values
                    if value < _ZERO
                ),
                _ZERO,
            )
        )

        if total_pain == _ZERO:
            return _ZERO

        return total_gain / total_pain

    @staticmethod
    def ulcer_index(
        equity_values: Iterable[Decimal],
    ) -> Decimal:
        values = tuple(equity_values)

        if not values:
            return _ZERO

        peak = values[0]
        squared_drawdowns: list[Decimal] = []

        for equity in values:
            if equity > peak:
                peak = equity

            if peak <= _ZERO:
                drawdown = _ZERO
            else:
                drawdown = (peak - equity) / peak

            squared_drawdowns.append(drawdown**2)

        mean_squared_drawdown = (
            sum(squared_drawdowns, _ZERO)
            / Decimal(len(squared_drawdowns))
        )

        with localcontext() as context:
            context.prec = 28
            return mean_squared_drawdown.sqrt()