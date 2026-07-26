from datetime import datetime, timezone
from decimal import Decimal

from app.strategy.backtesting import BacktestConfig, BacktestEngine, BacktestStatus


def main() -> None:
    config = BacktestConfig(
        strategy_id="momentum",
        strategy_version="1.0.0",
        dataset_id="SPY-DAILY-2020-2024",
        initial_capital=Decimal("100000"),
        start_time=datetime(2020, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    engine = BacktestEngine()
    result = engine.run(config)
    assert result.status is BacktestStatus.COMPLETED
    assert result.backtest_id.startswith("BT-")
    assert engine.get_result(result.backtest_id) == result


if __name__ == "__main__":
    main()
