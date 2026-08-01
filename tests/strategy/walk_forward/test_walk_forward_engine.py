from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.walk_forward.walk_forward_engine import (
    ValidationOutcome,
    WalkForwardEngine,
)
from app.strategy.walk_forward.walk_forward_models import (
    WalkForwardStatus,
    WalkForwardWindow,
)


START = datetime(
    2025,
    1,
    1,
    tzinfo=timezone.utc,
)


def window(
    number: int,
) -> WalkForwardWindow:
    training_start = START + timedelta(
        days=(number - 1) * 5
    )
    training_end = training_start + timedelta(
        days=10
    )
    validation_start = training_end
    validation_end = validation_start + timedelta(
        days=5
    )

    return WalkForwardWindow(
        window_id=f"window-{number:03d}",
        training_start=training_start,
        training_end=training_end,
        validation_start=validation_start,
        validation_end=validation_end,
    )


def trainer(
    current_window: WalkForwardWindow,
) -> Decimal:
    del current_window
    return Decimal("0.90")


def validator(
    current_window: WalkForwardWindow,
) -> ValidationOutcome:
    del current_window

    return ValidationOutcome(
        score=Decimal("0.80"),
        validation_return=Decimal("0.05"),
        drawdown=Decimal("0.03"),
    )


def test_run_completes_all_windows() -> None:
    report = WalkForwardEngine().run(
        windows=(
            window(1),
            window(2),
            window(3),
        ),
        trainer=trainer,
        validator=validator,
    )

    assert report.status is WalkForwardStatus.COMPLETED
    assert len(report.windows) == 3
    assert report.error is None


def test_run_creates_window_results() -> None:
    report = WalkForwardEngine().run(
        windows=(window(1),),
        trainer=trainer,
        validator=validator,
    )

    result = report.windows[0]

    assert result.window == window(1)
    assert result.training_score == Decimal("0.90")
    assert result.validation_score == Decimal("0.80")
    assert result.validation_return == Decimal("0.05")
    assert result.validation_drawdown == Decimal("0.03")
    assert result.passed is True


def test_windows_are_processed_chronologically() -> None:
    report = WalkForwardEngine().run(
        windows=(
            window(3),
            window(1),
            window(2),
        ),
        trainer=trainer,
        validator=validator,
    )

    assert tuple(
        result.window.window_id
        for result in report.windows
    ) == (
        "window-001",
        "window-002",
        "window-003",
    )


def test_validation_threshold_determines_pass() -> None:
    report = WalkForwardEngine().run(
        windows=(window(1),),
        trainer=trainer,
        validator=lambda current_window: (
            ValidationOutcome(
                score=Decimal("0.59"),
            )
        ),
        minimum_validation_score=Decimal("0.60"),
    )

    assert report.windows[0].passed is False
    assert report.pass_rate == Decimal("0")


def test_score_equal_to_threshold_passes() -> None:
    report = WalkForwardEngine().run(
        windows=(window(1),),
        trainer=trainer,
        validator=lambda current_window: (
            ValidationOutcome(
                score=Decimal("0.60"),
            )
        ),
        minimum_validation_score=Decimal("0.60"),
    )

    assert report.windows[0].passed is True
    assert report.pass_rate == Decimal("1")


def test_robustness_score_is_average_validation_score() -> None:
    scores = iter(
        (
            Decimal("0.90"),
            Decimal("0.70"),
            Decimal("0.50"),
        )
    )

    report = WalkForwardEngine().run(
        windows=(
            window(1),
            window(2),
            window(3),
        ),
        trainer=trainer,
        validator=lambda current_window: (
            ValidationOutcome(
                score=next(scores),
            )
        ),
    )

    assert report.robustness_score == Decimal("0.70")


def test_pass_rate_is_calculated() -> None:
    scores = iter(
        (
            Decimal("0.80"),
            Decimal("0.40"),
            Decimal("0.70"),
            Decimal("0.30"),
        )
    )

    report = WalkForwardEngine().run(
        windows=(
            window(1),
            window(2),
            window(3),
            window(4),
        ),
        trainer=trainer,
        validator=lambda current_window: (
            ValidationOutcome(
                score=next(scores),
            )
        ),
        minimum_validation_score=Decimal("0.60"),
    )

    assert report.pass_rate == Decimal("0.5")


def test_empty_windows_return_completed_report() -> None:
    report = WalkForwardEngine().run(
        windows=(),
        trainer=trainer,
        validator=validator,
    )

    assert report.status is WalkForwardStatus.COMPLETED
    assert report.windows == ()
    assert report.robustness_score == Decimal("0")
    assert report.pass_rate == Decimal("0")
    assert report.warnings == (
        "No walk-forward windows were supplied.",
    )


def test_validator_warnings_are_aggregated() -> None:
    report = WalkForwardEngine().run(
        windows=(
            window(1),
            window(2),
        ),
        trainer=trainer,
        validator=lambda current_window: (
            ValidationOutcome(
                score=Decimal("0.80"),
                warnings=(
                    f"{current_window.window_id} warning",
                ),
            )
        ),
    )

    assert report.warnings == (
        "window-001 warning",
        "window-002 warning",
    )


def test_trainer_failure_returns_failed_report() -> None:
    def failing_trainer(
        current_window: WalkForwardWindow,
    ) -> Decimal:
        del current_window
        raise RuntimeError("training failed")

    report = WalkForwardEngine().run(
        windows=(window(1),),
        trainer=failing_trainer,
        validator=validator,
    )

    assert report.status is WalkForwardStatus.FAILED
    assert report.windows == ()
    assert report.error == "training failed"


def test_validator_failure_preserves_completed_windows() -> None:
    calls = 0

    def sometimes_failing_validator(
        current_window: WalkForwardWindow,
    ) -> ValidationOutcome:
        nonlocal calls
        del current_window

        calls += 1

        if calls == 2:
            raise RuntimeError("validation failed")

        return ValidationOutcome(
            score=Decimal("0.80"),
        )

    report = WalkForwardEngine().run(
        windows=(
            window(1),
            window(2),
            window(3),
        ),
        trainer=trainer,
        validator=sometimes_failing_validator,
    )

    assert report.status is WalkForwardStatus.FAILED
    assert len(report.windows) == 1
    assert report.error == "validation failed"
    assert report.robustness_score == Decimal("0.80")
    assert report.pass_rate == Decimal("1")


def test_validator_must_return_validation_outcome() -> None:
    report = WalkForwardEngine().run(
        windows=(window(1),),
        trainer=trainer,
        validator=lambda current_window: Decimal(
            "0.80"
        ),
    )

    assert report.status is WalkForwardStatus.FAILED
    assert (
        report.error
        == "validator must return ValidationOutcome"
    )


@pytest.mark.parametrize(
    "minimum_score",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_minimum_validation_score_must_be_valid(
    minimum_score: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be between 0 and 1",
    ):
        WalkForwardEngine().run(
            windows=(),
            trainer=trainer,
            validator=validator,
            minimum_validation_score=minimum_score,
        )


def test_minimum_validation_score_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="must be a Decimal",
    ):
        WalkForwardEngine().run(
            windows=(),
            trainer=trainer,
            validator=validator,
            minimum_validation_score=0.60,
        )


def test_trainer_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="trainer must be callable",
    ):
        WalkForwardEngine().run(
            windows=(),
            trainer=None,
            validator=validator,
        )


def test_validator_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="validator must be callable",
    ):
        WalkForwardEngine().run(
            windows=(),
            trainer=trainer,
            validator=None,
        )


def test_validation_outcome_normalizes_warnings() -> None:
    outcome = ValidationOutcome(
        score=Decimal("0.80"),
        warnings=["A warning"],
    )

    assert outcome.warnings == ("A warning",)


def test_validation_outcome_rejects_negative_drawdown() -> None:
    with pytest.raises(
        ValueError,
        match="drawdown must not be negative",
    ):
        ValidationOutcome(
            score=Decimal("0.80"),
            drawdown=Decimal("-0.01"),
        )