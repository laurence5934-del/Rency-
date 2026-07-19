"""
Portfolio History
AI Trading Platform Version 9

In-memory performance-history models and calculations. Persistence can be
added later through a repository without changing the public API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import sqrt
from statistics import mean, pstdev


@dataclass(frozen=True, order=True)
class PortfolioHistoryPoint:
    snapshot_date: date
    net_liquidation: float
    daily_pnl: float = 0.0


def calculate_total_return_percent(
    history: list[PortfolioHistoryPoint],
) -> float:
    """Calculate total return from the first to the last history point."""
    if len(history) < 2:
        return 0.0

    ordered = sorted(history)
    starting_value = float(ordered[0].net_liquidation)
    ending_value = float(ordered[-1].net_liquidation)

    if starting_value <= 0:
        return 0.0

    return (ending_value - starting_value) / starting_value * 100.0


def calculate_max_drawdown_percent(
    history: list[PortfolioHistoryPoint],
) -> float:
    """Calculate maximum peak-to-trough drawdown."""
    if not history:
        return 0.0

    peak = 0.0
    max_drawdown = 0.0

    for point in sorted(history):
        value = float(point.net_liquidation)
        if value <= 0:
            continue

        peak = max(peak, value)
        if peak > 0:
            drawdown = (peak - value) / peak * 100.0
            max_drawdown = max(max_drawdown, drawdown)

    return max_drawdown


def calculate_daily_returns(
    history: list[PortfolioHistoryPoint],
) -> list[float]:
    """Calculate decimal daily returns between consecutive snapshots."""
    ordered = sorted(history)
    returns: list[float] = []

    for previous, current in zip(ordered, ordered[1:]):
        previous_value = float(previous.net_liquidation)
        current_value = float(current.net_liquidation)

        if previous_value <= 0:
            continue

        returns.append(
            (current_value - previous_value) / previous_value
        )

    return returns


def calculate_annualized_sharpe_ratio(
    history: list[PortfolioHistoryPoint],
    *,
    risk_free_rate: float = 0.0,
    trading_days_per_year: int = 252,
) -> float:
    """
    Calculate an annualized Sharpe ratio from daily equity returns.

    risk_free_rate is an annual decimal rate, for example 0.04 for 4%.
    """
    returns = calculate_daily_returns(history)
    if len(returns) < 2:
        return 0.0

    daily_risk_free_rate = (
        (1.0 + risk_free_rate) ** (1.0 / trading_days_per_year) - 1.0
    )
    excess_returns = [
        daily_return - daily_risk_free_rate
        for daily_return in returns
    ]

    volatility = pstdev(excess_returns)
    if volatility == 0:
        return 0.0

    return mean(excess_returns) / volatility * sqrt(trading_days_per_year)
