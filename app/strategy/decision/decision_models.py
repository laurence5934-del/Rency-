from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")
_ONE = Decimal("1")


class DecisionAction(str, Enum):
    """Deployment action selected by the decision engine."""

    REJECT = "REJECT"
    IMPROVE = "IMPROVE"
    PAPER_TRADE = "PAPER_TRADE"
    LIVE_TRADE = "LIVE_TRADE"


@dataclass(frozen=True, slots=True)
class Decision:
    """Immutable deployment decision for an evaluated strategy."""

    action: DecisionAction
    confidence: Decimal
    reason: str
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.action, DecisionAction):
            raise TypeError(
                "action must be a DecisionAction"
            )

        if not isinstance(self.confidence, Decimal):
            raise TypeError(
                "confidence must be a Decimal"
            )

        if not _ZERO <= self.confidence <= _ONE:
            raise ValueError(
                "confidence must be between 0 and 1"
            )

        normalized_reason = self.reason.strip()

        if not normalized_reason:
            raise ValueError(
                "reason must not be empty"
            )

        object.__setattr__(
            self,
            "reason",
            normalized_reason,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )

    @property
    def approved(self) -> bool:
        """Return whether the decision permits strategy deployment."""

        return self.action in {
            DecisionAction.PAPER_TRADE,
            DecisionAction.LIVE_TRADE,
        }