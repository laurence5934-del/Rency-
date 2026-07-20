from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TradeSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class Trade:
    """
    Represents one completed or open simulated trade.
    """

    symbol: str
    side: TradeSide
    quantity: float
    entry_price: float
    entry_time: datetime

    exit_price: float | None = None
    exit_time: datetime | None = None

    commission: float = 0.0
    status: TradeStatus = TradeStatus.OPEN

    def __post_init__(self) -> None:
        normalized_symbol = self.symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("symbol cannot be empty.")

        object.__setattr__(self, "symbol", normalized_symbol)

        if not isinstance(self.side, TradeSide):
            raise TypeError("side must be a TradeSide.")

        if not isinstance(self.status, TradeStatus):
            raise TypeError("status must be a TradeStatus.")

        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero.")

        if self.entry_price <= 0:
            raise ValueError("entry_price must be greater than zero.")

        if self.commission < 0:
            raise ValueError("commission cannot be negative.")

        if not isinstance(self.entry_time, datetime):
            raise TypeError("entry_time must be a datetime.")

        if self.exit_price is not None and self.exit_price <= 0:
            raise ValueError("exit_price must be greater than zero.")

        if self.exit_time is not None and not isinstance(
            self.exit_time,
            datetime,
        ):
            raise TypeError("exit_time must be a datetime.")

        if (
            self.exit_time is not None
            and self.exit_time < self.entry_time
        ):
            raise ValueError(
                "exit_time cannot be earlier than entry_time."
            )

        if self.status is TradeStatus.CLOSED:
            if self.exit_price is None or self.exit_time is None:
                raise ValueError(
                    "closed trades require exit_price and exit_time."
                )

        if self.status is TradeStatus.OPEN:
            if self.exit_price is not None or self.exit_time is not None:
                raise ValueError(
                    "open trades cannot have exit details."
                )

    @property
    def is_open(self) -> bool:
        return self.status is TradeStatus.OPEN

    @property
    def is_closed(self) -> bool:
        return self.status is TradeStatus.CLOSED

    @property
    def entry_value(self) -> float:
        return self.quantity * self.entry_price

    @property
    def exit_value(self) -> float | None:
        if self.exit_price is None:
            return None

        return self.quantity * self.exit_price

    @property
    def gross_profit(self) -> float | None:
        if not self.is_closed or self.exit_price is None:
            return None

        price_change = self.exit_price - self.entry_price

        if self.side is TradeSide.BUY:
            return price_change * self.quantity

        return -price_change * self.quantity

    @property
    def net_profit(self) -> float | None:
        gross_profit = self.gross_profit

        if gross_profit is None:
            return None

        return gross_profit - self.commission

    @property
    def return_percent(self) -> float | None:
        net_profit = self.net_profit

        if net_profit is None:
            return None

        return (net_profit / self.entry_value) * 100.0

    @property
    def holding_period_seconds(self) -> float | None:
        if self.exit_time is None:
            return None

        return (
            self.exit_time - self.entry_time
        ).total_seconds()