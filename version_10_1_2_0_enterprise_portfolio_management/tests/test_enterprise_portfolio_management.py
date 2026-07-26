from app.portfolio import EnterprisePortfolioManager, TradeFill


def test_average_cost_and_realized_pnl():
    manager = EnterprisePortfolioManager(starting_cash=10000.0)
    manager.apply_fill(TradeFill("ABC", 10, 100.0, "BUY"))
    manager.apply_fill(TradeFill("ABC", 10, 120.0, "BUY"))
    assert manager.get_position("ABC").average_cost == 110.0
    manager.apply_fill(TradeFill("ABC", 5, 130.0, "SELL"))
    position = manager.get_position("ABC")
    assert position.quantity == 15
    assert position.realized_pnl == 100.0


def test_insufficient_cash_rejected():
    manager = EnterprisePortfolioManager(starting_cash=100.0)
    try:
        manager.apply_fill(TradeFill("XYZ", 2, 100.0, "BUY"))
    except ValueError as exc:
        assert "insufficient" in str(exc)
    else:
        raise AssertionError("expected insufficient-cash failure")
