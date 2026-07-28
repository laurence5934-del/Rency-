from decimal import Decimal

from .performance_models import PerformanceMetrics


class PerformanceAnalyzer:
    """Calculates risk-adjusted portfolio performance."""

    def analyze(self, result) -> PerformanceMetrics:
        return PerformanceMetrics(
            sharpe_ratio=Decimal("0")
        )