import pytest

from app.scanner.market_scanner import MarketScanner
from app.scanner.scanner_config import ScannerConfig
from app.scanner.scanner_models import ScanResult, ScanSummary


def test_default_scanner_config():
    config = ScannerConfig()

    assert config.min_total_score == 70.0
    assert config.relative_volume_threshold == 1.20


def test_scan_result_defaults():
    result = ScanResult(symbol="AAPL", last_price=200.0)

    assert result.symbol == "AAPL"
    assert result.total_score == 0.0
    assert result.qualified is False
    assert result.reasons == []


def test_scan_summary_creation():
    summary = ScanSummary(
        total_symbols=1,
        qualified_symbols=0,
        results=[]
    )

    assert summary.total_symbols == 1
    assert summary.qualified_symbols == 0


def test_market_scanner_initialization():
    scanner = MarketScanner()

    assert isinstance(scanner.config, ScannerConfig)


def test_market_scanner_scan_not_implemented():
    scanner = MarketScanner()

    with pytest.raises(NotImplementedError):
        scanner.scan(["AAPL"])