"""
Scanner Data Provider
AI Trading Platform Version 6.1

Provides deterministic development data for the scanner.
This is not live market data.
"""

from typing import Any


def get_symbol_data(symbol: str) -> dict[str, Any]:
    symbol = symbol.upper()

    base_prices = {
        "NVDA": 120.0,
        "AMD": 165.0,
        "AVGO": 245.0,
        "MSFT": 510.0,
        "META": 720.0,
        "AAPL": 235.0,
        "AMZN": 240.0,
        "GOOGL": 195.0,
        "TSLA": 320.0,
        "SMCI": 58.0,
        "PLTR": 155.0,
        "NFLX": 1280.0,
        "QQQ": 610.0,
        "SPY": 690.0,
        "SMH": 360.0,
    }

    current_price = base_prices.get(symbol, 100.0)

    closing_prices = [
        round(current_price * (0.82 + index * 0.006), 2)
        for index in range(30)
    ]

    highs = [
        round(price * 1.01, 2)
        for price in closing_prices
    ]

    lows = [
        round(price * 0.99, 2)
        for price in closing_prices
    ]

    sma20 = sum(closing_prices[-20:]) / 20
    sma50 = current_price * 0.92
    sma200 = current_price * 0.78

    current_volume = 2_500_000
    average_volume = 1_500_000
    stop_loss = current_price * 0.98

    return {
        "symbol": symbol,
        "current_price": current_price,
        "sma20": round(sma20, 2),
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
        "closing_prices": closing_prices,
        "current_volume": current_volume,
        "average_volume": average_volume,
        "highs": highs,
        "lows": lows,
        "closes": closing_prices,
        "stop_loss": round(stop_loss, 2),
        "sentiment": "BULLISH",
        "relevance": 0.9,
        "event_risk": "LOW",
        "catalyst_strength": "STRONG",
        "source_quality": "HIGH",
        "data_source": "DEVELOPMENT_MOCK",
    }