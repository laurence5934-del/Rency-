from decimal import Decimal
from datetime import datetime

from app.strategy.analytics.performance import PerformanceAnalyzer
from app.strategy.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    BacktestStatus,
    Timeframe,
)


def test_default_sharpe_ratio_is_zero():
    result = BacktestResult(
        backtest_id="perf-001",
        status=BacktestStatus.COMPLETED,
        config=BacktestConfig(
            strategy_id="test",
            strategy_version="1.0.0",
            dataset_id="dataset",
            initial_capital=Decimal("100000"),
            start_time=datetime(2025, 1, 1),
            end_time=datetime(2025, 1, 1),
            timeframe=Timeframe.DAY,
        ),
        started_at=datetime(2025, 1, 1),
        snapshots=(),
    )

    metrics = PerformanceAnalyzer().analyze(result)

    assert metrics.sharpe_ratio == Decimal("0")

def test_positive_sharpe_ratio() -> None:
    from app.strategy.backtesting.models import PortfolioSnapshot

    start = datetime(2025, 1, 1)

    config = BacktestConfig(
        strategy_id="sharpe-test",
        strategy_version="1.0.0",
        dataset_id="dataset",
        initial_capital=Decimal("100"),
        start_time=start,
        end_time=datetime(2025, 1, 4),
        timeframe=Timeframe.DAY,
    )

    snapshots = (
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 1),
            cash=Decimal("100"),
            positions_value=Decimal("0"),
            equity=Decimal("100"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 2),
            cash=Decimal("110"),
            positions_value=Decimal("0"),
            equity=Decimal("110"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 3),
            cash=Decimal("99"),
            positions_value=Decimal("0"),
            equity=Decimal("99"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 4),
            cash=Decimal("108.9"),
            positions_value=Decimal("0"),
            equity=Decimal("108.9"),
        ),
    )

    result = BacktestResult(
        backtest_id="sharpe-001",
        status=BacktestStatus.COMPLETED,
        config=config,
        started_at=start,
        completed_at=datetime(2025, 1, 4),
        snapshots=snapshots,
    )

    metrics = PerformanceAnalyzer().analyze(result)

    assert metrics.sharpe_ratio > Decimal("0")

def test_sharpe_ratio_matches_expected_value() -> None:
    from app.strategy.backtesting.models import PortfolioSnapshot

    start = datetime(2025, 1, 1)

    config = BacktestConfig(
        strategy_id="sharpe-exact-test",
        strategy_version="1.0.0",
        dataset_id="dataset",
        initial_capital=Decimal("100"),
        start_time=start,
        end_time=datetime(2025, 1, 4),
        timeframe=Timeframe.DAY,
    )

    snapshots = (
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 1),
            cash=Decimal("100"),
            positions_value=Decimal("0"),
            equity=Decimal("100"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 2),
            cash=Decimal("110"),
            positions_value=Decimal("0"),
            equity=Decimal("110"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 3),
            cash=Decimal("99"),
            positions_value=Decimal("0"),
            equity=Decimal("99"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 4),
            cash=Decimal("108.9"),
            positions_value=Decimal("0"),
            equity=Decimal("108.9"),
        ),
    )

    result = BacktestResult(
        backtest_id="sharpe-exact-001",
        status=BacktestStatus.COMPLETED,
        config=config,
        started_at=start,
        completed_at=datetime(2025, 1, 4),
        snapshots=snapshots,
    )

    metrics = PerformanceAnalyzer().analyze(result)

    expected = Decimal("0.2886751345948128822545743903")
    tolerance = Decimal("0.0000000000000000000000000001")

    assert abs(metrics.sharpe_ratio - expected) <= tolerance

def test_default_sortino_ratio_is_zero() -> None:
    start = datetime(2025, 1, 1)

    config = BacktestConfig(
        strategy_id="sortino-scaffold-test",
        strategy_version="1.0.0",
        dataset_id="dataset",
        initial_capital=Decimal("100"),
        start_time=start,
        end_time=start,
        timeframe=Timeframe.DAY,
    )

    result = BacktestResult(
        backtest_id="sortino-scaffold-001",
        status=BacktestStatus.COMPLETED,
        config=config,
        started_at=start,
        completed_at=start,
        snapshots=(),
    )

    metrics = PerformanceAnalyzer().analyze(result)

    assert metrics.sortino_ratio == Decimal("0")