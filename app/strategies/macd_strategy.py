from __future__ import annotations

from collections import deque
from datetime import datetime
from numbers import Real
from typing import Any, Iterable

from .base_strategy import BaseStrategy
from .strategy_signal import SignalAction, StrategySignal


class MACDStrategy(BaseStrategy):
    """
    Moving Average Convergence Divergence trading strategy.

    BUY:
        The MACD line crosses above the signal line.

    SELL:
        The MACD line crosses below the signal line.

    HOLD:
        There is not enough history, no crossover occurred, or this is the
        first fully initialized MACD observation.
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        enabled: bool = True,
    ) -> None:
        super().__init__(
            name="MACD Strategy",
            description="Moving Average Convergence Divergence strategy",
            config={
                "fast_period": fast_period,
                "slow_period": slow_period,
                "signal_period": signal_period,
            },
            enabled=enabled,
        )

        self._prices: list[float] = []
        self._macd_history: deque[float] = deque(maxlen=signal_period)

        self._current_macd: float | None = None
        self._current_signal: float | None = None
        self._current_histogram: float | None = None

        self._previous_macd: float | None = None
        self._previous_signal: float | None = None

    @property
    def fast_period(self) -> int:
        return self.config["fast_period"]

    @property
    def slow_period(self) -> int:
        return self.config["slow_period"]

    @property
    def signal_period(self) -> int:
        return self.config["signal_period"]

    @property
    def current_macd(self) -> float | None:
        return self._current_macd

    @property
    def current_signal(self) -> float | None:
        return self._current_signal

    @property
    def current_histogram(self) -> float | None:
        return self._current_histogram

    @property
    def ready(self) -> bool:
        return (
            self._current_macd is not None
            and self._current_signal is not None
            and len(self._macd_history) >= self.signal_period
        )

    def validate_config(self) -> None:
        config = self.config

        fast = config.get("fast_period")
        slow = config.get("slow_period")
        signal = config.get("signal_period")

        for name, value in (
            ("fast_period", fast),
            ("slow_period", slow),
            ("signal_period", signal),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be an integer")

            if value <= 1:
                raise ValueError(f"{name} must be greater than one")

        if fast >= slow:
            raise ValueError("fast_period must be less than slow_period")

    @staticmethod
    def calculate_ema(
        values: Iterable[float],
        period: int,
    ) -> float | None:
        """
        Calculate an exponential moving average.

        The first value seeds the EMA. At least ``period`` observations are
        required before a result is returned.
        """
        data = list(values)

        if len(data) < period:
            return None

        multiplier = 2.0 / (period + 1.0)
        ema = data[0]

        for value in data[1:]:
            ema = ((value - ema) * multiplier) + ema

        return ema

    def calculate_macd(self) -> float | None:
        """Return the latest MACD value when enough prices are available."""
        if len(self._prices) < self.slow_period:
            return None

        fast_ema = self.calculate_ema(self._prices, self.fast_period)
        slow_ema = self.calculate_ema(self._prices, self.slow_period)

        if fast_ema is None or slow_ema is None:
            return None

        return fast_ema - slow_ema

    def calculate_signal_line(self) -> float | None:
        """Return the EMA of the recent MACD values."""
        return self.calculate_ema(
            self._macd_history,
            self.signal_period,
        )

    def on_reset(self) -> None:
        """Reset all internal MACD state."""
        self._prices.clear()
        self._macd_history.clear()

        self._current_macd = None
        self._current_signal = None
        self._current_histogram = None

        self._previous_macd = None
        self._previous_signal = None

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
        """Process one market-data record and return a MACD signal."""
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

        macd_value = self.calculate_macd()

        if macd_value is None:
            return self._build_signal(
                symbol=symbol,
                action=SignalAction.HOLD,
                confidence=0.0,
                reason="Waiting for sufficient price history",
            )

        self._macd_history.append(macd_value)
        signal_value = self.calculate_signal_line()

        self._current_macd = macd_value
        self._current_signal = signal_value
        self._current_histogram = (
            None
            if signal_value is None
            else macd_value - signal_value
        )

        if signal_value is None:
            return self._build_signal(
                symbol=symbol,
                action=SignalAction.HOLD,
                confidence=0.0,
                reason="Waiting for sufficient MACD history",
            )

        previous_macd = self._previous_macd
        previous_signal = self._previous_signal

        self._previous_macd = macd_value
        self._previous_signal = signal_value

        if previous_macd is None or previous_signal is None:
            return self._build_signal(
                symbol=symbol,
                action=SignalAction.HOLD,
                confidence=0.5,
                reason="MACD initialized; waiting for crossover",
            )

        if (
            previous_macd <= previous_signal
            and macd_value > signal_value
        ):
            confidence = min(
                1.0,
                abs(macd_value - signal_value)
                / max(abs(signal_value), 1.0),
            )

            return self._build_signal(
                symbol=symbol,
                action=SignalAction.BUY,
                confidence=confidence,
                reason="Bullish MACD crossover",
            )

        if (
            previous_macd >= previous_signal
            and macd_value < signal_value
        ):
            confidence = min(
                1.0,
                abs(macd_value - signal_value)
                / max(abs(signal_value), 1.0),
            )

            return self._build_signal(
                symbol=symbol,
                action=SignalAction.SELL,
                confidence=confidence,
                reason="Bearish MACD crossover",
            )

        return self._build_signal(
            symbol=symbol,
            action=SignalAction.HOLD,
            confidence=0.5,
            reason="No MACD crossover",
        )
