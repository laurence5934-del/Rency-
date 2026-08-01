from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.strategy.analytics import StrategyEvaluation
from app.strategy.decision import Decision


@dataclass(frozen=True, slots=True)
class StrategyCandidate:
    """A strategy submitted to the supervisor."""

    strategy_id: str
    evaluation: StrategyEvaluation
    decision: Decision


@dataclass(frozen=True, slots=True)
class RankedStrategy:
    """A candidate ranked for deployment."""

    strategy: StrategyCandidate
    rank: int
    score: Decimal


@dataclass(frozen=True, slots=True)
class CapitalAllocation:
    """Capital assigned to an approved strategy."""

    strategy_id: str
    allocation: Decimal
    weight: Decimal


@dataclass(frozen=True, slots=True)
class DeploymentPlan:
    """Final deployment plan produced by the supervisor."""

    allocations: tuple[CapitalAllocation, ...] = field(
        default_factory=tuple
    )

    total_capital: Decimal = Decimal("0")

    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "allocations",
            tuple(self.allocations),
        )

        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )