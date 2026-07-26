from datetime import datetime, timezone
from decimal import Decimal

from app.strategy.backtesting import PortfolioEngine, Trade


timestamp = datetime(2026, 7, 25, tzinfo=timezone.utc)

portfolio = PortfolioEngine(Decimal("10000"))

portfolio.apply_trade(
    Trade(
        trade_id="BUY-AAPL-1",
        symbol="AAPL",
        quantity=Decimal("10"),
        price=Decimal("100"),
        side="buy",
        timestamp=timestamp,
        commission=Decimal("1"),
    )
)

portfolio.mark_to_market("AAPL", Decimal("110"))
snapshot = portfolio.create_snapshot(timestamp)

assert portfolio.cash == Decimal("8999")
assert snapshot.positions_value == Decimal("1100")
assert snapshot.unrealized_pnl == Decimal("100")
assert snapshot.equity == Decimal("10099")
assert snapshot.drawdown == Decimal("0")
