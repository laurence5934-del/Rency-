from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class PositionState(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIALLY_CLOSED = "PARTIALLY_CLOSED"
    CLOSED = "CLOSED"
    ERROR = "ERROR"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def determine_position_side(quantity: float) -> PositionSide:
    if quantity > 0:
        return PositionSide.LONG

    if quantity < 0:
        return PositionSide.SHORT

    return PositionSide.FLAT


@dataclass(slots=True)
class ManagedPosition:
    account: str
    symbol: str
    security_type: str
    currency: str
    exchange: str
    quantity: float
    average_cost: float

    position_id: int | None = None
    current_price: float | None = None
    realized_pnl: float = 0.0
    stop_loss_price: float | None = None
    profit_target_price: float | None = None
    state: PositionState = PositionState.PENDING
    opened_quantity: float | None = None
    opened_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    closed_at: datetime | None = None

    def __post_init__(self) -> None:
        self.account = str(self.account).strip()
        self.symbol = str(self.symbol).strip().upper()
        self.security_type = str(self.security_type).strip().upper()
        self.currency = str(self.currency).strip().upper()
        self.exchange = str(self.exchange).strip().upper()

        self.quantity = float(self.quantity)
        self.average_cost = float(self.average_cost)
        self.realized_pnl = float(self.realized_pnl)

        if self.current_price is not None:
            self.current_price = float(self.current_price)

        if self.stop_loss_price is not None:
            self.stop_loss_price = float(self.stop_loss_price)

        if self.profit_target_price is not None:
            self.profit_target_price = float(
                self.profit_target_price
            )

        if self.opened_quantity is None:
            self.opened_quantity = abs(self.quantity)
        else:
            self.opened_quantity = abs(
                float(self.opened_quantity)
            )

        if not self.account:
            raise ValueError("Position account is required.")

        if not self.symbol:
            raise ValueError("Position symbol is required.")

        if self.average_cost < 0:
            raise ValueError(
                "Average cost cannot be negative."
            )

        if self.opened_quantity < abs(self.quantity):
            raise ValueError(
                "Opened quantity cannot be smaller than "
                "the current absolute quantity."
            )

    @property
    def side(self) -> PositionSide:
        return determine_position_side(self.quantity)

    @property
    def absolute_quantity(self) -> float:
        return abs(self.quantity)

    @property
    def is_open(self) -> bool:
        return (
            self.state
            in {
                PositionState.OPEN,
                PositionState.PARTIALLY_CLOSED,
            }
            and self.quantity != 0
        )

    @property
    def is_terminal(self) -> bool:
        return self.state in {
            PositionState.CLOSED,
            PositionState.ERROR,
        }

    @property
    def market_value(self) -> float | None:
        if self.current_price is None:
            return None

        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.average_cost

    @property
    def unrealized_pnl(self) -> float | None:
        if self.current_price is None:
            return None

        return (
            self.current_price - self.average_cost
        ) * self.quantity

    @property
    def unrealized_pnl_percent(self) -> float | None:
        if (
            self.current_price is None
            or self.average_cost == 0
        ):
            return None

        if self.side == PositionSide.LONG:
            return (
                (
                    self.current_price
                    - self.average_cost
                )
                / self.average_cost
            ) * 100.0

        if self.side == PositionSide.SHORT:
            return (
                (
                    self.average_cost
                    - self.current_price
                )
                / self.average_cost
            ) * 100.0

        return 0.0

    @property
    def closed_quantity(self) -> float:
        return max(
            0.0,
            float(self.opened_quantity)
            - self.absolute_quantity,
        )

    def update_market_price(
        self,
        current_price: float,
    ) -> None:
        price = float(current_price)

        if price < 0:
            raise ValueError(
                "Current price cannot be negative."
            )

        self.current_price = price
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_id": self.position_id,
            "account": self.account,
            "symbol": self.symbol,
            "security_type": self.security_type,
            "currency": self.currency,
            "exchange": self.exchange,
            "quantity": self.quantity,
            "absolute_quantity": self.absolute_quantity,
            "opened_quantity": self.opened_quantity,
            "closed_quantity": self.closed_quantity,
            "average_cost": self.average_cost,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "cost_basis": self.cost_basis,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_percent": (
                self.unrealized_pnl_percent
            ),
            "realized_pnl": self.realized_pnl,
            "stop_loss_price": self.stop_loss_price,
            "profit_target_price": (
                self.profit_target_price
            ),
            "side": self.side.value,
            "state": self.state.value,
            "is_open": self.is_open,
            "is_terminal": self.is_terminal,
            "opened_at": self.opened_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "closed_at": (
                self.closed_at.isoformat()
                if self.closed_at is not None
                else None
            ),
        }

    @classmethod
    def from_ibkr(
        cls,
        payload: dict[str, Any],
    ) -> ManagedPosition:
        quantity = float(
            payload.get("position", 0.0)
        )

        state = (
            PositionState.OPEN
            if quantity != 0
            else PositionState.CLOSED
        )

        return cls(
            account=str(payload.get("account", "")),
            symbol=str(payload.get("symbol", "")),
            security_type=str(
                payload.get("secType", "STK")
            ),
            currency=str(
                payload.get("currency", "USD")
            ),
            exchange=str(
                payload.get("exchange", "")
            ),
            quantity=quantity,
            average_cost=float(
                payload.get("avgCost", 0.0)
            ),
            state=state,
        )
