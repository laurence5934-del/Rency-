from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import UUID, uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class CashMovementType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    FEE = "FEE"
    TAX = "TAX"
    ADJUSTMENT = "ADJUSTMENT"


@dataclass(frozen=True, slots=True)
class TradeFill:
    symbol: str
    quantity: int
    price: float
    side: str
    commission: float = 0.0
    fill_id: UUID = field(default_factory=uuid4)
    timestamp_utc: str = field(default_factory=utc_now)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.price <= 0:
            raise ValueError("price must be positive")
        if self.commission < 0:
            raise ValueError("commission cannot be negative")
        if self.side.upper() not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")


@dataclass(slots=True)
class Position:
    symbol: str
    quantity: int = 0
    average_cost: float = 0.0
    market_price: float = 0.0
    realized_pnl: float = 0.0
    dividends_received: float = 0.0
    updated_at_utc: str = field(default_factory=utc_now)

    @property
    def side(self) -> PositionSide:
        return PositionSide.LONG if self.quantity >= 0 else PositionSide.SHORT

    @property
    def market_value(self) -> float:
        return self.quantity * self.market_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.average_cost

    @property
    def unrealized_pnl(self) -> float:
        return self.quantity * (self.market_price - self.average_cost)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.update(
            side=self.side.value,
            market_value=self.market_value,
            cost_basis=self.cost_basis,
            unrealized_pnl=self.unrealized_pnl,
        )
        return data


@dataclass(slots=True)
class AccountBalance:
    cash: float = 0.0
    reserved_cash: float = 0.0
    buying_power_multiplier: float = 1.0

    @property
    def available_cash(self) -> float:
        return self.cash - self.reserved_cash

    @property
    def buying_power(self) -> float:
        return max(0.0, self.available_cash * self.buying_power_multiplier)


@dataclass(frozen=True, slots=True)
class CashMovement:
    movement_type: CashMovementType
    amount: float
    description: str = ""
    movement_id: UUID = field(default_factory=uuid4)
    timestamp_utc: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("amount must be positive")


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    snapshot_id: UUID
    cash: float
    buying_power: float
    gross_market_value: float
    net_liquidation_value: float
    realized_pnl: float
    unrealized_pnl: float
    dividends_received: float
    positions: tuple[dict[str, Any], ...]
    created_at_utc: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        cash: float,
        buying_power: float,
        gross_market_value: float,
        net_liquidation_value: float,
        realized_pnl: float,
        unrealized_pnl: float,
        dividends_received: float,
        positions: tuple[dict[str, Any], ...],
    ) -> "PortfolioSnapshot":
        return cls(
            uuid4(),
            cash,
            buying_power,
            gross_market_value,
            net_liquidation_value,
            realized_pnl,
            unrealized_pnl,
            dividends_received,
            positions,
        )
