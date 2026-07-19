import pandas as pd
import pytest

from app.scanner.market_scanner import MarketScanner
from app.scanner.scanner_config import ScannerConfig
from app.scanner.scanner_models import ScanResult, ScanSummary


def make_market_data(
    *,
    rows: int = 80,
    start_price: float = 100.0,
    daily_increase: float = 0.50,
    final_volume_multiplier: float = 2.0,
) -> pd.DataFrame:
    close = [
        start_price + index * daily_increase
        for index in range(rows)
    ]

    volume = [1_000_000.0] * rows
    volume[-1] *= final_volume_multiplier

    return pd.DataFrame(
        {
            "open": [price - 0.25 for price in close],
            "high": [price + 1.00 for price in close],
            "low": [price - 1.00 for price in close],
            "close": close,
            "volume": volume,
        }
    )


def test_default_scanner_config():
    config = ScannerConfig()

    assert config.min_total_score == 70.0
    assert config.relative_volume_threshold == 1.20


def test_scan_result_defaults():
    result = ScanResult(
        symbol="AAPL",
        last_price=200.0,
    )

    assert result.symbol == "AAPL"
    assert result.total_score == 0.0
    assert result.qualified is False
    assert result.reasons == []


def test_scan_summary_creation():
    summary = ScanSummary(
        total_symbols=1,
        qualified_symbols=0,
        results=[],
    )

    assert summary.total_symbols == 1
    assert summary.qualified_symbols == 0
    assert summary.results == []


def test_market_scanner_initialization():
    scanner = MarketScanner()

    assert isinstance(scanner.config, ScannerConfig)
    assert scanner.data_loader is None


def test_scan_symbol_returns_scored_result():
    data = make_market_data()

    scanner = MarketScanner(
        data_loader=lambda symbol: data,
    )

    result = scanner.scan_symbol("aapl")

    assert result.symbol == "AAPL"
    assert result.last_price > 0
    assert result.total_score > 0
    assert result.total_score <= 100
    assert len(result.reasons) > 0


def test_scan_returns_summary():
    data = make_market_data()

    scanner = MarketScanner(
        data_loader=lambda symbol: data,
    )

    summary = scanner.scan(
        ["AAPL", "MSFT"],
    )

    assert summary.total_symbols == 2
    assert len(summary.results) == 2
    assert {
        result.symbol for result in summary.results
    } == {"AAPL", "MSFT"}


def test_scan_ranks_highest_score_first():
    strong_data = make_market_data(
        daily_increase=0.75,
        final_volume_multiplier=2.5,
    )

    weak_data = make_market_data(
        daily_increase=-0.10,
        final_volume_multiplier=0.50,
    )

    market_data = {
        "STRONG": strong_data,
        "WEAK": weak_data,
    }

    scanner = MarketScanner(
        data_loader=lambda symbol: market_data[symbol],
    )

    summary = scanner.scan(
        ["WEAK", "STRONG"],
    )

    assert summary.results[0].symbol == "STRONG"
    assert (
        summary.results[0].total_score
        >= summary.results[1].total_score
    )


def test_scan_removes_duplicate_symbols():
    data = make_market_data()

    scanner = MarketScanner(
        data_loader=lambda symbol: data,
    )

    summary = scanner.scan(
        ["aapl", "AAPL", " msft ", "MSFT"],
    )

    assert summary.total_symbols == 2
    assert [
        result.symbol for result in summary.results
    ] == ["AAPL", "MSFT"]


def test_scan_records_loader_failure():
    def failing_loader(symbol: str) -> pd.DataFrame:
        raise ConnectionError("Test data source unavailable.")

    scanner = MarketScanner(
        data_loader=failing_loader,
    )

    summary = scanner.scan(["AAPL"])

    result = summary.results[0]

    assert result.symbol == "AAPL"
    assert result.total_score == 0.0
    assert result.qualified is False
    assert "ConnectionError" in result.reasons[0]


def test_scan_accepts_single_symbol_string():
    data = make_market_data()

    scanner = MarketScanner(
        data_loader=lambda symbol: data,
    )

    summary = scanner.scan("aapl")

    assert summary.total_symbols == 1
    assert summary.results[0].symbol == "AAPL"


def test_scan_rejects_empty_symbol():
    data = make_market_data()

    scanner = MarketScanner(
        data_loader=lambda symbol: data,
    )

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        scanner.scan([""])


def test_scan_result_score_components_are_bounded():
    data = make_market_data()

    scanner = MarketScanner(
        data_loader=lambda symbol: data,
    )

    result = scanner.scan_symbol("AAPL")

    assert 0 <= result.trend_score <= 30
    assert 0 <= result.momentum_score <= 25
    assert 0 <= result.volume_score <= 20
    assert 0 <= result.breakout_score <= 15
    assert 0 <= result.risk_score <= 10
    assert 0 <= result.total_score <= 100