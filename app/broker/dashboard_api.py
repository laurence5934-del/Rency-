from __future__ import annotations


class BrokerDashboardAPI:
    def __init__(self, manager) -> None:
        self._manager = manager

    def health(self) -> dict[str, object]:
        return self._manager.health()

    def metrics(self) -> dict[str, int]:
        return self._manager.metrics.snapshot()

    def recent_orders(self, limit: int = 50) -> list[dict[str, object]]:
        return [item.to_dict() for item in self._manager.audit_log.recent(limit)]
