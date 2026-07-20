from datetime import datetime

from app.backtesting.backtest_engine import BacktestEngine
from app.backtesting.backtest_models import BacktestConfig
from app.backtesting.trade_models import (
    Trade,
    TradeSide,
    TradeStatus,
)


def create_trade(entry, exit_, qty=10):
    return Trade(
        symbol="AAPL",
        side=TradeSide.BUY,
        quantity=qty,
        entry_price=entry,
        exit_price=exit_,
        entry_time=datetime(2026, 1, 1),
        exit_time=datetime(2026, 1, 2),
        commission=0.0,
        status=TradeStatus.CLOSED,
    )


def test_engine_initialization():
    config = BacktestConfig(initial_cash=100000)

    engine = BacktestEngine(config)

    assert engine.portfolio.cash == 100000
    assert engine.equity_curve.count == 0


def test_record_equity():
    config = BacktestConfig(initial_cash=100000)

    engine = BacktestEngine(config)

    equity = engine.record_equity(datetime(2026, 1, 1))

    assert equity == 100000
    assert engine.equity_curve.count == 1


def test_run_single_trade():
    config = BacktestConfig(initial_cash=100000)

    engine = BacktestEngine(config)

    trade = create_trade(100, 110)

    result = engine.run(
        [trade],
        datetime(2026, 1, 1),
        datetime(2026, 1, 2),
    )

    assert len(result.trades) == 1
    assert result.ending_equity > 100000
    assert result.win_rate == 100.0


def test_engine_reset():
    config = BacktestConfig(initial_cash=100000)

    engine = BacktestEngine(config)

    engine.record_equity(datetime(2026, 1, 1))

    engine.reset()

    assert engine.portfolio.cash == 100000
    assert engine.equity_curve.count == 0


def test_run_multiple_trades():
    config = BacktestConfig(initial_cash=100000)

    engine = BacktestEngine(config)

    trades = [
        create_trade(100, 110),
        create_trade(100, 90),
        create_trade(100, 120),
    ]

    result = engine.run(
        trades,
        datetime(2026, 1, 1),
        datetime(2026, 1, 5),
    )

    assert len(result.trades) == 3
    assert result.profit_factor > 1.0