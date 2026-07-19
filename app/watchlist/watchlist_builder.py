from __future__ import annotations

from app.scanner.scanner_models import ScanResult, ScanSummary
from app.watchlist.watchlist_config import WatchlistConfig
from app.watchlist.watchlist_models import (
    Watchlist,
    WatchlistEntry,
)


class WatchlistBuilder:
    """
    Build ranked watchlists from MarketScanner results.

    The builder is read-only. It does not place orders or modify
    portfolio positions.
    """

    def __init__(
        self,
        config: WatchlistConfig | None = None,
    ) -> None:
        self.config = config or WatchlistConfig()

    def build(
        self,
        scan_summary: ScanSummary,
        *,
        name: str = "AI Watchlist",
    ) -> Watchlist:
        if not isinstance(scan_summary, ScanSummary):
            raise TypeError(
                "scan_summary must be a ScanSummary."
            )

        filtered_results = [
            result
            for result in scan_summary.results
            if self._should_include(result)
        ]

        ranked_results = sorted(
            filtered_results,
            key=lambda result: (
                -result.total_score,
                result.symbol,
            ),
        )

        selected_results = ranked_results[
            : self.config.max_symbols
        ]

        entries = tuple(
            self._create_entry(
                rank=rank,
                result=result,
            )
            for rank, result in enumerate(
                selected_results,
                start=1,
            )
        )

        return Watchlist(
            name=name.strip(),
            entries=entries,
            source_symbol_count=scan_summary.total_symbols,
        )

    def _should_include(
        self,
        result: ScanResult,
    ) -> bool:
        failed = self._is_failed_result(result)

        if failed and not self.config.include_failed:
            return False

        if (
            not result.qualified
            and not self.config.include_unqualified
        ):
            return False

        return (
            result.total_score
            >= self.config.min_total_score
        )

    @staticmethod
    def _is_failed_result(
        result: ScanResult,
    ) -> bool:
        return any(
            reason.lower().startswith("scan failed:")
            for reason in result.reasons
        )

    @staticmethod
    def _create_entry(
        *,
        rank: int,
        result: ScanResult,
    ) -> WatchlistEntry:
        return WatchlistEntry(
            rank=rank,
            symbol=result.symbol,
            last_price=result.last_price,
            total_score=result.total_score,
            qualified=result.qualified,
            trend_score=result.trend_score,
            momentum_score=result.momentum_score,
            volume_score=result.volume_score,
            breakout_score=result.breakout_score,
            risk_score=result.risk_score,
            reasons=tuple(result.reasons),
        )