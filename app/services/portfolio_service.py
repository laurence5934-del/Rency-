"""
Portfolio Service
AI Trading Platform Version 9

Creates a complete, immutable portfolio summary from PortfolioSnapshot.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.models.portfolio_risk_models import PortfolioSnapshot
from app.services.portfolio_metrics import (
    calculate_buying_power_percent,
    calculate_cash_percent,
    calculate_cash_value,
    calculate_daily_return_percent,
    calculate_exposure_percent,
    calculate_largest_position,
    calculate_largest_position_percent,
    calculate_portfolio_health_score,
    calculate_position_weights,
    calculate_utilization_percent,
    classify_portfolio_health,
)


@dataclass(frozen=True)
class PortfolioSummary:
    net_liquidation: float
    buying_power: float
    cash_value: float
    market_value: float
    open_position_count: int
    daily_realized_pnl: float
    daily_unrealized_pnl: float
    daily_total_pnl: float
    daily_return_percent: float
    exposure_percent: float
    utilization_percent: float
    buying_power_percent: float
    cash_percent: float
    drawdown_percent: float
    largest_position_symbol: str | None
    largest_position_value: float
    largest_position_percent: float
    position_weights: dict[str, float]
    health_score: float
    health_status: str

    def to_dict(self) -> dict[str, Any]:
        """Return a dashboard/API-friendly dictionary."""
        result = asdict(self)

        money_fields = (
            "net_liquidation",
            "buying_power",
            "cash_value",
            "market_value",
            "daily_realized_pnl",
            "daily_unrealized_pnl",
            "daily_total_pnl",
            "largest_position_value",
        )
        percent_fields = (
            "daily_return_percent",
            "exposure_percent",
            "utilization_percent",
            "buying_power_percent",
            "cash_percent",
            "drawdown_percent",
            "largest_position_percent",
            "health_score",
        )

        for field_name in money_fields:
            result[field_name] = round(float(result[field_name]), 2)

        for field_name in percent_fields:
            result[field_name] = round(float(result[field_name]), 2)

        result["position_weights"] = {
            symbol: round(float(weight), 2)
            for symbol, weight in self.position_weights.items()
        }
        return result


class PortfolioService:
    """Build portfolio analytics from an existing PortfolioSnapshot."""

    def __init__(
        self,
        *,
        maximum_exposure_percent: float = 80.0,
        maximum_drawdown_percent: float = 10.0,
        concentration_warning_percent: float = 20.0,
    ) -> None:
        self.maximum_exposure_percent = maximum_exposure_percent
        self.maximum_drawdown_percent = maximum_drawdown_percent
        self.concentration_warning_percent = concentration_warning_percent

    def get_summary(self, snapshot: PortfolioSnapshot) -> PortfolioSummary:
        """Calculate a complete portfolio summary."""
        largest_symbol, largest_value = calculate_largest_position(snapshot)

        health_score = calculate_portfolio_health_score(
            snapshot,
            maximum_exposure_percent=self.maximum_exposure_percent,
            maximum_drawdown_percent=self.maximum_drawdown_percent,
            concentration_warning_percent=self.concentration_warning_percent,
        )

        return PortfolioSummary(
            net_liquidation=float(snapshot.net_liquidation),
            buying_power=float(snapshot.buying_power),
            cash_value=calculate_cash_value(snapshot),
            market_value=float(snapshot.total_position_value),
            open_position_count=int(snapshot.open_position_count),
            daily_realized_pnl=float(snapshot.daily_realized_pnl),
            daily_unrealized_pnl=float(snapshot.daily_unrealized_pnl),
            daily_total_pnl=float(snapshot.daily_total_pnl),
            daily_return_percent=calculate_daily_return_percent(snapshot),
            exposure_percent=calculate_exposure_percent(snapshot),
            utilization_percent=calculate_utilization_percent(snapshot),
            buying_power_percent=calculate_buying_power_percent(snapshot),
            cash_percent=calculate_cash_percent(snapshot),
            drawdown_percent=float(snapshot.drawdown_percent),
            largest_position_symbol=largest_symbol,
            largest_position_value=largest_value,
            largest_position_percent=calculate_largest_position_percent(snapshot),
            position_weights=calculate_position_weights(snapshot),
            health_score=health_score,
            health_status=classify_portfolio_health(health_score),
        )
