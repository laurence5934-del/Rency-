from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from app.strategy.supervisor import CapitalAllocation


_ZERO = Decimal("0")
_ONE = Decimal("1")


class OptimizationObjective(str, Enum):
    """Portfolio objective used to select an allocation policy."""

    BALANCED = "BALANCED"
    MAXIMIZE_SCORE = "MAXIMIZE_SCORE"
    MAXIMIZE_CONFIDENCE = "MAXIMIZE_CONFIDENCE"


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    """Immutable result produced by the portfolio optimizer."""

    objective: OptimizationObjective
    selected_policy: str
    allocations: tuple[CapitalAllocation, ...] = field(
        default_factory=tuple
    )
    total_capital: Decimal = _ZERO
    portfolio_score: Decimal = _ZERO
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.objective,
            OptimizationObjective,
        ):
            raise TypeError(
                "objective must be an OptimizationObjective"
            )

        if not self.selected_policy.strip():
            raise ValueError(
                "selected_policy must not be empty"
            )

        if not isinstance(self.total_capital, Decimal):
            raise TypeError(
                "total_capital must be a Decimal"
            )

        if self.total_capital < _ZERO:
            raise ValueError(
                "total_capital must not be negative"
            )

        if not isinstance(self.portfolio_score, Decimal):
            raise TypeError(
                "portfolio_score must be a Decimal"
            )

        if not _ZERO <= self.portfolio_score <= _ONE:
            raise ValueError(
                "portfolio_score must be between 0 and 1"
            )

        object.__setattr__(
            self,
            "selected_policy",
            self.selected_policy.strip(),
        )
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