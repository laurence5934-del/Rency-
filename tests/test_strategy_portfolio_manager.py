from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from app.strategies.base_strategy import BaseStrategy
from app.strategies.strategy_portfolio_manager import StrategyPortfolioManager
from app.strategies.strategy_signal import SignalAction, StrategySignal


class FixedSignalStrategy(BaseStrategy):
    """Small deterministic strategy used to test the portfolio manager."""

    def __init__(
        self,
        name: str,
        action: SignalAction = SignalAction.HOLD,
        confidence: float = 0.5,
        enabled: bool = True,
    ) -> None:
        self._action = action
        self._confidence = confidence
        self.reset_hook_calls = 0

        super().__init__(
            name=name,
            description=f"Fixed {action.value} test strategy",
            config={},
            enabled=enabled,
        )

    def validate_config(self) -> None:
        return None

    def on_reset(self) -> None:
        self.reset_hook_calls += 1

    def generate_signal(
        self,
        market_data: dict[str, Any],
    ) -> StrategySignal:
        if not self.enabled:
            raise RuntimeError("strategy is disabled")

        symbol = str(market_data.get("symbol", "UNKNOWN"))

        signal = StrategySignal(
            symbol=symbol,
            action=self._action,
            timestamp=datetime.now(),
            confidence=self._confidence,
            reason=f"Fixed {self._action.value} signal",
        )

        self._signal_count += 1
        return signal


class InvalidReturnStrategy(FixedSignalStrategy):
    def generate_signal(self, market_data: dict[str, Any]) -> Any:
        self._signal_count += 1
        return "not-a-strategy-signal"


def test_default_initialization() -> None:
    manager = StrategyPortfolioManager()

    assert manager.strategy_count == 0
    assert manager.consensus_count == 0
    assert manager.strategies == ()
    assert manager.last_signals == ()
    assert manager.weights == {}


def test_initialization_with_strategies() -> None:
    first = FixedSignalStrategy("First")
    second = FixedSignalStrategy("Second")

    manager = StrategyPortfolioManager([first, second])

    assert manager.strategy_count == 2
    assert manager.strategies == (first, second)
    assert manager.weights == {
        "First": 1.0,
        "Second": 1.0,
    }


def test_initialization_with_custom_weights() -> None:
    first = FixedSignalStrategy("First")
    second = FixedSignalStrategy("Second")

    manager = StrategyPortfolioManager(
        [first, second],
        weights={
            "First": 2.5,
            "Second": 0.75,
        },
    )

    assert manager.weights == {
        "First": 2.5,
        "Second": 0.75,
    }


def test_weights_must_be_dictionary() -> None:
    with pytest.raises(TypeError, match="weights must be a dictionary"):
        StrategyPortfolioManager(weights=[("First", 1.0)])  # type: ignore[arg-type]


def test_unknown_weight_name_is_rejected() -> None:
    strategy = FixedSignalStrategy("Known")

    with pytest.raises(
        ValueError,
        match="weights contain unknown strategies: Unknown",
    ):
        StrategyPortfolioManager(
            [strategy],
            weights={"Unknown": 2.0},
        )


def test_add_strategy() -> None:
    manager = StrategyPortfolioManager()
    strategy = FixedSignalStrategy("Added")

    manager.add_strategy(strategy, weight=1.5)

    assert manager.strategy_count == 1
    assert manager.strategies == (strategy,)
    assert manager.weights == {"Added": 1.5}


def test_invalid_strategy_is_rejected() -> None:
    manager = StrategyPortfolioManager()

    with pytest.raises(
        TypeError,
        match="strategy must inherit from BaseStrategy",
    ):
        manager.add_strategy(object())  # type: ignore[arg-type]


def test_duplicate_strategy_name_is_rejected() -> None:
    manager = StrategyPortfolioManager(
        [FixedSignalStrategy("Duplicate")]
    )

    with pytest.raises(
        ValueError,
        match="strategy with name 'Duplicate' already exists",
    ):
        manager.add_strategy(FixedSignalStrategy("Duplicate"))


@pytest.mark.parametrize("weight", [0, -1, -0.1])
def test_weight_must_be_positive(weight: float) -> None:
    manager = StrategyPortfolioManager()

    with pytest.raises(
        ValueError,
        match="weight must be greater than zero",
    ):
        manager.add_strategy(
            FixedSignalStrategy("Invalid Weight"),
            weight=weight,
        )


@pytest.mark.parametrize("weight", ["1", True, None])
def test_weight_must_be_numeric(weight: Any) -> None:
    manager = StrategyPortfolioManager()

    with pytest.raises(TypeError, match="weight must be numeric"):
        manager.add_strategy(
            FixedSignalStrategy("Invalid Weight"),
            weight=weight,
        )


def test_get_strategy() -> None:
    strategy = FixedSignalStrategy("Lookup")
    manager = StrategyPortfolioManager([strategy])

    assert manager.get_strategy("Lookup") is strategy
    assert manager.get_strategy("  Lookup  ") is strategy


def test_get_unknown_strategy_is_rejected() -> None:
    manager = StrategyPortfolioManager()

    with pytest.raises(
        KeyError,
        match="strategy 'Missing' was not found",
    ):
        manager.get_strategy("Missing")


def test_remove_strategy() -> None:
    first = FixedSignalStrategy("First")
    second = FixedSignalStrategy("Second")
    manager = StrategyPortfolioManager(
        [first, second],
        weights={"First": 2.0, "Second": 3.0},
    )

    removed = manager.remove_strategy("First")

    assert removed is first
    assert manager.strategies == (second,)
    assert manager.weights == {"Second": 3.0}


def test_remove_unknown_strategy_is_rejected() -> None:
    manager = StrategyPortfolioManager()

    with pytest.raises(
        KeyError,
        match="strategy 'Missing' was not found",
    ):
        manager.remove_strategy("Missing")


def test_set_weight() -> None:
    strategy = FixedSignalStrategy("Weighted")
    manager = StrategyPortfolioManager([strategy])

    manager.set_weight("Weighted", 4.25)

    assert manager.weights == {"Weighted": 4.25}


def test_set_weight_for_unknown_strategy_is_rejected() -> None:
    manager = StrategyPortfolioManager()

    with pytest.raises(
        KeyError,
        match="strategy 'Missing' was not found",
    ):
        manager.set_weight("Missing", 2.0)


def test_run_strategies() -> None:
    buy = FixedSignalStrategy(
        "Buy",
        SignalAction.BUY,
        confidence=0.8,
    )
    sell = FixedSignalStrategy(
        "Sell",
        SignalAction.SELL,
        confidence=0.6,
    )
    manager = StrategyPortfolioManager([buy, sell])

    signals = manager.run_strategies(
        {"symbol": "AAPL", "price": 100.0}
    )

    assert len(signals) == 2
    assert signals[0].action is SignalAction.BUY
    assert signals[1].action is SignalAction.SELL
    assert manager.last_signals == tuple(signals)


def test_run_strategies_skips_disabled_strategy() -> None:
    enabled = FixedSignalStrategy(
        "Enabled",
        SignalAction.BUY,
        confidence=0.9,
    )
    disabled = FixedSignalStrategy(
        "Disabled",
        SignalAction.SELL,
        confidence=1.0,
        enabled=False,
    )
    manager = StrategyPortfolioManager([enabled, disabled])

    signals = manager.run_strategies(
        {"symbol": "AAPL", "price": 100.0}
    )

    assert len(signals) == 1
    assert signals[0].action is SignalAction.BUY
    assert enabled.signal_count == 1
    assert disabled.signal_count == 0


def test_run_strategies_requires_dictionary() -> None:
    manager = StrategyPortfolioManager()

    with pytest.raises(
        TypeError,
        match="market_data must be a dictionary",
    ):
        manager.run_strategies([])  # type: ignore[arg-type]


def test_invalid_strategy_signal_is_rejected() -> None:
    manager = StrategyPortfolioManager(
        [InvalidReturnStrategy("Invalid")]
    )

    with pytest.raises(
        TypeError,
        match="strategy 'Invalid' returned an invalid signal",
    ):
        manager.run_strategies(
            {"symbol": "AAPL", "price": 100.0}
        )


def test_buy_consensus() -> None:
    manager = StrategyPortfolioManager(
        [
            FixedSignalStrategy(
                "Buy",
                SignalAction.BUY,
                confidence=0.8,
            ),
            FixedSignalStrategy(
                "Sell",
                SignalAction.SELL,
                confidence=0.3,
            ),
        ]
    )

    consensus = manager.generate_consensus(
        {"symbol": "AAPL", "price": 100.0}
    )

    assert consensus.action is SignalAction.BUY
    assert consensus.confidence == pytest.approx(0.4)
    assert consensus.reason == (
        "Weighted strategy consensus favors BUY"
    )
    assert manager.consensus_count == 1


def test_sell_consensus() -> None:
    manager = StrategyPortfolioManager(
        [
            FixedSignalStrategy(
                "Buy",
                SignalAction.BUY,
                confidence=0.2,
            ),
            FixedSignalStrategy(
                "Sell",
                SignalAction.SELL,
                confidence=0.9,
            ),
        ]
    )

    consensus = manager.generate_consensus(
        {"symbol": "MSFT", "price": 200.0}
    )

    assert consensus.action is SignalAction.SELL
    assert consensus.confidence == pytest.approx(0.45)
    assert consensus.reason == (
        "Weighted strategy consensus favors SELL"
    )


def test_custom_weights_change_consensus() -> None:
    buy = FixedSignalStrategy(
        "Buy",
        SignalAction.BUY,
        confidence=0.6,
    )
    sell = FixedSignalStrategy(
        "Sell",
        SignalAction.SELL,
        confidence=0.9,
    )
    manager = StrategyPortfolioManager(
        [buy, sell],
        weights={
            "Buy": 3.0,
            "Sell": 1.0,
        },
    )

    consensus = manager.generate_consensus(
        {"symbol": "NVDA", "price": 150.0}
    )

    assert consensus.action is SignalAction.BUY
    assert consensus.confidence == pytest.approx(0.45)


def test_directional_tie_returns_hold() -> None:
    manager = StrategyPortfolioManager(
        [
            FixedSignalStrategy(
                "Buy",
                SignalAction.BUY,
                confidence=0.7,
            ),
            FixedSignalStrategy(
                "Sell",
                SignalAction.SELL,
                confidence=0.7,
            ),
        ]
    )

    consensus = manager.generate_consensus(
        {"symbol": "TSLA", "price": 250.0}
    )

    assert consensus.action is SignalAction.HOLD
    assert consensus.confidence == 0.0
    assert consensus.reason == (
        "BUY and SELL strategy support is tied"
    )


def test_hold_only_consensus() -> None:
    manager = StrategyPortfolioManager(
        [
            FixedSignalStrategy(
                "Hold One",
                SignalAction.HOLD,
                confidence=0.8,
            ),
            FixedSignalStrategy(
                "Hold Two",
                SignalAction.HOLD,
                confidence=0.4,
            ),
        ]
    )

    consensus = manager.generate_consensus(
        {"symbol": "AMD", "price": 120.0}
    )

    assert consensus.action is SignalAction.HOLD
    assert consensus.confidence == pytest.approx(0.6)
    assert consensus.reason == "No directional strategy consensus"


def test_empty_manager_returns_hold_consensus() -> None:
    manager = StrategyPortfolioManager()

    consensus = manager.generate_consensus(
        {"symbol": "SPY", "price": 500.0}
    )

    assert consensus.symbol == "SPY"
    assert consensus.action is SignalAction.HOLD
    assert consensus.confidence == 0.0
    assert consensus.reason == "No enabled strategies available"
    assert manager.consensus_count == 1


def test_action_summary() -> None:
    manager = StrategyPortfolioManager(
        [
            FixedSignalStrategy("Buy", SignalAction.BUY),
            FixedSignalStrategy("Sell", SignalAction.SELL),
            FixedSignalStrategy("Hold", SignalAction.HOLD),
        ]
    )

    manager.run_strategies(
        {"symbol": "QQQ", "price": 400.0}
    )

    assert manager.action_summary() == {
        "BUY": 1,
        "SELL": 1,
        "HOLD": 1,
    }


def test_reset() -> None:
    first = FixedSignalStrategy(
        "First",
        SignalAction.BUY,
        confidence=0.8,
    )
    second = FixedSignalStrategy(
        "Second",
        SignalAction.HOLD,
        confidence=0.5,
    )
    manager = StrategyPortfolioManager([first, second])

    manager.generate_consensus(
        {"symbol": "AAPL", "price": 100.0}
    )

    assert manager.consensus_count == 1
    assert manager.last_signals
    assert first.signal_count == 1
    assert second.signal_count == 1

    manager.reset()

    assert manager.consensus_count == 0
    assert manager.last_signals == ()
    assert first.signal_count == 0
    assert second.signal_count == 0
    assert first.reset_hook_calls == 1
    assert second.reset_hook_calls == 1


def test_to_dict() -> None:
    strategy = FixedSignalStrategy(
        "Dictionary",
        SignalAction.BUY,
        confidence=0.75,
    )
    manager = StrategyPortfolioManager(
        [strategy],
        weights={"Dictionary": 2.0},
    )

    manager.generate_consensus(
        {"symbol": "AAPL", "price": 100.0}
    )

    data = manager.to_dict()

    assert data["strategy_count"] == 1
    assert data["consensus_count"] == 1
    assert data["weights"] == {"Dictionary": 2.0}
    assert len(data["strategies"]) == 1
    assert len(data["last_signals"]) == 1
    assert data["action_summary"] == {
        "BUY": 1,
        "SELL": 0,
        "HOLD": 0,
    }


def test_repr() -> None:
    manager = StrategyPortfolioManager(
        [FixedSignalStrategy("One")]
    )

    assert repr(manager) == (
        "StrategyPortfolioManager("
        "strategy_count=1, consensus_count=0)"
    )
