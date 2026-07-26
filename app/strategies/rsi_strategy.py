from __future__ import annotations

from collections import deque
from datetime import datetime
from numbers import Real
from typing import Any

from .base_strategy import BaseStrategy
from .strategy_signal import SignalAction, StrategySignal


class RSIStrategy(BaseStrategy):
    """
    Relative Strength Index trading strategy.

    BUY:
        RSI is at or below the oversold threshold.

    SELL:
        RSI is at or above the overbought threshold.

    HOLD:
        RSI is between the configured thresholds or there is not enough
        price history to calculate RSI.
    """

    def __init__(
        self,
        period: int = 14,
        oversold_threshold: float = 30.0,
        overbought_threshold: float = 70.0,
        enabled: bool = True,
    ) -> None:
        super().__init__(
            name="RSI Strategy",
            description="Relative Strength Index momentum strategy",
            config={
                "period": period,
                "oversold_threshold": oversold_threshold,
                "overbought_threshold": overbought_threshold,
            },
            enabled=enabled,
        )

        self._prices: deque[float] = deque(maxlen=period + 1)
        self._current_rsi: float | None = None

    @property
    def period(self) -> int:
        return self.config["period"]

    @property
    def oversold_threshold(self) -> float:
        return float(self.config["oversold_threshold"])

    @property
    def overbought_threshold(self) -> float:
        return float(self.config["overbought_threshold"])

    @property
    def current_rsi(self) -> float | None:
        return self._current_rsi

    @property
    def ready(self) -> bool:
        return len(self._prices) >= self.period + 1

    def validate_config(self) -> None:
        config = self.config

        period = config.get("period")
        oversold = config.get("oversold_threshold")
        overbought = config.get("overbought_threshold")

        if not isinstance(period, int) or isinstance(period, bool):
            raise TypeError("period must be an integer")

        if period <= 1:
            raise ValueError("period must be greater than one")

        if not isinstance(oversold, Real) or isinstance(oversold, bool):
            raise TypeError("oversold_threshold must be numeric")

        if not isinstance(overbought, Real) or isinstance(overbought, bool):
            raise TypeError("overbought_threshold must be numeric")

        if not 0.0 <= oversold <= 100.0:
            raise ValueError(
                "oversold_threshold must be between 0.0 and 100.0"
            )

        if not 0.0 <= overbought <= 100.0:
            raise ValueError(
                "overbought_threshold must be between 0.0 and 100.0"
            )

        if oversold >= overbought:
            raise ValueError(
                "oversold_threshold must be less than overbought_threshold"
            )

    def calculate_rsi(self) -> float | None:
        if not self.ready:
            return None

        prices = list(self._prices)
        changes = [
            prices[index] - prices[index - 1]
            for index in range(1, len(prices))
        ]

        gains = [change for change in changes if change > 0]
        losses = [-change for change in changes if change < 0]

        average_gain = sum(gains) / self.period
        average_loss = sum(losses) / self.period

        if average_loss == 0:
            return 100.0

        if average_gain == 0:
            return 0.0

        relative_strength = average_gain / average_loss

        return 100.0 - (100.0 / (1.0 + relative_strength))

    def on_reset(self) -> None:
        self._prices.clear()
        self._current_rsi = None

    def _build_signal(
        self,
        *,
        symbol: str,
        action: SignalAction,
        confidence: float,
        reason: str,
    ) -> StrategySignal:
        signal = StrategySignal(
            symbol=symbol,
            action=action,
            timestamp=datetime.now(),
            confidence=confidence,
            reason=reason,
        )

        self._signal_count += 1
        return signal

    def generate_signal(
        self,
        market_data: dict[str, Any],
    ) -> StrategySignal:
        if not self.enabled:
            raise RuntimeError("strategy is disabled")

        if not isinstance(market_data, dict):
            raise TypeError("market_data must be a dictionary")

        if "price" not in market_data:
            raise KeyError("price is required")

        price = market_data["price"]

        if not isinstance(price, Real) or isinstance(price, bool):
            raise TypeError("price must be numeric")

        if price <= 0:
            raise ValueError("price must be greater than zero")

        symbol = market_data.get("symbol", "UNKNOWN")

        self._prices.append(float(price))
        self._current_rsi = self.calculate_rsi()

        if self._current_rsi is None:
            return self._build_signal(
                symbol=symbol,
                action=SignalAction.HOLD,
                confidence=0.0,
                reason="Waiting for sufficient price history",
            )

        if self._current_rsi <= self.oversold_threshold:
            confidence = min(
                1.0,
                (self.oversold_threshold - self._current_rsi) / 30.0,
            )

            return self._build_signal(
                symbol=symbol,
                action=SignalAction.BUY,
                confidence=confidence,
                reason="RSI indicates oversold conditions",
            )

        if self._current_rsi >= self.overbought_threshold:
            confidence = min(
                1.0,
                (self._current_rsi - self.overbought_threshold) / 30.0,
            )

            return self._build_signal(
                symbol=symbol,
                action=SignalAction.SELL,
                confidence=confidence,
                reason="RSI indicates overbought conditions",
            )

        return self._build_signal(
            symbol=symbol,
            action=SignalAction.HOLD,
            confidence=0.5,
            reason="RSI is within the neutral range",
        )