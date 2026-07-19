from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.watchlist.watchlist_models import Watchlist


@dataclass(frozen=True, slots=True)
class WatchlistSnapshot:
    """
    Immutable snapshot of a watchlist at a point in time.
    """

    watchlist: Watchlist

    snapshot_id: str = field(
        default_factory=lambda: uuid4().hex
    )

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    version: str = "9.4.5"

    notes: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.watchlist, Watchlist):
            raise TypeError(
                "watchlist must be a Watchlist."
            )

        if not self.snapshot_id.strip():
            raise ValueError(
                "snapshot_id cannot be empty."
            )

        if not self.version.strip():
            raise ValueError(
                "version cannot be empty."
            )

    @property
    def symbol_count(self) -> int:
        return self.watchlist.symbol_count

    @property
    def symbols(self) -> tuple[str, ...]:
        return self.watchlist.symbols

    @property
    def snapshot_date(self) -> str:
        return self.created_at.strftime("%Y-%m-%d")