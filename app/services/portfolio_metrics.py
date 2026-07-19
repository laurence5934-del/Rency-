"""
Portfolio Metrics
AI Trading Platform Version 9

Pure calculation helpers for portfolio-level analytics.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeAlias

from app.models.portfolio_risk_models import PortfolioSnapshot

Number: TypeAlias = int | float


def _safe_percent(numerator: Number, denominator: Number) -> float:
    """Return numerator / denominator * 100, or 0 when denominator is invalid."""
    denominator_value = float(denominator)
    if denominator_value <= 0:
        return 0.0
    return float(numerator) / denominator_value * 100.0


def calculate_exposure_percent(snapshot: PortfolioSnapshot) -> float:
    """Gross portfolio exposure as a percentage of net liquidation value."""
    return _safe_percent(
        snapshot.total_position_value,
        snapshot.net_liquidation,
    )


def calculate_buying_power_percent(snapshot: PortfolioSnapshot) -> float:
    """Buying power as a percentage of net liquidation value."""
    return _safe_percent(
        snapshot.buying_power,
        snapshot.net_liquidation,
    )


def calculate_cash_value(snapshot: PortfolioSnapshot) -> float:
    """
    Estimate uninvested equity.

    This is net liquidation minus gross position value. It is intentionally
    floored at zero because margin accounts can otherwise produce a negative
    estimate that is not useful as a dashboard cash-allocation metric.
    """
    return max(
        float(snapshot.net_liquidation)
        - float(snapshot.total_position_value),
        0.0,
    )


def calculate_cash_percent(snapshot: PortfolioSnapshot) -> float:
    """Estimated cash as a percentage of net liquidation value."""
    return _safe_percent(
        calculate_cash_value(snapshot),
        snapshot.net_liquidation,
    )


def calculate_utilization_percent(snapshot: PortfolioSnapshot) -> float:
    """
    Capital utilization percentage.

    For the current model, utilization is equivalent to gross exposure.
    The separate function keeps dashboard and service code expressive and
    allows the formula to evolve later without changing callers.
    """
    return calculate_exposure_percent(snapshot)


def calculate_daily_return_percent(snapshot: PortfolioSnapshot) -> float:
    """Daily total P/L as a percentage of net liquidation value."""
    return _safe_percent(
        snapshot.daily_total_pnl,
        snapshot.net_liquidation,
    )


def calculate_largest_position(
    snapshot: PortfolioSnapshot,
) -> tuple[str | None, float]:
    """Return the largest position symbol and absolute position value."""
    if not snapshot.symbol_position_values:
        return None, 0.0

    symbol, value = max(
        snapshot.symbol_position_values.items(),
        key=lambda item: abs(float(item[1])),
    )
    return str(symbol).upper(), abs(float(value))


def calculate_largest_position_percent(snapshot: PortfolioSnapshot) -> float:
    """Largest individual position as a percentage of net liquidation value."""
    _, largest_value = calculate_largest_position(snapshot)
    return _safe_percent(largest_value, snapshot.net_liquidation)


def calculate_position_weights(
    snapshot: PortfolioSnapshot,
) -> dict[str, float]:
    """Return each symbol's weight as a percentage of net liquidation value."""
    if snapshot.net_liquidation <= 0:
        return {
            str(symbol).upper(): 0.0
            for symbol in snapshot.symbol_position_values
        }

    return {
        str(symbol).upper(): _safe_percent(
            abs(float(value)),
            snapshot.net_liquidation,
        )
        for symbol, value in snapshot.symbol_position_values.items()
    }


def calculate_portfolio_health_score(
    snapshot: PortfolioSnapshot,
    *,
    maximum_exposure_percent: float = 80.0,
    maximum_drawdown_percent: float = 10.0,
    concentration_warning_percent: float = 20.0,
) -> float:
    """
    Calculate a 0-100 portfolio health score.

    The score penalizes:
    - exposure above the configured maximum,
    - drawdown approaching or exceeding the configured maximum,
    - excessive single-position concentration,
    - negative daily return.

    It is a dashboard indicator, not a replacement for the risk manager.
    """
    score = 100.0

    exposure = calculate_exposure_percent(snapshot)
    if maximum_exposure_percent > 0:
        exposure_ratio = exposure / maximum_exposure_percent
        if exposure_ratio > 1:
            score -= min((exposure_ratio - 1) * 40.0 + 20.0, 45.0)
        elif exposure_ratio >= 0.8:
            score -= (exposure_ratio - 0.8) / 0.2 * 15.0

    if maximum_drawdown_percent > 0:
        drawdown_ratio = max(float(snapshot.drawdown_percent), 0.0) / maximum_drawdown_percent
        score -= min(drawdown_ratio * 30.0, 40.0)

    concentration = calculate_largest_position_percent(snapshot)
    if concentration_warning_percent > 0 and concentration > concentration_warning_percent:
        excess_ratio = (
            concentration - concentration_warning_percent
        ) / concentration_warning_percent
        score -= min(10.0 + excess_ratio * 20.0, 30.0)

    daily_return = calculate_daily_return_percent(snapshot)
    if daily_return < 0:
        score -= min(abs(daily_return) * 5.0, 20.0)

    return round(min(max(score, 0.0), 100.0), 2)


def classify_portfolio_health(score: Number) -> str:
    """Convert a numeric portfolio health score to a dashboard label."""
    value = float(score)
    if value >= 90:
        return "EXCELLENT"
    if value >= 75:
        return "HEALTHY"
    if value >= 60:
        return "WATCH"
    if value >= 40:
        return "HIGH_RISK"
    return "CRITICAL"
