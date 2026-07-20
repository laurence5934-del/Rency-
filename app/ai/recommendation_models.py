from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Recommendation(StrEnum):
    """
    Standard AI recommendation categories.
    """

    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    WATCH = "WATCH"
    HOLD = "HOLD"
    SELL = "SELL"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(member.value for member in cls)

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.values()


@dataclass(frozen=True)
class RecommendationReport:
    """
    Complete AI recommendation output.
    """

    symbol: str
    recommendation: Recommendation
    confidence: float
    overall_score: float

    strengths: tuple[str, ...] = field(default_factory=tuple)
    weaknesses: tuple[str, ...] = field(default_factory=tuple)
    risks: tuple[str, ...] = field(default_factory=tuple)
    suggested_actions: tuple[str, ...] = field(default_factory=tuple)

    @property
    def summary(self) -> str:
        return (
            f"{self.symbol}: "
            f"{self.recommendation.value} "
            f"({self.confidence:.1f}% confidence)"
        )