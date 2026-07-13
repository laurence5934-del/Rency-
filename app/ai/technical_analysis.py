"""
Technical Analysis Engine
AI Trading Platform Version 6.1
"""

from typing import Any


def calculate_trend_score(
    *,
    current_price: float,
    sma20: float,
    sma50: float,
    sma200: float,
) -> dict[str, Any]:
    """
    Calculates trend strength using
    moving averages.

    Maximum Score = 25
    """

    score = 0
    reasons = []

    if current_price > sma20:
        score += 5
        reasons.append("Price above 20 SMA")

    if current_price > sma50:
        score += 5
        reasons.append("Price above 50 SMA")

    if current_price > sma200:
        score += 5
        reasons.append("Price above 200 SMA")

    if sma20 > sma50:
        score += 5
        reasons.append("20 SMA above 50 SMA")

    if sma50 > sma200:
        score += 5
        reasons.append("50 SMA above 200 SMA")

    if score >= 25:
        trend = "STRONG_BULL"

    elif score >= 20:
        trend = "BULL"

    elif score >= 10:
        trend = "NEUTRAL"

    elif score >= 5:
        trend = "BEAR"

    else:
        trend = "STRONG_BEAR"

    return {
        "trend": trend,
        "trend_score": score,
        "reasons": reasons,
    }