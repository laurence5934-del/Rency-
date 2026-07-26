from __future__ import annotations

from .evaluation_engine import StrategyEvaluationEngine
from .ranking_engine import StrategyRankingEngine


class StrategyEvaluationDashboardAPI:
    def __init__(self, engine: StrategyEvaluationEngine) -> None:
        self.engine = engine
        self.ranker = StrategyRankingEngine()

    def health(self) -> dict[str, object]:
        return {"status": "healthy", "live_trading": False, "metrics": self.engine.metrics.snapshot()}

    def leaderboard(self) -> list[dict[str, object]]:
        return [item.as_dict() for item in self.ranker.rank(self.engine.list_evaluations())]
