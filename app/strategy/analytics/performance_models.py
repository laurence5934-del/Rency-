from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PerformanceMetrics:
    """Risk-adjusted performance statistics."""

    sharpe_ratio: Decimal = Decimal("0")