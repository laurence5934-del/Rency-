from __future__ import annotations

from dataclasses import dataclass, field

from app.backtesting.trade_models import Trade


@dataclass
class Portfolio:
    """
    Represents the simulated portfolio during a backtest.
    """

    initial_cash: float

    cash: float = field(init=False)

    trades: list[Trade] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError(
                "initial_cash must be greater than zero."
            )

        self.cash = self.initial_cash

    @property
    def trade_count(self) -> int:
        return len(self.trades)

    @property
    def open_trades(self) -> list[Trade]:
        return [
            trade
            for trade in self.trades
            if trade.is_open
        ]

    @property
    def closed_trades(self) -> list[Trade]:
        return [
            trade
            for trade in self.trades
            if trade.is_closed
        ]

    @property
    def realized_profit(self) -> float:
        return sum(
            trade.net_profit or 0.0
            for trade in self.closed_trades
        )

    @property
    def equity(self) -> float:
        """
    Current cash balance.

    Open-position market value and unrealized profit
    will be supplied by the trade simulator.
        """
        return self.cash

    def add_trade(self, trade: Trade) -> None:
        self.trades.append(trade)