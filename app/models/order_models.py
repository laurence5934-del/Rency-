"""
Order Management System Models
AI Trading Platform Version 7.7

Defines normalized OMS order states and persistent order records.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class OrderState(StrEnum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    SUBMITTING = "SUBMITTING"
    PRESUBMITTED = "PRESUBMITTED"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"


TERMINAL_ORDER_STATES = {
    OrderState.FILLED,
    OrderState.CANCELLED,
    OrderState.REJECTED,
    OrderState.INACTIVE,
    OrderState.ERROR,
}


ACTIVE_ORDER_STATES = {
    OrderState.CREATED,
    OrderState.VALIDATED,
    OrderState.APPROVED,
    OrderState.SUBMITTING,
    OrderState.PRESUBMITTED,
    OrderState.SUBMITTED,
    OrderState.PARTIALLY_FILLED,
    OrderState.CANCEL_PENDING,
}


@dataclass(frozen=True)
class ManagedOrder:
    local_order_id: int | None
    broker_order_id: int | None
    candidate_id: int | None
    symbol: str
    action: str
    quantity: float
    order_type: str
    limit_price: float | None
    state: OrderState
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    average_fill_price: float = 0.0
    last_fill_price: float = 0.0
    strategy: str | None = None
    paper_only: bool = True
    created_at: str | None = None
    updated_at: str | None = None

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_ORDER_STATES

    @property
    def is_active(self) -> bool:
        return self.state in ACTIVE_ORDER_STATES

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        data["is_terminal"] = self.is_terminal
        data["is_active"] = self.is_active
        return data


@dataclass(frozen=True)
class OrderEvent:
    event_id: int | None
    local_order_id: int
    previous_state: OrderState | None
    new_state: OrderState
    source: str
    message: str | None = None
    broker_payload: dict[str, Any] | None = None
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "local_order_id": self.local_order_id,
            "previous_state": (
                self.previous_state.value
                if self.previous_state
                else None
            ),
            "new_state": self.new_state.value,
            "source": self.source,
            "message": self.message,
            "broker_payload": self.broker_payload,
            "created_at": self.created_at,
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()