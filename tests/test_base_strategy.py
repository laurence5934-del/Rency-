from datetime import datetime

import pytest

from app.strategies.base_strategy import BaseStrategy
from app.strategies.strategy_signal import SignalAction, StrategySignal


class ExampleStrategy(BaseStrategy):
    def generate_signal(
        self,
        *,
        symbol,
        timestamp,
        **kwargs,
    ):
        return StrategySignal(
            symbol=symbol,
            action=kwargs.get("action", SignalAction.HOLD),
            timestamp=timestamp,
            confidence=kwargs.get("confidence", 0.5),
            reason="Example strategy",
        )


class InvalidReturnStrategy(BaseStrategy):
    def generate_signal(
        self,
        *,
        symbol,
        timestamp,
        **kwargs,
    ):
        return "invalid"


class ResettableStrategy(ExampleStrategy):
    def __init__(self):
        self.custom_state = 10
        super().__init__(name="Resettable")

    def on_reset(self):
        self.custom_state = 0


def test_base_strategy_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseStrategy(name="Base")


def test_create_strategy():
    strategy = ExampleStrategy(
        name="Example",
        description="  Example description  ",
        config={"period": 20},
    )

    assert strategy.name == "Example"
    assert strategy.description == "Example description"
    assert strategy.config == {"period": 20}
    assert strategy.enabled is True
    assert strategy.signal_count == 0


def test_strategy_name_is_trimmed():
    strategy = ExampleStrategy(name="  Momentum  ")

    assert strategy.name == "Momentum"


def test_empty_name_is_rejected():
    with pytest.raises(
        ValueError,
        match="strategy name must not be empty",
    ):
        ExampleStrategy(name="   ")


def test_invalid_enabled_value_is_rejected():
    with pytest.raises(TypeError, match="enabled must be a bool"):
        ExampleStrategy(
            name="Example",
            enabled="yes",
        )


def test_invalid_config_is_rejected():
    with pytest.raises(TypeError, match="config must be a mapping"):
        ExampleStrategy(
            name="Example",
            config=["period", 20],
        )


def test_config_returns_copy():
    strategy = ExampleStrategy(
        name="Example",
        config={"period": 20},
    )

    returned_config = strategy.config
    returned_config["period"] = 50

    assert strategy.config == {"period": 20}


def test_disable_and_enable_strategy():
    strategy = ExampleStrategy(name="Example")

    strategy.disable()
    assert strategy.enabled is False

    strategy.enable()
    assert strategy.enabled is True


def test_disabled_strategy_cannot_create_signal():
    strategy = ExampleStrategy(name="Example")
    strategy.disable()

    with pytest.raises(RuntimeError, match="strategy is disabled"):
        strategy.create_signal(
            symbol="AAPL",
            timestamp=datetime(2026, 7, 20),
        )


def test_create_signal():
    strategy = ExampleStrategy(name="Example")
    timestamp = datetime(2026, 7, 20, 10, 30)

    signal = strategy.create_signal(
        symbol="aapl",
        timestamp=timestamp,
        action=SignalAction.BUY,
        confidence=0.85,
    )

    assert signal.symbol == "AAPL"
    assert signal.action is SignalAction.BUY
    assert signal.timestamp == timestamp
    assert signal.confidence == 0.85
    assert signal.reason == "Example strategy"
    assert strategy.signal_count == 1


def test_signal_count_increases():
    strategy = ExampleStrategy(name="Example")
    timestamp = datetime(2026, 7, 20)

    strategy.create_signal(
        symbol="AAPL",
        timestamp=timestamp,
    )
    strategy.create_signal(
        symbol="MSFT",
        timestamp=timestamp,
    )

    assert strategy.signal_count == 2


def test_invalid_signal_return_is_rejected():
    strategy = InvalidReturnStrategy(name="Invalid")

    with pytest.raises(
        TypeError,
        match="generate_signal must return a StrategySignal",
    ):
        strategy.create_signal(
            symbol="AAPL",
            timestamp=datetime(2026, 7, 20),
        )

    assert strategy.signal_count == 0


def test_reset_clears_signal_count():
    strategy = ExampleStrategy(name="Example")

    strategy.create_signal(
        symbol="AAPL",
        timestamp=datetime(2026, 7, 20),
    )

    strategy.reset()

    assert strategy.signal_count == 0


def test_reset_calls_strategy_hook():
    strategy = ResettableStrategy()

    strategy.reset()

    assert strategy.custom_state == 0


def test_to_dict():
    strategy = ExampleStrategy(
        name="Example",
        description="Testing strategy",
        config={"period": 20},
    )

    strategy.create_signal(
        symbol="AAPL",
        timestamp=datetime(2026, 7, 20),
    )

    assert strategy.to_dict() == {
        "name": "Example",
        "description": "Testing strategy",
        "config": {"period": 20},
        "enabled": True,
        "signal_count": 1,
    }


def test_repr():
    strategy = ExampleStrategy(name="Example")

    assert repr(strategy) == (
        "ExampleStrategy("
        "name='Example', "
        "enabled=True, "
        "signal_count=0)"
    )