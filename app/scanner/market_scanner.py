"""
Live AI Market Scanner
AI Trading Platform Version 6.2

Uses Yahoo Finance daily data and the explainable
100-point master scoring engine.

Research and paper-trading use only.
"""

from typing import Any

from app.ai.master_scoring import analyze_symbol
from app.scanner.yahoo_provider import (
    YahooProviderError,
    get_symbol_data,
)


WATCHLIST = [
    "NVDA",
    "AMD",
    "AVGO",
    "MSFT",
    "META",
    "AAPL",
    "AMZN",
    "GOOGL",
    "TSLA",
    "SMCI",
    "PLTR",
    "NFLX",
    "QQQ",
    "SPY",
    "SMH",
]


def get_watchlist() -> list[str]:
    return WATCHLIST.copy()


def analyze_live_symbol(symbol: str) -> dict[str, Any]:
    data = get_symbol_data(symbol)

    result = analyze_symbol(
        symbol=data["symbol"],
        current_price=data["current_price"],
        sma20=data["sma20"],
        sma50=data["sma50"],
        sma200=data["sma200"],
        closing_prices=data["closing_prices"],
        current_volume=data["current_volume"],
        average_volume=data["average_volume"],
        highs=data["highs"],
        lows=data["lows"],
        closes=data["closes"],
        stop_loss=data["stop_loss"],
        sentiment=data["sentiment"],
        relevance=data["relevance"],
        event_risk=data["event_risk"],
        catalyst_strength=data["catalyst_strength"],
        source_quality=data["source_quality"],
    )

    return {
        "symbol": result["symbol"],
        "score": result["total_score"],
        "grade": result["grade"],
        "action": result["action"],
        "price": data["current_price"],
        "trend": result["trend"]["trend"],
        "trend_score": result["component_scores"]["trend"],
        "momentum": result["momentum"]["momentum"],
        "momentum_score": result["component_scores"]["momentum"],
        "rsi": result["momentum"]["rsi"],
        "macd": result["momentum"]["macd"],
        "relative_volume": result["volume"]["relative_volume"],
        "volume_score": result["component_scores"]["volume"],
        "volatility": result["volatility"]["volatility_status"],
        "volatility_score": result["component_scores"]["volatility"],
        "risk": result["risk"]["risk_status"],
        "risk_score": result["component_scores"]["risk"],
        "news_score": result["component_scores"]["news"],
        "data_source": data["data_source"],
        "as_of": data["as_of"],
        "reasons": result["reasons"],
        "warnings": result["warnings"],
    }


def scan_market() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for symbol in get_watchlist():
        try:
            results.append(analyze_live_symbol(symbol))

        except (YahooProviderError, ValueError) as exc:
            results.append(
                {
                    "symbol": symbol,
                    "score": 0,
                    "grade": "N/A",
                    "action": "DATA_ERROR",
                    "price": None,
                    "trend": "N/A",
                    "trend_score": 0,
                    "momentum": "N/A",
                    "momentum_score": 0,
                    "rsi": None,
                    "macd": None,
                    "relative_volume": None,
                    "volume_score": 0,
                    "volatility": "N/A",
                    "volatility_score": 0,
                    "risk": "N/A",
                    "risk_score": 0,
                    "news_score": 0,
                    "data_source": "YAHOO_FINANCE_YFINANCE",
                    "as_of": None,
                    "reasons": [],
                    "warnings": [str(exc)],
                }
            )

        except Exception as exc:
            results.append(
                {
                    "symbol": symbol,
                    "score": 0,
                    "grade": "N/A",
                    "action": "SYSTEM_ERROR",
                    "price": None,
                    "trend": "N/A",
                    "trend_score": 0,
                    "momentum": "N/A",
                    "momentum_score": 0,
                    "rsi": None,
                    "macd": None,
                    "relative_volume": None,
                    "volume_score": 0,
                    "volatility": "N/A",
                    "volatility_score": 0,
                    "risk": "N/A",
                    "risk_score": 0,
                    "news_score": 0,
                    "data_source": "UNKNOWN",
                    "as_of": None,
                    "reasons": [],
                    "warnings": [f"Unexpected error: {exc}"],
                }
            )

    return sorted(
        results,
        key=lambda item: item["score"],
        reverse=True,
    )