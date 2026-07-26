from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.strategy.backtesting import (
    DuplicateTradeError,
    InsufficientBuyingPowerError,
    InsufficientPositionError,
    PortfolioEngine,
    Trade,
)


NOW = datetime(2026, 7, 25, tzinfo=timezone.utc)


def trade(
    *,
    trade_id: str,
    side: str,
    quantity: str,
    price: str,
    commission: str = "0",
    symbol: str = "AAPL",
) -> Trade:
    return Trade(
        trade_id=trade_id,
        symbol=symbol,
        quantity=Decimal(quantity),
        price=Decimal(price),
        side=side,
        timestamp=NOW,
        commission=Decimal(commission),
    )


def test_buy_reduces_cash_and_creates_position() -> None:
    portfolio = PortfolioEngine(Decimal("10000"))

    portfolio.apply_trade(
        trade(
            trade_id="BUY-1",
            side="buy",
            quantity="10",
            price="100",
            commission="1",
        )
    )

    position = portfolio.position_for("AAPL")

    assert position is not None
    assert position.quantity == Decimal("10")
    assert position.average_price == Decimal("100")
    assert portfolio.cash == Decimal("8999")
    assert portfolio.positions_value == Decimal("1000")
    assert portfolio.equity == Decimal("9999")


def test_multiple_buys_use_weighted_average_cost() -> None:
    portfolio = PortfolioEngine(Decimal("10000"))

    portfolio.apply_trade(
        trade(
            trade_id="BUY-1",
            side="buy",
            quantity="10",
            price="100",
        )
    )
    portfolio.apply_trade(
        trade(
            trade_id="BUY-2",
            side="buy",
            quantity="10",
            price="120",
        )
    )

    position = portfolio.position_for("AAPL")

    assert position is not None
    assert position.quantity == Decimal("20")
    assert position.average_price == Decimal("110")
    assert portfolio.cash == Decimal("7800")


def test_partial_sell_updates_cash_and_realized_pnl() -> None:
    portfolio = PortfolioEngine(Decimal("10000"))

    portfolio.apply_trade(
        trade(
            trade_id="BUY-1",
            side="buy",
            quantity="10",
            price="100",
        )
    )
    portfolio.apply_trade(
        trade(
            trade_id="SELL-1",
            side="sell",
            quantity="4",
            price="125",
            commission="2",
        )
    )

    position = portfolio.position_for("AAPL")

    assert position is not None
    assert position.quantity == Decimal("6")
    assert position.average_price == Decimal("100")
    assert portfolio.cash == Decimal("9498")
    assert portfolio.realized_pnl == Decimal("98")


def test_full_sell_removes_position() -> None:
    portfolio = PortfolioEngine(Decimal("10000"))

    portfolio.apply_trade(
        trade(
            trade_id="BUY-1",
            side="buy",
            quantity="5",
            price="100",
        )
    )
    portfolio.apply_trade(
        trade(
            trade_id="SELL-1",
            side="sell",
            quantity="5",
            price="110",
        )
    )

    assert portfolio.position_for("AAPL") is None
    assert portfolio.positions == {}
    assert portfolio.cash == Decimal("10050")
    assert portfolio.realized_pnl == Decimal("50")


def test_mark_to_market_updates_unrealized_pnl_and_equity() -> None:
    portfolio = PortfolioEngine(Decimal("10000"))

    portfolio.apply_trade(
        trade(
            trade_id="BUY-1",
            side="buy",
            quantity="10",
            price="100",
        )
    )

    portfolio.mark_to_market("AAPL", Decimal("115"))

    assert portfolio.positions_value == Decimal("1150")
    assert portfolio.unrealized_pnl == Decimal("150")
    assert portfolio.equity == Decimal("10150")


def test_snapshot_contains_equity_pnl_and_drawdown() -> None:
    portfolio = PortfolioEngine(Decimal("10000"))

    portfolio.apply_trade(
        trade(
            trade_id="BUY-1",
            side="buy",
            quantity="10",
            price="100",
        )
    )

    portfolio.mark_to_market("AAPL", Decimal("110"))
    peak_snapshot = portfolio.create_snapshot(NOW)

    assert peak_snapshot.equity == Decimal("10100")
    assert peak_snapshot.drawdown == Decimal("0")

    portfolio.mark_to_market("AAPL", Decimal("90"))
    loss_snapshot = portfolio.create_snapshot(NOW)

    assert loss_snapshot.equity == Decimal("9900")
    assert loss_snapshot.unrealized_pnl == Decimal("-100")
    assert loss_snapshot.drawdown == Decimal("200") / Decimal("10100")
    assert portfolio.maximum_drawdown == (
        Decimal("200") / Decimal("10100")
    )


def test_insufficient_buying_power_is_rejected_without_mutation() -> None:
    portfolio = PortfolioEngine(Decimal("1000"))

    with pytest.raises(InsufficientBuyingPowerError):
        portfolio.apply_trade(
            trade(
                trade_id="BUY-TOO-LARGE",
                side="buy",
                quantity="11",
                price="100",
            )
        )

    assert portfolio.cash == Decimal("1000")
    assert portfolio.positions == {}


def test_oversell_is_rejected_without_mutation() -> None:
    portfolio = PortfolioEngine(Decimal("10000"))

    portfolio.apply_trade(
        trade(
            trade_id="BUY-1",
            side="buy",
            quantity="5",
            price="100",
        )
    )

    with pytest.raises(InsufficientPositionError):
        portfolio.apply_trade(
            trade(
                trade_id="SELL-TOO-LARGE",
                side="sell",
                quantity="6",
                price="110",
            )
        )

    position = portfolio.position_for("AAPL")

    assert position is not None
    assert position.quantity == Decimal("5")
    assert portfolio.cash == Decimal("9500")


def test_duplicate_trade_is_rejected() -> None:
    portfolio = PortfolioEngine(Decimal("10000"))

    completed_trade = trade(
        trade_id="BUY-1",
        side="buy",
        quantity="5",
        price="100",
    )

    portfolio.apply_trade(completed_trade)

    with pytest.raises(DuplicateTradeError):
        portfolio.apply_trade(completed_trade)

    position = portfolio.position_for("AAPL")

    assert position is not None
    assert position.quantity == Decimal("5")
    assert portfolio.cash == Decimal("9500")