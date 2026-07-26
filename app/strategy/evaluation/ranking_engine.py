from __future__ import annotations

from .models import StrategyEvaluation


class StrategyRankingEngine:
    def rank(self, evaluations: list[StrategyEvaluation] | tuple[StrategyEvaluation, ...]) -> tuple[StrategyEvaluation, ...]:
        return tuple(sorted(evaluations, key=lambda item: (-item.scores.overall, item.strategy_id, item.strategy_version)))
