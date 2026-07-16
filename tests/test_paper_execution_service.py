from app.broker.paper_execution_service import (
    prepare_paper_execution,
)
from app.models.portfolio_risk_models import (
    PortfolioRiskLimits,
    PortfolioSnapshot,
)


def make_candidate(
    *,
    symbol: str = "AAPL",
    action: str = "BUY",
    quantity: int = 10,
    entry_price: float = 200.00,
    status: str = "APPROVED",
) -> dict:
    return {
        "id": 101,
        "symbol": symbol,
        "action": action,
        "quantity": quantity,
        "entry_price": entry_price,
        "status": status,
    }


def make_portfolio(
    **overrides,
) -> PortfolioSnapshot:
    values = {
        "net_liquidation": 100_000.00,
        "buying_power": 50_000.00,
        "total_position_value": 30_000.00,
        "open_position_count": 4,
        "daily_realized_pnl": 100.00,
        "daily_unrealized_pnl": -50.00,
        "drawdown_percent": 2.0,
        "symbol_position_values": {},
    }

    values.update(overrides)

    return PortfolioSnapshot(**values)


def test_blocks_when_portfolio_snapshot_is_missing():
    result = prepare_paper_execution(
        candidate=make_candidate(),
        ibkr_connected=True,
        paper_account_confirmed=True,
        portfolio=None,
    )

    assert result["ready"] is False
    assert result["guard"] is None
    assert result["order"] is None
    assert (
        "PORTFOLIO_SNAPSHOT_REQUIRED"
        in result["portfolio_risk"]["codes"]
    )


def test_blocks_when_portfolio_risk_rejects_order():
    limits = PortfolioRiskLimits(
        maximum_order_value=1_000.00,
    )

    result = prepare_paper_execution(
        candidate=make_candidate(
            quantity=10,
            entry_price=200.00,
        ),
        ibkr_connected=True,
        paper_account_confirmed=True,
        portfolio=make_portfolio(),
        risk_limits=limits,
    )

    assert result["ready"] is False
    assert result["portfolio_risk"]["approved"] is False
    assert "ORDER_VALUE_EXCEEDED" in (
        result["portfolio_risk"]["codes"]
    )
    assert result["guard"] is None
    assert result["order"] is None


def test_blocks_when_emergency_lock_is_active():
    result = prepare_paper_execution(
        candidate=make_candidate(),
        ibkr_connected=True,
        paper_account_confirmed=True,
        portfolio=make_portfolio(),
        emergency_lock_active=True,
    )

    assert result["ready"] is False
    assert "EMERGENCY_LOCK_ACTIVE" in (
        result["portfolio_risk"]["codes"]
    )


def test_blocks_when_ibkr_is_disconnected():
    result = prepare_paper_execution(
        candidate=make_candidate(),
        ibkr_connected=False,
        paper_account_confirmed=True,
        portfolio=make_portfolio(),
    )

    assert result["ready"] is False
    assert result["portfolio_risk"]["approved"] is True
    assert result["guard"]["approved"] is False
    assert "IBKR is not connected." in (
        result["guard"]["errors"]
    )


def test_blocks_without_paper_account_confirmation():
    result = prepare_paper_execution(
        candidate=make_candidate(),
        ibkr_connected=True,
        paper_account_confirmed=False,
        portfolio=make_portfolio(),
    )

    assert result["ready"] is False
    assert result["portfolio_risk"]["approved"] is True
    assert result["guard"]["approved"] is False


def test_builds_non_transmitting_order_after_all_checks():
    result = prepare_paper_execution(
        candidate=make_candidate(),
        ibkr_connected=True,
        paper_account_confirmed=True,
        portfolio=make_portfolio(),
        order_type="MKT",
    )

    assert result["ready"] is True
    assert result["portfolio_risk"]["approved"] is True
    assert result["guard"]["approved"] is True

    order = result["order"]

    assert order["symbol"] == "AAPL"
    assert order["action"] == "BUY"
    assert order["quantity"] == 10
    assert order["order_type"] == "MKT"
    assert order["paper_only"] is True
    assert order["transmit"] is False


def test_builds_valid_limit_order():
    result = prepare_paper_execution(
        candidate=make_candidate(),
        ibkr_connected=True,
        paper_account_confirmed=True,
        portfolio=make_portfolio(),
        order_type="LMT",
        limit_price=198.50,
    )

    assert result["ready"] is True
    assert result["order"]["order_type"] == "LMT"
    assert result["order"]["limit_price"] == 198.50
    assert result["order"]["transmit"] is False