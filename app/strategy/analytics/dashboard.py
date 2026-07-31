from .dashboard_models import (
    AnalyticsDashboard,
    DashboardSection,
)


class AnalyticsDashboardBuilder:
    """Builds a presentation-friendly analytics dashboard."""

    def build(self, report):
        return AnalyticsDashboard(
            sections=(
                DashboardSection(
                    title="Returns",
                    metrics={
                        "Net Profit": str(
                            report.returns.net_profit
                        ),
                        "Total Return": str(
                            report.returns.total_return
                        ),
                        "CAGR": str(
                            report.returns.cagr
                        ),
                    },
                ),
                DashboardSection(
                    title="Performance",
                    metrics={
                        "Sharpe": str(
                            report.performance.sharpe_ratio
                        ),
                        "Sortino": str(
                            report.performance.sortino_ratio
                        ),
                        "Calmar": str(
                            report.performance.calmar_ratio
                        ),
                        "Profit Factor": str(
                            report.performance.profit_factor
                        ),
                        "Win Rate": str(
                            report.performance.win_rate
                        ),
                    },
                ),
                DashboardSection(
                    title="Risk",
                    metrics={
                        "Max Drawdown": str(
                            report.risk.max_drawdown
                        ),
                        "Volatility": str(
                            report.risk.volatility
                        ),
                    },
                ),
                DashboardSection(
                    title="Expectancy",
                    metrics={
                        "Expectancy": str(
                            report.expectancy.expectancy
                        ),
                        "Payoff Ratio": str(
                            report.expectancy.payoff_ratio
                        ),
                        "Recovery Factor": str(
                            report.expectancy.recovery_factor
                        ),
                    },
                ),
                DashboardSection(
                    title="Strategy Quality",
                    metrics={
                        "SQN": str(
                            report.strategy_quality.system_quality_number
                        ),
                        "Kelly": str(
                            report.strategy_quality.kelly_criterion
                        ),
                        "Gain/Pain": str(
                            report.strategy_quality.gain_to_pain_ratio
                        ),
                        "Ulcer": str(
                            report.strategy_quality.ulcer_index
                        ),
                    },
                ),
            ),
        )