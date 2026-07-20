from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True, slots=True)
class RankingResult:
    """
    AI ranking result for a single symbol.
    """

    symbol: str

    overall_score: float

    confidence: float

    recommendation: str

    trend_score: float

    momentum_score: float

    volume_score: float

    breakout_score: float

    risk_score: float

    explanations: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError(
                "symbol cannot be empty."
            )

        if not 0.0 <= self.confidence <= 100.0:
            raise ValueError(
                "confidence must be between 0 and 100."
            )

        if self.overall_score < 0:
            raise ValueError(
                "overall_score cannot be negative."
            )

        allowed = {
            "STRONG_BUY",
            "BUY",
            "WATCH",
            "HOLD",
            "SELL",
        }

        if self.recommendation not in allowed:
            raise ValueError(
                "Invalid recommendation."
            )


@dataclass(frozen=True, slots=True)
class RankingSummary:
    """
    Collection of ranked symbols.
    """

    results: Tuple[RankingResult, ...]

    @property
    def symbols(self) -> Tuple[str, ...]:
        return tuple(
            result.symbol
            for result in self.results
        )

    @property
    def strongest(self) -> RankingResult | None:
        if not self.results:
            return None

        return max(
            self.results,
            key=lambda result: result.overall_score,
        )

    @property
    def average_score(self) -> float:
        if not self.results:
            return 0.0

        return (
            sum(
                result.overall_score
                for result in self.results
            )
            / len(self.results)
        )