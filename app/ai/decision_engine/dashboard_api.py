from __future__ import annotations


class DecisionDashboardAPI:
    def __init__(self, engine) -> None:
        self._engine = engine

    def health(self) -> dict[str, object]:
        return self._engine.health()

    def metrics(self) -> dict[str, int]:
        return self._engine.metrics()

    def recent_decisions(self, limit: int = 50) -> list[dict[str, object]]:
        return [
            report.to_dict()
            for report in self._engine.recent_decisions(limit)
        ]

    def decide(self, context) -> dict[str, object]:
        return self._engine.decide(context).to_dict()
