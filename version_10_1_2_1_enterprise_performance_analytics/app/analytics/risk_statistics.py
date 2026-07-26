from __future__ import annotations

from math import sqrt
from statistics import pstdev
from typing import Iterable


class RiskStatistics:
    def calculate(self, equity_values: Iterable[float], allocation: dict[str, float]) -> dict[str, float]:
        values = tuple(float(value) for value in equity_values)
        returns = tuple(
            0.0 if previous == 0 else (current - previous) / previous
            for previous, current in zip(values, values[1:])
        )
        volatility = pstdev(returns) * sqrt(252) if len(returns) > 1 else 0.0
        maximum_drawdown = self.maximum_drawdown(values)
        concentration = max(allocation.values(), default=0.0)
        return {
            "maximum_drawdown": maximum_drawdown,
            "annualized_volatility": volatility,
            "largest_position_weight": concentration,
            "herfindahl_index": sum(weight * weight for weight in allocation.values()),
        }

    @staticmethod
    def maximum_drawdown(values: Iterable[float]) -> float:
        peak = 0.0
        maximum = 0.0
        for value in values:
            peak = max(peak, float(value))
            if peak > 0:
                maximum = max(maximum, (peak - float(value)) / peak)
        return maximum
