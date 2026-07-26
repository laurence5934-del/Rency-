from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock

from .models import Position, TradeFill


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PositionManager:
    def __init__(self) -> None:
        self._positions: dict[str, Position] = {}
        self._lock = RLock()

    def apply_fill(self, fill: TradeFill) -> Position:
        symbol = fill.symbol.upper().strip()
        with self._lock:
            position = self._positions.setdefault(symbol, Position(symbol=symbol))
            signed_quantity = fill.quantity if fill.side.upper() == "BUY" else -fill.quantity
            old_quantity = position.quantity
            new_quantity = old_quantity + signed_quantity

            if old_quantity == 0 or (old_quantity > 0 and signed_quantity > 0) or (old_quantity < 0 and signed_quantity < 0):
                total_cost = abs(old_quantity) * position.average_cost + fill.quantity * fill.price
                position.average_cost = total_cost / abs(new_quantity)
            else:
                closing_quantity = min(abs(old_quantity), fill.quantity)
                direction = 1.0 if old_quantity > 0 else -1.0
                position.realized_pnl += closing_quantity * (fill.price - position.average_cost) * direction
                if new_quantity == 0:
                    position.average_cost = 0.0
                elif old_quantity * new_quantity < 0:
                    position.average_cost = fill.price

            position.quantity = new_quantity
            position.market_price = fill.price
            position.updated_at_utc = utc_now()
            return position

    def mark_price(self, symbol: str, price: float) -> Position:
        if price <= 0:
            raise ValueError("price must be positive")
        key = symbol.upper().strip()
        with self._lock:
            position = self._positions.setdefault(key, Position(symbol=key))
            position.market_price = price
            position.updated_at_utc = utc_now()
            return position

    def add_dividend(self, symbol: str, amount: float) -> Position:
        if amount <= 0:
            raise ValueError("amount must be positive")
        key = symbol.upper().strip()
        with self._lock:
            position = self._positions.setdefault(key, Position(symbol=key))
            position.dividends_received += amount
            position.updated_at_utc = utc_now()
            return position

    def get(self, symbol: str) -> Position | None:
        with self._lock:
            return self._positions.get(symbol.upper().strip())

    def all(self) -> tuple[Position, ...]:
        with self._lock:
            return tuple(self._positions.values())
