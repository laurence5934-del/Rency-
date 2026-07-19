from __future__ import annotations

import pytest

from app.scanner.scanner_models import ScanResult, ScanSummary
from app.watchlist.watchlist_builder import WatchlistBuilder
from app.watchlist.watchlist_config import WatchlistConfig


def make_result(
    symbol: str,
    total_score: float,
    *,
    qualified: bool = True,
    last_price: float = 100.0,
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


def make_summary(
    results: list[ScanResult],
) -> ScanSummary:
    return ScanSummary(
        total_symbols=len(results),
        qualified_symbols=sum(
            1
            for result in results
            if result.qualified
        ),
        results=results,
    )


def test_builder_returns_ranked_watchlist() -> None:
    summary = make_summary(
        [
            make_result("MSFT", 72.0),
            make_result("AAPL", 88.0),
            make_result("NVDA", 81.0),
        ]
    )

    builder = WatchlistBuilder(
        WatchlistConfig(
            min_total_score=60.0,
            max_symbols=10,
        )
    )

    watchlist = builder.build(
        summary,
        name="Morning Scan",
    )

    assert watchlist.name == "Morning Scan"
    assert watchlist.symbols == (
        "AAPL",
        "NVDA",
        "MSFT",
    )

    assert [
        entry.rank
        for entry in watchlist.entries
    ] == [1, 2, 3]


def test_builder_respects_max_symbols() -> None:
    summary = make_summary(
        [
            make_result("AAPL", 90.0),
            make_result("MSFT", 85.0),
            make_result("NVDA", 80.0),
        ]
    )

    builder = WatchlistBuilder(
        WatchlistConfig(
            min_total_score=0.0,
            max_symbols=2,
        )
    )

    watchlist = builder.build(summary)

    assert watchlist.symbol_count == 2
    assert watchlist.symbols == (
        "AAPL",
        "MSFT",
    )


def test_builder_excludes_scores_below_threshold() -> None:
    summary = make_summary(
        [
            make_result("AAPL", 80.0),
            make_result("MSFT", 59.0),
        ]
    )

    builder = WatchlistBuilder(
        WatchlistConfig(
            min_total_score=60.0,
        )
    )

    watchlist = builder.build(summary)

    assert watchlist.symbols == ("AAPL",)


def test_builder_excludes_unqualified_results() -> None:
    summary = make_summary(
        [
            make_result(
                "AAPL",
                80.0,
                qualified=True,
            ),
            make_result(
                "MSFT",
                80.0,
                qualified=False,
            ),
        ]
    )

    builder = WatchlistBuilder(
        WatchlistConfig(
            min_total_score=60.0,
            include_unqualified=False,
        )
    )

    watchlist = builder.build(summary)

    assert watchlist.symbols == ("AAPL",)


def test_builder_can_include_unqualified_results() -> None:
    summary = make_summary(
        [
            make_result(
                "AAPL",
                80.0,
                qualified=False,
            )
        ]
    )

    builder = WatchlistBuilder(
        WatchlistConfig(
            min_total_score=60.0,
            include_unqualified=True,
        )
    )

    watchlist = builder.build(summary)

    assert watchlist.symbols == ("AAPL",)


def test_builder_excludes_failed_results() -> None:
    summary = make_summary(
        [
            make_result("AAPL", 80.0),
            make_result(
                "FAIL",
                80.0,
                reasons=[
                    "Scan failed: ConnectionError: unavailable"
                ],
            ),
        ]
    )

    builder = WatchlistBuilder(
        WatchlistConfig(
            min_total_score=60.0,
            include_failed=False,
        )
    )

    watchlist = builder.build(summary)

    assert watchlist.symbols == ("AAPL",)


def test_builder_preserves_source_symbol_count() -> None:
    summary = make_summary(
        [
            make_result("AAPL", 80.0),
            make_result(
                "MSFT",
                20.0,
                qualified=False,
            ),
        ]
    )

    builder = WatchlistBuilder()

    watchlist = builder.build(summary)

    assert watchlist.source_symbol_count == 2
    assert watchlist.symbol_count == 1


def test_config_rejects_invalid_score() -> None:
    with pytest.raises(
        ValueError,
        match="between 0 and 100",
    ):
        WatchlistConfig(
            min_total_score=101.0
        )


def test_config_rejects_invalid_max_symbols() -> None:
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        WatchlistConfig(
            max_symbols=0
        )


def test_builder_requires_scan_summary() -> None:
    builder = WatchlistBuilder()

    with pytest.raises(
        TypeError,
        match="ScanSummary",
    ):
        builder.build([])  # type: ignore[arg-type]