from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PerformanceMetrics:
    sharpe_ratio: Decimal = Decimal("0")
    sortino_ratio: Decimal = Decimal("0")