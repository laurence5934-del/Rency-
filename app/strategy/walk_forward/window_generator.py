from __future__ import annotations

from datetime import datetime, timedelta

from .walk_forward_models import WalkForwardWindow


class WalkForwardWindowGenerator:
    """Builds deterministic rolling training and validation windows."""

    def generate(
        self,
        *,
        start_time: datetime,
        end_time: datetime,
        training_days: int,
        validation_days: int,
        step_days: int,
    ) -> tuple[WalkForwardWindow, ...]:
        self._validate_inputs(
            start_time=start_time,
            end_time=end_time,
            training_days=training_days,
            validation_days=validation_days,
            step_days=step_days,
        )

        windows: list[WalkForwardWindow] = []

        training_delta = timedelta(days=training_days)
        validation_delta = timedelta(days=validation_days)
        step_delta = timedelta(days=step_days)

        training_start = start_time
        window_number = 1

        while True:
            training_end = training_start + training_delta
            validation_start = training_end
            validation_end = validation_start + validation_delta

            if validation_end > end_time:
                break

            windows.append(
                WalkForwardWindow(
                    window_id=f"window-{window_number:03d}",
                    training_start=training_start,
                    training_end=training_end,
                    validation_start=validation_start,
                    validation_end=validation_end,
                )
            )

            training_start = training_start + step_delta
            window_number += 1

        return tuple(windows)

    @staticmethod
    def _validate_inputs(
        *,
        start_time: datetime,
        end_time: datetime,
        training_days: int,
        validation_days: int,
        step_days: int,
    ) -> None:
        if start_time >= end_time:
            raise ValueError(
                "start_time must be earlier than end_time"
            )

        if training_days <= 0:
            raise ValueError(
                "training_days must be greater than zero"
            )

        if validation_days <= 0:
            raise ValueError(
                "validation_days must be greater than zero"
            )

        if step_days <= 0:
            raise ValueError(
                "step_days must be greater than zero"
            )

        if start_time.tzinfo is None or end_time.tzinfo is None:
            raise ValueError(
                "start_time and end_time must be timezone-aware"
            )