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

def test_default_volatility_is_zero() -> None:
    metrics = RiskAnalyzer().analyze(
        BacktestResult(
            backtest_id="volatility-default",
            status=BacktestStatus.COMPLETED,
            config=BacktestConfig(
                strategy_id="vol-test",
                strategy_version="1.0.0",
                dataset_id="vol-data",
                initial_capital=Decimal("100000"),
                start_time=datetime(2025, 1, 1),
                end_time=datetime(2025, 1, 1),
                timeframe=Timeframe.DAY,
            ),
            started_at=datetime(2025, 1, 1),
            completed_at=datetime(2025, 1, 1),
            snapshots=(),
        )
    )

    assert metrics.volatility == Decimal("0")

def test_volatility_calculation() -> None:
    start = datetime(2025, 1, 1)

    config = BacktestConfig(
        strategy_id="volatility-test",
        strategy_version="1.0.0",
        dataset_id="volatility-data",
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
        backtest_id="volatility-test-001",
        status=BacktestStatus.COMPLETED,
        config=config,
        started_at=start,
        completed_at=datetime(2025, 1, 4),
        snapshots=snapshots,
    )

    metrics = RiskAnalyzer().analyze(result)

    assert abs(metrics.volatility - Decimal("0.11547005383792515")) < Decimal("0.000000000000001")