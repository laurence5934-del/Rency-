"""
Portfolio Intelligence Layer
AI Trading Platform Version 9.1

Builds a single dashboard-ready portfolio view from the existing
IBKR account summary, positions, portfolio snapshot adapter, and
portfolio risk limits. This module never submits orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.broker.portfolio_snapshot_adapter import build_portfolio_snapshot
from app.models.portfolio_risk_models import PortfolioRiskLimits, PortfolioSnapshot


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _summary_values(account_summary: list[dict[str, Any]]) -> dict[str, float]:
    values: dict[str, float] = {}
    for row in account_summary:
        tag = str(row.get("tag", "")).strip()
        if tag:
            values[tag] = _to_float(row.get("value"))
    return values


@dataclass(frozen=True, slots=True)
class PortfolioAdvisor:
    risk_level: str
    recommendation: str
    suggested_position_size: float
    can_open_new_position: bool
    checks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PortfolioIntelligence:
    snapshot: PortfolioSnapshot
    available_funds: float
    total_cash: float
    exposure_percent: float
    buying_power_percent: float
    cash_percent: float
    utilization_percent: float
    largest_position_symbol: str | None
    largest_position_value: float
    largest_position_percent: float
    health_score: int
    health_status: str
    advisor: PortfolioAdvisor

    def to_dict(self) -> dict[str, Any]:
        return {
            "net_liquidation": round(self.snapshot.net_liquidation, 2),
            "buying_power": round(self.snapshot.buying_power, 2),
            "available_funds": round(self.available_funds, 2),
            "total_cash": round(self.total_cash, 2),
            "daily_total_pnl": round(self.snapshot.daily_total_pnl, 2),
            "total_position_value": round(self.snapshot.total_position_value, 2),
            "open_position_count": self.snapshot.open_position_count,
            "drawdown_percent": round(self.snapshot.drawdown_percent, 2),
            "exposure_percent": round(self.exposure_percent, 2),
            "buying_power_percent": round(self.buying_power_percent, 2),
            "cash_percent": round(self.cash_percent, 2),
            "utilization_percent": round(self.utilization_percent, 2),
            "largest_position_symbol": self.largest_position_symbol,
            "largest_position_value": round(self.largest_position_value, 2),
            "largest_position_percent": round(self.largest_position_percent, 2),
            "health_score": self.health_score,
            "health_status": self.health_status,
            "advisor": {
                "risk_level": self.advisor.risk_level,
                "recommendation": self.advisor.recommendation,
                "suggested_position_size": round(self.advisor.suggested_position_size, 2),
                "can_open_new_position": self.advisor.can_open_new_position,
                "checks": list(self.advisor.checks),
            },
        }


def _percent(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return max(numerator / denominator * 100.0, 0.0)


def _health_status(score: int) -> str:
    if score >= 85:
        return "HEALTHY"
    if score >= 70:
        return "WATCH"
    if score >= 50:
        return "ELEVATED RISK"
    return "CRITICAL"


def _risk_level(score: int) -> str:
    if score >= 85:
        return "LOW"
    if score >= 70:
        return "MODERATE"
    if score >= 50:
        return "HIGH"
    return "CRITICAL"


def _calculate_health_score(
    snapshot: PortfolioSnapshot,
    limits: PortfolioRiskLimits,
    exposure_percent: float,
) -> int:
    score = 100.0

    if limits.maximum_portfolio_exposure_percent > 0:
        ratio = exposure_percent / limits.maximum_portfolio_exposure_percent
        if ratio > 1:
            score -= 35
        elif ratio >= 0.9:
            score -= 22
        elif ratio >= 0.8:
            score -= 12

    if limits.maximum_drawdown_percent > 0:
        ratio = snapshot.drawdown_percent / limits.maximum_drawdown_percent
        if ratio >= 1:
            score -= 35
        elif ratio >= 0.8:
            score -= 22
        elif ratio >= 0.5:
            score -= 10

    if snapshot.daily_total_pnl < 0 and limits.maximum_daily_loss > 0:
        ratio = abs(snapshot.daily_total_pnl) / limits.maximum_daily_loss
        if ratio >= 1:
            score -= 30
        elif ratio >= 0.8:
            score -= 18
        elif ratio >= 0.5:
            score -= 8

    if snapshot.open_position_count >= limits.maximum_open_positions:
        score -= 18
    elif snapshot.open_position_count >= max(limits.maximum_open_positions - 2, 1):
        score -= 8

    if snapshot.buying_power < limits.minimum_buying_power:
        score -= 20

    if snapshot.net_liquidation <= 0:
        score = 0

    return max(0, min(100, int(round(score))))


def _build_advisor(
    snapshot: PortfolioSnapshot,
    limits: PortfolioRiskLimits,
    health_score: int,
    exposure_percent: float,
) -> PortfolioAdvisor:
    checks: list[str] = []
    exposure_ok = exposure_percent < limits.maximum_portfolio_exposure_percent
    positions_ok = snapshot.open_position_count < limits.maximum_open_positions
    buying_power_ok = snapshot.buying_power > limits.minimum_buying_power
    daily_loss_ok = snapshot.daily_total_pnl > -abs(limits.maximum_daily_loss)
    drawdown_ok = snapshot.drawdown_percent < limits.maximum_drawdown_percent

    checks.append("Exposure is within limits." if exposure_ok else "Exposure limit is reached.")
    checks.append("Open-position capacity is available." if positions_ok else "Open-position limit is reached.")
    checks.append("Buying power reserve is healthy." if buying_power_ok else "Buying power reserve is too low.")
    checks.append("Daily loss limit is clear." if daily_loss_ok else "Daily loss limit is reached.")
    checks.append("Drawdown is within limits." if drawdown_ok else "Maximum drawdown is reached.")

    remaining_exposure_value = max(
        snapshot.net_liquidation * limits.maximum_portfolio_exposure_percent / 100.0
        - snapshot.total_position_value,
        0.0,
    )
    buying_power_capacity = max(
        snapshot.buying_power - limits.minimum_buying_power,
        0.0,
    )
    suggested_size = max(
        min(
            limits.maximum_order_value,
            limits.maximum_position_value,
            remaining_exposure_value,
            buying_power_capacity,
        ),
        0.0,
    )

    can_open = all((
        exposure_ok,
        positions_ok,
        buying_power_ok,
        daily_loss_ok,
        drawdown_ok,
        suggested_size > 0,
    ))

    if can_open and health_score >= 70:
        recommendation = (
            "Portfolio limits permit one additional paper-trade position, "
            "subject to symbol-level risk approval."
        )
    elif can_open:
        recommendation = (
            "Capacity exists, but portfolio health is elevated. "
            "Use a reduced paper position and manual review."
        )
        suggested_size *= 0.5
    else:
        recommendation = (
            "Do not open another position until the failed portfolio checks are resolved."
        )
        suggested_size = 0.0

    return PortfolioAdvisor(
        risk_level=_risk_level(health_score),
        recommendation=recommendation,
        suggested_position_size=suggested_size,
        can_open_new_position=can_open,
        checks=tuple(checks),
    )


def build_portfolio_intelligence(
    *,
    account_data: dict[str, Any],
    positions_data: dict[str, Any],
    peak_net_liquidation: float | None = None,
    limits: PortfolioRiskLimits | None = None,
) -> PortfolioIntelligence:
    configured_limits = limits or PortfolioRiskLimits()
    summary_rows = list(account_data.get("summary", []) or [])
    positions = list(positions_data.get("positions", []) or [])

    snapshot = build_portfolio_snapshot(
        account_summary=summary_rows,
        positions=positions,
        peak_net_liquidation=peak_net_liquidation,
    )

    values = _summary_values(summary_rows)
    available_funds = values.get("AvailableFunds", 0.0)
    total_cash = values.get("TotalCashValue", 0.0)
    exposure_percent = _percent(snapshot.total_position_value, snapshot.net_liquidation)
    buying_power_percent = _percent(snapshot.buying_power, snapshot.net_liquidation)
    cash_percent = _percent(total_cash, snapshot.net_liquidation)
    utilization_percent = min(exposure_percent, 100.0)

    largest_symbol: str | None = None
    largest_value = 0.0
    if snapshot.symbol_position_values:
        largest_symbol, largest_value = max(
            snapshot.symbol_position_values.items(),
            key=lambda item: item[1],
        )
    largest_percent = _percent(largest_value, snapshot.net_liquidation)

    health_score = _calculate_health_score(snapshot, configured_limits, exposure_percent)
    advisor = _build_advisor(snapshot, configured_limits, health_score, exposure_percent)

    return PortfolioIntelligence(
        snapshot=snapshot,
        available_funds=available_funds,
        total_cash=total_cash,
        exposure_percent=exposure_percent,
        buying_power_percent=buying_power_percent,
        cash_percent=cash_percent,
        utilization_percent=utilization_percent,
        largest_position_symbol=largest_symbol,
        largest_position_value=largest_value,
        largest_position_percent=largest_percent,
        health_score=health_score,
        health_status=_health_status(health_score),
        advisor=advisor,
    )
