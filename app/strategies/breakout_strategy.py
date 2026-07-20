from __future__ import annotations

from collections import deque
from datetime import datetime
from numbers import Real
from typing import Any

from .base_strategy import BaseStrategy
from .strategy_signal import SignalAction, StrategySignal


class BreakoutStrategy(BaseStrategy):
    """Rolling price-breakout trading strategy."""

    def __init__(
        self,
        lookback_period: int = 20,
        breakout_threshold: float = 0.0,
        enabled: bool = True,
    ) -> None:
        super().__init__(
            name="Breakout Strategy",
            description="Rolling breakout strategy",
            config={
                "lookback_period": lookback_period,
                "breakout_threshold": breakout_threshold,
            },
            enabled=enabled,
        )

        self._prices: deque[float] = deque(maxlen=lookback_period)
        self._highest_high: float | None = None
        self._lowest_low: float | None = None

    @property
    def lookback_period(self) -> int:
        return self.config["lookback_period"]

    @property
    def breakout_threshold(self) -> float:
        return float(self.config["breakout_threshold"])

    @property
    def highest_high(self) -> float | None:
        return self._highest_high

    @property
    def lowest_low(self) -> float | None:
        return self._lowest_low

    @property
    def ready(self) -> bool:
        return len(self._prices) >= self.lookback_period

    def validate_config(self) -> None:
        config = self.config
        lookback = config.get("lookback_period")
        threshold = config.get("breakout_threshold")

        if not isinstance(lookback, int) or isinstance(lookback, bool):
            raise TypeError("lookback_period must be an integer")

        if lookback <= 1:
            raise ValueError("lookback_period must be greater than one")

        if not isinstance(threshold, Real) or isinstance(threshold, bool):
            raise TypeError("breakout_threshold must be numeric")

        if threshold < 0:
            raise ValueError("breakout_threshold must not be negative")

    def calculate_high(self) -> float | None:
        if not self._prices:
            return None
        return max(self._prices)

    def calculate_low(self) -> float | None:
        if not self._prices:
            return None
        return min(self._prices)

    def on_reset(self) -> None:
        self._prices.clear()
        self._highest_high = None
        self._lowest_low = None

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

    def generate_signal(self, market_data: dict[str, Any]) -> StrategySignal:
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
        current_price = float(price)

        self._prices.append(current_price)
        self._highest_high = self.calculate_high()
        self._lowest_low = self.calculate_low()

        if not self.ready:
            return self._build_signal(
                symbol=symbol,
                action=SignalAction.HOLD,
                confidence=0.0,
                reason="Waiting for sufficient price history",
            )

        previous_prices = list(self._prices)[:-1]
        previous_high = max(previous_prices)
        previous_low = min(previous_prices)
        threshold = self.breakout_threshold

        if current_price > previous_high * (1.0 + threshold):
            confidence = min(
                1.0,
                ((current_price - previous_high) / previous_high) * 20.0,
            )
            return self._build_signal(
                symbol=symbol,
                action=SignalAction.BUY,
                confidence=confidence,
                reason="Bullish breakout",
            )

        if current_price < previous_low * (1.0 - threshold):
            confidence = min(
                1.0,
                ((previous_low - current_price) / previous_low) * 20.0,
            )
            return self._build_signal(
                symbol=symbol,
                action=SignalAction.SELL,
                confidence=confidence,
                reason="Bearish breakdown",
            )

        return self._build_signal(
            symbol=symbol,
            action=SignalAction.HOLD,
            confidence=0.5,
            reason="Price inside breakout range",
        )
