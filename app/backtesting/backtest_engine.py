from __future__ import annotations

from datetime import datetime
from typing import Iterable

from app.backtesting.backtest_models import (
    BacktestConfig,
    BacktestResult,
)
from app.backtesting.equity_curve import EquityCurveBuilder
from app.backtesting.performance_metrics import PerformanceMetrics
from app.backtesting.portfolio_models import Portfolio
from app.backtesting.trade_models import Trade
from app.backtesting.trade_simulator import TradeSimulator


class BacktestEngine:
    """
    Coordinates trade execution, portfolio accounting,
    equity-curve generation, and performance reporting.
    """

    def __init__(self, config: BacktestConfig) -> None:
        self.config = config
        self.portfolio = Portfolio(
            initial_cash=config.initial_cash,
        )
        self.simulator = TradeSimulator(
            portfolio=self.portfolio,
            commission_per_trade=config.commission_per_trade,
            allow_short=config.allow_short,
        )
        self.equity_curve = EquityCurveBuilder()

    def record_equity(
        self,
        timestamp: datetime,
        market_prices: dict[str, float] | None = None,
    ) -> float:
        """
        Records current portfolio equity.

        market_prices should contain the latest price for each
        symbol with an open position.
        """

        prices = market_prices or {}

        equity = self.simulator.portfolio_equity(prices)

        self.equity_curve.add(
            timestamp=timestamp,
            equity=equity,
        )

        return equity

    def run(
        self,
        trades: Iterable[Trade],
        start_time: datetime,
        end_time: datetime,
    ) -> BacktestResult:
        """
        Builds a completed backtest result from an ordered collection
        of already simulated trades.

        Trade generation remains separate so strategies can later
        create trades from historical market data.
        """

        ordered_trades = sorted(
            trades,
            key=lambda trade: trade.entry_time,
        )

        for trade in ordered_trades:
            self.portfolio.add_trade(trade)

        self._rebuild_cash_from_closed_trades()

        if self.equity_curve.count == 0:
            self.equity_curve.add(
                timestamp=start_time,
                equity=self.config.initial_cash,
            )
            self.equity_curve.add(
                timestamp=end_time,
                equity=self.portfolio.equity,
            )

        curve = self.equity_curve.build()
        ending_equity = (
            curve[-1].equity
            if curve
            else self.portfolio.equity
        )

        duration_years = self._duration_years(
            start_time=start_time,
            end_time=end_time,
        )

        return BacktestResult(
            config=self.config,
            trades=list(ordered_trades),
            equity_curve=curve,
            total_return=PerformanceMetrics.total_return(
                self.config.initial_cash,
                ending_equity,
            ),
            annualized_return=PerformanceMetrics.annualized_return(
                self.config.initial_cash,
                ending_equity,
                duration_years,
            ),
            max_drawdown=PerformanceMetrics.max_drawdown(curve),
            win_rate=PerformanceMetrics.win_rate(ordered_trades),
            profit_factor=PerformanceMetrics.profit_factor(
                ordered_trades
            ),
            ending_equity=ending_equity,
        )

    def reset(self) -> None:
        """
        Resets the engine so the same instance can run a new backtest.
        """
        self.portfolio = Portfolio(
        initial_cash=self.config.initial_cash,
        )

        self.simulator = TradeSimulator(
            portfolio=self.portfolio,
            commission_per_trade=self.config.commission_per_trade,
            allow_short=self.config.allow_short,
        )
        self.equity_curve.clear()

    def _rebuild_cash_from_closed_trades(self) -> None:
        """
        Reconstructs ending cash from closed-trade net profit.
        """

        realized_profit = sum(
            trade.net_profit
            for trade in self.portfolio.closed_trades
        )

        self.portfolio.cash = (
            self.config.initial_cash + realized_profit
        )

    @staticmethod
    def _duration_years(
        start_time: datetime,
        end_time: datetime,
    ) -> float:
        if end_time <= start_time:
            return 0.0

        elapsed_seconds = (
            end_time - start_time
        ).total_seconds()

        seconds_per_year = 365.25 * 24 * 60 * 60

        return elapsed_seconds / seconds_per_year