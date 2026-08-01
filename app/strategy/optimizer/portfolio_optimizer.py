from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from app.strategy.supervisor import (
    ConfidenceWeightedAllocator,
    EqualWeightAllocator,
    RankedStrategy,
    ScoreWeightedAllocator,
)

from .optimizer_models import (
    OptimizationObjective,
    OptimizationResult,
)


class PortfolioOptimizer:
    """Selects the most appropriate allocation policy."""

    def optimize(
        self,
        ranked_strategies: Iterable[RankedStrategy],
        *,
        objective: OptimizationObjective,
        capital: Decimal,
    ) -> OptimizationResult:

        ranked = tuple(ranked_strategies)

        allocator = self._allocator_for(objective)

        allocations = allocator.allocate(
            ranked,
            capital=capital,
        )

        if ranked:
            portfolio_score = (
                sum(
                    strategy.score
                    for strategy in ranked
                )
                / Decimal(len(ranked))
                / Decimal("100")
            )
        else:
            portfolio_score = Decimal("0")

        return OptimizationResult(
            objective=objective,
            selected_policy=allocator.__class__.__name__,
            allocations=allocations,
            total_capital=capital,
            portfolio_score=portfolio_score,
        )

    @staticmethod
    def _allocator_for(
        objective: OptimizationObjective,
    ):
        match objective:

            case OptimizationObjective.BALANCED:
                return EqualWeightAllocator()

            case OptimizationObjective.MAXIMIZE_SCORE:
                return ScoreWeightedAllocator()

            case OptimizationObjective.MAXIMIZE_CONFIDENCE:
                return ConfidenceWeightedAllocator()

        raise ValueError(
            f"Unsupported optimization objective: {objective}"
        )