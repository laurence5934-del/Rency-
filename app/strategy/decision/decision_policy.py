from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from app.strategy.analytics import StrategyEvaluation

from .decision_models import (
    Decision,
    DecisionAction,
)


_ONE_HUNDRED = Decimal("100")



class DecisionPolicy(ABC):
    """Base class for all deployment policies."""

    @staticmethod
    def _confidence(score: int) -> Decimal:
        return Decimal(score) / _ONE_HUNDRED

    @abstractmethod
    def decide(
        self,
        evaluation: StrategyEvaluation,
    ) -> Decision:
        raise NotImplementedError


class ConservativePolicy(DecisionPolicy):
    """Only exceptional strategies may trade live."""

    def decide(
        self,
        evaluation: StrategyEvaluation,
    ) -> Decision:

        if (
            evaluation.grade == "A"
            and evaluation.score >= 95
            and not evaluation.concerns
        ):
            return Decision(
                action=DecisionAction.LIVE_TRADE,
                confidence=self._confidence(evaluation.score),
                reason="Strategy satisfies conservative deployment requirements.",
            )

        return Decision(
            action=DecisionAction.IMPROVE,
            confidence=self._confidence(evaluation.score),
            reason="Strategy requires further validation under the conservative policy.",
            warnings=evaluation.concerns,
        )


class BalancedPolicy(DecisionPolicy):
    """Suitable for most production environments."""

    def decide(
        self,
        evaluation: StrategyEvaluation,
    ) -> Decision:

        if (
            evaluation.grade in {"A", "B"}
            and evaluation.score >= 85
        ):
            return Decision(
                action=DecisionAction.PAPER_TRADE,
                confidence=self._confidence(evaluation.score),
                reason="Strategy satisfies balanced deployment requirements.",
                warnings=evaluation.concerns,
            )

        return Decision(
                action=DecisionAction.IMPROVE,
                confidence=self._confidence(evaluation.score),
                reason="Strategy should be optimized before deployment.",
                warnings=evaluation.concerns,
        )


class AggressivePolicy(DecisionPolicy):
    """Aggressive deployment policy."""

    def decide(
        self,
        evaluation: StrategyEvaluation,
    ) -> Decision:

        if (
            evaluation.grade in {"A", "B"}
            and evaluation.score >= 75
        ):
            return Decision(
                action=DecisionAction.PAPER_TRADE,
                confidence=self._confidence(evaluation.score),
                reason="Strategy satisfies aggressive deployment requirements.",
                warnings=evaluation.concerns,
            )

        return Decision(
            action=DecisionAction.REJECT,
            confidence=self._confidence(evaluation.score),
            reason="Strategy does not satisfy aggressive deployment requirements.",
            warnings=evaluation.concerns,
        )