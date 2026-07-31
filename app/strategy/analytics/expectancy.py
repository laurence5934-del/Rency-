from __future__ import annotations

from decimal import Decimal
from typing import Iterable


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