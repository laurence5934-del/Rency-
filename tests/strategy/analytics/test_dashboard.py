from decimal import Decimal

from app.strategy.analytics.dashboard import (
    AnalyticsDashboardBuilder,
)
from app.strategy.analytics.expectancy_models import (
    ExpectancyMetrics,
)
from app.strategy.analytics.models import (
    AnalyticsReport,
    ReturnMetrics,
)
from app.strategy.analytics.performance_models import (
    PerformanceMetrics,
)
from app.strategy.analytics.risk_models import (
    RiskMetrics,
)
from app.strategy.analytics.strategy_quality_models import (
    StrategyQualityMetrics,
)


def test_build_creates_all_dashboard_sections():
    report = AnalyticsReport(
        returns=ReturnMetrics(
            initial_capital=Decimal("10000"),
            final_equity=Decimal("11000"),
            net_profit=Decimal("1000"),
            total_return=Decimal("0.10"),
            annualized_return=Decimal("0.10"),
            cagr=Decimal("0.10"),
        ),
        performance=PerformanceMetrics(
            sharpe_ratio=Decimal("1.5"),
            sortino_ratio=Decimal("2"),
            calmar_ratio=Decimal("1.25"),
            profit_factor=Decimal("1.8"),
            win_rate=Decimal("60"),
        ),
        risk=RiskMetrics(
            max_drawdown=Decimal("0.08"),
            drawdown_duration=3,
            volatility=Decimal("0.12"),
        ),
        expectancy=ExpectancyMetrics(
            average_win=Decimal("200"),
            average_loss=Decimal("100"),
            payoff_ratio=Decimal("2"),
            expectancy=Decimal("80"),
            expectancy_percent=Decimal("0.8"),
            recovery_factor=Decimal("4"),
        ),
        strategy_quality=StrategyQualityMetrics(
            system_quality_number=Decimal("2.1"),
            kelly_criterion=Decimal("0.25"),
            gain_to_pain_ratio=Decimal("3"),
            ulcer_index=Decimal("0.05"),
        ),
    )

    dashboard = AnalyticsDashboardBuilder().build(report)

    assert len(dashboard.sections) == 5

    assert dashboard.sections[0].title == "Returns"
    assert dashboard.sections[1].title == "Performance"
    assert dashboard.sections[2].title == "Risk"
    assert dashboard.sections[3].title == "Expectancy"
    assert dashboard.sections[4].title == "Strategy Quality"

    assert (
        dashboard.sections[0].metrics["Net Profit"]
        == "1000"
    )
    assert (
        dashboard.sections[1].metrics["Sharpe"]
        == "1.5"
    )
    assert (
        dashboard.sections[3].metrics["Recovery Factor"]
        == "4"
    )
    assert (
        dashboard.sections[4].metrics["SQN"]
        == "2.1"
    )