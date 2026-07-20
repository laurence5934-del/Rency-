from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.backtesting.trade_models import Trade


@dataclass(frozen=True)
class BacktestConfig:
    """
    Configuration used to run a backtest.
    """

    initial_cash: float = 100_000.0
    commission_per_trade: float = 0.0
    allow_short: bool = False

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError(
                "initial_cash must be greater than zero."
            )

        if self.commission_per_trade < 0:
            raise ValueError(
                "commission_per_trade cannot be negative."
            )


@dataclass(frozen=True)
class EquityPoint:
    """
    Represents portfolio equity at a point in time.
    """

    timestamp: datetime
    equity: float

    def __post_init__(self) -> None:
        if self.equity < 0:
            raise ValueError(
                "equity cannot be negative."
            )


@dataclass
class BacktestResult:
    """
    Final output of a completed backtest.
    """

    config: BacktestConfig

    trades: list[Trade] = field(default_factory=list)

    equity_curve: list[EquityPoint] = field(default_factory=list)

    total_return: float = 0.0

    annualized_return: float = 0.0

    max_drawdown: float = 0.0

    win_rate: float = 0.0

    profit_factor: float = 0.0

    ending_equity: float = 0.0

    def add_trade(self, trade: Trade) -> None:
        self.trades.append(trade)

    def add_equity_point(self, point: EquityPoint) -> None:
        self.equity_curve.append(point)