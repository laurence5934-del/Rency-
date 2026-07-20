from __future__ import annotations

from math import inf

from app.backtesting.backtest_models import EquityPoint
from app.backtesting.trade_models import Trade


class PerformanceMetrics:
    """
    Calculates performance statistics for completed backtests.
    """

    @staticmethod
    def closed_trades(trades: list[Trade]) -> list[Trade]:
        return [trade for trade in trades if trade.is_closed]

    @classmethod
    def winning_trades(cls, trades: list[Trade]) -> list[Trade]:
        return [
            trade
            for trade in cls.closed_trades(trades)
            if (trade.net_profit or 0.0) > 0
        ]

    @classmethod
    def losing_trades(cls, trades: list[Trade]) -> list[Trade]:
        return [
            trade
            for trade in cls.closed_trades(trades)
            if (trade.net_profit or 0.0) < 0
        ]

    @classmethod
    def gross_profit(cls, trades: list[Trade]) -> float:
        return sum(
            trade.net_profit or 0.0
            for trade in cls.winning_trades(trades)
        )

    @classmethod
    def gross_loss(cls, trades: list[Trade]) -> float:
        return abs(
            sum(
                trade.net_profit or 0.0
                for trade in cls.losing_trades(trades)
            )
        )

    @classmethod
    def win_rate(cls, trades: list[Trade]) -> float:
        closed = cls.closed_trades(trades)

        if not closed:
            return 0.0

        return (len(cls.winning_trades(trades)) / len(closed)) * 100.0

    @classmethod
    def profit_factor(cls, trades: list[Trade]) -> float:
        gross_profit = cls.gross_profit(trades)
        gross_loss = cls.gross_loss(trades)

        if gross_loss == 0:
            return inf if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    @classmethod
    def average_win(cls, trades: list[Trade]) -> float:
        winners = cls.winning_trades(trades)

        if not winners:
            return 0.0

        return cls.gross_profit(trades) / len(winners)

    @classmethod
    def average_loss(cls, trades: list[Trade]) -> float:
        losers = cls.losing_trades(trades)

        if not losers:
            return 0.0

        return cls.gross_loss(trades) / len(losers)

    @classmethod
    def risk_reward_ratio(cls, trades: list[Trade]) -> float:
        average_loss = cls.average_loss(trades)
        average_win = cls.average_win(trades)

        if average_loss == 0:
            return inf if average_win > 0 else 0.0

        return average_win / average_loss

    @classmethod
    def expectancy(cls, trades: list[Trade]) -> float:
        closed = cls.closed_trades(trades)

        if not closed:
            return 0.0

        win_probability = len(cls.winning_trades(trades)) / len(closed)
        loss_probability = len(cls.losing_trades(trades)) / len(closed)

        return (
            win_probability * cls.average_win(trades)
            - loss_probability * cls.average_loss(trades)
        )

    @staticmethod
    def total_return(
        initial_equity: float,
        ending_equity: float,
    ) -> float:
        if initial_equity <= 0:
            raise ValueError(
                "initial_equity must be greater than zero."
            )

        if ending_equity < 0:
            raise ValueError(
                "ending_equity cannot be negative."
            )

        return (
            (ending_equity - initial_equity)
            / initial_equity
        ) * 100.0

    @staticmethod
    def annualized_return(
        initial_equity: float,
        ending_equity: float,
        years: float,
    ) -> float:
        if initial_equity <= 0:
            raise ValueError(
                "initial_equity must be greater than zero."
            )

        if ending_equity < 0:
            raise ValueError(
                "ending_equity cannot be negative."
            )

        if years <= 0:
            raise ValueError(
                "years must be greater than zero."
            )

        if ending_equity == 0:
            return -100.0

        return (
            (ending_equity / initial_equity) ** (1.0 / years)
            - 1.0
        ) * 100.0

    @staticmethod
    def max_drawdown(
        equity_curve: list[EquityPoint],
    ) -> float:
        if not equity_curve:
            return 0.0

        peak = equity_curve[0].equity
        max_drawdown = 0.0

        for point in equity_curve:
            if point.equity > peak:
                peak = point.equity

            if peak == 0:
                continue

            drawdown = (
                (peak - point.equity)
                / peak
            ) * 100.0

            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return max_drawdown