from __future__ import annotations

import pytest

from app.watchlist.watchlist_comparator import WatchlistComparator
from app.watchlist.watchlist_models import (
    Watchlist,
    WatchlistEntry,
)


def make_entry(
    rank: int,
    symbol: str,
    score: float,
    *,
    price: float = 100.0,
) -> WatchlistEntry:
    return WatchlistEntry(
        rank=rank,
        symbol=symbol,
        last_price=price,
        total_score=score,
        qualified=True,
        trend_score=20.0,
        momentum_score=15.0,
        volume_score=10.0,
        breakout_score=10.0,
        risk_score=5.0,
        reasons=(),
    )


def make_watchlist(
    name: str,
    entries: list[WatchlistEntry],
) -> Watchlist:
    return Watchlist(
        name=name,
        entries=tuple(entries),
        source_symbol_count=len(entries),
    )


def test_identical_watchlists_are_unchanged() -> None:
    previous = make_watchlist(
        "Previous",
        [
            make_entry(1, "AAPL", 90),
            make_entry(2, "MSFT", 85),
        ],
    )

    current = make_watchlist(
        "Current",
        [
            make_entry(1, "AAPL", 90),
            make_entry(2, "MSFT", 85),
        ],
    )

    comparison = WatchlistComparator().compare(
        previous,
        current,
    )

    assert len(comparison.unchanged) == 2
    assert len(comparison.changed) == 0
    assert len(comparison.added) == 0
    assert len(comparison.removed) == 0


def test_added_symbol_detected() -> None:
    previous = make_watchlist(
        "Previous",
        [
            make_entry(1, "AAPL", 90),
        ],
    )

    current = make_watchlist(
        "Current",
        [
            make_entry(1, "AAPL", 90),
            make_entry(2, "NVDA", 82),
        ],
    )

    comparison = WatchlistComparator().compare(
        previous,
        current,
    )

    assert comparison.added_symbols == ("NVDA",)


def test_removed_symbol_detected() -> None:
    previous = make_watchlist(
        "Previous",
        [
            make_entry(1, "AAPL", 90),
            make_entry(2, "NVDA", 80),
        ],
    )

    current = make_watchlist(
        "Current",
        [
            make_entry(1, "AAPL", 90),
        ],
    )

    comparison = WatchlistComparator().compare(
        previous,
        current,
    )

    assert comparison.removed_symbols == ("NVDA",)


def test_rank_change_calculation() -> None:
    previous = make_watchlist(
        "Previous",
        [
            make_entry(3, "AAPL", 85),
        ],
    )

    current = make_watchlist(
        "Current",
        [
            make_entry(1, "AAPL", 85),
        ],
    )

    comparison = WatchlistComparator().compare(
        previous,
        current,
    )

    change = comparison.changed[0]

    assert change.rank_change == 2


def test_score_change_calculation() -> None:
    previous = make_watchlist(
        "Previous",
        [
            make_entry(1, "AAPL", 75),
        ],
    )

    current = make_watchlist(
        "Current",
        [
            make_entry(1, "AAPL", 82),
        ],
    )

    comparison = WatchlistComparator().compare(
        previous,
        current,
    )

    change = comparison.changed[0]

    assert change.score_change == 7


def test_price_change_calculation() -> None:
    previous = make_watchlist(
        "Previous",
        [
            make_entry(
                1,
                "AAPL",
                90,
                price=100,
            ),
        ],
    )

    current = make_watchlist(
        "Current",
        [
            make_entry(
                1,
                "AAPL",
                90,
                price=107,
            ),
        ],
    )

    comparison = WatchlistComparator().compare(
        previous,
        current,
    )

    change = comparison.changed[0]

    assert change.price_change == 7


def test_compare_requires_watchlists() -> None:
    comparator = WatchlistComparator()

    with pytest.raises(TypeError):
        comparator.compare([], [])  # type: ignore[arg-type]


def test_added_and_removed_counts() -> None:
    previous = make_watchlist(
        "Previous",
        [
            make_entry(1, "AAPL", 90),
        ],
    )

    current = make_watchlist(
        "Current",
        [
            make_entry(1, "MSFT", 92),
        ],
    )

    comparison = WatchlistComparator().compare(
        previous,
        current,
    )

    assert len(comparison.added) == 1
    assert len(comparison.removed) == 1


def test_comparison_symbol_counts() -> None:
    previous = make_watchlist(
        "Previous",
        [
            make_entry(1, "AAPL", 90),
        ],
    )

    current = make_watchlist(
        "Current",
        [
            make_entry(1, "AAPL", 90),
            make_entry(2, "MSFT", 85),
        ],
    )

    comparison = WatchlistComparator().compare(
        previous,
        current,
    )

    assert comparison.previous_symbol_count == 1
    assert comparison.current_symbol_count == 2


def test_changed_status_when_any_value_changes() -> None:
    previous = make_watchlist(
        "Previous",
        [
            make_entry(1, "AAPL", 90),
        ],
    )

    current = make_watchlist(
        "Current",
        [
            make_entry(1, "AAPL", 91),
        ],
    )

    comparison = WatchlistComparator().compare(
        previous,
        current,
    )

    assert comparison.changed[0].status == "changed"