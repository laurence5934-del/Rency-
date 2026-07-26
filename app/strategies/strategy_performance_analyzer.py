from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from numbers import Real
from statistics import mean, pstdev
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class StrategyTrade:
    """One completed trade produced by a trading strategy."""

    strategy_name: str
    symbol: str
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: datetime
    exit_time: datetime
    fees: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.strategy_name, str):
            raise TypeError("strategy_name must be a string")

        strategy_name = self.strategy_name.strip()
        if not strategy_name:
            raise ValueError("strategy_name cannot be empty")

        if not isinstance(self.symbol, str):
            raise TypeError("symbol must be a string")

        symbol = self.symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol cannot be empty")

        for name, value in (
            ("entry_price", self.entry_price),
            ("exit_price", self.exit_price),
            ("quantity", self.quantity),
            ("fees", self.fees),
        ):
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{name} must be numeric")

        if self.entry_price <= 0:
            raise ValueError("entry_price must be greater than zero")
        if self.exit_price <= 0:
            raise ValueError("exit_price must be greater than zero")
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero")
        if self.fees < 0:
            raise ValueError("fees cannot be negative")

        if not isinstance(self.entry_time, datetime):
            raise TypeError("entry_time must be a datetime")
        if not isinstance(self.exit_time, datetime):
            raise TypeError("exit_time must be a datetime")
        if self.exit_time < self.entry_time:
            raise ValueError("exit_time cannot be before entry_time")

        object.__setattr__(self, "strategy_name", strategy_name)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "entry_price", float(self.entry_price))
        object.__setattr__(self, "exit_price", float(self.exit_price))
        object.__setattr__(self, "quantity", float(self.quantity))
        object.__setattr__(self, "fees", float(self.fees))

    @property
    def gross_profit(self) -> float:
        return (self.exit_price - self.entry_price) * self.quantity

    @property
    def net_profit(self) -> float:
        return self.gross_profit - self.fees

    @property
    def return_pct(self) -> float:
        invested_capital = self.entry_price * self.quantity
        return self.net_profit / invested_capital

    @property
    def holding_seconds(self) -> float:
        return (self.exit_time - self.entry_time).total_seconds()

    @property
    def is_winner(self) -> bool:
        return self.net_profit > 0

    @property
    def is_loser(self) -> bool:
        return self.net_profit < 0

    @property
    def is_breakeven(self) -> bool:
        return self.net_profit == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat(),
            "fees": self.fees,
            "gross_profit": self.gross_profit,
            "net_profit": self.net_profit,
            "return_pct": self.return_pct,
            "holding_seconds": self.holding_seconds,
            "is_winner": self.is_winner,
            "is_loser": self.is_loser,
            "is_breakeven": self.is_breakeven,
        }


class StrategyPerformanceAnalyzer:
    """Calculate trading-performance metrics for completed strategy trades."""

    def __init__(
        self,
        trades: Iterable[StrategyTrade] | None = None,
        *,
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252,
    ) -> None:
        if not isinstance(risk_free_rate, Real) or isinstance(
            risk_free_rate,
            bool,
        ):
            raise TypeError("risk_free_rate must be numeric")

        if not isinstance(periods_per_year, int) or isinstance(
            periods_per_year,
            bool,
        ):
            raise TypeError("periods_per_year must be an integer")

        if periods_per_year <= 0:
            raise ValueError("periods_per_year must be greater than zero")

        self._risk_free_rate = float(risk_free_rate)
        self._periods_per_year = periods_per_year
        self._trades: list[StrategyTrade] = []

        if trades is not None:
            self.add_trades(trades)

    @property
    def trades(self) -> tuple[StrategyTrade, ...]:
        return tuple(self._trades)

    @property
    def trade_count(self) -> int:
        return len(self._trades)

    @property
    def strategy_names(self) -> tuple[str, ...]:
        return tuple(sorted({trade.strategy_name for trade in self._trades}))

    @property
    def risk_free_rate(self) -> float:
        return self._risk_free_rate

    @property
    def periods_per_year(self) -> int:
        return self._periods_per_year

    def add_trade(self, trade: StrategyTrade) -> None:
        if not isinstance(trade, StrategyTrade):
            raise TypeError("trade must be a StrategyTrade")
        self._trades.append(trade)

    def add_trades(self, trades: Iterable[StrategyTrade]) -> None:
        if isinstance(trades, (str, bytes)):
            raise TypeError("trades must be an iterable of StrategyTrade")

        for trade in trades:
            self.add_trade(trade)

    def clear(self) -> None:
        self._trades.clear()

    def trades_for_strategy(
        self,
        strategy_name: str,
    ) -> tuple[StrategyTrade, ...]:
        if not isinstance(strategy_name, str):
            raise TypeError("strategy_name must be a string")

        strategy_name = strategy_name.strip()
        if not strategy_name:
            raise ValueError("strategy_name cannot be empty")

        return tuple(
            trade
            for trade in self._trades
            if trade.strategy_name == strategy_name
        )

    @staticmethod
    def _maximum_drawdown(trades: Iterable[StrategyTrade]) -> float:
        cumulative_profit = 0.0
        peak_profit = 0.0
        maximum_drawdown = 0.0

        for trade in sorted(trades, key=lambda item: item.exit_time):
            cumulative_profit += trade.net_profit
            peak_profit = max(peak_profit, cumulative_profit)
            maximum_drawdown = max(
                maximum_drawdown,
                peak_profit - cumulative_profit,
            )

        return maximum_drawdown

    def _sharpe_ratio(self, trades: Iterable[StrategyTrade]) -> float:
        returns = [trade.return_pct for trade in trades]

        if len(returns) < 2:
            return 0.0

        return_deviation = pstdev(returns)
        if return_deviation == 0:
            return 0.0

        periodic_risk_free_rate = (
            self._risk_free_rate / self._periods_per_year
        )
        excess_returns = [
            value - periodic_risk_free_rate for value in returns
        ]

        return (
            mean(excess_returns)
            / return_deviation
            * sqrt(self._periods_per_year)
        )

    def summarize(
        self,
        trades: Iterable[StrategyTrade] | None = None,
    ) -> dict[str, Any]:
        selected = list(self._trades if trades is None else trades)

        if any(not isinstance(trade, StrategyTrade) for trade in selected):
            raise TypeError("all trades must be StrategyTrade instances")

        winners = [trade for trade in selected if trade.is_winner]
        losers = [trade for trade in selected if trade.is_loser]
        breakeven = [trade for trade in selected if trade.is_breakeven]

        total_trades = len(selected)
        gross_profit = sum(trade.net_profit for trade in winners)
        gross_loss = abs(sum(trade.net_profit for trade in losers))
        net_profit = sum(trade.net_profit for trade in selected)
        total_fees = sum(trade.fees for trade in selected)

        win_rate = len(winners) / total_trades if total_trades else 0.0
        loss_rate = len(losers) / total_trades if total_trades else 0.0
        average_win = (
            mean(trade.net_profit for trade in winners) if winners else 0.0
        )
        average_loss = (
            mean(trade.net_profit for trade in losers) if losers else 0.0
        )
        average_trade = net_profit / total_trades if total_trades else 0.0
        average_return = (
            mean(trade.return_pct for trade in selected) if selected else 0.0
        )
        average_holding_seconds = (
            mean(trade.holding_seconds for trade in selected)
            if selected
            else 0.0
        )

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = float("inf")
        else:
            profit_factor = 0.0

        expectancy = (win_rate * average_win) + (loss_rate * average_loss)

        return {
            "total_trades": total_trades,
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "breakeven_trades": len(breakeven),
            "win_rate": win_rate,
            "loss_rate": loss_rate,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "net_profit": net_profit,
            "total_fees": total_fees,
            "average_win": average_win,
            "average_loss": average_loss,
            "average_trade": average_trade,
            "average_return": average_return,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "maximum_drawdown": self._maximum_drawdown(selected),
            "sharpe_ratio": self._sharpe_ratio(selected),
            "average_holding_seconds": average_holding_seconds,
        }

    def summarize_strategy(
        self,
        strategy_name: str,
    ) -> dict[str, Any]:
        trades = self.trades_for_strategy(strategy_name)
        summary = self.summarize(trades)
        summary["strategy_name"] = strategy_name.strip()
        return summary

    def summarize_all_strategies(self) -> dict[str, dict[str, Any]]:
        return {
            name: self.summarize_strategy(name)
            for name in self.strategy_names
        }

    def rank_strategies(
        self,
        metric: str = "net_profit",
        *,
        descending: bool = True,
    ) -> list[dict[str, Any]]:
        if not isinstance(metric, str):
            raise TypeError("metric must be a string")

        metric = metric.strip()
        if not metric:
            raise ValueError("metric cannot be empty")

        summaries = list(self.summarize_all_strategies().values())
        if not summaries:
            return []

        if metric not in summaries[0]:
            raise KeyError(f"unknown performance metric: {metric}")

        if not isinstance(summaries[0][metric], Real):
            raise TypeError(
                f"performance metric '{metric}' is not numeric"
            )

        return sorted(
            summaries,
            key=lambda summary: summary[metric],
            reverse=descending,
        )

    def best_strategy(
        self,
        metric: str = "net_profit",
    ) -> dict[str, Any] | None:
        rankings = self.rank_strategies(metric)
        return rankings[0] if rankings else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trade_count": self.trade_count,
            "strategy_names": list(self.strategy_names),
            "risk_free_rate": self.risk_free_rate,
            "periods_per_year": self.periods_per_year,
            "overall": self.summarize(),
            "strategies": self.summarize_all_strategies(),
            "trades": [trade.to_dict() for trade in self._trades],
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"trade_count={self.trade_count}, "
            f"strategy_count={len(self.strategy_names)})"
        )
