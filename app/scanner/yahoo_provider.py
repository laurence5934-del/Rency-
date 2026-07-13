"""
Yahoo Finance Market Data Provider
AI Trading Platform Version 6.2

Uses yfinance to retrieve daily historical OHLCV data.
Research and paper-trading use only.
"""

from typing import Any

import pandas as pd
import yfinance as yf


class YahooProviderError(RuntimeError):
    """Raised when Yahoo Finance data cannot be retrieved or validated."""


def _safe_float(value: Any) -> float:
    if pd.isna(value):
        raise YahooProviderError("Required market-data value is missing.")

    return float(value)


def get_symbol_data(
    symbol: str,
    *,
    period: str = "1y",
    interval: str = "1d",
) -> dict[str, Any]:
    symbol = symbol.strip().upper()

    if not symbol:
        raise ValueError("symbol cannot be empty.")

    ticker = yf.Ticker(symbol)

    history = ticker.history(
        period=period,
        interval=interval,
        auto_adjust=True,
        actions=False,
    )

    if history.empty:
        raise YahooProviderError(
            f"No Yahoo Finance history returned for {symbol}."
        )

    required_columns = {
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    }

    missing_columns = required_columns.difference(history.columns)

    if missing_columns:
        raise YahooProviderError(
            f"Missing columns for {symbol}: "
            f"{sorted(missing_columns)}"
        )

    history = history.dropna(
        subset=["High", "Low", "Close", "Volume"]
    ).copy()

    if len(history) < 200:
        raise YahooProviderError(
            f"{symbol} returned only {len(history)} usable bars; "
            "at least 200 daily bars are required."
        )

    closes_series = history["Close"].astype(float)
    highs_series = history["High"].astype(float)
    lows_series = history["Low"].astype(float)
    volume_series = history["Volume"].astype(float)

    current_price = _safe_float(closes_series.iloc[-1])

    sma20 = _safe_float(
        closes_series.rolling(20).mean().iloc[-1]
    )

    sma50 = _safe_float(
        closes_series.rolling(50).mean().iloc[-1]
    )

    sma200 = _safe_float(
        closes_series.rolling(200).mean().iloc[-1]
    )

    current_volume = _safe_float(volume_series.iloc[-1])

    average_volume = _safe_float(
        volume_series.tail(20).mean()
    )

    analysis_bars = history.tail(60)

    closing_prices = (
        analysis_bars["Close"]
        .astype(float)
        .round(4)
        .tolist()
    )

    highs = (
        analysis_bars["High"]
        .astype(float)
        .round(4)
        .tolist()
    )

    lows = (
        analysis_bars["Low"]
        .astype(float)
        .round(4)
        .tolist()
    )

    stop_loss = round(current_price * 0.98, 4)

    latest_timestamp = history.index[-1]

    return {
        "symbol": symbol,
        "current_price": round(current_price, 4),
        "sma20": round(sma20, 4),
        "sma50": round(sma50, 4),
        "sma200": round(sma200, 4),
        "closing_prices": closing_prices,
        "current_volume": round(current_volume, 2),
        "average_volume": round(average_volume, 2),
        "highs": highs,
        "lows": lows,
        "closes": closing_prices,
        "stop_loss": stop_loss,

        # Neutral placeholders until live news analysis is added.
        "sentiment": "NEUTRAL",
        "relevance": 0.5,
        "event_risk": "MEDIUM",
        "catalyst_strength": "WEAK",
        "source_quality": "MEDIUM",

        "data_source": "YAHOO_FINANCE_YFINANCE",
        "as_of": latest_timestamp.isoformat(),
        "period": period,
        "interval": interval,
    }