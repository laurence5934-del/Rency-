from __future__ import annotations

from datetime import datetime
from typing import Any

from .base_strategy import BaseStrategy
from .strategy_signal import StrategySignal


class StrategyRunner:
    """
    Executes a strategy against incoming market bars.

    The runner is intentionally lightweight—it is responsible only for
    invoking strategies and collecting signals. Trade execution belongs
    to the Backtest Engine.
    """

    def __init__(self, strategy: BaseStrategy) -> None:
        if not isinstance(strategy, BaseStrategy):
            raise TypeError("strategy must be a BaseStrategy")

        self._strategy = strategy
        self._processed_bars = 0

    @property
    def strategy(self) -> BaseStrategy:
        return self._strategy

    @property
    def processed_bars(self) -> int:
        return self._processed_bars

    def reset(self) -> None:
        self._processed_bars = 0
        self.strategy.reset()

    def process_bar(
        self,
        *,
        symbol: str,
        timestamp: datetime,
        **kwargs: Any,
    ) -> StrategySignal | None:
        """
        Process one market bar.

        Returns:
            StrategySignal if generated.
            None if the strategy is disabled.
        """

        if not self.strategy.enabled:
            return None

        signal = self.strategy.create_signal(
            symbol=symbol,
            timestamp=timestamp,
            **kwargs,
        )

        self._processed_bars += 1

        return signal

    def process_many(self, bars: list[dict[str, Any]]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []

        for bar in bars:
            signal = self.process_bar(**bar)

            if signal is not None:
                signals.append(signal)

        return signals

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy.name,
            "processed_bars": self.processed_bars,
        }

    def __repr__(self) -> str:
        return (
            f"StrategyRunner("
            f"strategy={self.strategy.name!r}, "
            f"processed_bars={self.processed_bars}"
            f")"
        )