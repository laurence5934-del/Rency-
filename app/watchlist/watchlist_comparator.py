from __future__ import annotations

from app.watchlist.watchlist_comparison_models import (
    WatchlistComparison,
    WatchlistEntryChange,
)
from app.watchlist.watchlist_models import (
    Watchlist,
    WatchlistEntry,
)


class WatchlistComparator:
    """
    Compare two watchlists and describe every symbol change.
    """

    def compare(
        self,
        previous: Watchlist,
        current: Watchlist,
    ) -> WatchlistComparison:

        if not isinstance(previous, Watchlist):
            raise TypeError(
                "previous must be a Watchlist."
            )

        if not isinstance(current, Watchlist):
            raise TypeError(
                "current must be a Watchlist."
            )

        previous_lookup = {
            entry.symbol: entry
            for entry in previous.entries
        }

        current_lookup = {
            entry.symbol: entry
            for entry in current.entries
        }

        symbols = sorted(
            set(previous_lookup) | set(current_lookup)
        )

        changes = tuple(
            self._compare_symbol(
                symbol,
                previous_lookup.get(symbol),
                current_lookup.get(symbol),
            )
            for symbol in symbols
        )

        return WatchlistComparison(
            previous_name=previous.name,
            current_name=current.name,
            changes=changes,
            previous_symbol_count=previous.symbol_count,
            current_symbol_count=current.symbol_count,
        )

    @staticmethod
    def _compare_symbol(
        symbol: str,
        previous: WatchlistEntry | None,
        current: WatchlistEntry | None,
    ) -> WatchlistEntryChange:

        if previous is None:
            return WatchlistEntryChange(
                symbol=symbol,
                previous_rank=None,
                current_rank=current.rank,
                previous_score=None,
                current_score=current.total_score,
                previous_price=None,
                current_price=current.last_price,
                status="added",
            )

        if current is None:
            return WatchlistEntryChange(
                symbol=symbol,
                previous_rank=previous.rank,
                current_rank=None,
                previous_score=previous.total_score,
                current_score=None,
                previous_price=previous.last_price,
                current_price=None,
                status="removed",
            )

        status = "unchanged"

        if (
            previous.rank != current.rank
            or previous.total_score != current.total_score
            or previous.last_price != current.last_price
        ):
            status = "changed"

        return WatchlistEntryChange(
            symbol=symbol,
            previous_rank=previous.rank,
            current_rank=current.rank,
            previous_score=previous.total_score,
            current_score=current.total_score,
            previous_price=previous.last_price,
            current_price=current.last_price,
            status=status,
        )