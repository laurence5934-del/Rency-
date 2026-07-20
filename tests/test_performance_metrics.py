from datetime import datetime

from app.backtesting.backtest_models import EquityPoint
from app.backtesting.trade_models import (
    Trade,
    TradeSide,
    TradeStatus,
)
from app.backtesting.performance_metrics import PerformanceMetrics


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


def test_total_return():
    assert PerformanceMetrics.total_return(
        10000,
        11000,
    ) == 10.0


def test_annualized_return():
    result = PerformanceMetrics.annualized_return(
        10000,
        12100,
        2,
    )

    assert round(result, 2) == 10.0


def test_win_rate():
    trades = [
        create_trade(100, 110),
        create_trade(100, 90),
        create_trade(100, 120),
    ]

    assert round(
        PerformanceMetrics.win_rate(trades),
        2,
    ) == 66.67


def test_profit_factor():
    trades = [
        create_trade(100, 110),
        create_trade(100, 90),
    ]

    assert PerformanceMetrics.profit_factor(trades) == 1.0


def test_average_win():
    trades = [
        create_trade(100, 120),
        create_trade(100, 110),
    ]

    assert PerformanceMetrics.average_win(trades) == 150


def test_average_loss():
    trades = [
        create_trade(100, 90),
        create_trade(100, 80),
    ]

    assert PerformanceMetrics.average_loss(trades) == 150


def test_risk_reward_ratio():
    trades = [
        create_trade(100, 120),
        create_trade(100, 90),
    ]

    assert PerformanceMetrics.risk_reward_ratio(trades) == 2.0


def test_expectancy_positive():
    trades = [
        create_trade(100, 120),
        create_trade(100, 110),
        create_trade(100, 90),
    ]

    assert PerformanceMetrics.expectancy(trades) > 0


def test_max_drawdown():
    curve = [
        EquityPoint(
            datetime(2026, 1, 1),
            100000,
        ),
        EquityPoint(
            datetime(2026, 1, 2),
            120000,
        ),
        EquityPoint(
            datetime(2026, 1, 3),
            90000,
        ),
        EquityPoint(
            datetime(2026, 1, 4),
            130000,
        ),
    ]

    drawdown = PerformanceMetrics.max_drawdown(curve)

    assert round(drawdown, 2) == 25.0