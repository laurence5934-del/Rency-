from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PerformanceMetrics:
    sharpe_ratio: Decimal = Decimal("0")
    sortino_ratio: Decimal = Decimal("0")
    calmar_ratio: Decimal = Decimal("0")
    profit_factor: Decimal = Decimal("0")
    win_rate: Decimal = Decimal("0")