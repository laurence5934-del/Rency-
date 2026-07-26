from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from threading import RLock
from typing import Mapping

from .audit_log import BacktestAuditLog
from .commission_model import CommissionModel, NoCommission
from .models import Trade
from .slippage_model import NoSlippage, OrderSide, SlippageModel


ZERO = Decimal("0")


class ExecutionError(ValueError):
    """Raised when a simulated order cannot be executed safely."""


class OrderType(str, Enum):
    MARKET = "market"


@dataclass(frozen=True, slots=True)
class SimulatedOrder:
    order_id: str
    symbol: str
    quantity: Decimal
    side: OrderSide
    submitted_at: datetime
    order_type: OrderType = OrderType.MARKET
    metadata: Mapping[str, str] | None = None


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    execution_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    reference_price: Decimal
    fill_price: Decimal
    commission: Decimal
    slippage_per_unit: Decimal
    slippage_cost: Decimal
    gross_notional: Decimal
    net_cash_effect: Decimal
    executed_at: datetime
    execution_quality: Decimal

    def to_trade(self) -> Trade:
        return Trade(
            trade_id=self.execution_id,
            symbol=self.symbol,
            quantity=self.quantity,
            price=self.fill_price,
            side=self.side.value,
            timestamp=self.executed_at,
            commission=self.commission,
            slippage=self.slippage_cost,
        )


class ExecutionSimulator:
    """Deterministic, broker-free market-order execution simulator."""

    def __init__(
        self,
        *,
        commission_model: CommissionModel | None = None,
        slippage_model: SlippageModel | None = None,
        audit_log: BacktestAuditLog | None = None,
        backtest_id: str = "UNASSIGNED",
    ) -> None:
        self.commission_model = commission_model or NoCommission()
        self.slippage_model = slippage_model or NoSlippage()
        self.audit_log = audit_log
        self.backtest_id = backtest_id
        self._reports: list[ExecutionReport] = []
        self._executed_order_ids: set[str] = set()
        self._lock = RLock()

    def execute(
        self,
        order: SimulatedOrder,
        *,
        market_price: Decimal,
        executed_at: datetime,
    ) -> ExecutionReport:
        self._validate(order=order, market_price=market_price, executed_at=executed_at)
        with self._lock:
            if order.order_id in self._executed_order_ids:
                raise ExecutionError(f"order_id already executed: {order.order_id}")

            fill_price = self.slippage_model.apply(reference_price=market_price, side=order.side)
            commission = self.commission_model.calculate(quantity=order.quantity, price=fill_price)
            slippage_per_unit = abs(fill_price - market_price)
            slippage_cost = slippage_per_unit * order.quantity
            gross_notional = fill_price * order.quantity
            net_cash_effect = (
                -(gross_notional + commission)
                if order.side is OrderSide.BUY
                else gross_notional - commission
            )
            total_execution_cost = commission + slippage_cost
            reference_notional = market_price * order.quantity
            execution_quality = _execution_quality(
                total_execution_cost=total_execution_cost,
                reference_notional=reference_notional,
            )
            execution_id = _execution_id(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                fill_price=fill_price,
                executed_at=executed_at,
            )
            report = ExecutionReport(
                execution_id=execution_id,
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                reference_price=market_price,
                fill_price=fill_price,
                commission=commission,
                slippage_per_unit=slippage_per_unit,
                slippage_cost=slippage_cost,
                gross_notional=gross_notional,
                net_cash_effect=net_cash_effect,
                executed_at=executed_at,
                execution_quality=execution_quality,
            )
            self._reports.append(report)
            self._executed_order_ids.add(order.order_id)

        if self.audit_log is not None:
            self.audit_log.record(
                self.backtest_id,
                "ORDER_EXECUTED",
                order_id=order.order_id,
                execution_id=report.execution_id,
                symbol=order.symbol,
                side=order.side.value,
                quantity=str(order.quantity),
                reference_price=str(market_price),
                fill_price=str(fill_price),
                commission=str(commission),
                slippage_cost=str(slippage_cost),
            )
        return report

    def reports(self) -> tuple[ExecutionReport, ...]:
        with self._lock:
            return tuple(self._reports)

    def reset(self) -> None:
        with self._lock:
            self._reports.clear()
            self._executed_order_ids.clear()

    @staticmethod
    def _validate(
        *,
        order: SimulatedOrder,
        market_price: Decimal,
        executed_at: datetime,
    ) -> None:
        if not order.order_id.strip():
            raise ExecutionError("order_id is required")
        if not order.symbol.strip():
            raise ExecutionError("symbol is required")
        if order.quantity <= ZERO:
            raise ExecutionError("quantity must be greater than zero")
        if market_price <= ZERO:
            raise ExecutionError("market_price must be greater than zero")
        if order.submitted_at.tzinfo is None or executed_at.tzinfo is None:
            raise ExecutionError("submitted_at and executed_at must be timezone-aware")
        if executed_at < order.submitted_at:
            raise ExecutionError("executed_at cannot be earlier than submitted_at")
        if order.order_type is not OrderType.MARKET:
            raise ExecutionError(f"unsupported order type: {order.order_type}")


def _execution_id(
    *,
    order_id: str,
    symbol: str,
    side: OrderSide,
    quantity: Decimal,
    fill_price: Decimal,
    executed_at: datetime,
) -> str:
    payload = "|".join(
        (
            order_id,
            symbol.upper(),
            side.value,
            str(quantity),
            str(fill_price),
            executed_at.isoformat(),
        )
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16].upper()
    return f"EX-{digest}"


def _execution_quality(*, total_execution_cost: Decimal, reference_notional: Decimal) -> Decimal:
    if reference_notional <= ZERO:
        return ZERO
    quality = Decimal("100") * (Decimal("1") - (total_execution_cost / reference_notional))
    return max(ZERO, min(Decimal("100"), quality))
