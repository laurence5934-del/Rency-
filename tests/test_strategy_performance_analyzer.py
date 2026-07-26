from __future__ import annotations

from datetime import datetime, timedelta
from math import isinf

import pytest

from app.strategies.strategy_performance_analyzer import (
    StrategyPerformanceAnalyzer,
    StrategyTrade,
)


BASE_TIME = datetime(2026, 1, 1, 9, 30)


def make_trade(
    strategy_name: str = "Test Strategy",
    symbol: str = "AAPL",
    entry_price: float = 100.0,
    exit_price: float = 110.0,
    quantity: float = 10.0,
    entry_time: datetime = BASE_TIME,
    exit_time: datetime = BASE_TIME + timedelta(hours=1),
    fees: float = 0.0,
) -> StrategyTrade:
    return StrategyTrade(
        strategy_name=strategy_name,
        symbol=symbol,
        entry_price=entry_price,
        exit_price=exit_price,
        quantity=quantity,
        entry_time=entry_time,
        exit_time=exit_time,
        fees=fees,
    )


def test_strategy_trade_normalizes_fields() -> None:
    trade = make_trade(
        strategy_name="  RSI Strategy  ",
        symbol="  aapl  ",
    )

    assert trade.strategy_name == "RSI Strategy"
    assert trade.symbol == "AAPL"
    assert trade.entry_price == 100.0
    assert trade.exit_price == 110.0
    assert trade.quantity == 10.0
    assert trade.fees == 0.0


@pytest.mark.parametrize(
    ("field", "value", "error_type", "message"),
    [
        ("strategy_name", 123, TypeError, "strategy_name must be a string"),
        ("strategy_name", "   ", ValueError, "strategy_name cannot be empty"),
        ("symbol", 123, TypeError, "symbol must be a string"),
        ("symbol", "   ", ValueError, "symbol cannot be empty"),
    ],
)
def test_strategy_trade_invalid_text_fields(
    field: str,
    value: object,
    error_type: type[Exception],
    message: str,
) -> None:
    kwargs = {field: value}

    with pytest.raises(error_type, match=message):
        make_trade(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("entry_price", "100"),
        ("exit_price", None),
        ("quantity", True),
        ("fees", "1.00"),
    ],
)
def test_strategy_trade_numeric_fields_must_be_numeric(
    field: str,
    value: object,
) -> None:
    kwargs = {field: value}

    with pytest.raises(TypeError, match=f"{field} must be numeric"):
        make_trade(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("entry_price", 0, "entry_price must be greater than zero"),
        ("entry_price", -1, "entry_price must be greater than zero"),
        ("exit_price", 0, "exit_price must be greater than zero"),
        ("quantity", 0, "quantity must be greater than zero"),
        ("fees", -0.01, "fees cannot be negative"),
    ],
)
def test_strategy_trade_numeric_value_validation(
    field: str,
    value: float,
    message: str,
) -> None:
    kwargs = {field: value}

    with pytest.raises(ValueError, match=message):
        make_trade(**kwargs)


def test_strategy_trade_time_validation() -> None:
    with pytest.raises(TypeError, match="entry_time must be a datetime"):
        make_trade(entry_time="2026-01-01")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="exit_time must be a datetime"):
        make_trade(exit_time="2026-01-01")  # type: ignore[arg-type]

    with pytest.raises(
        ValueError,
        match="exit_time cannot be before entry_time",
    ):
        make_trade(
            entry_time=BASE_TIME,
            exit_time=BASE_TIME - timedelta(minutes=1),
        )


def test_strategy_trade_profit_and_return_metrics() -> None:
    trade = make_trade(
        entry_price=100.0,
        exit_price=110.0,
        quantity=10.0,
        fees=5.0,
    )

    assert trade.gross_profit == pytest.approx(100.0)
    assert trade.net_profit == pytest.approx(95.0)
    assert trade.return_pct == pytest.approx(0.095)
    assert trade.holding_seconds == pytest.approx(3600.0)
    assert trade.is_winner is True
    assert trade.is_loser is False
    assert trade.is_breakeven is False


def test_strategy_trade_loser_and_breakeven_classification() -> None:
    loser = make_trade(exit_price=90.0)
    breakeven = make_trade(exit_price=100.0)

    assert loser.is_loser is True
    assert loser.is_winner is False
    assert loser.is_breakeven is False

    assert breakeven.is_breakeven is True
    assert breakeven.is_winner is False
    assert breakeven.is_loser is False


def test_strategy_trade_to_dict() -> None:
    trade = make_trade(fees=1.5)

    data = trade.to_dict()

    assert data["strategy_name"] == "Test Strategy"
    assert data["symbol"] == "AAPL"
    assert data["entry_time"] == BASE_TIME.isoformat()
    assert data["exit_time"] == (
        BASE_TIME + timedelta(hours=1)
    ).isoformat()
    assert data["gross_profit"] == pytest.approx(100.0)
    assert data["net_profit"] == pytest.approx(98.5)


def test_default_analyzer_initialization() -> None:
    analyzer = StrategyPerformanceAnalyzer()

    assert analyzer.trade_count == 0
    assert analyzer.trades == ()
    assert analyzer.strategy_names == ()
    assert analyzer.risk_free_rate == 0.0
    assert analyzer.periods_per_year == 252


def test_analyzer_initialization_with_trades() -> None:
    trades = [
        make_trade(strategy_name="RSI"),
        make_trade(strategy_name="MACD"),
    ]

    analyzer = StrategyPerformanceAnalyzer(trades)

    assert analyzer.trade_count == 2
    assert analyzer.strategy_names == ("MACD", "RSI")
    assert analyzer.trades == tuple(trades)


@pytest.mark.parametrize("value", ["0.02", None, True])
def test_risk_free_rate_must_be_numeric(value: object) -> None:
    with pytest.raises(TypeError, match="risk_free_rate must be numeric"):
        StrategyPerformanceAnalyzer(
            risk_free_rate=value,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("value", [252.0, "252", True, None])
def test_periods_per_year_must_be_integer(value: object) -> None:
    with pytest.raises(
        TypeError,
        match="periods_per_year must be an integer",
    ):
        StrategyPerformanceAnalyzer(
            periods_per_year=value,  # type: ignore[arg-type]
        )


def test_periods_per_year_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="periods_per_year must be greater than zero",
    ):
        StrategyPerformanceAnalyzer(periods_per_year=0)


def test_add_trade_and_add_trades() -> None:
    analyzer = StrategyPerformanceAnalyzer()
    first = make_trade(strategy_name="RSI")
    second = make_trade(strategy_name="MACD")

    analyzer.add_trade(first)
    analyzer.add_trades([second])

    assert analyzer.trade_count == 2
    assert analyzer.trades == (first, second)


def test_add_trade_rejects_invalid_object() -> None:
    analyzer = StrategyPerformanceAnalyzer()

    with pytest.raises(TypeError, match="trade must be a StrategyTrade"):
        analyzer.add_trade(object())  # type: ignore[arg-type]


def test_add_trades_rejects_string() -> None:
    analyzer = StrategyPerformanceAnalyzer()

    with pytest.raises(
        TypeError,
        match="trades must be an iterable of StrategyTrade",
    ):
        analyzer.add_trades("invalid")  # type: ignore[arg-type]


def test_clear_removes_all_trades() -> None:
    analyzer = StrategyPerformanceAnalyzer([make_trade()])

    analyzer.clear()

    assert analyzer.trade_count == 0
    assert analyzer.trades == ()
    assert analyzer.strategy_names == ()


def test_trades_for_strategy() -> None:
    rsi_trade = make_trade(strategy_name="RSI")
    macd_trade = make_trade(strategy_name="MACD")
    analyzer = StrategyPerformanceAnalyzer([rsi_trade, macd_trade])

    assert analyzer.trades_for_strategy(" RSI ") == (rsi_trade,)
    assert analyzer.trades_for_strategy("Unknown") == ()


def test_trades_for_strategy_validation() -> None:
    analyzer = StrategyPerformanceAnalyzer()

    with pytest.raises(
        TypeError,
        match="strategy_name must be a string",
    ):
        analyzer.trades_for_strategy(123)  # type: ignore[arg-type]

    with pytest.raises(
        ValueError,
        match="strategy_name cannot be empty",
    ):
        analyzer.trades_for_strategy("   ")


def test_empty_summary() -> None:
    analyzer = StrategyPerformanceAnalyzer()

    summary = analyzer.summarize()

    assert summary["total_trades"] == 0
    assert summary["winning_trades"] == 0
    assert summary["losing_trades"] == 0
    assert summary["breakeven_trades"] == 0
    assert summary["win_rate"] == 0.0
    assert summary["loss_rate"] == 0.0
    assert summary["net_profit"] == 0.0
    assert summary["profit_factor"] == 0.0
    assert summary["maximum_drawdown"] == 0.0
    assert summary["sharpe_ratio"] == 0.0


def test_summary_metrics() -> None:
    trades = [
        make_trade(
            entry_price=100.0,
            exit_price=110.0,
            quantity=10.0,
            fees=5.0,
        ),
        make_trade(
            entry_price=100.0,
            exit_price=95.0,
            quantity=10.0,
            fees=5.0,
            exit_time=BASE_TIME + timedelta(hours=2),
        ),
        make_trade(
            entry_price=100.0,
            exit_price=100.0,
            quantity=10.0,
            fees=0.0,
            exit_time=BASE_TIME + timedelta(hours=3),
        ),
    ]
    analyzer = StrategyPerformanceAnalyzer(trades)

    summary = analyzer.summarize()

    assert summary["total_trades"] == 3
    assert summary["winning_trades"] == 1
    assert summary["losing_trades"] == 1
    assert summary["breakeven_trades"] == 1
    assert summary["win_rate"] == pytest.approx(1 / 3)
    assert summary["loss_rate"] == pytest.approx(1 / 3)
    assert summary["gross_profit"] == pytest.approx(95.0)
    assert summary["gross_loss"] == pytest.approx(55.0)
    assert summary["net_profit"] == pytest.approx(40.0)
    assert summary["total_fees"] == pytest.approx(10.0)
    assert summary["average_win"] == pytest.approx(95.0)
    assert summary["average_loss"] == pytest.approx(-55.0)
    assert summary["average_trade"] == pytest.approx(40 / 3)
    assert summary["profit_factor"] == pytest.approx(95 / 55)
    assert summary["expectancy"] == pytest.approx(40 / 3)


def test_profit_factor_is_infinite_without_losses() -> None:
    analyzer = StrategyPerformanceAnalyzer(
        [
            make_trade(exit_price=110.0),
            make_trade(exit_price=105.0),
        ]
    )

    summary = analyzer.summarize()

    assert isinf(summary["profit_factor"])


def test_maximum_drawdown_uses_exit_order() -> None:
    trades = [
        make_trade(
            exit_price=110.0,
            exit_time=BASE_TIME + timedelta(hours=1),
        ),
        make_trade(
            exit_price=95.0,
            quantity=10.0,
            exit_time=BASE_TIME + timedelta(hours=2),
        ),
        make_trade(
            exit_price=92.0,
            quantity=10.0,
            exit_time=BASE_TIME + timedelta(hours=3),
        ),
        make_trade(
            exit_price=115.0,
            quantity=10.0,
            exit_time=BASE_TIME + timedelta(hours=4),
        ),
    ]
    analyzer = StrategyPerformanceAnalyzer(trades)

    summary = analyzer.summarize()

    assert summary["maximum_drawdown"] == pytest.approx(130.0)


def test_sharpe_ratio_is_zero_with_too_few_trades() -> None:
    analyzer = StrategyPerformanceAnalyzer([make_trade()])

    assert analyzer.summarize()["sharpe_ratio"] == 0.0


def test_sharpe_ratio_is_zero_with_identical_returns() -> None:
    analyzer = StrategyPerformanceAnalyzer(
        [
            make_trade(exit_price=110.0),
            make_trade(
                exit_price=110.0,
                exit_time=BASE_TIME + timedelta(hours=2),
            ),
        ]
    )

    assert analyzer.summarize()["sharpe_ratio"] == 0.0


def test_sharpe_ratio_is_calculated() -> None:
    analyzer = StrategyPerformanceAnalyzer(
        [
            make_trade(exit_price=110.0),
            make_trade(
                exit_price=105.0,
                exit_time=BASE_TIME + timedelta(hours=2),
            ),
            make_trade(
                exit_price=95.0,
                exit_time=BASE_TIME + timedelta(hours=3),
            ),
        ],
        risk_free_rate=0.02,
        periods_per_year=252,
    )

    assert analyzer.summarize()["sharpe_ratio"] != 0.0


def test_summarize_rejects_invalid_trade_collection() -> None:
    analyzer = StrategyPerformanceAnalyzer()

    with pytest.raises(
        TypeError,
        match="all trades must be StrategyTrade instances",
    ):
        analyzer.summarize([object()])  # type: ignore[list-item]


def test_summarize_strategy() -> None:
    analyzer = StrategyPerformanceAnalyzer(
        [
            make_trade(strategy_name="RSI", exit_price=110.0),
            make_trade(strategy_name="MACD", exit_price=90.0),
        ]
    )

    summary = analyzer.summarize_strategy("RSI")

    assert summary["strategy_name"] == "RSI"
    assert summary["total_trades"] == 1
    assert summary["net_profit"] == pytest.approx(100.0)


def test_summarize_all_strategies() -> None:
    analyzer = StrategyPerformanceAnalyzer(
        [
            make_trade(strategy_name="RSI"),
            make_trade(strategy_name="MACD"),
        ]
    )

    summaries = analyzer.summarize_all_strategies()

    assert set(summaries) == {"RSI", "MACD"}
    assert summaries["RSI"]["strategy_name"] == "RSI"
    assert summaries["MACD"]["strategy_name"] == "MACD"


def test_rank_strategies_by_net_profit() -> None:
    analyzer = StrategyPerformanceAnalyzer(
        [
            make_trade(strategy_name="RSI", exit_price=120.0),
            make_trade(strategy_name="MACD", exit_price=105.0),
            make_trade(strategy_name="Breakout", exit_price=90.0),
        ]
    )

    rankings = analyzer.rank_strategies()

    assert [
        summary["strategy_name"] for summary in rankings
    ] == ["RSI", "MACD", "Breakout"]


def test_rank_strategies_ascending() -> None:
    analyzer = StrategyPerformanceAnalyzer(
        [
            make_trade(strategy_name="RSI", exit_price=120.0),
            make_trade(strategy_name="MACD", exit_price=105.0),
        ]
    )

    rankings = analyzer.rank_strategies(descending=False)

    assert [
        summary["strategy_name"] for summary in rankings
    ] == ["MACD", "RSI"]


def test_rank_strategies_validation() -> None:
    analyzer = StrategyPerformanceAnalyzer([make_trade()])

    with pytest.raises(TypeError, match="metric must be a string"):
        analyzer.rank_strategies(123)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="metric cannot be empty"):
        analyzer.rank_strategies("   ")

    with pytest.raises(
        KeyError,
        match="unknown performance metric: missing",
    ):
        analyzer.rank_strategies("missing")

    with pytest.raises(
        TypeError,
        match="performance metric 'strategy_name' is not numeric",
    ):
        analyzer.rank_strategies("strategy_name")


def test_rank_strategies_empty_analyzer() -> None:
    analyzer = StrategyPerformanceAnalyzer()

    assert analyzer.rank_strategies() == []


def test_best_strategy() -> None:
    analyzer = StrategyPerformanceAnalyzer(
        [
            make_trade(strategy_name="RSI", exit_price=115.0),
            make_trade(strategy_name="MACD", exit_price=105.0),
        ]
    )

    best = analyzer.best_strategy()

    assert best is not None
    assert best["strategy_name"] == "RSI"


def test_best_strategy_returns_none_when_empty() -> None:
    analyzer = StrategyPerformanceAnalyzer()

    assert analyzer.best_strategy() is None


def test_to_dict() -> None:
    analyzer = StrategyPerformanceAnalyzer(
        [make_trade(strategy_name="RSI")],
        risk_free_rate=0.03,
        periods_per_year=365,
    )

    data = analyzer.to_dict()

    assert data["trade_count"] == 1
    assert data["strategy_names"] == ["RSI"]
    assert data["risk_free_rate"] == 0.03
    assert data["periods_per_year"] == 365
    assert data["overall"]["total_trades"] == 1
    assert "RSI" in data["strategies"]
    assert len(data["trades"]) == 1


def test_repr() -> None:
    analyzer = StrategyPerformanceAnalyzer(
        [
            make_trade(strategy_name="RSI"),
            make_trade(strategy_name="MACD"),
        ]
    )

    assert repr(analyzer) == (
        "StrategyPerformanceAnalyzer("
        "trade_count=2, strategy_count=2)"
    )
