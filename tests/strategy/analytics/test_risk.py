from app.strategy.analytics.risk import RiskAnalyzer


def test_risk_analyzer_exists():
    analyzer = RiskAnalyzer()
    assert analyzer is not None

from datetime import datetime
from decimal import Decimal

from app.strategy.analytics.risk import RiskAnalyzer
from app.strategy.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    BacktestStatus,
    PortfolioSnapshot,
    Timeframe,
)


def test_max_drawdown_calculation() -> None:
    start = datetime(2025, 1, 1)

    config = BacktestConfig(
        strategy_id="risk-test",
        strategy_version="1.0.0",
        dataset_id="risk-data",
        initial_capital=Decimal("100000"),
        start_time=start,
        end_time=start,
        timeframe=Timeframe.DAY,
    )

    snapshots = (
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 1),
            cash=Decimal("100000"),
            positions_value=Decimal("0"),
            equity=Decimal("100000"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 2),
            cash=Decimal("110000"),
            positions_value=Decimal("0"),
            equity=Decimal("110000"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 3),
            cash=Decimal("95000"),
            positions_value=Decimal("0"),
            equity=Decimal("95000"),
        ),
    )

    result = BacktestResult(
        backtest_id="risk-test-001",
        status=BacktestStatus.COMPLETED,
        config=config,
        started_at=start,
        completed_at=start,
        snapshots=snapshots,
    )

    metrics = RiskAnalyzer().analyze(result)

    assert abs(metrics.max_drawdown - Decimal("0.13636")) < Decimal("0.001")

def test_drawdown_duration() -> None:
    start = datetime(2025, 1, 1)

    config = BacktestConfig(
        strategy_id="duration-test",
        strategy_version="1.0.0",
        dataset_id="duration-data",
        initial_capital=Decimal("100000"),
        start_time=start,
        end_time=datetime(2025, 1, 6),
        timeframe=Timeframe.DAY,
    )

    snapshots = (
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 1),
            cash=Decimal("100000"),
            positions_value=Decimal("0"),
            equity=Decimal("100000"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 2),
            cash=Decimal("110000"),
            positions_value=Decimal("0"),
            equity=Decimal("110000"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 3),
            cash=Decimal("105000"),
            positions_value=Decimal("0"),
            equity=Decimal("105000"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 4),
            cash=Decimal("100000"),
            positions_value=Decimal("0"),
            equity=Decimal("100000"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 5),
            cash=Decimal("102000"),
            positions_value=Decimal("0"),
            equity=Decimal("102000"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 6),
            cash=Decimal("111000"),
            positions_value=Decimal("0"),
            equity=Decimal("111000"),
        ),
    )

    result = BacktestResult(
        backtest_id="duration-test-001",
        status=BacktestStatus.COMPLETED,
        config=config,
        started_at=start,
        completed_at=datetime(2025, 1, 6),
        snapshots=snapshots,
    )

    metrics = RiskAnalyzer().analyze(result)

    assert metrics.drawdown_duration == 3