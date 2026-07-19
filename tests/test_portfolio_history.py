from datetime import date

from app.services.portfolio_history import (
    PortfolioHistoryPoint,
    calculate_annualized_sharpe_ratio,
    calculate_daily_returns,
    calculate_max_drawdown_percent,
    calculate_total_return_percent,
)


def sample_history():
    return [
        PortfolioHistoryPoint(date(2026, 1, 1), 100_000.0),
        PortfolioHistoryPoint(date(2026, 1, 2), 105_000.0),
        PortfolioHistoryPoint(date(2026, 1, 3), 94_500.0),
        PortfolioHistoryPoint(date(2026, 1, 4), 110_000.0),
    ]


def test_total_return():
    assert calculate_total_return_percent(sample_history()) == 10.0


def test_max_drawdown():
    assert calculate_max_drawdown_percent(sample_history()) == 10.0


def test_daily_returns():
    returns = calculate_daily_returns(sample_history())

    assert len(returns) == 3
    assert returns[0] == 0.05


def test_sharpe_ratio_returns_number():
    result = calculate_annualized_sharpe_ratio(sample_history())
    assert isinstance(result, float)
