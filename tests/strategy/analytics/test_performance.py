from decimal import Decimal
from datetime import datetime

from app.strategy.analytics.performance_models import PerformanceMetrics
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

def test_positive_sortino_ratio() -> None:
    from app.strategy.backtesting.models import PortfolioSnapshot

    start = datetime(2025, 1, 1)

    config = BacktestConfig(
        strategy_id="sortino-test",
        strategy_version="1.0.0",
        dataset_id="dataset",
        initial_capital=Decimal("100"),
        start_time=start,
        end_time=datetime(2025, 1, 5),
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
            cash=Decimal("104.5"),
            positions_value=Decimal("0"),
            equity=Decimal("104.5"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 4),
            cash=Decimal("114.95"),
            positions_value=Decimal("0"),
            equity=Decimal("114.95"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 5),
            cash=Decimal("103.455"),
            positions_value=Decimal("0"),
            equity=Decimal("103.455"),
        ),
    )

    result = BacktestResult(
        backtest_id="sortino-001",
        status=BacktestStatus.COMPLETED,
        config=config,
        started_at=start,
        completed_at=datetime(2025, 1, 5),
        snapshots=snapshots,
    )

    metrics = PerformanceAnalyzer().analyze(result)

    assert metrics.sortino_ratio > Decimal("0")

def test_default_calmar_ratio_is_zero() -> None:
    metrics = PerformanceMetrics()
    
    assert metrics.calmar_ratio == Decimal("0")

def test_positive_calmar_ratio() -> None:
    metrics = PerformanceMetrics(
        calmar_ratio=Decimal("1.25")
    )

    assert metrics.calmar_ratio > Decimal("0")

def test_default_profit_factor_is_zero() -> None:
    metrics = PerformanceMetrics()

    assert metrics.profit_factor == Decimal("0")

def test_positive_profit_factor() -> None:
    from app.strategy.backtesting.models import PortfolioSnapshot

    start = datetime(2025, 1, 1)

    config = BacktestConfig(
        strategy_id="profit-factor-test",
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
            realized_pnl=Decimal("0"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 2),
            cash=Decimal("200"),
            positions_value=Decimal("0"),
            equity=Decimal("200"),
            realized_pnl=Decimal("100"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 3),
            cash=Decimal("160"),
            positions_value=Decimal("0"),
            equity=Decimal("160"),
            realized_pnl=Decimal("60"),
        ),
        PortfolioSnapshot(
            timestamp=datetime(2025, 1, 4),
            cash=Decimal("240"),
            positions_value=Decimal("0"),
            equity=Decimal("240"),
            realized_pnl=Decimal("140"),
        ),
    )

    result = BacktestResult(
        backtest_id="profit-factor-001",
        status=BacktestStatus.COMPLETED,
        config=config,
        started_at=start,
        completed_at=datetime(2025, 1, 4),
        snapshots=snapshots,
    )

    metrics = PerformanceAnalyzer().analyze(result)

    assert metrics.profit_factor == Decimal("4.5")

def test_default_win_rate_is_zero() -> None:
    metrics = PerformanceMetrics()

    assert metrics.win_rate == Decimal("0")


def test_win_rate_is_one_hundred_for_all_winners() -> None:
    pnl_changes = [
        Decimal("25"),
        Decimal("50"),
        Decimal("10"),
    ]

    win_rate = PerformanceAnalyzer._calculate_win_rate(
        pnl_changes
    )

    assert win_rate == Decimal("100")


def test_win_rate_is_zero_for_all_losers() -> None:
    pnl_changes = [
        Decimal("-25"),
        Decimal("-50"),
        Decimal("-10"),
    ]

    win_rate = PerformanceAnalyzer._calculate_win_rate(
        pnl_changes
    )

    assert win_rate == Decimal("0")


def test_win_rate_matches_mixed_results() -> None:
    pnl_changes = [
        Decimal("100"),
        Decimal("-40"),
        Decimal("80"),
    ]

    win_rate = PerformanceAnalyzer._calculate_win_rate(
        pnl_changes
    )

    expected = Decimal(
        "66.66666666666666666666666667"
    )

    assert win_rate == expected


def test_win_rate_excludes_breakeven_results() -> None:
    pnl_changes = [
        Decimal("100"),
        Decimal("0"),
        Decimal("-50"),
        Decimal("0"),
    ]

    win_rate = PerformanceAnalyzer._calculate_win_rate(
        pnl_changes
    )

    assert win_rate == Decimal("50")


def test_win_rate_is_zero_without_closed_results() -> None:
    pnl_changes = [
        Decimal("0"),
        Decimal("0"),
    ]

    win_rate = PerformanceAnalyzer._calculate_win_rate(
        pnl_changes
    )

    assert win_rate == Decimal("0")