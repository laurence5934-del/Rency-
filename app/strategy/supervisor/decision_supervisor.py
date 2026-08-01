from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from app.strategy.decision import DecisionAction

from .supervisor_models import (
    CapitalAllocation,
    DeploymentPlan,
    RankedStrategy,
    StrategyCandidate,
)


_ZERO = Decimal("0")
_ONE = Decimal("1")


class DecisionSupervisor:
    """Coordinates ranking and capital allocation across strategies."""

    def create_plan(
        self,
        candidates: Iterable[StrategyCandidate],
        *,
        capital: Decimal,
    ) -> DeploymentPlan:
        if not isinstance(capital, Decimal):
            raise TypeError("capital must be a Decimal")

        if capital < _ZERO:
            raise ValueError("capital must not be negative")

        approved_candidates = self._approved_candidates(
            candidates
        )

        if not approved_candidates:
            return DeploymentPlan(
                allocations=(),
                total_capital=_ZERO,
                warnings=(
                    "No approved strategies were available for deployment.",
                ),
            )

        ranked = self._rank_candidates(
            approved_candidates
        )

        allocations = self._allocate_equally(
            ranked,
            capital=capital,
        )

        allocated_capital = sum(
            (
                allocation.allocation
                for allocation in allocations
            ),
            _ZERO,
        )

        warnings: list[str] = []

        if capital == _ZERO:
            warnings.append(
                "Available capital is zero."
            )

        return DeploymentPlan(
            allocations=allocations,
            total_capital=allocated_capital,
            warnings=tuple(warnings),
        )

    @staticmethod
    def _approved_candidates(
        candidates: Iterable[StrategyCandidate],
    ) -> tuple[StrategyCandidate, ...]:
        return tuple(
            candidate
            for candidate in candidates
            if candidate.decision.action
            in {
                DecisionAction.PAPER_TRADE,
                DecisionAction.LIVE_TRADE,
            }
        )

    @staticmethod
    def _rank_candidates(
        candidates: Iterable[StrategyCandidate],
    ) -> tuple[RankedStrategy, ...]:
        ordered = sorted(
            candidates,
            key=lambda candidate: (
                candidate.evaluation.score,
                candidate.decision.confidence,
                candidate.strategy_id,
            ),
            reverse=True,
        )

        return tuple(
            RankedStrategy(
                strategy=candidate,
                rank=index,
                score=Decimal(candidate.evaluation.score),
            )
            for index, candidate in enumerate(
                ordered,
                start=1,
            )
        )

    @staticmethod
    def _allocate_equally(
        ranked: tuple[RankedStrategy, ...],
        *,
        capital: Decimal,
    ) -> tuple[CapitalAllocation, ...]:
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