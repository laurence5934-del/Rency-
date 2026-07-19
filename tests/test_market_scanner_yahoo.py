import pytest

from app.scanner.market_scanner import MarketScanner


@pytest.mark.integration
def test_scan_uses_default_provider_when_loader_is_missing(
    monkeypatch,
):
    provider_data = {
        "symbol": "AAPL",
        "highs": [
            101.0 + index
            for index in range(60)
        ],
        "lows": [
            99.0 + index
            for index in range(60)
        ],
        "closes": [
            100.0 + index
            for index in range(60)
        ],
        "current_volume": 1_500_000,
    }

    monkeypatch.setattr(
        "app.scanner.market_scanner."
        "get_yahoo_symbol_data",
        lambda symbol: provider_data,
    )

    scanner = MarketScanner()
    summary = scanner.scan(["AAPL"])

    assert summary.total_symbols == 1
    assert summary.results[0].symbol == "AAPL"
    assert summary.results[0].last_price > 0