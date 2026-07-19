from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class WatchlistFilterConfig:
    """
    Configuration for filtering scanner results before
    building a watchlist.
    """

    min_score: float = 0.0
    max_score: float = 100.0

    min_price: float = 0.0
    max_price: float = float("inf")

    include_unqualified: bool = False
    include_failed: bool = False

    include_symbols: frozenset[str] = field(
        default_factory=frozenset
    )

    exclude_symbols: frozenset[str] = field(
        default_factory=frozenset
    )

    def __post_init__(self) -> None:
        if not 0 <= self.min_score <= 100:
            raise ValueError(
                "min_score must be between 0 and 100."
            )

        if not 0 <= self.max_score <= 100:
            raise ValueError(
                "max_score must be between 0 and 100."
            )

        if self.min_score > self.max_score:
            raise ValueError(
                "min_score cannot exceed max_score."
            )

        if self.min_price < 0:
            raise ValueError(
                "min_price cannot be negative."
            )

        if self.max_price < self.min_price:
            raise ValueError(
                "max_price cannot be less than min_price."
            )

        object.__setattr__(
            self,
            "include_symbols",
            frozenset(
                symbol.strip().upper()
                for symbol in self.include_symbols
            ),
        )

        object.__setattr__(
            self,
            "exclude_symbols",
            frozenset(
                symbol.strip().upper()
                for symbol in self.exclude_symbols
            ),
        )
    