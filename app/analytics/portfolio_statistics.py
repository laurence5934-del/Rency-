from __future__ import annotations

from typing import Iterable

from .models import PortfolioObservation


class PortfolioStatistics:
    def calculate(self, observation: PortfolioObservation) -> dict[str, object]:
        positions = tuple(observation.positions)
        market_values = [abs(float(p.get("market_value", 0.0))) for p in positions]
        gross_exposure = sum(market_values)
        allocation = {
            str(p.get("symbol", "UNKNOWN")): (abs(float(p.get("market_value", 0.0))) / gross_exposure if gross_exposure else 0.0)
            for p in positions
        }
        return {
            "cash": observation.cash,
            "buying_power": observation.buying_power,
            "portfolio_value": observation.portfolio_value,
            "realized_pnl": observation.realized_pnl,
            "unrealized_pnl": observation.unrealized_pnl,
            "total_pnl": observation.realized_pnl + observation.unrealized_pnl,
            "position_count": len(positions),
            "gross_exposure": gross_exposure,
            "allocation": allocation,
            "timestamp_utc": observation.timestamp_utc,
        }

    def returns(self, values: Iterable[float]) -> tuple[float, ...]:
        series = tuple(float(v) for v in values)
        if len(series) < 2:
            return ()
        result: list[float] = []
        for previous, current in zip(series, series[1:]):
            result.append(0.0 if previous == 0 else (current - previous) / previous)
        return tuple(result)
