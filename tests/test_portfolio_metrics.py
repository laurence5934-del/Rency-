from app.models.portfolio_risk_models import PortfolioSnapshot
from app.services.portfolio_metrics import (
    calculate_cash_percent,
    calculate_cash_value,
    calculate_daily_return_percent,
    calculate_exposure_percent,
    calculate_largest_position,
    calculate_largest_position_percent,
    calculate_portfolio_health_score,
    calculate_position_weights,
    classify_portfolio_health,
)


def make_snapshot(**overrides):
    values = {
        "net_liquidation": 100_000.0,
        "buying_power": 40_000.0,
        "total_position_value": 60_000.0,
        "open_position_count": 3,
        "daily_realized_pnl": 300.0,
        "daily_unrealized_pnl": 200.0,
        "drawdown_percent": 2.0,
        "symbol_position_values": {
            "AAPL": 25_000.0,
            "MSFT": 20_000.0,
            "NVDA": 15_000.0,
        },
    }
    values.update(overrides)
    return PortfolioSnapshot(**values)


def test_basic_portfolio_metrics():
    snapshot = make_snapshot()

    assert calculate_exposure_percent(snapshot) == 60.0
    assert calculate_cash_value(snapshot) == 40_000.0
    assert calculate_cash_percent(snapshot) == 40.0
    assert calculate_daily_return_percent(snapshot) == 0.5


def test_largest_position_metrics():
    snapshot = make_snapshot()

    assert calculate_largest_position(snapshot) == ("AAPL", 25_000.0)
    assert calculate_largest_position_percent(snapshot) == 25.0


def test_position_weights():
    weights = calculate_position_weights(make_snapshot())

    assert weights == {
        "AAPL": 25.0,
        "MSFT": 20.0,
        "NVDA": 15.0,
    }


def test_zero_net_liquidation_is_safe():
    snapshot = make_snapshot(net_liquidation=0.0)

    assert calculate_exposure_percent(snapshot) == 0.0
    assert calculate_cash_percent(snapshot) == 0.0
    assert calculate_daily_return_percent(snapshot) == 0.0


def test_health_score_and_label():
    snapshot = make_snapshot()
    score = calculate_portfolio_health_score(snapshot)

    assert 0.0 <= score <= 100.0
    assert classify_portfolio_health(score) in {
        "EXCELLENT",
        "HEALTHY",
        "WATCH",
        "HIGH_RISK",
        "CRITICAL",
    }


def test_health_score_penalizes_high_risk():
    healthy = calculate_portfolio_health_score(make_snapshot())
    risky = calculate_portfolio_health_score(
        make_snapshot(
            total_position_value=95_000.0,
            drawdown_percent=12.0,
            daily_realized_pnl=-2_000.0,
            daily_unrealized_pnl=-1_000.0,
            symbol_position_values={"AAPL": 55_000.0},
        )
    )

    assert risky < healthy
