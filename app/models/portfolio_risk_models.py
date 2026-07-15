"""
Portfolio Risk Models
AI Trading Platform Version 7.5

Data models used by the portfolio-level risk manager.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RiskDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RiskCode(StrEnum):
    APPROVED = "APPROVED"
    PAPER_TRADING_REQUIRED = "PAPER_TRADING_REQUIRED"
    EMERGENCY_LOCK_ACTIVE = "EMERGENCY_LOCK_ACTIVE"
    INVALID_SYMBOL = "INVALID_SYMBOL"
    INVALID_ACTION = "INVALID_ACTION"
    INVALID_QUANTITY = "INVALID_QUANTITY"
    INVALID_ENTRY_PRICE = "INVALID_ENTRY_PRICE"
    INVALID_ACCOUNT_VALUE = "INVALID_ACCOUNT_VALUE"
    ORDER_VALUE_EXCEEDED = "ORDER_VALUE_EXCEEDED"
    POSITION_VALUE_EXCEEDED = "POSITION_VALUE_EXCEEDED"
    PORTFOLIO_EXPOSURE_EXCEEDED = "PORTFOLIO_EXPOSURE_EXCEEDED"
    OPEN_POSITION_LIMIT_REACHED = "OPEN_POSITION_LIMIT_REACHED"
    BUYING_POWER_INSUFFICIENT = "BUYING_POWER_INSUFFICIENT"
    DAILY_LOSS_LIMIT_REACHED = "DAILY_LOSS_LIMIT_REACHED"
    MAXIMUM_DRAWDOWN_REACHED = "MAXIMUM_DRAWDOWN_REACHED"
    EXISTING_SYMBOL_EXPOSURE = "EXISTING_SYMBOL_EXPOSURE"


@dataclass(frozen=True)
class PortfolioRiskLimits:
    maximum_order_value: float = 10_000.00
    maximum_position_value: float = 25_000.00
    maximum_portfolio_exposure_percent: float = 80.0
    maximum_open_positions: int = 10
    minimum_buying_power: float = 2_000.00
    maximum_daily_loss: float = 1_000.00
    maximum_drawdown_percent: float = 10.0
    allow_existing_symbol_additions: bool = False


@dataclass(frozen=True)
class PortfolioSnapshot:
    net_liquidation: float
    buying_power: float
    total_position_value: float
    open_position_count: int
    daily_realized_pnl: float
    daily_unrealized_pnl: float
    drawdown_percent: float
    symbol_position_values: dict[str, float] = field(
        default_factory=dict
    )

    @property
    def daily_total_pnl(self) -> float:
        return (
            float(self.daily_realized_pnl)
            + float(self.daily_unrealized_pnl)
        )


@dataclass(frozen=True)
class PortfolioRiskResult:
    approved: bool
    decision: RiskDecision
    symbol: str
    action: str
    quantity: int
    entry_price: float
    order_value: float
    projected_symbol_value: float
    projected_portfolio_value: float
    projected_exposure_percent: float
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    codes: tuple[RiskCode, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "decision": self.decision.value,
            "symbol": self.symbol,
            "action": self.action,
            "quantity": self.quantity,
            "entry_price": round(self.entry_price, 2),
            "order_value": round(self.order_value, 2),
            "projected_symbol_value": round(
                self.projected_symbol_value,
                2,
            ),
            "projected_portfolio_value": round(
                self.projected_portfolio_value,
                2,
            ),
            "projected_exposure_percent": round(
                self.projected_exposure_percent,
                2,
            ),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "codes": [
                code.value
                for code in self.codes
            ],
        }