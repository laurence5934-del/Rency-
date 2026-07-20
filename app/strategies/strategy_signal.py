from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class StrategySignal:
    symbol: str
    action: SignalAction
    timestamp: datetime
    confidence: float = 0.0
    reason: str = ""
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None

    def __post_init__(self) -> None:
        normalized_symbol = self.symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("symbol must not be empty")

        if not isinstance(self.action, SignalAction):
            raise TypeError("action must be a SignalAction")

        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be a datetime")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        if self.stop_loss is not None and self.stop_loss <= 0:
            raise ValueError("stop_loss must be greater than zero")

        if self.take_profit is not None and self.take_profit <= 0:
            raise ValueError("take_profit must be greater than zero")

        if self.position_size is not None and self.position_size <= 0:
            raise ValueError("position_size must be greater than zero")

        object.__setattr__(self, "symbol", normalized_symbol)
        object.__setattr__(self, "reason", self.reason.strip())

    @property
    def is_buy(self) -> bool:
        return self.action is SignalAction.BUY

    @property
    def is_sell(self) -> bool:
        return self.action is SignalAction.SELL

    @property
    def is_hold(self) -> bool:
        return self.action is SignalAction.HOLD

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "action": self.action.value,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "reason": self.reason,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_size": self.position_size,
        }