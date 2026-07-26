from __future__ import annotations

from threading import RLock

from .audit_log import PortfolioAuditLog
from .metrics import PortfolioMetrics
from .models import AccountBalance, CashMovement, CashMovementType, PortfolioSnapshot, TradeFill
from .position_manager import PositionManager
from .reconciliation import PortfolioReconciler
from .valuation import PortfolioValuationEngine


class EnterprisePortfolioManager:
    def __init__(
        self,
        *,
        starting_cash: float = 0.0,
        buying_power_multiplier: float = 1.0,
        positions: PositionManager | None = None,
        valuation: PortfolioValuationEngine | None = None,
        reconciler: PortfolioReconciler | None = None,
        audit_log: PortfolioAuditLog | None = None,
        metrics: PortfolioMetrics | None = None,
    ) -> None:
        if starting_cash < 0:
            raise ValueError("starting_cash cannot be negative")
        if buying_power_multiplier <= 0:
            raise ValueError("buying_power_multiplier must be positive")
        self.balance = AccountBalance(starting_cash, 0.0, buying_power_multiplier)
        self._positions = positions or PositionManager()
        self._valuation = valuation or PortfolioValuationEngine()
        self._reconciler = reconciler or PortfolioReconciler()
        self._audit = audit_log or PortfolioAuditLog()
        self._metrics = metrics or PortfolioMetrics()
        self._snapshots: list[PortfolioSnapshot] = []
        self._lock = RLock()

    def apply_fill(self, fill: TradeFill):
        with self._lock:
            gross = fill.quantity * fill.price
            if fill.side.upper() == "BUY":
                required = gross + fill.commission
                if required > self.balance.available_cash:
                    raise ValueError("insufficient available cash")
                self.balance.cash -= required
            else:
                self.balance.cash += gross - fill.commission
            position = self._positions.apply_fill(fill)
            self._metrics.increment("fills_applied")
            self._audit.append({"event": "FILL_APPLIED", "symbol": fill.symbol.upper(), "quantity": fill.quantity, "side": fill.side.upper()})
            return position

    def apply_cash_movement(self, movement: CashMovement) -> float:
        with self._lock:
            positive = movement.movement_type in {
                CashMovementType.DEPOSIT,
                CashMovementType.DIVIDEND,
                CashMovementType.INTEREST,
                CashMovementType.ADJUSTMENT,
            }
            if positive:
                self.balance.cash += movement.amount
            else:
                if movement.amount > self.balance.available_cash:
                    raise ValueError("cash movement exceeds available cash")
                self.balance.cash -= movement.amount
            self._metrics.increment("cash_movements")
            self._audit.append({"event": "CASH_MOVEMENT", "type": movement.movement_type.value, "amount": movement.amount})
            return self.balance.cash

    def record_dividend(self, symbol: str, amount: float) -> None:
        movement = CashMovement(CashMovementType.DIVIDEND, amount, f"Dividend from {symbol.upper()}")
        self.apply_cash_movement(movement)
        self._positions.add_dividend(symbol, amount)

    def update_market_price(self, symbol: str, price: float) -> None:
        self._positions.mark_price(symbol, price)
        self._metrics.increment("price_updates")

    def reserve_cash(self, amount: float) -> None:
        if amount < 0 or amount > self.balance.available_cash:
            raise ValueError("invalid reserve amount")
        self.balance.reserved_cash += amount

    def release_cash(self, amount: float) -> None:
        if amount < 0 or amount > self.balance.reserved_cash:
            raise ValueError("invalid release amount")
        self.balance.reserved_cash -= amount

    def snapshot(self) -> PortfolioSnapshot:
        positions = self._positions.all()
        valuation = self._valuation.calculate(self.balance, positions)
        snapshot = PortfolioSnapshot.create(
            cash=self.balance.cash,
            buying_power=self.balance.buying_power,
            gross_market_value=valuation["gross_market_value"],
            net_liquidation_value=valuation["net_liquidation_value"],
            realized_pnl=valuation["realized_pnl"],
            unrealized_pnl=valuation["unrealized_pnl"],
            dividends_received=valuation["dividends_received"],
            positions=tuple(position.to_dict() for position in positions),
        )
        self._snapshots.append(snapshot)
        self._metrics.increment("snapshots_created")
        return snapshot

    def reconcile(self) -> tuple[bool, tuple[str, ...]]:
        result = self._reconciler.reconcile(self.balance, self._positions.all())
        self._metrics.increment("reconciliations")
        if not result[0]:
            self._metrics.increment("reconciliation_failures")
        return result

    def get_position(self, symbol: str):
        return self._positions.get(symbol)

    def positions(self):
        return self._positions.all()

    def metrics(self) -> dict[str, int]:
        return self._metrics.snapshot()

    def recent_audit_events(self, limit: int = 50):
        return self._audit.recent(limit)

    def health(self) -> dict[str, object]:
        reconciled, issues = self.reconcile()
        return {
            "status": "HEALTHY" if reconciled else "DEGRADED",
            "reconciled": reconciled,
            "issues": issues,
            "cash": self.balance.cash,
            "buying_power": self.balance.buying_power,
            "positions": len(self._positions.all()),
            "metrics": self.metrics(),
        }
