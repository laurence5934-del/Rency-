from app.models.portfolio_risk_models import PortfolioSnapshot
from app.services.portfolio_service import PortfolioService


def test_portfolio_service_builds_complete_summary():
    snapshot = PortfolioSnapshot(
        net_liquidation=100_000.0,
        buying_power=40_000.0,
        total_position_value=60_000.0,
        open_position_count=3,
        daily_realized_pnl=300.0,
        daily_unrealized_pnl=200.0,
        drawdown_percent=2.0,
        symbol_position_values={
            "AAPL": 25_000.0,
            "MSFT": 20_000.0,
            "NVDA": 15_000.0,
        },
    )

    summary = PortfolioService().get_summary(snapshot)

    assert summary.net_liquidation == 100_000.0
    assert summary.cash_value == 40_000.0
    assert summary.daily_total_pnl == 500.0
    assert summary.exposure_percent == 60.0
    assert summary.largest_position_symbol == "AAPL"
    assert summary.largest_position_percent == 25.0
    assert summary.health_status in {
        "EXCELLENT",
        "HEALTHY",
        "WATCH",
        "HIGH_RISK",
        "CRITICAL",
    }


def test_summary_to_dict_rounds_values():
    snapshot = PortfolioSnapshot(
        net_liquidation=100_000.0,
        buying_power=33_333.333,
        total_position_value=66_666.667,
        open_position_count=1,
        daily_realized_pnl=100.125,
        daily_unrealized_pnl=50.126,
        drawdown_percent=1.234,
        symbol_position_values={"AAPL": 66_666.667},
    )

    result = PortfolioService().get_summary(snapshot).to_dict()

    assert result["buying_power"] == 33_333.33
    assert result["daily_total_pnl"] == 150.25
    assert result["drawdown_percent"] == 1.23
