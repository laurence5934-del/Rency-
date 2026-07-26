from __future__ import annotations


class PortfolioDashboardAPI:
    def __init__(self, manager) -> None:
        self._manager = manager

    def health(self) -> dict[str, object]:
        return self._manager.health()

    def summary(self) -> dict[str, object]:
        snapshot = self._manager.snapshot()
        return {
            "cash": snapshot.cash,
            "buying_power": snapshot.buying_power,
            "gross_market_value": snapshot.gross_market_value,
            "net_liquidation_value": snapshot.net_liquidation_value,
            "realized_pnl": snapshot.realized_pnl,
            "unrealized_pnl": snapshot.unrealized_pnl,
            "dividends_received": snapshot.dividends_received,
        }

    def positions(self) -> list[dict[str, object]]:
        return [position.to_dict() for position in self._manager.positions()]

    def metrics(self) -> dict[str, int]:
        return self._manager.metrics()

    def audit(self, limit: int = 50) -> list[dict[str, object]]:
        return list(self._manager.recent_audit_events(limit))
