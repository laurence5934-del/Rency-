from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ExpectancyMetrics:
    """Expectancy and trade-outcome analytics."""

    average_win: Decimal = Decimal("0")
    average_loss: Decimal = Decimal("0")
    payoff_ratio: Decimal = Decimal("0")
    expectancy: Decimal = Decimal("0")
    expectancy_percent: Decimal = Decimal("0")
    recovery_factor: Decimal = Decimal("0")