from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.strategy.walk_forward.walk_forward_models import (
    WalkForwardReport,
    WalkForwardStatus,
    WalkForwardWindow,
    WalkForwardWindowResult,
)


def timestamp(day: int) -> datetime:
    return datetime(
        2025,
        1,
        day,
        tzinfo=timezone.utc,
    )


def window() -> WalkForwardWindow:
    return WalkForwardWindow(
        window_id="window-001",
        training_start=timestamp(1),
        training_end=timestamp(10),
        validation_start=timestamp(10),
        validation_end=timestamp(15),
    )


def window_result(
    *,
    passed: bool = True,
) -> WalkForwardWindowResult:
    return WalkForwardWindowResult(
        window=window(),
        training_score=Decimal("0.90"),
        validation_score=Decimal("0.80"),
        validation_return=Decimal("0.05"),
        validation_drawdown=Decimal("0.03"),
        passed=passed,
    )


def test_walk_forward_window() -> None:
    result = window()

    assert result.window_id == "window-001"
    assert result.training_end == result.validation_start


def test_window_id_is_normalized() -> None:
    result = WalkForwardWindow(
        window_id="  window-001  ",
        training_start=timestamp(1),
        training_end=timestamp(10),
        validation_start=timestamp(10),
        validation_end=timestamp(15),
    )

    assert result.window_id == "window-001"


def test_window_id_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="window_id must not be empty",
    ):
        WalkForwardWindow(
            window_id="   ",
            training_start=timestamp(1),
            training_end=timestamp(10),
            validation_start=timestamp(10),
            validation_end=timestamp(15),
        )


def test_training_window_must_be_ordered() -> None:
    with pytest.raises(
        ValueError,
        match="training_start must be earlier",
    ):
        WalkForwardWindow(
            window_id="window-001",
            training_start=timestamp(10),
            training_end=timestamp(1),
            validation_start=timestamp(10),
            validation_end=timestamp(15),
        )


def test_validation_window_must_be_ordered() -> None:
    with pytest.raises(
        ValueError,
        match="validation_start must be earlier",
    ):
        WalkForwardWindow(
            window_id="window-001",
            training_start=timestamp(1),
            training_end=timestamp(10),
            validation_start=timestamp(15),
            validation_end=timestamp(10),
        )


def test_training_and_validation_must_not_overlap() -> None:
    with pytest.raises(
        ValueError,
        match="must not overlap",
    ):
        WalkForwardWindow(
            window_id="window-001",
            training_start=timestamp(1),
            training_end=timestamp(12),
            validation_start=timestamp(10),
            validation_end=timestamp(15),
        )


def test_window_result() -> None:
    result = window_result()

    assert result.passed is True
    assert result.validation_score == Decimal("0.80")


@pytest.mark.parametrize(
    "score",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_training_score_must_be_between_zero_and_one(
    score: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="training_score must be between 0 and 1",
    ):
        WalkForwardWindowResult(
            window=window(),
            training_score=score,
            validation_score=Decimal("0.80"),
        )


@pytest.mark.parametrize(
    "score",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_validation_score_must_be_between_zero_and_one(
    score: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="validation_score must be between 0 and 1",
    ):
        WalkForwardWindowResult(
            window=window(),
            training_score=Decimal("0.90"),
            validation_score=score,
        )


def test_validation_drawdown_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="validation_drawdown must not be negative",
    ):
        WalkForwardWindowResult(
            window=window(),
            training_score=Decimal("0.90"),
            validation_score=Decimal("0.80"),
            validation_drawdown=Decimal("-0.01"),
        )


def test_report_converts_collections_to_tuples() -> None:
    result = WalkForwardReport(
        status=WalkForwardStatus.COMPLETED,
        windows=[window_result()],
        robustness_score=Decimal("0.80"),
        pass_rate=Decimal("1"),
        warnings=["Validation warning."],
    )

    assert result.windows == (window_result(),)
    assert result.warnings == (
        "Validation warning.",
    )


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        WalkForwardReport(
            status=WalkForwardStatus.FAILED,
        )


def test_completed_report_cannot_include_error() -> None:
    with pytest.raises(
        ValueError,
        match="only failed reports may include an error",
    ):
        WalkForwardReport(
            status=WalkForwardStatus.COMPLETED,
            error="Unexpected error.",
        )


@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_robustness_score_must_be_between_zero_and_one(
    value: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="robustness_score must be between 0 and 1",
    ):
        WalkForwardReport(
            status=WalkForwardStatus.COMPLETED,
            robustness_score=value,
        )


@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_pass_rate_must_be_between_zero_and_one(
    value: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="pass_rate must be between 0 and 1",
    ):
        WalkForwardReport(
            status=WalkForwardStatus.COMPLETED,
            pass_rate=value,
        )


def test_models_are_immutable() -> None:
    result = window()

    with pytest.raises(FrozenInstanceError):
        result.window_id = "changed"