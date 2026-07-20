from datetime import datetime, timedelta

import pytest

from app.backtesting.portfolio_models import Portfolio
from app.backtesting.trade_models import (
    Trade,
    TradeSide,
    TradeStatus,
)
from app.backtesting.trade_simulator import TradeSimulator


def test_create_valid_buy_trade():
    trade = Trade(
        symbol="aapl",
        side=TradeSide.BUY,
        quantity=10,
        entry_price=100,
        entry_time=datetime.now(),
    )

    assert trade.symbol == "AAPL"
    assert trade.is_open
    assert trade.entry_value == 1000


def test_create_valid_sell_trade():
    trade = Trade(
        symbol="MSFT",
        side=TradeSide.SELL,
        quantity=5,
        entry_price=200,
        entry_time=datetime.now(),
    )

    assert trade.side is TradeSide.SELL


def test_invalid_quantity():
    with pytest.raises(ValueError):
        Trade(
            symbol="AAPL",
            side=TradeSide.BUY,
            quantity=0,
            entry_price=100,
            entry_time=datetime.now(),
        )


def test_invalid_entry_price():
    with pytest.raises(ValueError):
        Trade(
            symbol="AAPL",
            side=TradeSide.BUY,
            quantity=1,
            entry_price=0,
            entry_time=datetime.now(),
        )


def test_portfolio_creation():
    portfolio = Portfolio(10000)

    assert portfolio.cash == 10000
    assert portfolio.trade_count == 0


def test_add_trade():
    portfolio = Portfolio(10000)

    trade = Trade(
        symbol="AAPL",
        side=TradeSide.BUY,
        quantity=10,
        entry_price=100,
        entry_time=datetime.now(),
    )

    portfolio.add_trade(trade)

    assert portfolio.trade_count == 1
    assert len(portfolio.open_trades) == 1


def test_open_long_trade():
    portfolio = Portfolio(10000)

    simulator = TradeSimulator(portfolio)

    trade = simulator.open_trade(
        symbol="AAPL",
        side=TradeSide.BUY,
        quantity=10,
        price=100,
        timestamp=datetime.now(),
    )

    assert trade.is_open
    assert portfolio.trade_count == 1
    assert portfolio.cash == 9000


def test_close_long_trade():
    portfolio = Portfolio(10000)

    simulator = TradeSimulator(portfolio)

    trade = simulator.open_trade(
        symbol="AAPL",
        side=TradeSide.BUY,
        quantity=10,
        price=100,
        timestamp=datetime.now(),
    )

    closed = simulator.close_trade(
        trade,
        price=110,
        timestamp=datetime.now() + timedelta(days=1),
    )

    assert closed.status is TradeStatus.CLOSED
    assert closed.net_profit == 100
    assert portfolio.cash == 10100


def test_insufficient_cash():
    portfolio = Portfolio(500)

    simulator = TradeSimulator(portfolio)

    with pytest.raises(ValueError):
        simulator.open_trade(
            symbol="AAPL",
            side=TradeSide.BUY,
            quantity=10,
            price=100,
            timestamp=datetime.now(),
        )


def test_short_trade_disabled():
    portfolio = Portfolio(10000)

    simulator = TradeSimulator(portfolio)

    with pytest.raises(ValueError):
        simulator.open_trade(
            symbol="AAPL",
            side=TradeSide.SELL,
            quantity=10,
            price=100,
            timestamp=datetime.now(),
        )


def test_short_trade_enabled():
    portfolio = Portfolio(10000)

    simulator = TradeSimulator(
        portfolio,
        allow_short=True,
    )

    trade = simulator.open_trade(
        symbol="AAPL",
        side=TradeSide.SELL,
        quantity=10,
        price=100,
        timestamp=datetime.now(),
    )

    assert trade.side is TradeSide.SELL
    assert portfolio.cash == 11000


def test_market_value():
    portfolio = Portfolio(10000)

    simulator = TradeSimulator(portfolio)

    simulator.open_trade(
        symbol="AAPL",
        side=TradeSide.BUY,
        quantity=10,
        price=100,
        timestamp=datetime.now(),
    )

    value = simulator.market_value(
        {"AAPL": 120}
    )

    assert value == 1200


def test_unrealized_profit():
    portfolio = Portfolio(10000)

    simulator = TradeSimulator(portfolio)

    simulator.open_trade(
        symbol="AAPL",
        side=TradeSide.BUY,
        quantity=10,
        price=100,
        timestamp=datetime.now(),
    )

    profit = simulator.unrealized_profit(
        {"AAPL": 120}
    )

    assert profit == 200


def test_portfolio_equity():
    portfolio = Portfolio(10000)

    simulator = TradeSimulator(portfolio)

    simulator.open_trade(
        symbol="AAPL",
        side=TradeSide.BUY,
        quantity=10,
        price=100,
        timestamp=datetime.now(),
    )

    equity = simulator.portfolio_equity(
        {"AAPL": 120}
    )

    assert equity == 10200