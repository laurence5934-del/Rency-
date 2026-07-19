from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class WatchlistEntry:
    """One ranked symbol selected for a trading watchlist."""

    rank: int
    symbol: str
    last_price: float
    total_score: float
    qualified: bool
    trend_score: float = 0.0
    momentum_score: float = 0.0
    volume_score: float = 0.0
    breakout_score: float = 0.0
    risk_score: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.rank <= 0:
            raise ValueError(
                "rank must be greater than zero."
            )

        if not self.symbol.strip():
            raise ValueError(
                "symbol cannot be empty."
            )

        if self.last_price < 0:
            raise ValueError(
                "last_price cannot be negative."
            )

        if self.total_score < 0:
            raise ValueError(
                "total_score cannot be negative."
            )


@dataclass(frozen=True, slots=True)
class Watchlist:
    """A generated collection of ranked watchlist entries."""

    name: str
    entries: tuple[WatchlistEntry, ...]
    source_symbol_count: int
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError(
                "Watchlist name cannot be empty."
            )

        if self.source_symbol_count < 0:
            raise ValueError(
                "source_symbol_count cannot be negative."
            )

    @property
    def symbol_count(self) -> int:
        return len(self.entries)

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(
            entry.symbol
            for entry in self.entries
        )