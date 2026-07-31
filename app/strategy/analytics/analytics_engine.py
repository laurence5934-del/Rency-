from __future__ import annotations

from app.strategy.backtesting.models import BacktestResult

from .models import AnalyticsReport, ReturnMetrics
from .performance import PerformanceAnalyzer
from .returns import ReturnAnalyzer
from .risk import RiskAnalyzer


class PerformanceAnalyticsEngine:
    """Central orchestrator for enterprise performance analytics."""

    def __init__(
        self,
        return_analyzer: ReturnAnalyzer | None = None,
        performance_analyzer: PerformanceAnalyzer | None = None,
        risk_analyzer: RiskAnalyzer | None = None,
    ) -> None:
        self._return_analyzer = return_analyzer or ReturnAnalyzer()
        self._performance_analyzer = (
            performance_analyzer or PerformanceAnalyzer()
        )
        self._risk_analyzer = risk_analyzer or RiskAnalyzer()

    def analyze_returns(
        self,
        result: BacktestResult,
    ) -> ReturnMetrics:
        return self._return_analyzer.analyze(result)

    def analyze(
        self,
        result: BacktestResult,
    ) -> AnalyticsReport:
        return AnalyticsReport(
            returns=self._return_analyzer.analyze(result),
            performance=self._performance_analyzer.analyze(result),
            risk=self._risk_analyzer.analyze(result),
        )