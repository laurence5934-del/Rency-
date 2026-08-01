from datetime import datetime, timezone

import pytest

from app.strategy.walk_forward.window_generator import (
    WalkForwardWindowGenerator,
)


def timestamp(day: int) -> datetime:
    return datetime(
        2025,
        1,
        day,
        tzinfo=timezone.utc,
    )


def test_generates_expected_windows() -> None:
    generator = WalkForwardWindowGenerator()

    windows = generator.generate(
        start_time=timestamp(1),
        end_time=timestamp(31),
        training_days=10,
        validation_days=5,
        step_days=5,
    )

    assert len(windows) == 4

    assert windows[0].window_id == "window-001"
    assert windows[0].training_start == timestamp(1)
    assert windows[0].training_end == timestamp(11)
    assert windows[0].validation_start == timestamp(11)
    assert windows[0].validation_end == timestamp(16)

    assert windows[1].window_id == "window-002"
    assert windows[1].training_start == timestamp(6)
    assert windows[1].training_end == timestamp(16)
    assert windows[1].validation_start == timestamp(16)
    assert windows[1].validation_end == timestamp(21)

    assert windows[3].window_id == "window-004"
    assert windows[3].training_start == timestamp(16)
    assert windows[3].validation_end == timestamp(31)


def test_returns_tuple() -> None:
    windows = WalkForwardWindowGenerator().generate(
        start_time=timestamp(1),
        end_time=timestamp(20),
        training_days=10,
        validation_days=5,
        step_days=5,
    )

    assert isinstance(windows, tuple)


def test_returns_empty_when_period_is_too_short() -> None:
    windows = WalkForwardWindowGenerator().generate(
        start_time=timestamp(1),
        end_time=timestamp(10),
        training_days=10,
        validation_days=5,
        step_days=5,
    )

    assert windows == ()


def test_step_can_equal_validation_window() -> None:
    windows = WalkForwardWindowGenerator().generate(
        start_time=timestamp(1),
        end_time=timestamp(31),
        training_days=10,
        validation_days=5,
        step_days=5,
    )

    assert windows[1].training_start == timestamp(6)


def test_step_can_be_larger_than_validation_window() -> None:
    windows = WalkForwardWindowGenerator().generate(
        start_time=timestamp(1),
        end_time=timestamp(31),
        training_days=10,
        validation_days=5,
        step_days=10,
    )

    assert len(windows) == 2
    assert windows[1].training_start == timestamp(11)


@pytest.mark.parametrize(
    "training_days",
    [0, -1],
)
def test_training_days_must_be_positive(
    training_days: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="training_days must be greater than zero",
    ):
        WalkForwardWindowGenerator().generate(
            start_time=timestamp(1),
            end_time=timestamp(31),
            training_days=training_days,
            validation_days=5,
            step_days=5,
        )


@pytest.mark.parametrize(
    "validation_days",
    [0, -1],
)
def test_validation_days_must_be_positive(
    validation_days: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="validation_days must be greater than zero",
    ):
        WalkForwardWindowGenerator().generate(
            start_time=timestamp(1),
            end_time=timestamp(31),
            training_days=10,
            validation_days=validation_days,
            step_days=5,
        )


@pytest.mark.parametrize(
    "step_days",
    [0, -1],
)
def test_step_days_must_be_positive(
    step_days: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="step_days must be greater than zero",
    ):
        WalkForwardWindowGenerator().generate(
            start_time=timestamp(1),
            end_time=timestamp(31),
            training_days=10,
            validation_days=5,
            step_days=step_days,
        )


def test_start_time_must_be_before_end_time() -> None:
    with pytest.raises(
        ValueError,
        match="start_time must be earlier than end_time",
    ):
        WalkForwardWindowGenerator().generate(
            start_time=timestamp(31),
            end_time=timestamp(1),
            training_days=10,
            validation_days=5,
            step_days=5,
        )


def test_times_must_be_timezone_aware() -> None:
    naive_start = datetime(2025, 1, 1)
    naive_end = datetime(2025, 1, 31)

    with pytest.raises(
        ValueError,
        match="must be timezone-aware",
    ):
        WalkForwardWindowGenerator().generate(
            start_time=naive_start,
            end_time=naive_end,
            training_days=10,
            validation_days=5,
            step_days=5,
        )