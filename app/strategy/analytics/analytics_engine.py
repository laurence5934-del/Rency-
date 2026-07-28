from __future__ import annotations

from app.strategy.backtesting.models import BacktestResult

from .models import ReturnMetrics
from .returns import ReturnAnalyzer


class PerformanceAnalyticsEngine:
    """Central orchestrator for enterprise performance analytics."""

    def __init__(
        self,
        return_analyzer: ReturnAnalyzer | None = None,
    ) -> None:
        self._return_analyzer = return_analyzer or ReturnAnalyzer()

    def analyze_returns(
        self,
        result: BacktestResult,
    ) -> ReturnMetrics:
        return self._return_analyzer.analyze(result)