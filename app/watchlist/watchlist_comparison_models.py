from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class WatchlistEntryChange:
    """
    Describes how one symbol changed between two watchlists.
    """

    symbol: str

    previous_rank: int | None
    current_rank: int | None

    previous_score: float | None
    current_score: float | None

    previous_price: float | None
    current_price: float | None

    status: str

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError(
                "symbol cannot be empty."
            )

        allowed_statuses = {
            "added",
            "removed",
            "unchanged",
            "changed",
        }

        if self.status not in allowed_statuses:
            raise ValueError(
                "status must be one of: "
                "added, removed, unchanged, changed."
            )

    @property
    def rank_change(self) -> int | None:
        """
        Positive means the symbol improved in rank.

        Example:
        previous rank 5, current rank 2
        rank_change = 3
        """
        if (
            self.previous_rank is None
            or self.current_rank is None
        ):
            return None

        return self.previous_rank - self.current_rank

    @property
    def score_change(self) -> float | None:
        if (
            self.previous_score is None
            or self.current_score is None
        ):
            return None

        return self.current_score - self.previous_score

    @property
    def price_change(self) -> float | None:
        if (
            self.previous_price is None
            or self.current_price is None
        ):
            return None

        return self.current_price - self.previous_price


@dataclass(frozen=True, slots=True)
class WatchlistComparison:
    """
    Complete comparison between an earlier and later watchlist.
    """

    previous_name: str
    current_name: str

    changes: tuple[WatchlistEntryChange, ...]

    previous_symbol_count: int
    current_symbol_count: int

    compared_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.previous_name.strip():
            raise ValueError(
                "previous_name cannot be empty."
            )

        if not self.current_name.strip():
            raise ValueError(
                "current_name cannot be empty."
            )

        if self.previous_symbol_count < 0:
            raise ValueError(
                "previous_symbol_count cannot be negative."
            )

        if self.current_symbol_count < 0:
            raise ValueError(
                "current_symbol_count cannot be negative."
            )

    @property
    def added(self) -> tuple[WatchlistEntryChange, ...]:
        return tuple(
            change
            for change in self.changes
            if change.status == "added"
        )

    @property
    def removed(self) -> tuple[WatchlistEntryChange, ...]:
        return tuple(
            change
            for change in self.changes
            if change.status == "removed"
        )

    @property
    def changed(self) -> tuple[WatchlistEntryChange, ...]:
        return tuple(
            change
            for change in self.changes
            if change.status == "changed"
        )

    @property
    def unchanged(self) -> tuple[WatchlistEntryChange, ...]:
        return tuple(
            change
            for change in self.changes
            if change.status == "unchanged"
        )

    @property
    def added_symbols(self) -> tuple[str, ...]:
        return tuple(
            change.symbol
            for change in self.added
        )

    @property
    def removed_symbols(self) -> tuple[str, ...]:
        return tuple(
            change.symbol
            for change in self.removed
        )