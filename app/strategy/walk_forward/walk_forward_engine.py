from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Iterable

from .walk_forward_models import (
    WalkForwardReport,
    WalkForwardStatus,
    WalkForwardWindow,
    WalkForwardWindowResult,
)


_ZERO = Decimal("0")
_ONE = Decimal("1")


@dataclass(frozen=True, slots=True)
class ValidationOutcome:
    """Out-of-sample performance returned by a validator callback."""

    score: Decimal
    validation_return: Decimal = _ZERO
    drawdown: Decimal = _ZERO
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.score, Decimal):
            raise TypeError("score must be a Decimal")

        if not _ZERO <= self.score <= _ONE:
            raise ValueError(
                "score must be between 0 and 1"
            )

        if not isinstance(
            self.validation_return,
            Decimal,
        ):
            raise TypeError(
                "validation_return must be a Decimal"
            )

        if not isinstance(self.drawdown, Decimal):
            raise TypeError(
                "drawdown must be a Decimal"
            )

        if self.drawdown < _ZERO:
            raise ValueError(
                "drawdown must not be negative"
            )

        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )


Trainer = Callable[[WalkForwardWindow], Decimal]
Validator = Callable[
    [WalkForwardWindow],
    ValidationOutcome,
]


class WalkForwardEngine:
    """Executes and aggregates walk-forward validation windows."""

    def run(
        self,
        *,
        windows: Iterable[WalkForwardWindow],
        trainer: Trainer,
        validator: Validator,
        minimum_validation_score: Decimal = Decimal(
            "0.60"
        ),
    ) -> WalkForwardReport:
        self._validate_inputs(
            trainer=trainer,
            validator=validator,
            minimum_validation_score=(
                minimum_validation_score
            ),
        )

        ordered_windows = tuple(
            sorted(
                windows,
                key=lambda window: (
                    window.training_start,
                    window.validation_start,
                    window.window_id,
                ),
            )
        )

        if not ordered_windows:
            return WalkForwardReport(
                status=WalkForwardStatus.COMPLETED,
                windows=(),
                robustness_score=_ZERO,
                pass_rate=_ZERO,
                warnings=(
                    "No walk-forward windows were supplied.",
                ),
            )

        results: list[WalkForwardWindowResult] = []

        try:
            for window in ordered_windows:
                training_score = trainer(window)

                self._validate_score(
                    training_score,
                    name="training_score",
                )

                validation = validator(window)

                if not isinstance(
                    validation,
                    ValidationOutcome,
                ):
                    raise TypeError(
                        "validator must return "
                        "ValidationOutcome"
                    )

                passed = (
                    validation.score
                    >= minimum_validation_score
                )

                results.append(
                    WalkForwardWindowResult(
                        window=window,
                        training_score=training_score,
                        validation_score=validation.score,
                        validation_return=(
                            validation.validation_return
                        ),
                        validation_drawdown=(
                            validation.drawdown
                        ),
                        passed=passed,
                        warnings=validation.warnings,
                    )
                )

        except Exception as exc:
            return WalkForwardReport(
                status=WalkForwardStatus.FAILED,
                windows=tuple(results),
                robustness_score=self._robustness_score(
                    results
                ),
                pass_rate=self._pass_rate(results),
                warnings=(
                    "Walk-forward execution stopped "
                    "before all windows completed.",
                ),
                error=str(exc),
            )

        return WalkForwardReport(
            status=WalkForwardStatus.COMPLETED,
            windows=tuple(results),
            robustness_score=self._robustness_score(
                results
            ),
            pass_rate=self._pass_rate(results),
            warnings=self._aggregate_warnings(results),
        )

    @staticmethod
    def _validate_inputs(
        *,
        trainer: Trainer,
        validator: Validator,
        minimum_validation_score: Decimal,
    ) -> None:
        if not callable(trainer):
            raise TypeError("trainer must be callable")

        if not callable(validator):
            raise TypeError("validator must be callable")

        if not isinstance(
            minimum_validation_score,
            Decimal,
        ):
            raise TypeError(
                "minimum_validation_score must be a Decimal"
            )

        if not (
            _ZERO
            <= minimum_validation_score
            <= _ONE
        ):
            raise ValueError(
                "minimum_validation_score must be "
                "between 0 and 1"
            )

    @staticmethod
    def _validate_score(
        score: Decimal,
        *,
        name: str,
    ) -> None:
        if not isinstance(score, Decimal):
            raise TypeError(
                f"{name} must be a Decimal"
            )

        if not _ZERO <= score <= _ONE:
            raise ValueError(
                f"{name} must be between 0 and 1"
            )

    @staticmethod
    def _robustness_score(
        results: Iterable[WalkForwardWindowResult],
    ) -> Decimal:
        completed = tuple(results)

        if not completed:
            return _ZERO

        return (
            sum(
                (
                    result.validation_score
                    for result in completed
                ),
                _ZERO,
            )
            / Decimal(len(completed))
        )

    @staticmethod
    def _pass_rate(
        results: Iterable[WalkForwardWindowResult],
    ) -> Decimal:
        completed = tuple(results)

        if not completed:
            return _ZERO

        passed_count = sum(
            1
            for result in completed
            if result.passed
        )

        return (
            Decimal(passed_count)
            / Decimal(len(completed))
        )

    @staticmethod
    def _aggregate_warnings(
        results: Iterable[WalkForwardWindowResult],
    ) -> tuple[str, ...]:
        return tuple(
            warning
            for result in results
            for warning in result.warnings
        )