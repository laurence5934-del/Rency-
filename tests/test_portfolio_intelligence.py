from app.models.portfolio_risk_models import PortfolioRiskLimits
from app.services.portfolio_intelligence import (
    build_portfolio_intelligence,
)


def _account_data() -> dict:
    return {
        "connected": True,
        "summary": [
            {"tag": "NetLiquidation", "value": "100000"},
            {"tag": "BuyingPower", "value": "400000"},
            {"tag": "AvailableFunds", "value": "25000"},
            {"tag": "TotalCashValue", "value": "20000"},
            {"tag": "GrossPositionValue", "value": "60000"},
            {"tag": "RealizedPnL", "value": "100"},
            {"tag": "UnrealizedPnL", "value": "250"},
        ],
    }


def _positions_data() -> dict:
    return {
        "connected": True,
        "positions": [
            {
                "symbol": "PLTR",
                "position": 100,
                "avgCost": 200,
            },
            {
                "symbol": "NVDA",
                "position": 50,
                "avgCost": 300,
            },
        ],
    }


def test_builds_portfolio_intelligence() -> None:
    result = build_portfolio_intelligence(
        account_data=_account_data(),
        positions_data=_positions_data(),
    )

    assert result.snapshot.net_liquidation == 100000
    assert result.snapshot.daily_total_pnl == 350
    assert result.exposure_percent == 60
    assert result.cash_percent == 20
    assert result.margin_multiple == 4
    assert result.available_margin == 340000
    assert result.largest_position_symbol == "PLTR"
    assert result.largest_position_value == 20000
    assert result.health_score >= 70


def test_backward_compatible_buying_power_percent() -> None:
    result = build_portfolio_intelligence(
        account_data=_account_data(),
        positions_data=_positions_data(),
    )

    assert result.buying_power_percent == 400


def test_advisor_recommends_capacity_within_limits() -> None:
    result = build_portfolio_intelligence(
        account_data=_account_data(),
        positions_data=_positions_data(),
    )

    assert result.advisor.can_open_new_position is True
    assert result.advisor.suggested_position_size == 10000


def test_advisor_blocks_at_position_limit() -> None:
    positions = {
        "positions": [
            {
                "symbol": f"SYM{index}",
                "position": 1,
                "avgCost": 1000,
            }
            for index in range(10)
        ],
    }

    result = build_portfolio_intelligence(
        account_data=_account_data(),
        positions_data=positions,
    )

    assert result.advisor.can_open_new_position is False
    assert result.advisor.suggested_position_size == 0


def test_health_declines_at_drawdown_limit() -> None:
    result = build_portfolio_intelligence(
        account_data=_account_data(),
        positions_data=_positions_data(),
        peak_net_liquidation=112000,
    )

    assert result.snapshot.drawdown_percent > 10
    assert result.health_score < 85


def test_invalid_missing_account_data_is_safe() -> None:
    result = build_portfolio_intelligence(
        account_data={"summary": []},
        positions_data={"positions": []},
    )

    assert result.snapshot.net_liquidation == 0
    assert result.health_score == 0
    assert result.advisor.can_open_new_position is False


def test_custom_limits_control_suggested_size() -> None:
    limits = PortfolioRiskLimits(
        maximum_order_value=5000,
        maximum_position_value=8000,
        maximum_portfolio_exposure_percent=80,
        maximum_open_positions=10,
        minimum_buying_power=2000,
        maximum_daily_loss=1000,
        maximum_drawdown_percent=10,
    )

    result = build_portfolio_intelligence(
        account_data=_account_data(),
        positions_data=_positions_data(),
        limits=limits,
    )

    assert result.advisor.suggested_position_size == 5000
