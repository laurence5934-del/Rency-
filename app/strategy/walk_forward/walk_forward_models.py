from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")
_ONE = Decimal("1")


class WalkForwardStatus(str, Enum):
    """Lifecycle status for a walk-forward validation run."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class WalkForwardWindow:
    """One training and out-of-sample validation window."""

    window_id: str
    training_start: datetime
    training_end: datetime
    validation_start: datetime
    validation_end: datetime

    def __post_init__(self) -> None:
        normalized_id = self.window_id.strip()

        if not normalized_id:
            raise ValueError("window_id must not be empty")

        if self.training_start >= self.training_end:
            raise ValueError(
                "training_start must be earlier than training_end"
            )

        if self.validation_start >= self.validation_end:
            raise ValueError(
                "validation_start must be earlier than validation_end"
            )

        if self.training_end > self.validation_start:
            raise ValueError(
                "training and validation windows must not overlap"
            )

        object.__setattr__(
            self,
            "window_id",
            normalized_id,
        )


@dataclass(frozen=True, slots=True)
class WalkForwardWindowResult:
    """Performance outcome for one validation window."""

    window: WalkForwardWindow
    training_score: Decimal
    validation_score: Decimal
    validation_return: Decimal = _ZERO
    validation_drawdown: Decimal = _ZERO
    passed: bool = False
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        if not isinstance(self.training_score, Decimal):
            raise TypeError(
                "training_score must be a Decimal"
            )

        if not isinstance(self.validation_score, Decimal):
            raise TypeError(
                "validation_score must be a Decimal"
            )

        if not _ZERO <= self.training_score <= _ONE:
            raise ValueError(
                "training_score must be between 0 and 1"
            )

        if not _ZERO <= self.validation_score <= _ONE:
            raise ValueError(
                "validation_score must be between 0 and 1"
            )

        if not isinstance(self.validation_return, Decimal):
            raise TypeError(
                "validation_return must be a Decimal"
            )

        if not isinstance(self.validation_drawdown, Decimal):
            raise TypeError(
                "validation_drawdown must be a Decimal"
            )

        if self.validation_drawdown < _ZERO:
            raise ValueError(
                "validation_drawdown must not be negative"
            )

        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )


@dataclass(frozen=True, slots=True)
class WalkForwardReport:
    """Aggregate report for a complete walk-forward run."""

    status: WalkForwardStatus
    windows: tuple[WalkForwardWindowResult, ...] = field(
        default_factory=tuple
    )
    robustness_score: Decimal = _ZERO
    pass_rate: Decimal = _ZERO
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, WalkForwardStatus):
            raise TypeError(
                "status must be a WalkForwardStatus"
            )

        if not isinstance(self.robustness_score, Decimal):
            raise TypeError(
                "robustness_score must be a Decimal"
            )

        if not isinstance(self.pass_rate, Decimal):
            raise TypeError(
                "pass_rate must be a Decimal"
            )

        if not _ZERO <= self.robustness_score <= _ONE:
            raise ValueError(
                "robustness_score must be between 0 and 1"
            )

        if not _ZERO <= self.pass_rate <= _ONE:
            raise ValueError(
                "pass_rate must be between 0 and 1"
            )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if self.status is WalkForwardStatus.FAILED:
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
            "windows",
            tuple(self.windows),
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