"""
Portfolio Snapshot Adapter
AI Trading Platform Version 7.6

Converts IBKR account summary and position data into the
standard PortfolioSnapshot model used by the risk manager.
"""

from __future__ import annotations

from typing import Any

from app.models.portfolio_risk_models import (
    PortfolioSnapshot,
)


def _to_float(
    value: Any,
    *,
    default: float = 0.0,
) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _summary_by_tag(
    account_summary: list[dict[str, Any]],
) -> dict[str, float]:
    values: dict[str, float] = {}

    for item in account_summary:
        tag = str(item.get("tag", "")).strip()

        if not tag:
            continue

        values[tag] = _to_float(
            item.get("value"),
        )

    return values


def build_portfolio_snapshot(
    *,
    account_summary: list[dict[str, Any]],
    positions: list[dict[str, Any]],
    peak_net_liquidation: float | None = None,
) -> PortfolioSnapshot:
    """
    Build a PortfolioSnapshot from IBKR account and position data.

    The adapter does not connect to IBKR directly. It accepts data
    already returned by the broker layer, which keeps it testable.
    """

    summary = _summary_by_tag(account_summary)

    net_liquidation = summary.get(
        "NetLiquidation",
        0.0,
    )

    buying_power = summary.get(
        "BuyingPower",
        0.0,
    )

    gross_position_value = summary.get(
        "GrossPositionValue",
        0.0,
    )

    realized_pnl = summary.get(
        "RealizedPnL",
        0.0,
    )

    unrealized_pnl = summary.get(
        "UnrealizedPnL",
        0.0,
    )

    symbol_position_values: dict[str, float] = {}
    open_position_count = 0

    for position in positions:
        quantity = _to_float(
            position.get("position"),
        )

        if quantity == 0:
            continue

        symbol = str(
            position.get("symbol", "")
        ).strip().upper()

        if not symbol:
            continue

        average_cost = _to_float(
            position.get("avgCost"),
        )

        position_value = abs(
            quantity * average_cost
        )

        symbol_position_values[symbol] = (
            symbol_position_values.get(symbol, 0.0)
            + position_value
        )

        open_position_count += 1

    calculated_position_value = sum(
        symbol_position_values.values()
    )

    total_position_value = (
        gross_position_value
        if gross_position_value > 0
        else calculated_position_value
    )

    drawdown_percent = 0.0

    if (
        peak_net_liquidation is not None
        and peak_net_liquidation > 0
        and net_liquidation > 0
    ):
        drawdown_percent = max(
            (
                peak_net_liquidation
                - net_liquidation
            )
            / peak_net_liquidation
            * 100.0,
            0.0,
        )

    return PortfolioSnapshot(
        net_liquidation=net_liquidation,
        buying_power=buying_power,
        total_position_value=total_position_value,
        open_position_count=open_position_count,
        daily_realized_pnl=realized_pnl,
        daily_unrealized_pnl=unrealized_pnl,
        drawdown_percent=drawdown_percent,
        symbol_position_values=symbol_position_values,
    )