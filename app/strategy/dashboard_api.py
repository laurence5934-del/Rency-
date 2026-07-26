from __future__ import annotations

from typing import Any

from .strategy_registry import StrategyRegistry


class StrategyDashboardAPI:
    """Read-only dashboard facade."""

    def __init__(self, registry: StrategyRegistry) -> None:
        self._registry = registry

    def health(self) -> dict[str, Any]:
        snapshot = self._registry.snapshot()
        return {"status": "healthy", **snapshot, "metrics": self._registry.metrics.snapshot()}

    def catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "id": item.strategy_id, "name": item.name, "version": str(item.version),
                "category": item.category, "risk_profile": item.risk_profile.value,
                "status": item.status.value, "assets": list(item.supported_assets),
                "timeframes": list(item.supported_timeframes),
            }
            for item in self._registry.list(latest_only=False)
        ]
