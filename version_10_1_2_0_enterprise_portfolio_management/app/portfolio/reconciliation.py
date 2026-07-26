from __future__ import annotations

from .models import AccountBalance, Position


class PortfolioReconciler:
    def reconcile(self, balance: AccountBalance, positions: tuple[Position, ...]) -> tuple[bool, tuple[str, ...]]:
        issues: list[str] = []
        if balance.reserved_cash < 0:
            issues.append("NEGATIVE_RESERVED_CASH")
        if balance.reserved_cash > balance.cash:
            issues.append("RESERVED_CASH_EXCEEDS_CASH")
        for position in positions:
            if position.quantity != 0 and position.average_cost <= 0:
                issues.append(f"INVALID_AVERAGE_COST:{position.symbol}")
            if position.market_price < 0:
                issues.append(f"NEGATIVE_MARKET_PRICE:{position.symbol}")
        return not issues, tuple(issues)
