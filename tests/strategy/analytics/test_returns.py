from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from app.strategy.analytics import ReturnAnalyzer
from app.strategy.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    BacktestStatus,
    PortfolioSnapshot,
    Timeframe,
)


def test_net_profit_and_total_return() -> None:
    start = datetime(2025, 1, 1)
    end = start + timedelta(days=365)

    config = BacktestConfig(
        strategy_id="unit-test-strategy",
        strategy_version="1.0.0",
        dataset_id="unit-test-dataset",
        initial_capital=Decimal("100000"),
        start_time=start,
        end_time=end,
        timeframe=Timeframe.DAY,
    )

    snapshots = (
        PortfolioSnapshot(
            timestamp=start,
            cash=Decimal("100000"),
            positions_value=Decimal("0"),
            equity=Decimal("100000"),
        ),
        PortfolioSnapshot(
            timestamp=end,
            cash=Decimal("110000"),
            positions_value=Decimal("0"),
            equity=Decimal("110000"),
            realized_pnl=Decimal("10000"),
        ),
    )

    result = BacktestResult(
        backtest_id="return-test-001",
        status=BacktestStatus.COMPLETED,
        config=config,
        started_at=start,
        completed_at=end,
        trades=(),
        snapshots=snapshots,
        metrics={},
        warnings=(),
        error=None,
    )

    metrics = ReturnAnalyzer().analyze(result)

    assert metrics.initial_capital == Decimal("100000")
    assert metrics.final_equity == Decimal("110000")
    assert metrics.net_profit == Decimal("10000")
    assert metrics.total_return == Decimal("0.10")
    assert metrics.periodic_returns == (Decimal("0.10"),)

def test_cagr_one_year() -> None:
    start = datetime(2025, 1, 1)
    end = start + timedelta(days=365)

    config = BacktestConfig(
        strategy_id="unit-test-strategy",
        strategy_version="1.0.0",
        dataset_id="unit-test-dataset",
        initial_capital=Decimal("100000"),
        start_time=start,
        end_time=end,
        timeframe=Timeframe.DAY,
    )

    snapshots = (
        PortfolioSnapshot(
            timestamp=start,
            cash=Decimal("100000"),
            positions_value=Decimal("0"),
            equity=Decimal("100000"),
        ),
        PortfolioSnapshot(
            timestamp=end,
            cash=Decimal("110000"),
            positions_value=Decimal("0"),
            equity=Decimal("110000"),
        ),
    )

    result = BacktestResult(
        backtest_id="cagr-test-001",
        status=BacktestStatus.COMPLETED,
        config=config,
        started_at=start,
        completed_at=end,
        snapshots=snapshots,
    )

    metrics = ReturnAnalyzer().analyze(result)

    assert abs(metrics.cagr - Decimal("0.10")) < Decimal("0.001")

def test_cagr_three_years() -> None:
    start = datetime(2025, 1, 1)
    end = datetime(2028, 1, 1)

    config = BacktestConfig(
        strategy_id="unit-test-strategy",
        strategy_version="1.0.0",
        dataset_id="unit-test-dataset",
        initial_capital=Decimal("100000"),
        start_time=start,
        end_time=end,
        timeframe=Timeframe.DAY,
    )

    snapshots = (
        PortfolioSnapshot(
            timestamp=start,
            cash=Decimal("100000"),
            positions_value=Decimal("0"),
            equity=Decimal("100000"),
        ),
        PortfolioSnapshot(
            timestamp=end,
            cash=Decimal("133100"),
            positions_value=Decimal("0"),
            equity=Decimal("133100"),
        ),
    )

    result = BacktestResult(
        backtest_id="cagr-test-003",
        status=BacktestStatus.COMPLETED,
        config=config,
        started_at=start,
        completed_at=end,
        snapshots=snapshots,
    )

    metrics = ReturnAnalyzer().analyze(result)

    assert abs(metrics.cagr - Decimal("0.10")) < Decimal("0.001")

def test_snapshots_are_sorted_before_analysis() -> None:
    start = datetime(2025, 1, 1)
    mid = datetime(2025, 1, 2)
    end = datetime(2025, 1, 3)

    config = BacktestConfig(
        strategy_id="unit-test-strategy",
        strategy_version="1.0.0",
        dataset_id="unit-test-dataset",
        initial_capital=Decimal("100000"),
        start_time=start,
        end_time=end,
        timeframe=Timeframe.DAY,
    )

    # Intentionally out of order
    snapshots = (
        PortfolioSnapshot(
            timestamp=end,
            cash=Decimal("110000"),
            positions_value=Decimal("0"),
            equity=Decimal("110000"),
        ),
        PortfolioSnapshot(
            timestamp=start,
            cash=Decimal("100000"),
            positions_value=Decimal("0"),
            equity=Decimal("100000"),
        ),
        PortfolioSnapshot(
            timestamp=mid,
            cash=Decimal("105000"),
            positions_value=Decimal("0"),
            equity=Decimal("105000"),
        ),
    )

    result = BacktestResult(
        backtest_id="sorting-test-001",
        status=BacktestStatus.COMPLETED,
        config=config,
        started_at=start,
        completed_at=end,
        snapshots=snapshots,
    )

    metrics = ReturnAnalyzer().analyze(result)

    assert metrics.net_profit == Decimal("10000")
    assert metrics.final_equity == Decimal("110000") 

def test_empty_snapshots_use_initial_capital() -> None:
    start = datetime(2025, 1, 1)
    end = datetime(2025, 1, 2)

    config = BacktestConfig(
        strategy_id="unit-test-strategy",
        strategy_version="1.0.0",
        dataset_id="unit-test-dataset",
        initial_capital=Decimal("100000"),
        start_time=start,
        end_time=end,
        timeframe=Timeframe.DAY,
    )

    result = BacktestResult(
        backtest_id="empty-snapshots-test-001",
        status=BacktestStatus.COMPLETED,
        config=config,
        started_at=start,
        completed_at=end,
        snapshots=(),
    )

    metrics = ReturnAnalyzer().analyze(result)

    assert metrics.initial_capital == Decimal("100000")
    assert metrics.final_equity == Decimal("100000")
    assert metrics.net_profit == Decimal("0")
    assert metrics.total_return == Decimal("0")
    assert metrics.cagr == Decimal("0")
    assert metrics.periodic_returns == ()
    assert metrics.warnings   