from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import UUID, uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class IncomeType(str, Enum):
    DIVIDEND = "DIVIDEND"
    OPTION_PREMIUM = "OPTION_PREMIUM"
    INTEREST = "INTEREST"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class EquityPoint:
    value: float
    timestamp_utc: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("equity value cannot be negative")


@dataclass(frozen=True, slots=True)
class ClosedTrade:
    symbol: str
    pnl: float
    strategy: str = "UNSPECIFIED"
    broker: str = "UNSPECIFIED"
    opened_at_utc: str = ""
    closed_at_utc: str = field(default_factory=utc_now)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")


@dataclass(frozen=True, slots=True)
class IncomeEvent:
    amount: float
    income_type: IncomeType
    symbol: str = ""
    timestamp_utc: str = field(default_factory=utc_now)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("income amount cannot be negative")


@dataclass(frozen=True, slots=True)
class AIDecisionObservation:
    confidence: float
    correct: bool | None = None
    model: str = "UNSPECIFIED"
    strategy: str = "UNSPECIFIED"
    decision_id: UUID = field(default_factory=uuid4)
    timestamp_utc: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class PortfolioObservation:
    cash: float
    buying_power: float
    portfolio_value: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    positions: tuple[dict[str, Any], ...] = ()
    timestamp_utc: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.cash < 0 or self.buying_power < 0 or self.portfolio_value < 0:
            raise ValueError("portfolio balances cannot be negative")


@dataclass(frozen=True, slots=True)
class AnalyticsSnapshot:
    snapshot_id: UUID
    portfolio: dict[str, Any]
    trades: dict[str, Any]
    risk: dict[str, Any]
    income: dict[str, Any]
    ai: dict[str, Any]
    benchmark: dict[str, Any]
    attribution: dict[str, Any]
    created_at_utc: str = field(default_factory=utc_now)

    @classmethod
    def create(cls, **sections: dict[str, Any]) -> "AnalyticsSnapshot":
        return cls(snapshot_id=uuid4(), **sections)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["snapshot_id"] = str(self.snapshot_id)
        return data
