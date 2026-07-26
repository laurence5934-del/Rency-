from __future__ import annotations


class ConfidenceDashboardAPI:
    def __init__(self, engine) -> None:
        self._engine = engine

    def health(self) -> dict[str, object]:
        return self._engine.health()

    def metrics(self) -> dict[str, int]:
        return self._engine.metrics()

    def evaluate(self, source) -> dict[str, object]:
        return self._engine.evaluate(source).to_dict()
