from __future__ import annotations

import pytest

from app.strategies.macd_strategy import MACDStrategy
from app.strategies.strategy_signal import SignalAction, StrategySignal


def test_default_creation() -> None:
    strategy = MACDStrategy()

    assert strategy.name == "MACD Strategy"
    assert strategy.fast_period == 12
    assert strategy.slow_period == 26
    assert strategy.signal_period == 9
    assert strategy.enabled is True
    assert strategy.ready is False
    assert strategy.current_macd is None
    assert strategy.current_signal is None
    assert strategy.current_histogram is None


def test_invalid_fast_period_type() -> None:
    with pytest.raises(TypeError, match="fast_period must be an integer"):
        MACDStrategy(fast_period=12.0)

    with pytest.raises(TypeError, match="fast_period must be an integer"):
        MACDStrategy(fast_period=True)


def test_invalid_slow_period_type() -> None:
    with pytest.raises(TypeError, match="slow_period must be an integer"):
        MACDStrategy(slow_period=26.0)

    with pytest.raises(TypeError, match="slow_period must be an integer"):
        MACDStrategy(slow_period=False)


def test_invalid_signal_period_type() -> None:
    with pytest.raises(TypeError, match="signal_period must be an integer"):
        MACDStrategy(signal_period=9.0)

    with pytest.raises(TypeError, match="signal_period must be an integer"):
        MACDStrategy(signal_period=True)


def test_invalid_period_values() -> None:
    with pytest.raises(ValueError, match="fast_period must be greater than one"):
        MACDStrategy(fast_period=1)

    with pytest.raises(ValueError, match="slow_period must be greater than one"):
        MACDStrategy(slow_period=1)

    with pytest.raises(ValueError, match="signal_period must be greater than one"):
        MACDStrategy(signal_period=1)


def test_fast_period_must_be_less_than_slow_period() -> None:
    with pytest.raises(
        ValueError,
        match="fast_period must be less than slow_period",
    ):
        MACDStrategy(fast_period=5, slow_period=5)

    with pytest.raises(
        ValueError,
        match="fast_period must be less than slow_period",
    ):
        MACDStrategy(fast_period=6, slow_period=5)


def test_calculate_ema_not_enough_values() -> None:
    result = MACDStrategy.calculate_ema([10.0, 11.0], period=3)

    assert result is None


def test_calculate_ema() -> None:
    result = MACDStrategy.calculate_ema(
        [10.0, 11.0, 12.0],
        period=3,
    )

    assert result == pytest.approx(11.25)


def test_calculate_macd_not_ready() -> None:
    strategy = MACDStrategy(
        fast_period=3,
        slow_period=5,
        signal_period=3,
    )

    strategy._prices.extend([10.0, 11.0, 12.0, 13.0])

    assert strategy.calculate_macd() is None


def test_calculate_macd() -> None:
    strategy = MACDStrategy(
        fast_period=3,
        slow_period=5,
        signal_period=3,
    )

    strategy._prices.extend([10.0, 11.0, 12.0, 13.0, 14.0])

    expected = (
        MACDStrategy.calculate_ema(strategy._prices, 3)
        - MACDStrategy.calculate_ema(strategy._prices, 5)
    )

    assert strategy.calculate_macd() == pytest.approx(expected)


def test_calculate_signal_line_not_ready() -> None:
    strategy = MACDStrategy(
        fast_period=3,
        slow_period=5,
        signal_period=3,
    )

    strategy._macd_history.extend([0.1, 0.2])

    assert strategy.calculate_signal_line() is None


def test_calculate_signal_line() -> None:
    strategy = MACDStrategy(
        fast_period=3,
        slow_period=5,
        signal_period=3,
    )

    strategy._macd_history.extend([0.0, 0.2, 0.4])

    assert strategy.calculate_signal_line() == pytest.approx(0.25)


def test_hold_until_enough_price_history() -> None:
    strategy = MACDStrategy(
        fast_period=3,
        slow_period=5,
        signal_period=3,
    )

    for price in [10.0, 10.0, 10.0, 10.0]:
        signal = strategy.generate_signal(
            {"symbol": "TEST", "price": price}
        )

        assert signal.action is SignalAction.HOLD
        assert signal.confidence == 0.0
        assert signal.reason == "Waiting for sufficient price history"

    assert strategy.ready is False


def test_hold_until_enough_macd_history() -> None:
    strategy = MACDStrategy(
        fast_period=3,
        slow_period=5,
        signal_period=3,
    )

    for price in [10.0, 10.0, 10.0, 10.0, 10.0, 10.0]:
        signal = strategy.generate_signal(
            {"symbol": "TEST", "price": price}
        )

    assert signal.action is SignalAction.HOLD
    assert signal.confidence == 0.0
    assert signal.reason == "Waiting for sufficient MACD history"
    assert strategy.ready is False


def test_strategy_becomes_ready() -> None:
    strategy = MACDStrategy(
        fast_period=3,
        slow_period=5,
        signal_period=3,
    )

    for price in [10.0] * 7:
        strategy.generate_signal(
            {"symbol": "TEST", "price": price}
        )

    assert strategy.ready is True
    assert strategy.current_macd == pytest.approx(0.0)
    assert strategy.current_signal == pytest.approx(0.0)
    assert strategy.current_histogram == pytest.approx(0.0)


def test_buy_on_bullish_crossover() -> None:
    strategy = MACDStrategy(
        fast_period=3,
        slow_period=5,
        signal_period=3,
    )

    signal: StrategySignal | None = None

    for price in [10.0] * 8 + [11.0]:
        signal = strategy.generate_signal(
            {"symbol": "TEST", "price": price}
        )

    assert signal is not None
    assert signal.action is SignalAction.BUY
    assert signal.reason == "Bullish MACD crossover"
    assert 0.0 <= signal.confidence <= 1.0
    assert strategy.current_histogram is not None
    assert strategy.current_histogram > 0.0


def test_sell_on_bearish_crossover() -> None:
    strategy = MACDStrategy(
        fast_period=3,
        slow_period=5,
        signal_period=3,
    )

    signal: StrategySignal | None = None

    for price in [10.0] * 8 + [9.0]:
        signal = strategy.generate_signal(
            {"symbol": "TEST", "price": price}
        )

    assert signal is not None
    assert signal.action is SignalAction.SELL
    assert signal.reason == "Bearish MACD crossover"
    assert 0.0 <= signal.confidence <= 1.0
    assert strategy.current_histogram is not None
    assert strategy.current_histogram < 0.0


def test_hold_when_no_crossover_occurs() -> None:
    strategy = MACDStrategy(
        fast_period=3,
        slow_period=5,
        signal_period=3,
    )

    signal: StrategySignal | None = None

    for price in [10.0] * 8:
        signal = strategy.generate_signal(
            {"symbol": "TEST", "price": price}
        )

    assert signal is not None
    assert signal.action is SignalAction.HOLD
    assert signal.confidence == 0.5
    assert signal.reason == "No MACD crossover"


def test_invalid_price_inputs() -> None:
    strategy = MACDStrategy()

    with pytest.raises(KeyError, match="price is required"):
        strategy.generate_signal({"symbol": "TEST"})

    with pytest.raises(TypeError, match="price must be numeric"):
        strategy.generate_signal(
            {"symbol": "TEST", "price": "100"}
        )

    with pytest.raises(TypeError, match="price must be numeric"):
        strategy.generate_signal(
            {"symbol": "TEST", "price": True}
        )

    with pytest.raises(
        ValueError,
        match="price must be greater than zero",
    ):
        strategy.generate_signal(
            {"symbol": "TEST", "price": 0.0}
        )

    with pytest.raises(
        ValueError,
        match="price must be greater than zero",
    ):
        strategy.generate_signal(
            {"symbol": "TEST", "price": -1.0}
        )


def test_reset_and_to_dict() -> None:
    strategy = MACDStrategy(
        fast_period=3,
        slow_period=5,
        signal_period=3,
    )

    for price in [10.0] * 8 + [11.0]:
        strategy.generate_signal(
            {"symbol": "TEST", "price": price}
        )

    assert strategy.signal_count == 9
    assert strategy.ready is True

    data = strategy.to_dict()

    assert data["name"] == "MACD Strategy"
    assert data["description"] == (
        "Moving Average Convergence Divergence strategy"
    )
    assert data["enabled"] is True
    assert data["config"] == {
        "fast_period": 3,
        "slow_period": 5,
        "signal_period": 3,
    }
    assert data["signal_count"] == 9

    strategy.reset()

    assert strategy.signal_count == 0
    assert strategy.ready is False
    assert strategy.current_macd is None
    assert strategy.current_signal is None
    assert strategy.current_histogram is None
    assert strategy.calculate_macd() is None
    assert strategy.calculate_signal_line() is None
