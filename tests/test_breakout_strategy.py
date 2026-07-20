from __future__ import annotations

import pytest

from app.strategies.breakout_strategy import BreakoutStrategy
from app.strategies.strategy_signal import SignalAction


def test_default_creation():
    strategy = BreakoutStrategy()

    assert strategy.name == "Breakout Strategy"
    assert strategy.lookback_period == 20
    assert strategy.breakout_threshold == 0.0
    assert strategy.enabled is True
    assert strategy.ready is False


def test_invalid_lookback_type():
    with pytest.raises(TypeError, match="lookback_period must be an integer"):
        BreakoutStrategy(lookback_period=2.5)


def test_invalid_lookback_period():
    with pytest.raises(ValueError, match="lookback_period must be greater than one"):
        BreakoutStrategy(lookback_period=1)


def test_invalid_threshold_type():
    with pytest.raises(TypeError, match="breakout_threshold must be numeric"):
        BreakoutStrategy(breakout_threshold="invalid")


def test_invalid_threshold_value():
    with pytest.raises(ValueError, match="breakout_threshold must not be negative"):
        BreakoutStrategy(breakout_threshold=-0.01)


def test_calculate_high_empty():
    strategy = BreakoutStrategy(lookback_period=3)

    assert strategy.calculate_high() is None


def test_calculate_low_empty():
    strategy = BreakoutStrategy(lookback_period=3)

    assert strategy.calculate_low() is None


def test_hold_until_ready():
    strategy = BreakoutStrategy(lookback_period=3)

    signal = strategy.generate_signal(
        {
            "symbol": "AAPL",
            "price": 100,
        }
    )

    assert signal.action is SignalAction.HOLD
    assert signal.confidence == 0.0
    assert strategy.ready is False


def test_strategy_becomes_ready():
    strategy = BreakoutStrategy(lookback_period=3)

    strategy.generate_signal({"symbol": "AAPL", "price": 100})
    strategy.generate_signal({"symbol": "AAPL", "price": 101})
    strategy.generate_signal({"symbol": "AAPL", "price": 102})

    assert strategy.ready is True


def test_buy_breakout():
    strategy = BreakoutStrategy(lookback_period=3)

    strategy.generate_signal({"symbol": "AAPL", "price": 100})
    strategy.generate_signal({"symbol": "AAPL", "price": 101})
    signal = strategy.generate_signal({"symbol": "AAPL", "price": 105})

    assert signal.action is SignalAction.BUY
    assert 0.0 <= signal.confidence <= 1.0
    assert signal.reason == "Bullish breakout"


def test_sell_breakdown():
    strategy = BreakoutStrategy(lookback_period=3)

    strategy.generate_signal({"symbol": "AAPL", "price": 105})
    strategy.generate_signal({"symbol": "AAPL", "price": 104})
    signal = strategy.generate_signal({"symbol": "AAPL", "price": 100})

    assert signal.action is SignalAction.SELL
    assert 0.0 <= signal.confidence <= 1.0
    assert signal.reason == "Bearish breakdown"


def test_hold_inside_range():
    strategy = BreakoutStrategy(lookback_period=3)

    strategy.generate_signal({"symbol": "AAPL", "price": 100})
    strategy.generate_signal({"symbol": "AAPL", "price": 110})
    signal = strategy.generate_signal({"symbol": "AAPL", "price": 105})

    assert signal.action is SignalAction.HOLD
    assert signal.confidence == 0.5
    assert signal.reason == "Price inside breakout range"


def test_breakout_threshold_blocks_small_breakout():
    strategy = BreakoutStrategy(
        lookback_period=3,
        breakout_threshold=0.05,
    )

    strategy.generate_signal({"symbol": "AAPL", "price": 100})
    strategy.generate_signal({"symbol": "AAPL", "price": 101})
    signal = strategy.generate_signal({"symbol": "AAPL", "price": 104})

    assert signal.action is SignalAction.HOLD


def test_price_required():
    strategy = BreakoutStrategy(lookback_period=3)

    with pytest.raises(KeyError, match="price is required"):
        strategy.generate_signal({"symbol": "AAPL"})


def test_price_must_be_numeric():
    strategy = BreakoutStrategy(lookback_period=3)

    with pytest.raises(TypeError, match="price must be numeric"):
        strategy.generate_signal(
            {
                "symbol": "AAPL",
                "price": "100",
            }
        )


def test_price_must_be_positive():
    strategy = BreakoutStrategy(lookback_period=3)

    with pytest.raises(ValueError, match="price must be greater than zero"):
        strategy.generate_signal(
            {
                "symbol": "AAPL",
                "price": 0,
            }
        )


def test_reset():
    strategy = BreakoutStrategy(lookback_period=3)

    strategy.generate_signal({"symbol": "AAPL", "price": 100})
    strategy.generate_signal({"symbol": "AAPL", "price": 101})
    strategy.generate_signal({"symbol": "AAPL", "price": 105})

    assert strategy.ready is True
    assert strategy.signal_count == 3

    strategy.reset()

    assert strategy.ready is False
    assert strategy.signal_count == 0
    assert strategy.highest_high is None
    assert strategy.lowest_low is None


def test_to_dict():
    strategy = BreakoutStrategy(
        lookback_period=10,
        breakout_threshold=0.02,
    )

    data = strategy.to_dict()

    assert data["name"] == "Breakout Strategy"
    assert data["config"]["lookback_period"] == 10
    assert data["config"]["breakout_threshold"] == 0.02