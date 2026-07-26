from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Sequence


class BacktestStatus(str, Enum):
    CREATED = "created"
    VALIDATED = "validated"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Timeframe(str, Enum):
    MINUTE = "1m"
    HOUR = "1h"
    DAY = "1d"


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    strategy_id: str
    strategy_version: str
    dataset_id: str
    initial_capital: Decimal
    start_time: datetime
    end_time: datetime
    timeframe: Timeframe = Timeframe.DAY
    base_currency: str = "USD"
    random_seed: int = 0
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized = dict(self.parameters)
        object.__setattr__(self, "parameters", MappingProxyType(normalized))


@dataclass(frozen=True, slots=True)
class Trade:
    trade_id: str
    symbol: str
    quantity: Decimal
    price: Decimal
    side: str
    timestamp: datetime
    commission: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class Position:
    symbol: str
    quantity: Decimal
    average_price: Decimal
    market_price: Decimal

    @property
    def market_value(self) -> Decimal:
        return self.quantity * self.market_price

    @property
    def unrealized_pnl(self) -> Decimal:
        return self.quantity * (self.market_price - self.average_price)


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    timestamp: datetime
    cash: Decimal
    positions_value: Decimal
    equity: Decimal
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    drawdown: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class BacktestResult:
    backtest_id: str
    status: BacktestStatus
    config: BacktestConfig
    started_at: datetime
    completed_at: datetime | None = None
    trades: Sequence[Trade] = field(default_factory=tuple)
    snapshots: Sequence[PortfolioSnapshot] = field(default_factory=tuple)
    metrics: Mapping[str, Decimal | int | float | str] = field(default_factory=dict)
    warnings: Sequence[str] = field(default_factory=tuple)
    error: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "trades", tuple(self.trades))
        object.__setattr__(self, "snapshots", tuple(self.snapshots))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
