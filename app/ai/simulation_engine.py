from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from numbers import Real
from typing import Any, Mapping, Sequence


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"
    COVER = "COVER"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    starting_cash: float = 100_000.0
    commission_per_order: float = 0.0
    commission_per_share: float = 0.0
    slippage_bps: float = 2.0
    allow_fractional_shares: bool = False
    allow_short_selling: bool = False
    maximum_position_weight: float = 0.25
    maximum_gross_exposure: float = 1.0

    def __post_init__(self) -> None:
        numeric_fields = (
            "starting_cash",
            "commission_per_order",
            "commission_per_share",
            "slippage_bps",
            "maximum_position_weight",
            "maximum_gross_exposure",
        )
        for name in numeric_fields:
            value = getattr(self, name)
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{name} must be numeric")
            value = float(value)
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
            object.__setattr__(self, name, value)

        if self.starting_cash <= 0:
            raise ValueError("starting_cash must be positive")
        if self.commission_per_order < 0:
            raise ValueError("commission_per_order cannot be negative")
        if self.commission_per_share < 0:
            raise ValueError("commission_per_share cannot be negative")
        if self.slippage_bps < 0:
            raise ValueError("slippage_bps cannot be negative")
        if not 0 < self.maximum_position_weight <= 1:
            raise ValueError("maximum_position_weight must be in (0, 1]")
        if not 0 < self.maximum_gross_exposure <= 2:
            raise ValueError("maximum_gross_exposure must be in (0, 2]")


@dataclass(frozen=True, slots=True)
class SimulatedOrder:
    order_id: str
    timestamp_utc: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    limit_price: float | None
    stop_price: float | None
    status: OrderStatus
    filled_quantity: float
    average_fill_price: float | None
    commission: float
    realized_pnl: float
    rejection_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["side"] = self.side.value
        data["order_type"] = self.order_type.value
        data["status"] = self.status.value
        return data


@dataclass(frozen=True, slots=True)
class Position:
    symbol: str
    quantity: float
    average_price: float
    market_price: float
    market_value: float
    unrealized_pnl: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    timestamp_utc: str
    cash: float
    equity: float
    gross_exposure: float
    realized_pnl: float
    unrealized_pnl: float
    total_return_pct: float
    positions: dict[str, Position]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "cash": self.cash,
            "equity": self.equity,
            "gross_exposure": self.gross_exposure,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_return_pct": self.total_return_pct,
            "positions": {
                symbol: position.to_dict()
                for symbol, position in self.positions.items()
            },
        }


class SimulationEngine:
    """
    Version 9.8.0.8 - Simulation Mode.

    Provides:
    - paper trading
    - market, limit, stop, and stop-limit orders
    - configurable commission and slippage
    - long and optional short positions
    - portfolio cash, equity, exposure, and P/L tracking
    - risk-aware order rejection
    - order history and portfolio snapshots
    - session reset
    """

    def __init__(self, config: SimulationConfig | None = None) -> None:
        self.config = config or SimulationConfig()
        self._cash = self.config.starting_cash
        self._positions: dict[str, dict[str, float]] = {}
        self._market_prices: dict[str, float] = {}
        self._orders: list[SimulatedOrder] = []
        self._realized_pnl = 0.0
        self._snapshots: list[PortfolioSnapshot] = []

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _symbol(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("symbol must be a string")
        value = value.strip().upper()
        if not value:
            raise ValueError("symbol cannot be empty")
        return value

    @staticmethod
    def _positive(name: str, value: Real) -> float:
        if not isinstance(value, Real) or isinstance(value, bool):
            raise TypeError(f"{name} must be numeric")
        value = float(value)
        if not isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
        return value

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def realized_pnl(self) -> float:
        return self._realized_pnl

    @property
    def orders(self) -> tuple[SimulatedOrder, ...]:
        return tuple(self._orders)

    @property
    def snapshots(self) -> tuple[PortfolioSnapshot, ...]:
        return tuple(self._snapshots)

    def update_market_price(self, symbol: str, price: Real) -> None:
        self._market_prices[self._symbol(symbol)] = self._positive("price", price)

    def update_market_prices(self, prices: Mapping[str, Real]) -> None:
        for symbol, price in prices.items():
            self.update_market_price(symbol, price)

    def _equity(self) -> float:
        value = self._cash
        for symbol, position in self._positions.items():
            price = self._market_prices.get(symbol, position["average_price"])
            value += position["quantity"] * price
        return value

    def _gross_exposure(self) -> float:
        equity = self._equity()
        if equity <= 0:
            return 0.0
        gross = 0.0
        for symbol, position in self._positions.items():
            price = self._market_prices.get(symbol, position["average_price"])
            gross += abs(position["quantity"] * price)
        return gross / equity

    def _commission(self, quantity: float) -> float:
        return (
            self.config.commission_per_order
            + abs(quantity) * self.config.commission_per_share
        )

    def _slipped_price(self, price: float, side: OrderSide) -> float:
        slip = self.config.slippage_bps / 10_000.0
        if side in {OrderSide.BUY, OrderSide.COVER}:
            return price * (1.0 + slip)
        return price * (1.0 - slip)

    def _should_trigger(
        self,
        order_type: OrderType,
        side: OrderSide,
        market_price: float,
        limit_price: float | None,
        stop_price: float | None,
    ) -> bool:
        if order_type == OrderType.MARKET:
            return True
        if order_type == OrderType.LIMIT:
            if limit_price is None:
                raise ValueError("limit_price is required for limit orders")
            return (
                market_price <= limit_price
                if side in {OrderSide.BUY, OrderSide.COVER}
                else market_price >= limit_price
            )
        if order_type == OrderType.STOP:
            if stop_price is None:
                raise ValueError("stop_price is required for stop orders")
            return (
                market_price >= stop_price
                if side in {OrderSide.BUY, OrderSide.COVER}
                else market_price <= stop_price
            )
        if limit_price is None or stop_price is None:
            raise ValueError(
                "limit_price and stop_price are required for stop-limit orders"
            )
        stop_triggered = (
            market_price >= stop_price
            if side in {OrderSide.BUY, OrderSide.COVER}
            else market_price <= stop_price
        )
        limit_valid = (
            market_price <= limit_price
            if side in {OrderSide.BUY, OrderSide.COVER}
            else market_price >= limit_price
        )
        return stop_triggered and limit_valid

    def submit_order(
        self,
        *,
        symbol: str,
        side: OrderSide | str,
        quantity: Real,
        order_type: OrderType | str = OrderType.MARKET,
        limit_price: Real | None = None,
        stop_price: Real | None = None,
        fill_fraction: Real = 1.0,
    ) -> SimulatedOrder:
        symbol = self._symbol(symbol)
        side = OrderSide(side)
        order_type = OrderType(order_type)
        quantity = self._positive("quantity", quantity)
        fill_fraction = float(fill_fraction)

        if not 0.0 <= fill_fraction <= 1.0:
            raise ValueError("fill_fraction must be between 0 and 1")
        if not self.config.allow_fractional_shares:
            quantity = float(int(quantity))
            if quantity <= 0:
                raise ValueError("quantity rounds to zero")

        if symbol not in self._market_prices:
            return self._record_rejection(
                symbol, side, order_type, quantity,
                limit_price, stop_price, "Market price unavailable"
            )

        if side in {OrderSide.SHORT, OrderSide.COVER} and not self.config.allow_short_selling:
            return self._record_rejection(
                symbol, side, order_type, quantity,
                limit_price, stop_price, "Short selling is disabled"
            )

        market_price = self._market_prices[symbol]
        limit_value = None if limit_price is None else self._positive(
            "limit_price", limit_price
        )
        stop_value = None if stop_price is None else self._positive(
            "stop_price", stop_price
        )

        if not self._should_trigger(
            order_type, side, market_price, limit_value, stop_value
        ):
            order = SimulatedOrder(
                order_id=str(uuid.uuid4()),
                timestamp_utc=self._utc_now(),
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                limit_price=limit_value,
                stop_price=stop_value,
                status=OrderStatus.PENDING,
                filled_quantity=0.0,
                average_fill_price=None,
                commission=0.0,
                realized_pnl=0.0,
                rejection_reason=None,
            )
            self._orders.append(order)
            return order

        filled_quantity = quantity * fill_fraction
        if not self.config.allow_fractional_shares:
            filled_quantity = float(int(filled_quantity))

        if filled_quantity <= 0:
            return self._record_rejection(
                symbol, side, order_type, quantity,
                limit_value, stop_value, "Filled quantity is zero"
            )

        fill_price = self._slipped_price(market_price, side)
        commission = self._commission(filled_quantity)

        rejection_reason = self._validate_order_risk(
            symbol=symbol,
            side=side,
            quantity=filled_quantity,
            fill_price=fill_price,
            commission=commission,
        )
        if rejection_reason:
            return self._record_rejection(
                symbol, side, order_type, quantity,
                limit_value, stop_value, rejection_reason
            )

        realized_pnl = self._apply_fill(
            symbol=symbol,
            side=side,
            quantity=filled_quantity,
            fill_price=fill_price,
            commission=commission,
        )

        status = (
            OrderStatus.FILLED
            if filled_quantity >= quantity
            else OrderStatus.PARTIALLY_FILLED
        )
        order = SimulatedOrder(
            order_id=str(uuid.uuid4()),
            timestamp_utc=self._utc_now(),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_value,
            stop_price=stop_value,
            status=status,
            filled_quantity=filled_quantity,
            average_fill_price=round(fill_price, 8),
            commission=round(commission, 8),
            realized_pnl=round(realized_pnl, 8),
            rejection_reason=None,
        )
        self._orders.append(order)
        self.capture_snapshot()
        return order

    def _validate_order_risk(
        self,
        *,
        symbol: str,
        side: OrderSide,
        quantity: float,
        fill_price: float,
        commission: float,
    ) -> str | None:
        current_quantity = self._positions.get(symbol, {}).get("quantity", 0.0)
        signed_quantity = quantity if side in {OrderSide.BUY, OrderSide.COVER} else -quantity
        projected_quantity = current_quantity + signed_quantity

        if not self.config.allow_short_selling and projected_quantity < 0:
            return "Order would create a short position"

        projected_position_value = abs(projected_quantity * fill_price)
        current_equity = self._equity()
        if current_equity <= 0:
            return "Portfolio equity is non-positive"

        if projected_position_value / current_equity > self.config.maximum_position_weight:
            return "Maximum position weight would be exceeded"

        cash_change = -(signed_quantity * fill_price) - commission
        projected_cash = self._cash + cash_change
        if projected_cash < 0 and side in {OrderSide.BUY, OrderSide.COVER}:
            return "Insufficient cash"

        projected_gross = 0.0
        for position_symbol, position in self._positions.items():
            price = self._market_prices.get(
                position_symbol, position["average_price"]
            )
            qty = projected_quantity if position_symbol == symbol else position["quantity"]
            projected_gross += abs(qty * price)
        if symbol not in self._positions:
            projected_gross += projected_position_value

        if projected_gross / current_equity > self.config.maximum_gross_exposure:
            return "Maximum gross exposure would be exceeded"

        return None

    def _apply_fill(
        self,
        *,
        symbol: str,
        side: OrderSide,
        quantity: float,
        fill_price: float,
        commission: float,
    ) -> float:
        signed_quantity = quantity if side in {OrderSide.BUY, OrderSide.COVER} else -quantity
        current = self._positions.get(
            symbol, {"quantity": 0.0, "average_price": 0.0}
        )
        old_quantity = current["quantity"]
        old_average = current["average_price"]
        new_quantity = old_quantity + signed_quantity
        realized = -commission

        same_direction = (
            old_quantity == 0
            or (old_quantity > 0 and signed_quantity > 0)
            or (old_quantity < 0 and signed_quantity < 0)
        )

        if same_direction:
            total_cost = old_quantity * old_average + signed_quantity * fill_price
            new_average = total_cost / new_quantity if new_quantity != 0 else 0.0
        else:
            closing_quantity = min(abs(old_quantity), abs(signed_quantity))
            if old_quantity > 0:
                realized += closing_quantity * (fill_price - old_average)
            else:
                realized += closing_quantity * (old_average - fill_price)

            if new_quantity == 0:
                new_average = 0.0
            elif (old_quantity > 0) == (new_quantity > 0):
                new_average = old_average
            else:
                new_average = fill_price

        self._cash -= signed_quantity * fill_price
        self._cash -= commission
        self._realized_pnl += realized

        if abs(new_quantity) < 1e-12:
            self._positions.pop(symbol, None)
        else:
            self._positions[symbol] = {
                "quantity": new_quantity,
                "average_price": new_average,
            }

        return realized

    def _record_rejection(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        limit_price: Real | None,
        stop_price: Real | None,
        reason: str,
    ) -> SimulatedOrder:
        order = SimulatedOrder(
            order_id=str(uuid.uuid4()),
            timestamp_utc=self._utc_now(),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=None if limit_price is None else float(limit_price),
            stop_price=None if stop_price is None else float(stop_price),
            status=OrderStatus.REJECTED,
            filled_quantity=0.0,
            average_fill_price=None,
            commission=0.0,
            realized_pnl=0.0,
            rejection_reason=reason,
        )
        self._orders.append(order)
        return order

    def positions(self) -> dict[str, Position]:
        result: dict[str, Position] = {}
        for symbol, raw in self._positions.items():
            market_price = self._market_prices.get(symbol, raw["average_price"])
            quantity = raw["quantity"]
            market_value = quantity * market_price
            unrealized = quantity * (market_price - raw["average_price"])
            result[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                average_price=round(raw["average_price"], 8),
                market_price=round(market_price, 8),
                market_value=round(market_value, 8),
                unrealized_pnl=round(unrealized, 8),
            )
        return result

    def capture_snapshot(self) -> PortfolioSnapshot:
        positions = self.positions()
        unrealized = sum(p.unrealized_pnl for p in positions.values())
        equity = self._equity()
        snapshot = PortfolioSnapshot(
            timestamp_utc=self._utc_now(),
            cash=round(self._cash, 8),
            equity=round(equity, 8),
            gross_exposure=round(self._gross_exposure(), 12),
            realized_pnl=round(self._realized_pnl, 8),
            unrealized_pnl=round(unrealized, 8),
            total_return_pct=round(
                (equity / self.config.starting_cash) - 1.0,
                12,
            ),
            positions=positions,
        )
        self._snapshots.append(snapshot)
        return snapshot

    def cancel_order(self, order_id: str) -> SimulatedOrder:
        for index, order in enumerate(self._orders):
            if order.order_id == order_id:
                if order.status != OrderStatus.PENDING:
                    raise ValueError("only pending orders can be cancelled")
                cancelled = SimulatedOrder(
                    order_id=order.order_id,
                    timestamp_utc=order.timestamp_utc,
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    limit_price=order.limit_price,
                    stop_price=order.stop_price,
                    status=OrderStatus.CANCELLED,
                    filled_quantity=order.filled_quantity,
                    average_fill_price=order.average_fill_price,
                    commission=order.commission,
                    realized_pnl=order.realized_pnl,
                    rejection_reason=None,
                )
                self._orders[index] = cancelled
                return cancelled
        raise KeyError(f"order not found: {order_id}")

    def reset(self) -> None:
        self._cash = self.config.starting_cash
        self._positions.clear()
        self._market_prices.clear()
        self._orders.clear()
        self._realized_pnl = 0.0
        self._snapshots.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": asdict(self.config),
            "cash": self._cash,
            "realized_pnl": self._realized_pnl,
            "market_prices": dict(self._market_prices),
            "positions": {
                symbol: position.to_dict()
                for symbol, position in self.positions().items()
            },
            "orders": [order.to_dict() for order in self._orders],
            "snapshots": [snapshot.to_dict() for snapshot in self._snapshots],
        }
