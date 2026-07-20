from datetime import datetime

import pytest

from app.strategies.moving_average_strategy import MovingAverageStrategy
from app.strategies.strategy_signal import SignalAction


def test_default_creation():
    strategy = MovingAverageStrategy()

    assert strategy.fast_period == 20
    assert strategy.slow_period == 50
    assert not strategy.is_ready
    assert strategy.fast_sma is None
    assert strategy.slow_sma is None


def test_invalid_fast_period():
    with pytest.raises(ValueError, match="fast_period must be greater than zero"):
        MovingAverageStrategy(fast_period=0)


def test_invalid_slow_period():
    with pytest.raises(ValueError, match="slow_period must be greater than zero"):
        MovingAverageStrategy(slow_period=0)


def test_fast_period_must_be_less_than_slow():
    with pytest.raises(ValueError, match="fast_period must be less than slow_period"):
        MovingAverageStrategy(
            fast_period=20,
            slow_period=20,
        )


def test_calculate_sma():
    sma = MovingAverageStrategy.calculate_sma(
        [1, 2, 3, 4, 5],
        5,
    )

    assert sma == 3.0


def test_not_enough_prices():
    with pytest.raises(ValueError):
        MovingAverageStrategy.calculate_sma(
            [1, 2],
            5,
        )


def test_hold_until_ready():
    strategy = MovingAverageStrategy(
        fast_period=3,
        slow_period=5,
    )

    for price in [10, 11, 12, 13]:
        signal = strategy.generate_signal(
            symbol="AAPL",
            timestamp=datetime.now(),
            close=price,
        )

        assert signal.action is SignalAction.HOLD

    assert not strategy.is_ready


def test_strategy_becomes_ready():
    strategy = MovingAverageStrategy(
        fast_period=3,
        slow_period=5,
    )

    for price in [10, 11, 12, 13, 14]:
        strategy.generate_signal(
            symbol="AAPL",
            timestamp=datetime.now(),
            close=price,
        )

    assert strategy.is_ready
    assert strategy.fast_sma is not None
    assert strategy.slow_sma is not None


def test_buy_or_hold_after_ready():
    strategy = MovingAverageStrategy(
        fast_period=2,
        slow_period=3,
    )

    prices = [10, 9, 8, 11]

    signal = None

    for p in prices:
        signal = strategy.generate_signal(
            symbol="AAPL",
            timestamp=datetime.now(),
            close=p,
        )

    assert signal.action in (
        SignalAction.BUY,
        SignalAction.HOLD,
    )


def test_sell_or_hold_after_ready():
    strategy = MovingAverageStrategy(
        fast_period=2,
        slow_period=3,
    )

    prices = [10, 11, 12, 8]

    signal = None

    for p in prices:
        signal = strategy.generate_signal(
            symbol="AAPL",
            timestamp=datetime.now(),
            close=p,
        )

    assert signal.action in (
        SignalAction.SELL,
        SignalAction.HOLD,
    )


def test_reset():
    strategy = MovingAverageStrategy(
        fast_period=3,
        slow_period=5,
    )

    for price in [1, 2, 3, 4, 5]:
        strategy.generate_signal(
            symbol="AAPL",
            timestamp=datetime.now(),
            close=price,
        )

    strategy.reset()

    assert strategy.fast_sma is None
    assert strategy.slow_sma is None
    assert strategy.price_history == ()
    assert not strategy.is_ready


def test_to_dict():
    strategy = MovingAverageStrategy(
        fast_period=5,
        slow_period=10,
    )

    data = strategy.to_dict()

    assert data["fast_period"] == 5
    assert data["slow_period"] == 10
    assert data["price_count"] == 0
    assert data["is_ready"] is False


def test_price_must_be_positive():
    strategy = MovingAverageStrategy(
        fast_period=3,
        slow_period=5,
    )

    with pytest.raises(ValueError):
        strategy.generate_signal(
            symbol="AAPL",
            timestamp=datetime.now(),
            close=0,
        )


def test_price_required():
    strategy = MovingAverageStrategy(
        fast_period=3,
        slow_period=5,
    )

    with pytest.raises(ValueError):
        strategy.generate_signal(
            symbol="AAPL",
            timestamp=datetime.now(),
        )


def test_price_history_grows():
    strategy = MovingAverageStrategy(
        fast_period=3,
        slow_period=5,
    )

    strategy.generate_signal(
        symbol="AAPL",
        timestamp=datetime.now(),
        close=100,
    )

    strategy.generate_signal(
        symbol="AAPL",
        timestamp=datetime.now(),
        close=101,
    )

    assert len(strategy.price_history) == 2