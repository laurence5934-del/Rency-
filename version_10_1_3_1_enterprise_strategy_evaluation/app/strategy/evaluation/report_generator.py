from __future__ import annotations

import json

from .models import StrategyEvaluation


class EvaluationReportGenerator:
    def as_dict(self, evaluation: StrategyEvaluation) -> dict[str, object]:
        return evaluation.as_dict()

    def as_json(self, evaluation: StrategyEvaluation, *, indent: int = 2) -> str:
        return json.dumps(self.as_dict(evaluation), indent=indent, sort_keys=True)

    def executive_summary(self, evaluation: StrategyEvaluation) -> str:
        return (
            f"{evaluation.strategy_id} v{evaluation.strategy_version}: "
            f"overall={evaluation.scores.overall:.2f}, "
            f"recommendation={evaluation.recommendation.value}."
        )
