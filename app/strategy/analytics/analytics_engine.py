from __future__ import annotations

from app.strategy.backtesting.models import BacktestResult

from .expectancy import ExpectancyAnalyzer
from .models import AnalyticsReport, ReturnMetrics
from .performance import PerformanceAnalyzer
from .returns import ReturnAnalyzer
from .risk import RiskAnalyzer
from .strategy_quality import StrategyQualityAnalyzer


class PerformanceAnalyticsEngine:
    """Central orchestrator for enterprise performance analytics."""

    def __init__(
        self,
        return_analyzer: ReturnAnalyzer | None = None,
        performance_analyzer: PerformanceAnalyzer | None = None,
        risk_analyzer: RiskAnalyzer | None = None,
        expectancy_analyzer: ExpectancyAnalyzer | None = None,
        strategy_quality_analyzer: StrategyQualityAnalyzer | None = None,
    ) -> None:
        self._return_analyzer = (
            return_analyzer or ReturnAnalyzer()
        )
        self._performance_analyzer = (
            performance_analyzer or PerformanceAnalyzer()
        )
        self._risk_analyzer = (
            risk_analyzer or RiskAnalyzer()
        )
        self._expectancy_analyzer = (
            expectancy_analyzer or ExpectancyAnalyzer()
        )
        self._strategy_quality_analyzer = (
            strategy_quality_analyzer
            or StrategyQualityAnalyzer()
        )

    def analyze_returns(
        self,
        result: BacktestResult,
    ) -> ReturnMetrics:
        return self._return_analyzer.analyze(result)

    def analyze(
        self,
        result: BacktestResult,
    ) -> AnalyticsReport:
        return_metrics = self._return_analyzer.analyze(
            result
        )
        performance_metrics = (
            self._performance_analyzer.analyze(result)
        )
        risk_metrics = self._risk_analyzer.analyze(
            result
        )
        expectancy_metrics = (
            self._expectancy_analyzer.analyze(
                result,
                max_drawdown=risk_metrics.max_drawdown,
            )
        )
        strategy_quality_metrics = (
            self._strategy_quality_analyzer.analyze(
                result
            )
        )

        return AnalyticsReport(
            returns=return_metrics,
            performance=performance_metrics,
            risk=risk_metrics,
            expectancy=expectancy_metrics,
            strategy_quality=strategy_quality_metrics,
        )