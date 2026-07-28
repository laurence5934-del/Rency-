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