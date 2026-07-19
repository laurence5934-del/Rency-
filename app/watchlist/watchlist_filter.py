from __future__ import annotations

from app.scanner.scanner_models import ScanResult
from app.watchlist.watchlist_filter_config import WatchlistFilterConfig


class WatchlistFilter:
    """
    Filters MarketScanner ScanResults before they are
    ranked into a Watchlist.
    """

    def __init__(
        self,
        config: WatchlistFilterConfig | None = None,
    ) -> None:
        self.config = config or WatchlistFilterConfig()

    def filter(
        self,
        results: list[ScanResult],
    ) -> list[ScanResult]:
        """
        Apply every configured filter while preserving
        the original ordering.
        """
        return [
            result
            for result in results
            if self._include(result)
        ]

    def _include(
        self,
        result: ScanResult,
    ) -> bool:

        if (
            result.total_score < self.config.min_score
            or result.total_score > self.config.max_score
        ):
            return False

        if (
            result.last_price < self.config.min_price
            or result.last_price > self.config.max_price
        ):
            return False

        if (
            not result.qualified
            and not self.config.include_unqualified
        ):
            return False

        failed = any(
            reason.lower().startswith("scan failed:")
            for reason in result.reasons
        )

        if failed and not self.config.include_failed:
            return False

        if (
            self.config.include_symbols
            and result.symbol.upper()
            not in self.config.include_symbols
        ):
            return False

        if (
            result.symbol.upper()
            in self.config.exclude_symbols
        ):
            return False

        return True