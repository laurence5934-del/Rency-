from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WatchlistConfig:
    """
    Configuration for creating ranked trading watchlists.

    The configuration controls the minimum scanner score required,
    the maximum number of symbols retained, and whether failed or
    unqualified scanner results should be included.
    """

    min_total_score: float = 60.0
    max_symbols: int = 20
    include_unqualified: bool = False
    include_failed: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.min_total_score <= 100:
            raise ValueError(
                "min_total_score must be between 0 and 100."
            )

        if self.max_symbols <= 0:
            raise ValueError(
                "max_symbols must be greater than zero."
            )