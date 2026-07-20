from __future__ import annotations

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
        """
        Return all recommendation values.
        """
        return tuple(member.value for member in cls)

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """
        Return True if value is a valid recommendation.
        """
        return value in cls.values()