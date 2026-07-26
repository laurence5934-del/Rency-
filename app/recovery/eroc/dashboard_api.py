from __future__ import annotations

from typing import Any


class RecoveryDashboardAPI:
    def __init__(self, operating_center: Any) -> None:
        self.operating_center = operating_center

    def overview(self) -> dict[str, Any]:
        health = self.operating_center.health()
        readiness = self.operating_center.readiness()
        return {
            "platform_health": health.to_dict(),
            "trading_readiness": readiness.to_dict(),
            "active_incidents": [
                item.to_dict()
                for item in self.operating_center.incidents.active()
            ],
            "metrics": self.operating_center.metrics.snapshot(),
            "integration": self.operating_center.integration.validate().__dict__,
        }

    def timeline(self, limit: int = 100) -> list[dict[str, Any]]:
        return [
            item.to_dict()
            for item in self.operating_center.timeline.events(limit)
        ]

    def diagnostics(self) -> list[dict[str, Any]]:
        return [
            item.to_dict()
            for item in self.operating_center.diagnostics.run()
        ]

    def components(self) -> list[dict[str, Any]]:
        return self.operating_center.registry.snapshot()

    def policies(self) -> list[dict[str, Any]]:
        return self.operating_center.policies.snapshot()
