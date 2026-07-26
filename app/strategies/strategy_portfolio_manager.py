from __future__ import annotations

from collections import Counter
from datetime import datetime
from numbers import Real
from typing import Any, Iterable

from .base_strategy import BaseStrategy
from .strategy_signal import SignalAction, StrategySignal


class StrategyPortfolioManager:
    """
    Run multiple strategies against the same market-data record and combine
    their outputs into one consensus signal.

    Consensus rules:
    - BUY when weighted BUY support is greater than weighted SELL support.
    - SELL when weighted SELL support is greater than weighted BUY support.
    - HOLD when BUY and SELL support are tied or no directional support exists.

    Each strategy may be assigned a positive numeric weight. The default
    weight is 1.0.
    """

    def __init__(
        self,
        strategies: Iterable[BaseStrategy] | None = None,
        weights: dict[str, float] | None = None,
    ) -> None:
        self._strategies: list[BaseStrategy] = []
        self._weights: dict[str, float] = {}
        self._last_signals: list[StrategySignal] = []
        self._consensus_count = 0

        if weights is not None and not isinstance(weights, dict):
            raise TypeError("weights must be a dictionary")

        supplied_weights = dict(weights or {})

        if strategies is not None:
            if isinstance(strategies, (str, bytes)):
                raise TypeError("strategies must be an iterable of BaseStrategy")

            for strategy in strategies:
                self.add_strategy(
                    strategy,
                    weight=supplied_weights.get(strategy.name, 1.0),
                )

        unknown_names = set(supplied_weights) - {
            strategy.name for strategy in self._strategies
        }

        if unknown_names:
            unknown = ", ".join(sorted(unknown_names))
            raise ValueError(f"weights contain unknown strategies: {unknown}")

    @property
    def strategies(self) -> tuple[BaseStrategy, ...]:
        return tuple(self._strategies)

    @property
    def strategy_count(self) -> int:
        return len(self._strategies)

    @property
    def consensus_count(self) -> int:
        return self._consensus_count

    @property
    def last_signals(self) -> tuple[StrategySignal, ...]:
        return tuple(self._last_signals)

    @property
    def weights(self) -> dict[str, float]:
        return dict(self._weights)

    @staticmethod
    def _validate_strategy(strategy: BaseStrategy) -> None:
        if not isinstance(strategy, BaseStrategy):
            raise TypeError("strategy must inherit from BaseStrategy")

    @staticmethod
    def _validate_weight(weight: float) -> float:
        if not isinstance(weight, Real) or isinstance(weight, bool):
            raise TypeError("weight must be numeric")

        numeric_weight = float(weight)

        if numeric_weight <= 0:
            raise ValueError("weight must be greater than zero")

        return numeric_weight

    def add_strategy(
        self,
        strategy: BaseStrategy,
        *,
        weight: float = 1.0,
    ) -> None:
        self._validate_strategy(strategy)
        validated_weight = self._validate_weight(weight)

        if any(existing.name == strategy.name for existing in self._strategies):
            raise ValueError(
                f"strategy with name '{strategy.name}' already exists"
            )

        self._strategies.append(strategy)
        self._weights[strategy.name] = validated_weight

    def remove_strategy(self, name: str) -> BaseStrategy:
        if not isinstance(name, str):
            raise TypeError("name must be a string")

        normalized_name = name.strip()

        if not normalized_name:
            raise ValueError("name cannot be empty")

        for index, strategy in enumerate(self._strategies):
            if strategy.name == normalized_name:
                removed = self._strategies.pop(index)
                self._weights.pop(removed.name, None)
                return removed

        raise KeyError(f"strategy '{normalized_name}' was not found")

    def set_weight(self, name: str, weight: float) -> None:
        if not isinstance(name, str):
            raise TypeError("name must be a string")

        normalized_name = name.strip()

        if normalized_name not in self._weights:
            raise KeyError(f"strategy '{normalized_name}' was not found")

        self._weights[normalized_name] = self._validate_weight(weight)

    def get_strategy(self, name: str) -> BaseStrategy:
        if not isinstance(name, str):
            raise TypeError("name must be a string")

        normalized_name = name.strip()

        for strategy in self._strategies:
            if strategy.name == normalized_name:
                return strategy

        raise KeyError(f"strategy '{normalized_name}' was not found")

    def run_strategies(
        self,
        market_data: dict[str, Any],
    ) -> list[StrategySignal]:
        if not isinstance(market_data, dict):
            raise TypeError("market_data must be a dictionary")

        signals: list[StrategySignal] = []

        for strategy in self._strategies:
            if not strategy.enabled:
                continue

            signal = strategy.generate_signal(market_data)

            if not isinstance(signal, StrategySignal):
                raise TypeError(
                    f"strategy '{strategy.name}' returned an invalid signal"
                )

            signals.append(signal)

        self._last_signals = signals
        return list(signals)

    def generate_consensus(
        self,
        market_data: dict[str, Any],
    ) -> StrategySignal:
        signals = self.run_strategies(market_data)

        symbol = str(market_data.get("symbol", "UNKNOWN"))

        if not signals:
            consensus = StrategySignal(
                symbol=symbol,
                action=SignalAction.HOLD,
                timestamp=datetime.now(),
                confidence=0.0,
                reason="No enabled strategies available",
            )
            self._consensus_count += 1
            return consensus

        weighted_support = {
            SignalAction.BUY: 0.0,
            SignalAction.SELL: 0.0,
            SignalAction.HOLD: 0.0,
        }

        enabled_strategies = [
            strategy for strategy in self._strategies if strategy.enabled
        ]

        total_weight = 0.0

        for strategy, signal in zip(enabled_strategies, signals, strict=True):
            weight = self._weights[strategy.name]
            weighted_support[signal.action] += weight * signal.confidence
            total_weight += weight

        buy_support = weighted_support[SignalAction.BUY]
        sell_support = weighted_support[SignalAction.SELL]

        if buy_support > sell_support:
            action = SignalAction.BUY
            winning_support = buy_support
            reason = "Weighted strategy consensus favors BUY"
        elif sell_support > buy_support:
            action = SignalAction.SELL
            winning_support = sell_support
            reason = "Weighted strategy consensus favors SELL"
        else:
            action = SignalAction.HOLD
            winning_support = weighted_support[SignalAction.HOLD]

            if buy_support == sell_support and buy_support > 0:
                reason = "BUY and SELL strategy support is tied"
            else:
                reason = "No directional strategy consensus"

        confidence = (
            min(1.0, winning_support / total_weight)
            if total_weight > 0
            else 0.0
        )

        consensus = StrategySignal(
            symbol=symbol,
            action=action,
            timestamp=datetime.now(),
            confidence=confidence,
            reason=reason,
        )

        self._consensus_count += 1
        return consensus

    def action_summary(self) -> dict[str, int]:
        counts = Counter(signal.action.value for signal in self._last_signals)

        return {
            SignalAction.BUY.value: counts[SignalAction.BUY.value],
            SignalAction.SELL.value: counts[SignalAction.SELL.value],
            SignalAction.HOLD.value: counts[SignalAction.HOLD.value],
        }

    def reset(self) -> None:
        for strategy in self._strategies:
            strategy.reset()

        self._last_signals.clear()
        self._consensus_count = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_count": self.strategy_count,
            "consensus_count": self.consensus_count,
            "weights": self.weights,
            "strategies": [
                strategy.to_dict() for strategy in self._strategies
            ],
            "last_signals": [
                signal.to_dict() for signal in self._last_signals
            ],
            "action_summary": self.action_summary(),
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"strategy_count={self.strategy_count}, "
            f"consensus_count={self.consensus_count})"
        )
