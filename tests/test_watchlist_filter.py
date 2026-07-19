from __future__ import annotations

import pytest

from app.scanner.scanner_models import ScanResult
from app.watchlist.watchlist_filter import WatchlistFilter
from app.watchlist.watchlist_filter_config import (
    WatchlistFilterConfig,
)


def make_result(
    symbol: str,
    total_score: float = 75.0,
    *,
    last_price: float = 100.0,
    qualified: bool = True,
    reasons: list[str] | None = None,
) -> ScanResult:
    return ScanResult(
        symbol=symbol,
        last_price=last_price,
        total_score=total_score,
        qualified=qualified,
        trend_score=20.0,
        momentum_score=15.0,
        volume_score=10.0,
        breakout_score=10.0,
        risk_score=5.0,
        reasons=reasons or [],
    )


def test_filter_keeps_valid_result() -> None:
    watchlist_filter = WatchlistFilter()

    results = watchlist_filter.filter(
        [make_result("AAPL")]
    )

    assert [result.symbol for result in results] == ["AAPL"]


def test_filter_excludes_score_below_minimum() -> None:
    watchlist_filter = WatchlistFilter(
        WatchlistFilterConfig(
            min_score=70.0,
        )
    )

    results = watchlist_filter.filter(
        [
            make_result("AAPL", 80.0),
            make_result("MSFT", 69.0),
        ]
    )

    assert [result.symbol for result in results] == ["AAPL"]


def test_filter_excludes_score_above_maximum() -> None:
    watchlist_filter = WatchlistFilter(
        WatchlistFilterConfig(
            max_score=80.0,
        )
    )

    results = watchlist_filter.filter(
        [
            make_result("AAPL", 80.0),
            make_result("MSFT", 81.0),
        ]
    )

    assert [result.symbol for result in results] == ["AAPL"]


def test_filter_score_boundaries_are_inclusive() -> None:
    watchlist_filter = WatchlistFilter(
        WatchlistFilterConfig(
            min_score=60.0,
            max_score=80.0,
        )
    )

    results = watchlist_filter.filter(
        [
            make_result("AAPL", 60.0),
            make_result("MSFT", 80.0),
        ]
    )

    assert [result.symbol for result in results] == [
        "AAPL",
        "MSFT",
    ]


def test_filter_excludes_price_below_minimum() -> None:
    watchlist_filter = WatchlistFilter(
        WatchlistFilterConfig(
            min_price=25.0,
        )
    )

    results = watchlist_filter.filter(
        [
            make_result("AAPL", last_price=50.0),
            make_result("PENNY", last_price=24.99),
        ]
    )

    assert [result.symbol for result in results] == ["AAPL"]


def test_filter_excludes_price_above_maximum() -> None:
    watchlist_filter = WatchlistFilter(
        WatchlistFilterConfig(
            max_price=200.0,
        )
    )

    results = watchlist_filter.filter(
        [
            make_result("AAPL", last_price=200.0),
            make_result("HIGH", last_price=200.01),
        ]
    )

    assert [result.symbol for result in results] == ["AAPL"]


def test_filter_excludes_unqualified_by_default() -> None:
    watchlist_filter = WatchlistFilter()

    results = watchlist_filter.filter(
        [
            make_result(
                "AAPL",
                qualified=False,
            )
        ]
    )

    assert results == []


def test_filter_can_include_unqualified() -> None:
    watchlist_filter = WatchlistFilter(
        WatchlistFilterConfig(
            include_unqualified=True,
        )
    )

    results = watchlist_filter.filter(
        [
            make_result(
                "AAPL",
                qualified=False,
            )
        ]
    )

    assert [result.symbol for result in results] == ["AAPL"]


def test_filter_excludes_failed_by_default() -> None:
    watchlist_filter = WatchlistFilter()

    results = watchlist_filter.filter(
        [
            make_result(
                "FAIL",
                reasons=[
                    "Scan failed: ConnectionError: unavailable"
                ],
            )
        ]
    )

    assert results == []


def test_filter_can_include_failed() -> None:
    watchlist_filter = WatchlistFilter(
        WatchlistFilterConfig(
            include_failed=True,
        )
    )

    results = watchlist_filter.filter(
        [
            make_result(
                "FAIL",
                reasons=[
                    "Scan failed: ConnectionError: unavailable"
                ],
            )
        ]
    )

    assert [result.symbol for result in results] == ["FAIL"]


def test_filter_respects_include_symbols() -> None:
    watchlist_filter = WatchlistFilter(
        WatchlistFilterConfig(
            include_symbols=frozenset(
                {
                    "AAPL",
                    "NVDA",
                }
            ),
        )
    )

    results = watchlist_filter.filter(
        [
            make_result("AAPL"),
            make_result("MSFT"),
            make_result("NVDA"),
        ]
    )

    assert [result.symbol for result in results] == [
        "AAPL",
        "NVDA",
    ]


def test_filter_include_symbols_are_normalized() -> None:
    config = WatchlistFilterConfig(
        include_symbols=frozenset(
            {
                " aapl ",
                "nvda",
            }
        ),
    )

    assert config.include_symbols == frozenset(
        {
            "AAPL",
            "NVDA",
        }
    )


def test_filter_respects_exclude_symbols() -> None:
    watchlist_filter = WatchlistFilter(
        WatchlistFilterConfig(
            exclude_symbols=frozenset(
                {
                    "MSFT",
                }
            ),
        )
    )

    results = watchlist_filter.filter(
        [
            make_result("AAPL"),
            make_result("MSFT"),
        ]
    )

    assert [result.symbol for result in results] == ["AAPL"]


def test_exclude_symbols_take_priority_over_include_symbols() -> None:
    watchlist_filter = WatchlistFilter(
        WatchlistFilterConfig(
            include_symbols=frozenset(
                {
                    "AAPL",
                    "MSFT",
                }
            ),
            exclude_symbols=frozenset(
                {
                    "MSFT",
                }
            ),
        )
    )

    results = watchlist_filter.filter(
        [
            make_result("AAPL"),
            make_result("MSFT"),
        ]
    )

    assert [result.symbol for result in results] == ["AAPL"]


def test_filter_preserves_original_order() -> None:
    watchlist_filter = WatchlistFilter()

    results = watchlist_filter.filter(
        [
            make_result("NVDA"),
            make_result("AAPL"),
            make_result("MSFT"),
        ]
    )

    assert [result.symbol for result in results] == [
        "NVDA",
        "AAPL",
        "MSFT",
    ]


def test_config_rejects_invalid_minimum_score() -> None:
    with pytest.raises(
        ValueError,
        match="min_score must be between 0 and 100",
    ):
        WatchlistFilterConfig(
            min_score=-1.0,
        )


def test_config_rejects_invalid_maximum_score() -> None:
    with pytest.raises(
        ValueError,
        match="max_score must be between 0 and 100",
    ):
        WatchlistFilterConfig(
            max_score=101.0,
        )


def test_config_rejects_minimum_score_above_maximum() -> None:
    with pytest.raises(
        ValueError,
        match="min_score cannot exceed max_score",
    ):
        WatchlistFilterConfig(
            min_score=80.0,
            max_score=70.0,
        )


def test_config_rejects_negative_minimum_price() -> None:
    with pytest.raises(
        ValueError,
        match="min_price cannot be negative",
    ):
        WatchlistFilterConfig(
            min_price=-0.01,
        )


def test_config_rejects_maximum_price_below_minimum() -> None:
    with pytest.raises(
        ValueError,
        match="max_price cannot be less than min_price",
    ):
        WatchlistFilterConfig(
            min_price=100.0,
            max_price=99.0,
        )