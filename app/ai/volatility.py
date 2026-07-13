"""
Volatility Analysis Engine
AI Trading Platform Version 6.1
"""

from typing import Any


def calculate_true_range(
    high: float,
    low: float,
    previous_close: float,
) -> float:
    return max(
        high - low,
        abs(high - previous_close),
        abs(low - previous_close),
    )


def calculate_atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> float:
    if period <= 0:
        raise ValueError("period must be greater than zero.")

    if not (
        len(highs) == len(lows) == len(closes)
    ):
        raise ValueError(
            "highs, lows, and closes must have equal length."
        )

    if len(closes) < period + 1:
        raise ValueError(
            f"At least {period + 1} price bars are required."
        )

    true_ranges = []

    for index in range(1, len(closes)):
        true_ranges.append(
            calculate_true_range(
                high=float(highs[index]),
                low=float(lows[index]),
                previous_close=float(closes[index - 1]),
            )
        )

    recent_ranges = true_ranges[-period:]
    atr = sum(recent_ranges) / period

    return round(atr, 4)


def calculate_volatility_score(
    *,
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> dict[str, Any]:
    """
    Calculate a volatility score from 0 to 10.

    Moderate volatility receives the highest score.
    Extremely high or very low volatility scores lower.
    """

    atr = calculate_atr(
        highs=highs,
        lows=lows,
        closes=closes,
        period=period,
    )

    current_price = float(closes[-1])

    if current_price <= 0:
        raise ValueError(
            "The latest closing price must be greater than zero."
        )

    atr_pct = (
        atr / current_price
        * 100
    )

    if 1.0 <= atr_pct <= 3.0:
        score = 10
        status = "HEALTHY"
        reasons = [
            "Volatility is in a healthy trading range."
        ]

    elif 0.5 <= atr_pct < 1.0:
        score = 7
        status = "LOW"
        reasons = [
            "Volatility is low but still tradable."
        ]

    elif 3.0 < atr_pct <= 5.0:
        score = 6
        status = "HIGH"
        reasons = [
            "Volatility is elevated; risk controls are important."
        ]

    elif atr_pct < 0.5:
        score = 3
        status = "VERY_LOW"
        reasons = [
            "Volatility is very low; price movement may be limited."
        ]

    else:
        score = 2
        status = "EXTREME"
        reasons = [
            "Volatility is extreme and may increase trading risk."
        ]

    return {
        "volatility_score": score,
        "volatility_status": status,
        "atr": atr,
        "atr_pct": round(atr_pct, 2),
        "reasons": reasons,
    }