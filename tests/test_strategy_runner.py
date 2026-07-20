from datetime import datetime

import pytest

from app.strategies.base_strategy import BaseStrategy
from app.strategies.strategy_runner import StrategyRunner
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
            reason="Runner Test",
        )


def test_runner_initialization():
    strategy = ExampleStrategy(name="Example")
    runner = StrategyRunner(strategy)

    assert runner.strategy is strategy
    assert runner.processed_bars == 0


def test_invalid_strategy():
    with pytest.raises(
        TypeError,
        match="strategy must be a BaseStrategy",
    ):
        StrategyRunner("not a strategy")


def test_process_single_bar():
    runner = StrategyRunner(
        ExampleStrategy(name="Example")
    )

    signal = runner.process_bar(
        symbol="AAPL",
        timestamp=datetime(2026, 7, 20),
        action=SignalAction.BUY,
    )

    assert signal is not None
    assert signal.symbol == "AAPL"
    assert signal.action is SignalAction.BUY
    assert runner.processed_bars == 1


def test_process_many():
    runner = StrategyRunner(
        ExampleStrategy(name="Example")
    )

    bars = [
        {
            "symbol": "AAPL",
            "timestamp": datetime(2026, 7, 20),
        },
        {
            "symbol": "MSFT",
            "timestamp": datetime(2026, 7, 21),
        },
        {
            "symbol": "NVDA",
            "timestamp": datetime(2026, 7, 22),
        },
    ]

    signals = runner.process_many(bars)

    assert len(signals) == 3
    assert runner.processed_bars == 3


def test_disabled_strategy_returns_none():
    strategy = ExampleStrategy(name="Example")
    strategy.disable()

    runner = StrategyRunner(strategy)

    signal = runner.process_bar(
        symbol="AAPL",
        timestamp=datetime(2026, 7, 20),
    )

    assert signal is None
    assert runner.processed_bars == 0


def test_reset():
    runner = StrategyRunner(
        ExampleStrategy(name="Example")
    )

    runner.process_bar(
        symbol="AAPL",
        timestamp=datetime(2026, 7, 20),
    )

    assert runner.processed_bars == 1

    runner.reset()

    assert runner.processed_bars == 0
    assert runner.strategy.signal_count == 0


def test_to_dict():
    runner = StrategyRunner(
        ExampleStrategy(name="Example")
    )

    runner.process_bar(
        symbol="AAPL",
        timestamp=datetime(2026, 7, 20),
    )

    assert runner.to_dict() == {
        "strategy": "Example",
        "processed_bars": 1,
    }


def test_repr():
    runner = StrategyRunner(
        ExampleStrategy(name="Momentum")
    )

    assert repr(runner) == (
        "StrategyRunner("
        "strategy='Momentum', "
        "processed_bars=0)"
    )


def test_process_many_empty():
    runner = StrategyRunner(
        ExampleStrategy(name="Example")
    )

    signals = runner.process_many([])

    assert signals == []
    assert runner.processed_bars == 0


def test_signal_count_matches_processed_bars():
    runner = StrategyRunner(
        ExampleStrategy(name="Example")
    )

    for symbol in ["AAPL", "MSFT", "NVDA"]:
        runner.process_bar(
            symbol=symbol,
            timestamp=datetime(2026, 7, 20),
        )

    assert runner.strategy.signal_count == 3
    assert runner.processed_bars == 3