from __future__ import annotations

from collections.abc import Iterable

from .models import ClosedTrade


class TradeStatistics:
    def calculate(self, trades: Iterable[ClosedTrade]) -> dict[str, float | int]:
        items = tuple(trades)
        wins = [trade.pnl for trade in items if trade.pnl > 0]
        losses = [trade.pnl for trade in items if trade.pnl < 0]
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        total = len(items)
        net_pnl = sum(trade.pnl for trade in items)
        average_win = gross_profit / len(wins) if wins else 0.0
        average_loss = sum(losses) / len(losses) if losses else 0.0
        win_rate = len(wins) / total if total else 0.0
        loss_rate = len(losses) / total if total else 0.0
        expectancy = net_pnl / total if total else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit else 0.0)
        return {
            "total_trades": total,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "breakeven_trades": total - len(wins) - len(losses),
            "win_rate": win_rate,
            "loss_rate": loss_rate,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "net_pnl": net_pnl,
            "average_win": average_win,
            "average_loss": average_loss,
            "largest_win": max(wins, default=0.0),
            "largest_loss": min(losses, default=0.0),
            "profit_factor": profit_factor,
            "expectancy": expectancy,
        }
