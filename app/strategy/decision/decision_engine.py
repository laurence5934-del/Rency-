from __future__ import annotations

from app.strategy.analytics import StrategyEvaluation

from .decision_models import Decision
from .decision_policy import (
    BalancedPolicy,
    DecisionPolicy,
)


class DecisionEngine:
    """Enterprise strategy deployment decision engine."""

    def __init__(
        self,
        *,
        policy: DecisionPolicy | None = None,
    ) -> None:
        self._policy = policy or BalancedPolicy()

    @property
    def policy(self) -> DecisionPolicy:
        """Return the active decision policy."""
        return self._policy

    def decide(
        self,
        evaluation: StrategyEvaluation,
    ) -> Decision:
        """Evaluate a strategy using the configured policy."""
        return self._policy.decide(evaluation)