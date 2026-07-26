from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.backtesting import (
    BacktestConfig,
    BacktestEngine,
    BacktestStatus,
    ExecutionError,
    ExecutionSimulator,
    FixedSlippage,
    FlatCommission,
    HistoricalBar,
    OrderSide,
    PercentageCommission,
    PercentageSlippage,
    SimulatedOrder,
    SimulationEngine,
    SimulationError,
)


START = datetime(2025, 1, 2, 14, 30, tzinfo=timezone.utc)


def bar(minutes: int, close: str, symbol: str = "AAPL") -> HistoricalBar:
    price = Decimal(close)
    return HistoricalBar(
        symbol=symbol,
        timestamp=START + timedelta(minutes=minutes),
        open=price,
        high=price + Decimal("1"),
        low=price - Decimal("1"),
        close=price,
        volume=Decimal("1000"),
    )


def config() -> BacktestConfig:
    return BacktestConfig(
        strategy_id="simulation-test",
        strategy_version="1.0.0",
        dataset_id="AAPL-TEST",
        initial_capital=Decimal("100000"),
        start_time=START,
        end_time=START + timedelta(days=1),
    )


def test_simulation_releases_bars_in_order_without_lookahead_and_resets():
    bars = (bar(0, "100"), bar(1, "101"), bar(2, "102"))
    engine = SimulationEngine(bars)

    assert engine.current_bar is None
    assert engine.visible_history() == ()

    first = engine.next_event()
    assert first is not None
    assert first.sequence == 1
    assert first.bar.close == Decimal("100")
    assert engine.visible_history() == bars[:1]

    remaining = engine.run()
    assert [event.bar.close for event in remaining] == [Decimal("101"), Decimal("102")]
    assert engine.is_finished()

    engine.reset()
    assert engine.current_index == 0
    assert engine.visible_history() == ()
    assert engine.next_event().bar.close == Decimal("100")


def test_unsorted_history_is_rejected():
    with pytest.raises(SimulationError, match="sorted"):
        SimulationEngine((bar(1, "101"), bar(0, "100")))


def test_commission_and_slippage_models_are_adverse_and_deterministic():
    percentage = PercentageCommission(rate=Decimal("0.001"), minimum=Decimal("1"))
    assert percentage.calculate(quantity=Decimal("10"), price=Decimal("100")) == Decimal("1.000")

    fixed = FixedSlippage(amount=Decimal("0.05"))
    assert fixed.apply(reference_price=Decimal("100"), side=OrderSide.BUY) == Decimal("100.05")
    assert fixed.apply(reference_price=Decimal("100"), side=OrderSide.SELL) == Decimal("99.95")

    percent = PercentageSlippage(rate=Decimal("0.001"))
    assert percent.apply(reference_price=Decimal("100"), side=OrderSide.BUY) == Decimal("100.100")
    assert percent.apply(reference_price=Decimal("100"), side=OrderSide.SELL) == Decimal("99.900")


def test_execution_simulator_applies_costs_and_blocks_duplicate_orders():
    simulator = ExecutionSimulator(
        commission_model=FlatCommission(Decimal("1")),
        slippage_model=FixedSlippage(Decimal("0.10")),
    )
    order = SimulatedOrder(
        order_id="ORD-1",
        symbol="AAPL",
        quantity=Decimal("10"),
        side=OrderSide.BUY,
        submitted_at=START,
    )

    report = simulator.execute(order, market_price=Decimal("100"), executed_at=START)
    assert report.fill_price == Decimal("100.10")
    assert report.commission == Decimal("1")
    assert report.slippage_cost == Decimal("1.00")
    assert report.gross_notional == Decimal("1001.00")
    assert report.net_cash_effect == Decimal("-1002.00")
    assert report.to_trade().trade_id == report.execution_id

    with pytest.raises(ExecutionError, match="already executed"):
        simulator.execute(order, market_price=Decimal("100"), executed_at=START)


def test_backtest_engine_integrates_market_replay_and_execution():
    bars = (bar(0, "100"), bar(1, "101"))
    execution = ExecutionSimulator(
        commission_model=FlatCommission(Decimal("1")),
        slippage_model=FixedSlippage(Decimal("0.05")),
    )

    def strategy(event):
        if event.sequence != 1:
            return ()
        return (
            SimulatedOrder(
                order_id="BUY-AAPL-1",
                symbol=event.bar.symbol,
                quantity=Decimal("5"),
                side=OrderSide.BUY,
                submitted_at=event.timestamp,
            ),
        )

    engine = BacktestEngine()
    result = engine.run_simulation(
        config(),
        bars=bars,
        strategy=strategy,
        execution_simulator=execution,
    )

    assert result.status is BacktestStatus.COMPLETED
    assert len(result.trades) == 1
    assert result.trades[0].price == Decimal("100.05")
    assert result.metrics["bars_processed"] == 2
    assert result.metrics["orders_executed"] == 1
    event_types = {event.event_type for event in engine.audit_log.events_for(result.backtest_id)}
    assert "MARKET_BAR_RELEASED" in event_types
    assert "ORDER_EXECUTED" in event_types
    assert "BACKTEST_COMPLETED" in event_types
