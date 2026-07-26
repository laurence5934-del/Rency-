from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.strategy.backtesting import (
    BacktestConfig,
    BacktestEngine,
    BacktestStatus,
    ExecutionSimulator,
    FixedSlippage,
    FlatCommission,
    HistoricalBar,
    OrderSide,
    SimulatedOrder,
)


def main() -> None:
    start = datetime(2025, 1, 2, 14, 30, tzinfo=timezone.utc)
    bars = (
        HistoricalBar(
            symbol="MSFT",
            timestamp=start,
            open=Decimal("400"),
            high=Decimal("402"),
            low=Decimal("399"),
            close=Decimal("401"),
            volume=Decimal("10000"),
        ),
    )
    config = BacktestConfig(
        strategy_id="smoke-strategy",
        strategy_version="1.0.0",
        dataset_id="MSFT-SMOKE",
        initial_capital=Decimal("100000"),
        start_time=start,
        end_time=start + timedelta(days=1),
    )

    def strategy(event):
        return (
            SimulatedOrder(
                order_id="SMOKE-ORDER-1",
                symbol=event.bar.symbol,
                quantity=Decimal("1"),
                side=OrderSide.BUY,
                submitted_at=event.timestamp,
            ),
        )

    engine = BacktestEngine()
    result = engine.run_simulation(
        config,
        bars=bars,
        strategy=strategy,
        execution_simulator=ExecutionSimulator(
            commission_model=FlatCommission(Decimal("1")),
            slippage_model=FixedSlippage(Decimal("0.01")),
        ),
    )
    assert result.status is BacktestStatus.COMPLETED
    assert len(result.trades) == 1
    assert result.trades[0].price == Decimal("401.01")


if __name__ == "__main__":
    main()
