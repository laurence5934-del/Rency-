from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")
_ONE = Decimal("1")


class MonteCarloStatus(str, Enum):
    """Lifecycle status for a Monte Carlo simulation."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class MonteCarloPathResult:
    """Outcome from one simulated portfolio path."""

    path_id: int
    final_equity: Decimal
    total_return: Decimal
    max_drawdown: Decimal
    ruined: bool = False

    def __post_init__(self) -> None:
        if self.path_id < 1:
            raise ValueError(
                "path_id must be greater than zero"
            )

        if not isinstance(self.final_equity, Decimal):
            raise TypeError(
                "final_equity must be a Decimal"
            )

        if not isinstance(self.total_return, Decimal):
            raise TypeError(
                "total_return must be a Decimal"
            )

        if not isinstance(self.max_drawdown, Decimal):
            raise TypeError(
                "max_drawdown must be a Decimal"
            )

        if self.final_equity < _ZERO:
            raise ValueError(
                "final_equity must not be negative"
            )

        if not _ZERO <= self.max_drawdown <= _ONE:
            raise ValueError(
                "max_drawdown must be between 0 and 1"
            )


@dataclass(frozen=True, slots=True)
class MonteCarloReport:
    """Aggregate results from a Monte Carlo simulation."""

    status: MonteCarloStatus
    paths: tuple[MonteCarloPathResult, ...] = field(
        default_factory=tuple
    )
    ruin_probability: Decimal = _ZERO
    median_final_equity: Decimal = _ZERO
    percentile_05_final_equity: Decimal = _ZERO
    percentile_95_final_equity: Decimal = _ZERO
    median_max_drawdown: Decimal = _ZERO
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, MonteCarloStatus):
            raise TypeError(
                "status must be a MonteCarloStatus"
            )

        if not isinstance(
            self.ruin_probability,
            Decimal,
        ):
            raise TypeError(
                "ruin_probability must be a Decimal"
            )

        if not _ZERO <= self.ruin_probability <= _ONE:
            raise ValueError(
                "ruin_probability must be between 0 and 1"
            )

        for name in (
            "median_final_equity",
            "percentile_05_final_equity",
            "percentile_95_final_equity",
            "median_max_drawdown",
        ):
            value = getattr(self, name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{name} must be a Decimal"
                )

        if self.median_final_equity < _ZERO:
            raise ValueError(
                "median_final_equity must not be negative"
            )

        if self.percentile_05_final_equity < _ZERO:
            raise ValueError(
                "percentile_05_final_equity must not be negative"
            )

        if self.percentile_95_final_equity < _ZERO:
            raise ValueError(
                "percentile_95_final_equity must not be negative"
            )

        if not _ZERO <= self.median_max_drawdown <= _ONE:
            raise ValueError(
                "median_max_drawdown must be between 0 and 1"
            )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if self.status is MonteCarloStatus.FAILED:
            if not normalized_error:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error:
            raise ValueError(
                "only failed reports may include an error"
            )

        object.__setattr__(
            self,
            "paths",
            tuple(self.paths),
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )
        object.__setattr__(
            self,
            "error",
            normalized_error,
        )