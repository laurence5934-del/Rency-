from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from .models import AIDecisionObservation


class AIStatistics:
    def calculate(self, observations: Iterable[AIDecisionObservation]) -> dict[str, object]:
        items = tuple(observations)
        evaluated = [item for item in items if item.correct is not None]
        correct = [item for item in evaluated if item.correct]
        by_model: dict[str, list[bool]] = defaultdict(list)
        for item in evaluated:
            by_model[item.model].append(bool(item.correct))
        return {
            "decision_count": len(items),
            "evaluated_decisions": len(evaluated),
            "correct_decisions": len(correct),
            "decision_accuracy": len(correct) / len(evaluated) if evaluated else 0.0,
            "average_confidence": sum(item.confidence for item in items) / len(items) if items else 0.0,
            "model_accuracy": {
                model: sum(results) / len(results) for model, results in sorted(by_model.items())
            },
        }
