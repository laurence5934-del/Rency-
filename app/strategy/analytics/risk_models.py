from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RiskMetrics:
    max_drawdown: Decimal
    drawdown_duration: int = 0