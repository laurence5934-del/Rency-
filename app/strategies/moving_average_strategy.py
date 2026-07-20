from __future__ import annotations

from collections import deque
from datetime import datetime
from numbers import Real
from typing import Any

from .base_strategy import BaseStrategy
from .strategy_signal import SignalAction, StrategySignal


class MovingAverageStrategy(BaseStrategy):
    """
    Simple moving-average crossover strategy.

    A BUY signal is generated when the fast moving average crosses above
    the slow moving average.

    A SELL signal is generated when the fast moving average crosses below
    the slow moving average.

    All other conditions generate a HOLD signal.
    """

    def __init__(
        self,
        *,
        fast_period: int = 20,
        slow_period: int = 50,
        name: str = "Moving Average Crossover",
        description: str = "Fast and slow simple moving-average crossover",
        enabled: bool = True,
    ) -> None:
        config = {
            "fast_period": fast_period,
            "slow_period": slow_period,
        }

        self._fast_period = fast_period
        self._slow_period = slow_period
        self._price_history: deque[float] = deque(maxlen=slow_period)
        self._previous_relationship: int | None = None
        self._fast_sma: float | None = None
        self._slow_sma: float | None = None

        super().__init__(
            name=name,
            description=description,
            config=config,
            enabled=enabled,
        )

    @property
    def fast_period(self) -> int:
        return self._fast_period

    @property
    def slow_period(self) -> int:
        return self._slow_period

    @property
    def price_history(self) -> tuple[float, ...]:
        return tuple(self._price_history)

    @property
    def fast_sma(self) -> float | None:
        return self._fast_sma

    @property
    def slow_sma(self) -> float | None:
        return self._slow_sma

    @property
    def is_ready(self) -> bool:
        return len(self._price_history) >= self.slow_period

    def validate_config(self) -> None:
        config = self.config

        fast_period = config.get("fast_period")
        slow_period = config.get("slow_period")

        if isinstance(fast_period, bool) or not isinstance(fast_period, int):
            raise TypeError("fast_period must be an integer")

        if isinstance(slow_period, bool) or not isinstance(slow_period, int):
            raise TypeError("slow_period must be an integer")

        if fast_period <= 0:
            raise ValueError("fast_period must be greater than zero")

        if slow_period <= 0:
            raise ValueError("slow_period must be greater than zero")

        if fast_period >= slow_period:
            raise ValueError("fast_period must be less than slow_period")

    @staticmethod
    def calculate_sma(
        prices: list[float] | tuple[float, ...],
        period: int,
    ) -> float:
        if isinstance(period, bool) or not isinstance(period, int):
            raise TypeError("period must be an integer")

        if period <= 0:
            raise ValueError("period must be greater than zero")

        if len(prices) < period:
            raise ValueError("not enough prices to calculate SMA")

        selected_prices = prices[-period:]
        return sum(selected_prices) / period

    def generate_signal(
        self,
        *,
        symbol: str,
        timestamp: datetime,
        **kwargs: Any,
    ) -> StrategySignal:
        price = kwargs.get("close", kwargs.get("price"))

        if price is None:
            raise ValueError("close or price is required")

        if isinstance(price, bool) or not isinstance(price, Real):
            raise TypeError("price must be numeric")

        numeric_price = float(price)

        if numeric_price <= 0:
            raise ValueError("price must be greater than zero")

        self._price_history.append(numeric_price)

        if not self.is_ready:
            return StrategySignal(
                symbol=symbol,
                action=SignalAction.HOLD,
                timestamp=timestamp,
                confidence=0.0,
                reason=(
                    "Insufficient price history: "
                    f"{len(self._price_history)}/{self.slow_period}"
                ),
            )

        prices = tuple(self._price_history)

        self._fast_sma = self.calculate_sma(
            prices,
            self.fast_period,
        )
        self._slow_sma = self.calculate_sma(
            prices,
            self.slow_period,
        )

        current_relationship = self._compare_averages(
            self._fast_sma,
            self._slow_sma,
        )

        action = SignalAction.HOLD
        reason = (
            f"No crossover: fast SMA={self._fast_sma:.4f}, "
            f"slow SMA={self._slow_sma:.4f}"
        )

        if self._previous_relationship is not None:
            if (
                self._previous_relationship <= 0
                and current_relationship > 0
            ):
                action = SignalAction.BUY
                reason = (
                    f"Bullish crossover: fast SMA={self._fast_sma:.4f} "
                    f"crossed above slow SMA={self._slow_sma:.4f}"
                )

            elif (
                self._previous_relationship >= 0
                and current_relationship < 0
            ):
                action = SignalAction.SELL
                reason = (
                    f"Bearish crossover: fast SMA={self._fast_sma:.4f} "
                    f"crossed below slow SMA={self._slow_sma:.4f}"
                )

        self._previous_relationship = current_relationship

        return StrategySignal(
            symbol=symbol,
            action=action,
            timestamp=timestamp,
            confidence=self._calculate_confidence(
                self._fast_sma,
                self._slow_sma,
            ),
            reason=reason,
        )

    def on_reset(self) -> None:
        self._price_history.clear()
        self._previous_relationship = None
        self._fast_sma = None
        self._slow_sma = None

    @staticmethod
    def _compare_averages(
        fast_sma: float,
        slow_sma: float,
    ) -> int:
        if fast_sma > slow_sma:
            return 1

        if fast_sma < slow_sma:
            return -1

        return 0

    @staticmethod
    def _calculate_confidence(
        fast_sma: float,
        slow_sma: float,
    ) -> float:
        if slow_sma == 0:
            return 0.0

        relative_difference = abs(fast_sma - slow_sma) / slow_sma

        return min(relative_difference, 1.0)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()

        data.update(
            {
                "fast_period": self.fast_period,
                "slow_period": self.slow_period,
                "price_count": len(self._price_history),
                "fast_sma": self.fast_sma,
                "slow_sma": self.slow_sma,
                "is_ready": self.is_ready,
            }
        )

        return data