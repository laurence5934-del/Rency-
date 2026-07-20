from __future__ import annotations

from datetime import datetime

from app.backtesting.backtest_models import EquityPoint


class EquityCurveBuilder:
    """
    Builds and manages an ordered equity curve.

    This class is intentionally lightweight so it can
    be reused by backtesting, reporting, dashboards,
    and future visualization modules.
    """

    def __init__(self) -> None:
        self._points: list[EquityPoint] = []

    def add(
        self,
        timestamp: datetime,
        equity: float,
    ) -> None:
        """
        Adds a new equity point.
        """

        self._points.append(
            EquityPoint(
                timestamp=timestamp,
                equity=equity,
            )
        )

    def build(self) -> list[EquityPoint]:
        """
        Returns a copy of the completed equity curve.
        """

        return list(self._points)

    def clear(self) -> None:
        """
        Removes all equity points.
        """

        self._points.clear()

    @property
    def count(self) -> int:
        return len(self._points)

    def latest(self) -> EquityPoint | None:
        if not self._points:
            return None

        return self._points[-1]

    def first(self) -> EquityPoint | None:
        if not self._points:
            return None

        return self._points[0]

    def max_equity(self) -> float:
        if not self._points:
            return 0.0

        return max(
            point.equity
            for point in self._points
        )

    def min_equity(self) -> float:
        if not self._points:
            return 0.0

        return min(
            point.equity
            for point in self._points
        )

    def highest_point(self) -> EquityPoint | None:
        if not self._points:
            return None

        return max(
            self._points,
            key=lambda point: point.equity,
        )

    def lowest_point(self) -> EquityPoint | None:
        if not self._points:
            return None

        return min(
            self._points,
            key=lambda point: point.equity,
        )