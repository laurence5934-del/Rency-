from datetime import datetime

from app.backtesting.equity_curve import EquityCurveBuilder


def test_empty_builder():
    builder = EquityCurveBuilder()

    assert builder.count == 0
    assert builder.build() == []
    assert builder.latest() is None
    assert builder.first() is None


def test_add_points():
    builder = EquityCurveBuilder()

    builder.add(datetime(2026, 1, 1), 100000)
    builder.add(datetime(2026, 1, 2), 101500)

    assert builder.count == 2


def test_build_returns_copy():
    builder = EquityCurveBuilder()

    builder.add(datetime(2026, 1, 1), 100000)

    curve = builder.build()

    curve.append(curve[0])

    assert builder.count == 1


def test_first_and_latest():
    builder = EquityCurveBuilder()

    builder.add(datetime(2026, 1, 1), 100000)
    builder.add(datetime(2026, 1, 2), 105000)

    assert builder.first().equity == 100000
    assert builder.latest().equity == 105000


def test_max_and_min_equity():
    builder = EquityCurveBuilder()

    builder.add(datetime(2026, 1, 1), 100000)
    builder.add(datetime(2026, 1, 2), 120000)
    builder.add(datetime(2026, 1, 3), 90000)

    assert builder.max_equity() == 120000
    assert builder.min_equity() == 90000


def test_highest_and_lowest_point():
    builder = EquityCurveBuilder()

    builder.add(datetime(2026, 1, 1), 100000)
    builder.add(datetime(2026, 1, 2), 125000)
    builder.add(datetime(2026, 1, 3), 95000)

    assert builder.highest_point().equity == 125000
    assert builder.lowest_point().equity == 95000


def test_clear():
    builder = EquityCurveBuilder()

    builder.add(datetime(2026, 1, 1), 100000)
    builder.add(datetime(2026, 1, 2), 110000)

    builder.clear()

    assert builder.count == 0
    assert builder.build() == []