from app.models.portfolio_risk_models import (
    PortfolioRiskLimits,
    PortfolioSnapshot,
    RiskCode,
)
from app.risk.portfolio_risk_manager import (
    evaluate_portfolio_risk,
)


def make_candidate(
    *,
    symbol: str = "AAPL",
    action: str = "BUY",
    quantity: int = 10,
    entry_price: float = 200.00,
) -> dict:
    return {
        "id": 1,
        "symbol": symbol,
        "action": action,
        "quantity": quantity,
        "entry_price": entry_price,
        "status": "APPROVED",
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


def test_approves_valid_paper_order():
    result = evaluate_portfolio_risk(
        candidate=make_candidate(),
        portfolio=make_portfolio(),
    )

    assert result.approved is True
    assert RiskCode.APPROVED in result.codes
    assert result.order_value == 2_000.00


def test_rejects_when_paper_mode_is_disabled():
    result = evaluate_portfolio_risk(
        candidate=make_candidate(),
        portfolio=make_portfolio(),
        paper_trading_only=False,
    )

    assert result.approved is False
    assert (
        RiskCode.PAPER_TRADING_REQUIRED
        in result.codes
    )


def test_rejects_when_emergency_lock_is_active():
    result = evaluate_portfolio_risk(
        candidate=make_candidate(),
        portfolio=make_portfolio(),
        emergency_lock_active=True,
    )

    assert result.approved is False
    assert (
        RiskCode.EMERGENCY_LOCK_ACTIVE
        in result.codes
    )


def test_rejects_order_above_maximum_value():
    limits = PortfolioRiskLimits(
        maximum_order_value=1_000.00,
    )

    result = evaluate_portfolio_risk(
        candidate=make_candidate(
            quantity=10,
            entry_price=200.00,
        ),
        portfolio=make_portfolio(),
        limits=limits,
    )

    assert result.approved is False
    assert (
        RiskCode.ORDER_VALUE_EXCEEDED
        in result.codes
    )


def test_rejects_insufficient_buying_power():
    result = evaluate_portfolio_risk(
        candidate=make_candidate(
            quantity=50,
            entry_price=200.00,
        ),
        portfolio=make_portfolio(
            buying_power=10_500.00,
        ),
    )

    assert result.approved is False
    assert (
        RiskCode.BUYING_POWER_INSUFFICIENT
        in result.codes
    )


def test_rejects_daily_loss_limit():
    result = evaluate_portfolio_risk(
        candidate=make_candidate(),
        portfolio=make_portfolio(
            daily_realized_pnl=-800.00,
            daily_unrealized_pnl=-300.00,
        ),
    )

    assert result.approved is False
    assert (
        RiskCode.DAILY_LOSS_LIMIT_REACHED
        in result.codes
    )


def test_rejects_maximum_drawdown():
    result = evaluate_portfolio_risk(
        candidate=make_candidate(),
        portfolio=make_portfolio(
            drawdown_percent=12.0,
        ),
    )

    assert result.approved is False
    assert (
        RiskCode.MAXIMUM_DRAWDOWN_REACHED
        in result.codes
    )


def test_rejects_existing_symbol_exposure():
    result = evaluate_portfolio_risk(
        candidate=make_candidate(
            symbol="AAPL",
        ),
        portfolio=make_portfolio(
            symbol_position_values={
                "AAPL": 5_000.00,
            },
        ),
    )

    assert result.approved is False
    assert (
        RiskCode.EXISTING_SYMBOL_EXPOSURE
        in result.codes
    )


def test_allows_sell_of_existing_position():
    result = evaluate_portfolio_risk(
        candidate=make_candidate(
            symbol="AAPL",
            action="SELL",
            quantity=5,
            entry_price=200.00,
        ),
        portfolio=make_portfolio(
            symbol_position_values={
                "AAPL": 5_000.00,
            },
        ),
    )

    assert result.approved is True
    assert result.projected_symbol_value == 4_000.00

def test_pytest_is_working():
    assert True