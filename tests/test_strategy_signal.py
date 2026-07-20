from datetime import datetime

import pytest

from app.strategies.strategy_signal import SignalAction, StrategySignal


def test_signal_action_values():
    assert SignalAction.BUY.value == "BUY"
    assert SignalAction.SELL.value == "SELL"
    assert SignalAction.HOLD.value == "HOLD"


def test_create_valid_buy_signal():
    timestamp = datetime(2026, 7, 20, 10, 30)

    signal = StrategySignal(
        symbol="aapl",
        action=SignalAction.BUY,
        timestamp=timestamp,
        confidence=0.85,
        reason="Moving average crossover",
        stop_loss=190.0,
        take_profit=220.0,
        position_size=10.0,
    )

    assert signal.symbol == "AAPL"
    assert signal.action is SignalAction.BUY
    assert signal.timestamp == timestamp
    assert signal.confidence == 0.85
    assert signal.reason == "Moving average crossover"
    assert signal.stop_loss == 190.0
    assert signal.take_profit == 220.0
    assert signal.position_size == 10.0


def test_signal_defaults():
    signal = StrategySignal(
        symbol="MSFT",
        action=SignalAction.HOLD,
        timestamp=datetime(2026, 7, 20),
    )

    assert signal.confidence == 0.0
    assert signal.reason == ""
    assert signal.stop_loss is None
    assert signal.take_profit is None
    assert signal.position_size is None


def test_symbol_is_normalized():
    signal = StrategySignal(
        symbol="  nvda  ",
        action=SignalAction.BUY,
        timestamp=datetime(2026, 7, 20),
    )

    assert signal.symbol == "NVDA"


def test_reason_is_trimmed():
    signal = StrategySignal(
        symbol="TSLA",
        action=SignalAction.SELL,
        timestamp=datetime(2026, 7, 20),
        reason="  Trend reversal  ",
    )

    assert signal.reason == "Trend reversal"


def test_empty_symbol_is_rejected():
    with pytest.raises(ValueError, match="symbol must not be empty"):
        StrategySignal(
            symbol="   ",
            action=SignalAction.BUY,
            timestamp=datetime(2026, 7, 20),
        )


def test_invalid_action_is_rejected():
    with pytest.raises(TypeError, match="action must be a SignalAction"):
        StrategySignal(
            symbol="AAPL",
            action="BUY",
            timestamp=datetime(2026, 7, 20),
        )


def test_invalid_timestamp_is_rejected():
    with pytest.raises(TypeError, match="timestamp must be a datetime"):
        StrategySignal(
            symbol="AAPL",
            action=SignalAction.BUY,
            timestamp="2026-07-20",
        )


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_invalid_confidence_is_rejected(confidence):
    with pytest.raises(
        ValueError,
        match="confidence must be between 0.0 and 1.0",
    ):
        StrategySignal(
            symbol="AAPL",
            action=SignalAction.BUY,
            timestamp=datetime(2026, 7, 20),
            confidence=confidence,
        )


@pytest.mark.parametrize(
    ("field_name", "field_value", "error_message"),
    [
        ("stop_loss", 0, "stop_loss must be greater than zero"),
        ("take_profit", -1, "take_profit must be greater than zero"),
        ("position_size", 0, "position_size must be greater than zero"),
    ],
)
def test_invalid_optional_numeric_values_are_rejected(
    field_name,
    field_value,
    error_message,
):
    kwargs = {
        "symbol": "AAPL",
        "action": SignalAction.BUY,
        "timestamp": datetime(2026, 7, 20),
        field_name: field_value,
    }

    with pytest.raises(ValueError, match=error_message):
        StrategySignal(**kwargs)


def test_signal_helpers():
    timestamp = datetime(2026, 7, 20)

    buy_signal = StrategySignal(
        symbol="AAPL",
        action=SignalAction.BUY,
        timestamp=timestamp,
    )
    sell_signal = StrategySignal(
        symbol="AAPL",
        action=SignalAction.SELL,
        timestamp=timestamp,
    )
    hold_signal = StrategySignal(
        symbol="AAPL",
        action=SignalAction.HOLD,
        timestamp=timestamp,
    )

    assert buy_signal.is_buy is True
    assert buy_signal.is_sell is False
    assert buy_signal.is_hold is False

    assert sell_signal.is_buy is False
    assert sell_signal.is_sell is True
    assert sell_signal.is_hold is False

    assert hold_signal.is_buy is False
    assert hold_signal.is_sell is False
    assert hold_signal.is_hold is True


def test_signal_to_dict():
    timestamp = datetime(2026, 7, 20, 9, 45)

    signal = StrategySignal(
        symbol="AAPL",
        action=SignalAction.BUY,
        timestamp=timestamp,
        confidence=0.9,
        reason="Breakout confirmed",
        stop_loss=195.0,
        take_profit=225.0,
        position_size=5.0,
    )

    assert signal.to_dict() == {
        "symbol": "AAPL",
        "action": "BUY",
        "timestamp": "2026-07-20T09:45:00",
        "confidence": 0.9,
        "reason": "Breakout confirmed",
        "stop_loss": 195.0,
        "take_profit": 225.0,
        "position_size": 5.0,
    }


def test_signal_is_immutable():
    signal = StrategySignal(
        symbol="AAPL",
        action=SignalAction.BUY,
        timestamp=datetime(2026, 7, 20),
    )

    with pytest.raises(Exception):
        signal.symbol = "MSFT"