from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import Any, Mapping

from app.strategies.strategy_performance_analyzer import (
    StrategyPerformanceAnalyzer,
)
from app.strategies.strategy_portfolio_manager import (
    StrategyPortfolioManager,
)


@dataclass(frozen=True, slots=True)
class AllocationRule:
    """Configuration used to score and allocate strategy weights."""

    metric: str = "net_profit"
    minimum_trades: int = 1
    minimum_weight: float = 0.05
    maximum_weight: float = 0.60
    smoothing: float = 0.50
    fallback_equal_weight: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.metric, str):
            raise TypeError("metric must be a string")

        metric = self.metric.strip()
        if not metric:
            raise ValueError("metric cannot be empty")

        if not isinstance(self.minimum_trades, int) or isinstance(
            self.minimum_trades,
            bool,
        ):
            raise TypeError("minimum_trades must be an integer")

        if self.minimum_trades < 0:
            raise ValueError("minimum_trades cannot be negative")

        for name, value in (
            ("minimum_weight", self.minimum_weight),
            ("maximum_weight", self.maximum_weight),
            ("smoothing", self.smoothing),
        ):
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{name} must be numeric")

        if not 0 <= self.minimum_weight <= 1:
            raise ValueError("minimum_weight must be between 0 and 1")

        if not 0 < self.maximum_weight <= 1:
            raise ValueError("maximum_weight must be greater than 0 and at most 1")

        if self.minimum_weight > self.maximum_weight:
            raise ValueError(
                "minimum_weight cannot exceed maximum_weight"
            )

        if not 0 <= self.smoothing <= 1:
            raise ValueError("smoothing must be between 0 and 1")

        if not isinstance(self.fallback_equal_weight, bool):
            raise TypeError("fallback_equal_weight must be a boolean")

        object.__setattr__(self, "metric", metric)
        object.__setattr__(self, "minimum_weight", float(self.minimum_weight))
        object.__setattr__(self, "maximum_weight", float(self.maximum_weight))
        object.__setattr__(self, "smoothing", float(self.smoothing))


class AdaptiveStrategyAllocator:
    """
    Rebalance StrategyPortfolioManager weights using measured performance.

    The allocator:
    - reads per-strategy metrics from StrategyPerformanceAnalyzer
    - converts scores into normalized target weights
    - enforces minimum and maximum weight bounds
    - smooths changes to reduce abrupt allocation shifts
    - applies the final weights to StrategyPortfolioManager
    """

    def __init__(
        self,
        portfolio_manager: StrategyPortfolioManager,
        performance_analyzer: StrategyPerformanceAnalyzer,
        *,
        rule: AllocationRule | None = None,
    ) -> None:
        if not isinstance(portfolio_manager, StrategyPortfolioManager):
            raise TypeError(
                "portfolio_manager must be a StrategyPortfolioManager"
            )

        if not isinstance(
            performance_analyzer,
            StrategyPerformanceAnalyzer,
        ):
            raise TypeError(
                "performance_analyzer must be a "
                "StrategyPerformanceAnalyzer"
            )

        if rule is not None and not isinstance(rule, AllocationRule):
            raise TypeError("rule must be an AllocationRule")

        self._portfolio_manager = portfolio_manager
        self._performance_analyzer = performance_analyzer
        self._rule = rule or AllocationRule()
        self._last_allocation: dict[str, float] = {}

    @property
    def portfolio_manager(self) -> StrategyPortfolioManager:
        return self._portfolio_manager

    @property
    def performance_analyzer(self) -> StrategyPerformanceAnalyzer:
        return self._performance_analyzer

    @property
    def rule(self) -> AllocationRule:
        return self._rule

    @property
    def last_allocation(self) -> dict[str, float]:
        return dict(self._last_allocation)

    def _strategy_names(self) -> tuple[str, ...]:
        data = self._portfolio_manager.to_dict()

        strategies = data.get("strategies", [])
        names: list[str] = []

        for strategy in strategies:
            if isinstance(strategy, Mapping):
                name = strategy.get("name")
                if isinstance(name, str) and name.strip():
                    names.append(name.strip())

        return tuple(names)

    def _current_weights(self) -> dict[str, float]:
        data = self._portfolio_manager.to_dict()
        raw_weights = data.get("weights", {})

        if not isinstance(raw_weights, Mapping):
            raise TypeError(
                "portfolio manager weights must be a mapping"
            )

        return {
            str(name): float(weight)
            for name, weight in raw_weights.items()
        }

    def _metric_scores(
        self,
        strategy_names: tuple[str, ...],
    ) -> dict[str, float]:
        scores: dict[str, float] = {}

        for strategy_name in strategy_names:
            summary = self._performance_analyzer.summarize_strategy(
                strategy_name
            )

            if summary["total_trades"] < self._rule.minimum_trades:
                scores[strategy_name] = 0.0
                continue

            if self._rule.metric not in summary:
                raise KeyError(
                    f"unknown performance metric: {self._rule.metric}"
                )

            value = summary[self._rule.metric]

            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(
                    f"performance metric '{self._rule.metric}' "
                    "must be numeric"
                )

            scores[strategy_name] = max(0.0, float(value))

        return scores

    @staticmethod
    def _normalize(scores: Mapping[str, float]) -> dict[str, float]:
        total = sum(scores.values())

        if total <= 0:
            return {name: 0.0 for name in scores}

        return {
            name: value / total
            for name, value in scores.items()
        }

    @staticmethod
    def _equal_weights(
        strategy_names: tuple[str, ...],
    ) -> dict[str, float]:
        if not strategy_names:
            return {}

        weight = 1.0 / len(strategy_names)
        return {name: weight for name in strategy_names}

    def _bounded_weights(
        self,
        weights: Mapping[str, float],
    ) -> dict[str, float]:
        if not weights:
            return {}

        minimum = self._rule.minimum_weight
        maximum = self._rule.maximum_weight
        count = len(weights)

        if minimum * count > 1:
            raise ValueError(
                "minimum_weight is too large for the number of strategies"
            )

        if maximum * count < 1:
            raise ValueError(
                "maximum_weight is too small for the number of strategies"
            )

        bounded = {
            name: min(max(value, minimum), maximum)
            for name, value in weights.items()
        }

        for _ in range(100):
            total = sum(bounded.values())
            difference = 1.0 - total

            if abs(difference) < 1e-12:
                break

            if difference > 0:
                adjustable = [
                    name
                    for name, value in bounded.items()
                    if value < maximum
                ]
            else:
                adjustable = [
                    name
                    for name, value in bounded.items()
                    if value > minimum
                ]

            if not adjustable:
                break

            adjustment = difference / len(adjustable)

            for name in adjustable:
                bounded[name] = min(
                    maximum,
                    max(minimum, bounded[name] + adjustment),
                )

        total = sum(bounded.values())

        if total <= 0:
            return self._equal_weights(tuple(bounded))

        return {
            name: value / total
            for name, value in bounded.items()
        }

    def calculate_target_weights(self) -> dict[str, float]:
        strategy_names = self._strategy_names()

        if not strategy_names:
            return {}

        scores = self._metric_scores(strategy_names)
        normalized = self._normalize(scores)

        if all(value == 0.0 for value in normalized.values()):
            if not self._rule.fallback_equal_weight:
                return self._current_weights()

            normalized = self._equal_weights(strategy_names)

        return self._bounded_weights(normalized)

    def calculate_smoothed_weights(self) -> dict[str, float]:
        targets = self.calculate_target_weights()

        if not targets:
            return {}

        current = self._current_weights()

        if not current:
            current = self._equal_weights(tuple(targets))

        smoothing = self._rule.smoothing

        blended = {
            name: (
                (1.0 - smoothing) * current.get(name, 0.0)
                + smoothing * target
            )
            for name, target in targets.items()
        }

        return self._bounded_weights(self._normalize(blended))

    def rebalance(self) -> dict[str, float]:
        allocation = self.calculate_smoothed_weights()

        for strategy_name, weight in allocation.items():
            self._portfolio_manager.set_weight(strategy_name, weight)

        self._last_allocation = dict(allocation)
        return dict(allocation)

    def preview(self) -> dict[str, Any]:
        strategy_names = self._strategy_names()
        scores = self._metric_scores(strategy_names)

        return {
            "metric": self._rule.metric,
            "scores": scores,
            "current_weights": self._current_weights(),
            "target_weights": self.calculate_target_weights(),
            "smoothed_weights": self.calculate_smoothed_weights(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": {
                "metric": self._rule.metric,
                "minimum_trades": self._rule.minimum_trades,
                "minimum_weight": self._rule.minimum_weight,
                "maximum_weight": self._rule.maximum_weight,
                "smoothing": self._rule.smoothing,
                "fallback_equal_weight": (
                    self._rule.fallback_equal_weight
                ),
            },
            "last_allocation": self.last_allocation,
            "preview": self.preview(),
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"metric={self._rule.metric!r}, "
            f"strategy_count={len(self._strategy_names())})"
        )
