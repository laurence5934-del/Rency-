from __future__ import annotations

from collections import Counter

from .models import DecisionAction, DecisionPriority, DecisionRuleResult


class DecisionConflictResolver:
    _priority_weight = {
        DecisionPriority.LOW: 1.0,
        DecisionPriority.NORMAL: 2.0,
        DecisionPriority.HIGH: 3.0,
        DecisionPriority.CRITICAL: 5.0,
    }

    _safety_rank = {
        DecisionAction.CANCEL: 9,
        DecisionAction.ESCALATE_REVIEW: 8,
        DecisionAction.DEFER: 7,
        DecisionAction.HOLD: 6,
        DecisionAction.CLOSE_POSITION: 5,
        DecisionAction.SCALE_OUT: 4,
        DecisionAction.SELL: 3,
        DecisionAction.SCALE_IN: 2,
        DecisionAction.BUY: 1,
    }

    def resolve(
        self,
        results: tuple[DecisionRuleResult, ...],
        fallback: DecisionAction,
    ) -> DecisionAction:
        if not results:
            return fallback

        critical_failures = [
            result
            for result in results
            if not result.passed and result.severity == DecisionPriority.CRITICAL
        ]
        if critical_failures:
            return max(
                (result.action for result in critical_failures),
                key=lambda action: self._safety_rank[action],
            )

        action_scores: Counter[DecisionAction] = Counter()
        for result in results:
            priority_weight = self._priority_weight[result.severity]
            pass_multiplier = 1.0 if result.passed else 1.25
            action_scores[result.action] += priority_weight * pass_multiplier

        if not action_scores:
            return fallback

        highest = max(action_scores.values())
        candidates = [
            action for action, score in action_scores.items() if score == highest
        ]
        return max(candidates, key=lambda action: self._safety_rank[action])
