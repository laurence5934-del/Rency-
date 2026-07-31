from dataclasses import dataclass
from decimal import Decimal

from app.strategy.analytics.analytics_engine import (
    PerformanceAnalyticsEngine,
)
from app.strategy.analytics.models import (
    AnalyticsReport,
    ReturnMetrics,
)
from app.strategy.analytics.performance_models import (
    PerformanceMetrics,
)
from app.strategy.analytics.risk_models import RiskMetrics


@dataclass
class StubAnalyzer:
    result: object

    def analyze(self, backtest_result):
        return self.result


def test_analyze_combines_all_analytics_results():
    backtest_result = object()

    return_metrics = ReturnMetrics(
        initial_capital=Decimal("10000"),
        final_equity=Decimal("11000"),
        net_profit=Decimal("1000"),
        total_return=Decimal("0.10"),
        annualized_return=Decimal("0.10"),
        cagr=Decimal("0.10"),
    )

    performance_metrics = PerformanceMetrics(
        sharpe_ratio=Decimal("1.5"),
        sortino_ratio=Decimal("2"),
        calmar_ratio=Decimal("1.25"),
        profit_factor=Decimal("1.8"),
        win_rate=Decimal("60"),
    )

    risk_metrics = RiskMetrics(
        max_drawdown=Decimal("0.08"),
        drawdown_duration=3,
        volatility=Decimal("0.12"),
    )

    engine = PerformanceAnalyticsEngine(
        return_analyzer=StubAnalyzer(return_metrics),
        performance_analyzer=StubAnalyzer(performance_metrics),
        risk_analyzer=StubAnalyzer(risk_metrics),
    )

    report = engine.analyze(backtest_result)

    assert report == AnalyticsReport(
        returns=return_metrics,
        performance=performance_metrics,
        risk=risk_metrics,
    )