from __future__ import annotations

import pytest

from app.strategies.rsi_strategy import RSIStrategy
from app.strategies.strategy_signal import SignalAction, StrategySignal


def test_default_creation() -> None:
    strategy = RSIStrategy()

    assert strategy.name == "RSI Strategy"
    assert strategy.period == 14
    assert strategy.oversold_threshold == 30.0
    assert strategy.overbought_threshold == 70.0
    assert strategy.enabled is True
    assert strategy.ready is False
    assert strategy.current_rsi is None


def test_invalid_period_type() -> None:
    with pytest.raises(TypeError, match="period must be an integer"):
        RSIStrategy(period=14.0)

    with pytest.raises(TypeError, match="period must be an integer"):
        RSIStrategy(period=True)


def test_invalid_period_value() -> None:
    with pytest.raises(ValueError, match="period must be greater than one"):
        RSIStrategy(period=1)

    with pytest.raises(ValueError, match="period must be greater than one"):
        RSIStrategy(period=0)


def test_invalid_oversold_threshold_type() -> None:
    with pytest.raises(
        TypeError,
        match="oversold_threshold must be numeric",
    ):
        RSIStrategy(oversold_threshold="30")  # type: ignore[arg-type]

    with pytest.raises(
        TypeError,
        match="oversold_threshold must be numeric",
    ):
        RSIStrategy(oversold_threshold=True)


def test_invalid_overbought_threshold_type() -> None:
    with pytest.raises(
        TypeError,
        match="overbought_threshold must be numeric",
    ):
        RSIStrategy(overbought_threshold="70")  # type: ignore[arg-type]

    with pytest.raises(
        TypeError,
        match="overbought_threshold must be numeric",
    ):
        RSIStrategy(overbought_threshold=False)


def test_invalid_threshold_range() -> None:
    with pytest.raises(
        ValueError,
        match="oversold_threshold must be between 0.0 and 100.0",
    ):
        RSIStrategy(oversold_threshold=-1.0)

    with pytest.raises(
        ValueError,
        match="overbought_threshold must be between 0.0 and 100.0",
    ):
        RSIStrategy(overbought_threshold=101.0)


def test_oversold_must_be_less_than_overbought() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "oversold_threshold must be less than "
            "overbought_threshold"
        ),
    ):
        RSIStrategy(
            oversold_threshold=70.0,
            overbought_threshold=70.0,
        )

    with pytest.raises(
        ValueError,
        match=(
            "oversold_threshold must be less than "
            "overbought_threshold"
        ),
    ):
        RSIStrategy(
            oversold_threshold=80.0,
            overbought_threshold=70.0,
        )


def test_calculate_rsi_not_ready() -> None:
    strategy = RSIStrategy(period=4)

    assert strategy.calculate_rsi() is None


def test_hold_until_ready() -> None:
    strategy = RSIStrategy(period=4)

    for price in [100.0, 101.0, 102.0, 103.0]:
        signal = strategy.generate_signal(
            {"symbol": "TEST", "price": price}
        )

        assert signal.action is SignalAction.HOLD
        assert signal.confidence == 0.0
        assert signal.reason == "Waiting for sufficient price history"

    assert strategy.ready is False


def test_strategy_becomes_ready() -> None:
    strategy = RSIStrategy(period=4)

    for price in [100.0, 101.0, 102.0, 103.0, 104.0]:
        strategy.generate_signal({"symbol": "TEST", "price": price})

    assert strategy.ready is True
    assert strategy.current_rsi is not None


def test_buy_when_rsi_is_oversold() -> None:
    strategy = RSIStrategy(period=4)

    signal: StrategySignal | None = None

    for price in [100.0, 90.0, 80.0, 70.0, 60.0]:
        signal = strategy.generate_signal(
            {"symbol": "TEST", "price": price}
        )

    assert signal is not None
    assert strategy.current_rsi == pytest.approx(0.0)
    assert signal.action is SignalAction.BUY
    assert signal.reason == "RSI indicates oversold conditions"
    assert 0.0 <= signal.confidence <= 1.0


def test_sell_when_rsi_is_overbought() -> None:
    strategy = RSIStrategy(period=4)

    signal: StrategySignal | None = None

    for price in [60.0, 70.0, 80.0, 90.0, 100.0]:
        signal = strategy.generate_signal(
            {"symbol": "TEST", "price": price}
        )

    assert signal is not None
    assert strategy.current_rsi == pytest.approx(100.0)
    assert signal.action is SignalAction.SELL
    assert signal.reason == "RSI indicates overbought conditions"
    assert 0.0 <= signal.confidence <= 1.0


def test_hold_when_rsi_is_neutral() -> None:
    strategy = RSIStrategy(period=4)

    signal: StrategySignal | None = None

    for price in [100.0, 110.0, 100.0, 110.0, 100.0]:
        signal = strategy.generate_signal(
            {"symbol": "TEST", "price": price}
        )

    assert signal is not None
    assert strategy.current_rsi == pytest.approx(50.0)
    assert signal.action is SignalAction.HOLD
    assert signal.confidence == 0.5
    assert signal.reason == "RSI is within the neutral range"


def test_price_required() -> None:
    strategy = RSIStrategy()

    with pytest.raises(KeyError, match="price is required"):
        strategy.generate_signal({"symbol": "TEST"})


def test_price_must_be_numeric() -> None:
    strategy = RSIStrategy()

    with pytest.raises(TypeError, match="price must be numeric"):
        strategy.generate_signal(
            {"symbol": "TEST", "price": "100"}
        )

    with pytest.raises(TypeError, match="price must be numeric"):
        strategy.generate_signal(
            {"symbol": "TEST", "price": True}
        )


def test_price_must_be_positive() -> None:
    strategy = RSIStrategy()

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


def test_reset() -> None:
    strategy = RSIStrategy(period=4)

    for price in [100.0, 90.0, 80.0, 70.0, 60.0]:
        strategy.generate_signal(
            {"symbol": "TEST", "price": price}
        )

    assert strategy.ready is True
    assert strategy.current_rsi is not None
    assert strategy.signal_count == 5

    strategy.reset()

    assert strategy.ready is False
    assert strategy.current_rsi is None
    assert strategy.signal_count == 0
    assert strategy.calculate_rsi() is None


def test_to_dict() -> None:
    strategy = RSIStrategy(
        period=10,
        oversold_threshold=25.0,
        overbought_threshold=75.0,
    )

    data = strategy.to_dict()

    assert data["name"] == "RSI Strategy"
    assert data["description"] == (
        "Relative Strength Index momentum strategy"
    )
    assert data["enabled"] is True
    assert data["config"] == {
        "period": 10,
        "oversold_threshold": 25.0,
        "overbought_threshold": 75.0,
    }
    assert data["signal_count"] == 0
