from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import UUID, uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BrokerEnvironment(str, Enum):
    SIMULATED = "SIMULATED"
    PAPER = "PAPER"
    LIVE = "LIVE"


class BrokerStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class BrokerOrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class BrokerOrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"


class BrokerTimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class BrokerOrderStatus(str, Enum):
    CREATED = "CREATED"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class BrokerCapabilities:
    market_orders: bool = True
    limit_orders: bool = True
    stop_orders: bool = True
    stop_limit_orders: bool = True
    trailing_stop_orders: bool = True
    fractional_shares: bool = False
    short_sales: bool = False
    extended_hours: bool = False


@dataclass(frozen=True, slots=True)
class BrokerOrderRequest:
    symbol: str
    side: BrokerOrderSide
    quantity: float
    order_type: BrokerOrderType = BrokerOrderType.MARKET
    time_in_force: BrokerTimeInForce = BrokerTimeInForce.DAY
    limit_price: float | None = None
    stop_price: float | None = None
    trailing_percent: float | None = None
    client_order_id: str | None = None
    correlation_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")


@dataclass(frozen=True, slots=True)
class BrokerFill:
    fill_id: UUID
    quantity: float
    price: float
    timestamp_utc: str = field(default_factory=utc_now)

    @classmethod
    def create(cls, quantity: float, price: float) -> "BrokerFill":
        if quantity <= 0 or price <= 0:
            raise ValueError("fill quantity and price must be positive")
        return cls(uuid4(), quantity, price)


@dataclass(frozen=True, slots=True)
class BrokerOrderResult:
    broker_name: str
    broker_order_id: str
    status: BrokerOrderStatus
    requested_quantity: float
    filled_quantity: float
    average_fill_price: float
    fills: tuple[BrokerFill, ...]
    message: str = ""
    created_at_utc: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["fills"] = [
            {
                **asdict(fill),
                "fill_id": str(fill.fill_id),
            }
            for fill in self.fills
        ]
        return data


@dataclass(frozen=True, slots=True)
class BrokerHealthSnapshot:
    broker_name: str
    status: BrokerStatus
    environment: BrokerEnvironment
    latency_ms: float
    message: str = ""
    checked_at_utc: str = field(default_factory=utc_now)
