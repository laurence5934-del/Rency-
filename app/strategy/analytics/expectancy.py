from __future__ import annotations

from decimal import Decimal
from typing import Iterable
from unittest import result
from .expectancy_models import ExpectancyMetrics

class ExpectancyAnalyzer:
    """Calculates expectancy-related trading performance metrics."""

    @staticmethod
    def average_win(trade_results: Iterable[Decimal]) -> Decimal:
        wins = [result for result in trade_results if result > 0]

        if not wins:
            return Decimal("0")

        return sum(wins, Decimal("0")) / Decimal(len(wins))

    @staticmethod
    def average_loss(trade_results: Iterable[Decimal]) -> Decimal:
        losses = [abs(result) for result in trade_results if result < 0]

        if not losses:
            return Decimal("0")

        return sum(losses, Decimal("0")) / Decimal(len(losses))

    @staticmethod
    def payoff_ratio(
        *,
        average_win: Decimal,
        average_loss: Decimal,
    ) -> Decimal:
        if average_loss == 0:
            return Decimal("0")

        return average_win / average_loss

    @staticmethod
    def expectancy(
        *,
        win_rate: Decimal,
        average_win: Decimal,
        average_loss: Decimal,
    ) -> Decimal:
        loss_rate = Decimal("1") - win_rate

        return (
            win_rate * average_win
            - loss_rate * average_loss
        )

    @staticmethod
    def expectancy_percent(
        *,
        expectancy: Decimal,
        average_loss: Decimal,
    ) -> Decimal:
        if average_loss == 0:
            return Decimal("0")

        return expectancy / average_loss

    @staticmethod
    def recovery_factor(
        *,
        net_profit: Decimal,
        max_drawdown: Decimal,
    ) -> Decimal:
        if max_drawdown == 0:
            return Decimal("0")

        return net_profit / abs(max_drawdown)
    def analyze(
        self,
        result,
        *,
        max_drawdown: Decimal | None = None,
    ) -> ExpectancyMetrics:
            snapshots = sorted(
            result.snapshots,
            key=lambda snapshot: snapshot.timestamp,
        )

            trade_results = [
            current.realized_pnl - previous.realized_pnl
            for previous, current in zip(
                snapshots,
                snapshots[1:],
                strict=False,
            )
            if current.realized_pnl - previous.realized_pnl != 0
        ]

            average_win = self.average_win(trade_results)
            average_loss = self.average_loss(trade_results)

            payoff_ratio = self.payoff_ratio(
            average_win=average_win,
            average_loss=average_loss,
        )

            winners = sum(
            1
            for trade_result in trade_results
            if trade_result > 0
        )
            losers = sum(
            1
            for trade_result in trade_results
            if trade_result < 0
        )
            closed_trades = winners + losers

            if closed_trades == 0:
                win_rate = Decimal("0")
            else:
                win_rate = (
                Decimal(winners)
                / Decimal(closed_trades)
            )

            expectancy = self.expectancy(
            win_rate=win_rate,
            average_win=average_win,
            average_loss=average_loss,
        )

            expectancy_percent = self.expectancy_percent(
            expectancy=expectancy,
            average_loss=average_loss,
        )

            if snapshots:
                final_equity = snapshots[-1].equity
            else:
                final_equity = result.config.initial_capital

                net_profit = (
                final_equity
                - result.config.initial_capital
        )

            recovery_factor = self.recovery_factor(
                net_profit=net_profit,
                max_drawdown=(
                max_drawdown
                if max_drawdown is not None
                else Decimal("0")
            ),
        )

            return ExpectancyMetrics(
            average_win=average_win,
            average_loss=average_loss,
            payoff_ratio=payoff_ratio,
            expectancy=expectancy,
            expectancy_percent=expectancy_percent,
            recovery_factor=recovery_factor,
        )