from app.portfolio import (
    CashMovement,
    CashMovementType,
    EnterprisePortfolioManager,
    TradeFill,
)

manager = EnterprisePortfolioManager(starting_cash=100000.0)

manager.apply_fill(TradeFill(symbol="PLTR", quantity=100, price=20.0, side="BUY", commission=1.0))
manager.update_market_price("PLTR", 25.0)
manager.record_dividend("PLTR", 50.0)

position = manager.get_position("PLTR")
assert position is not None
assert position.quantity == 100
assert position.average_cost == 20.0
assert position.unrealized_pnl == 500.0
assert position.dividends_received == 50.0

snapshot = manager.snapshot()
assert snapshot.cash == 98049.0
assert snapshot.net_liquidation_value == 100549.0
assert snapshot.unrealized_pnl == 500.0
assert snapshot.dividends_received == 50.0

ok, issues = manager.reconcile()
assert ok is True
assert issues == ()
assert manager.health()["status"] == "HEALTHY"
assert manager.metrics()["fills_applied"] == 1
