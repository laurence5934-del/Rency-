from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from app.backtesting.portfolio_models import Portfolio
from app.backtesting.trade_models import (
    Trade,
    TradeSide,
    TradeStatus,
)


class TradeSimulator:
    """
    Simulates opening and closing trades against a portfolio.

    Version 9.6.0 supports one cash account and validated
    long or short trade records.
    """

    def __init__(
        self,
        portfolio: Portfolio,
        commission_per_trade: float = 0.0,
        allow_short: bool = False,
    ) -> None:
        if not isinstance(portfolio, Portfolio):
            raise TypeError("portfolio must be a Portfolio.")

        if commission_per_trade < 0:
            raise ValueError(
                "commission_per_trade cannot be negative."
            )

        self.portfolio = portfolio
        self.commission_per_trade = commission_per_trade
        self.allow_short = allow_short

    def open_trade(
        self,
        *,
        symbol: str,
        side: TradeSide,
        quantity: float,
        price: float,
        timestamp: datetime,
    ) -> Trade:
        """
        Opens a simulated trade and records it in the portfolio.
        """

        if not isinstance(side, TradeSide):
            raise TypeError("side must be a TradeSide.")

        if side is TradeSide.SELL and not self.allow_short:
            raise ValueError(
                "short trades are disabled."
            )

        if quantity <= 0:
            raise ValueError(
                "quantity must be greater than zero."
            )

        if price <= 0:
            raise ValueError(
                "price must be greater than zero."
            )

        if not isinstance(timestamp, datetime):
            raise TypeError(
                "timestamp must be a datetime."
            )

        entry_value = quantity * price
        entry_commission = self.commission_per_trade

        if side is TradeSide.BUY:
            required_cash = entry_value + entry_commission

            if required_cash > self.portfolio.cash:
                raise ValueError(
                    "insufficient cash to open trade."
                )

            self.portfolio.cash -= required_cash

        else:
            if entry_commission > self.portfolio.cash:
                raise ValueError(
                    "insufficient cash to pay commission."
                )

            self.portfolio.cash += entry_value
            self.portfolio.cash -= entry_commission

        trade = Trade(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=price,
            entry_time=timestamp,
            commission=entry_commission,
            status=TradeStatus.OPEN,
        )

        self.portfolio.add_trade(trade)

        return trade

    def close_trade(
        self,
        trade: Trade,
        *,
        price: float,
        timestamp: datetime,
    ) -> Trade:
        """
        Closes an existing open trade and replaces it
        in the portfolio with a completed trade record.
        """

        if not isinstance(trade, Trade):
            raise TypeError("trade must be a Trade.")

        if not trade.is_open:
            raise ValueError(
                "trade is already closed."
            )

        if trade not in self.portfolio.trades:
            raise ValueError(
                "trade does not belong to this portfolio."
            )

        if price <= 0:
            raise ValueError(
                "price must be greater than zero."
            )

        if not isinstance(timestamp, datetime):
            raise TypeError(
                "timestamp must be a datetime."
            )

        if timestamp < trade.entry_time:
            raise ValueError(
                "timestamp cannot be earlier than entry_time."
            )

        exit_value = trade.quantity * price
        exit_commission = self.commission_per_trade

        if trade.side is TradeSide.BUY:
            self.portfolio.cash += exit_value
            self.portfolio.cash -= exit_commission

        else:
            required_cash = exit_value + exit_commission

            if required_cash > self.portfolio.cash:
                raise ValueError(
                    "insufficient cash to close short trade."
                )

            self.portfolio.cash -= required_cash

        closed_trade = replace(
            trade,
            exit_price=price,
            exit_time=timestamp,
            commission=trade.commission + exit_commission,
            status=TradeStatus.CLOSED,
        )

        trade_index = self.portfolio.trades.index(trade)
        self.portfolio.trades[trade_index] = closed_trade

        return closed_trade

    def market_value(
        self,
        prices: dict[str, float],
    ) -> float:
        """
        Calculates the net market value of all open positions.
        """

        total = 0.0

        for trade in self.portfolio.open_trades:
            if trade.symbol not in prices:
                raise KeyError(
                    f"missing market price for {trade.symbol}."
                )

            price = prices[trade.symbol]

            if price <= 0:
                raise ValueError(
                    f"market price for {trade.symbol} "
                    "must be greater than zero."
                )

            position_value = trade.quantity * price

            if trade.side is TradeSide.BUY:
                total += position_value
            else:
                total -= position_value

        return total

    def unrealized_profit(
        self,
        prices: dict[str, float],
    ) -> float:
        """
        Calculates unrealized profit for all open trades.
        """

        total = 0.0

        for trade in self.portfolio.open_trades:
            if trade.symbol not in prices:
                raise KeyError(
                    f"missing market price for {trade.symbol}."
                )

            current_price = prices[trade.symbol]

            if current_price <= 0:
                raise ValueError(
                    f"market price for {trade.symbol} "
                    "must be greater than zero."
                )

            price_change = current_price - trade.entry_price

            if trade.side is TradeSide.BUY:
                total += price_change * trade.quantity
            else:
                total -= price_change * trade.quantity

        return total

    def portfolio_equity(
        self,
        prices: dict[str, float],
    ) -> float:
        """
        Returns cash plus the net market value
        of all open positions.
        """

        return self.portfolio.cash + self.market_value(prices)