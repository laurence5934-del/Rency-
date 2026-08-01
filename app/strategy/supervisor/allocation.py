from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Iterable

from .supervisor_models import (
    CapitalAllocation,
    RankedStrategy,
)


_ZERO = Decimal("0")
_ONE = Decimal("1")


class AllocationPolicy(ABC):
    """Base class for portfolio-capital allocation policies."""

    @abstractmethod
    def allocate(
        self,
        ranked_strategies: Iterable[RankedStrategy],
        *,
        capital: Decimal,
    ) -> tuple[CapitalAllocation, ...]:
        """Allocate capital across ranked strategies."""
        raise NotImplementedError

    @staticmethod
    def _validate_capital(capital: Decimal) -> None:
        if not isinstance(capital, Decimal):
            raise TypeError("capital must be a Decimal")

        if capital < _ZERO:
            raise ValueError("capital must not be negative")


class EqualWeightAllocator(AllocationPolicy):
    """Allocates equal capital to every ranked strategy."""

    def allocate(
        self,
        ranked_strategies: Iterable[RankedStrategy],
        *,
        capital: Decimal,
    ) -> tuple[CapitalAllocation, ...]:
        self._validate_capital(capital)

        ranked = tuple(ranked_strategies)

        if not ranked:
            return ()

        count = Decimal(len(ranked))
        weight = _ONE / count
        allocation = capital / count

        return tuple(
            CapitalAllocation(
                strategy_id=ranked_strategy.strategy.strategy_id,
                allocation=allocation,
                weight=weight,
            )
            for ranked_strategy in ranked
        )


class ScoreWeightedAllocator(AllocationPolicy):
    """Allocates capital in proportion to evaluation score."""

    def allocate(
        self,
        ranked_strategies: Iterable[RankedStrategy],
        *,
        capital: Decimal,
    ) -> tuple[CapitalAllocation, ...]:
        self._validate_capital(capital)

        ranked = tuple(ranked_strategies)

        if not ranked:
            return ()

        positive_scores = tuple(
            max(ranked_strategy.score, _ZERO)
            for ranked_strategy in ranked
        )

        total_score = sum(
            positive_scores,
            _ZERO,
        )

        if total_score == _ZERO:
            return EqualWeightAllocator().allocate(
                ranked,
                capital=capital,
            )

        return tuple(
            CapitalAllocation(
                strategy_id=ranked_strategy.strategy.strategy_id,
                allocation=(
                    capital
                    * score
                    / total_score
                ),
                weight=score / total_score,
            )
            for ranked_strategy, score in zip(
                ranked,
                positive_scores,
                strict=True,
            )
        )


class ConfidenceWeightedAllocator(AllocationPolicy):
    """Allocates capital in proportion to decision confidence."""

    def allocate(
        self,
        ranked_strategies: Iterable[RankedStrategy],
        *,
        capital: Decimal,
    ) -> tuple[CapitalAllocation, ...]:
        self._validate_capital(capital)

        ranked = tuple(ranked_strategies)

        if not ranked:
            return ()

        confidences = tuple(
            max(
                ranked_strategy.strategy.decision.confidence,
                _ZERO,
            )
            for ranked_strategy in ranked
        )

        total_confidence = sum(
            confidences,
            _ZERO,
        )

        if total_confidence == _ZERO:
            return EqualWeightAllocator().allocate(
                ranked,
                capital=capital,
            )

        return tuple(
            CapitalAllocation(
                strategy_id=ranked_strategy.strategy.strategy_id,
                allocation=(
                    capital
                    * confidence
                    / total_confidence
                ),
                weight=confidence / total_confidence,
            )
            for ranked_strategy, confidence in zip(
                ranked,
                confidences,
                strict=True,
            )
        )