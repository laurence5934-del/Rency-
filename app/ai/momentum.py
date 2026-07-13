"""
Momentum Analysis Engine
AI Trading Platform Version 6.1

Calculates:
- RSI
- MACD
- Momentum score from 0 to 20
"""

from typing import Any


def calculate_ema(values: list[float], period: int) -> float:
    if period <= 0:
        raise ValueError("period must be greater than zero.")

    if len(values) < period:
        raise ValueError(
            f"At least {period} values are required."
        )

    multiplier = 2 / (period + 1)

    ema = sum(values[:period]) / period

    for value in values[period:]:
        ema = (
            value * multiplier
            + ema * (1 - multiplier)
        )

    return ema


def calculate_rsi(
    closing_prices: list[float],
    period: int = 14,
) -> float:
    if len(closing_prices) < period + 1:
        raise ValueError(
            f"At least {period + 1} closing prices are required."
        )

    changes = [
        closing_prices[index]
        - closing_prices[index - 1]
        for index in range(1, len(closing_prices))
    ]

    recent_changes = changes[-period:]

    gains = [
        max(change, 0)
        for change in recent_changes
    ]

    losses = [
        abs(min(change, 0))
        for change in recent_changes
    ]

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period

    if average_loss == 0:
        return 100.0

    relative_strength = average_gain / average_loss

    rsi = 100 - (
        100 / (1 + relative_strength)
    )

    return round(rsi, 2)


def calculate_macd(
    closing_prices: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
) -> dict[str, float]:
    if len(closing_prices) < slow_period:
        raise ValueError(
            f"At least {slow_period} closing prices are required."
        )

    fast_ema = calculate_ema(
        closing_prices,
        fast_period,
    )

    slow_ema = calculate_ema(
        closing_prices,
        slow_period,
    )

    macd_value = fast_ema - slow_ema

    return {
        "fast_ema": round(fast_ema, 4),
        "slow_ema": round(slow_ema, 4),
        "macd": round(macd_value, 4),
    }


def calculate_momentum_score(
    closing_prices: list[float],
) -> dict[str, Any]:
    """
    Calculate a momentum score from 0 to 20.

    RSI contributes up to 10 points.
    MACD contributes up to 10 points.
    """

    rsi = calculate_rsi(closing_prices)
    macd_result = calculate_macd(closing_prices)

    macd_value = macd_result["macd"]

    score = 0
    reasons: list[str] = []

    # RSI score: maximum 10 points.
    if 50 <= rsi <= 65:
        score += 10
        reasons.append(
            "RSI shows healthy bullish momentum."
        )
    elif 40 <= rsi < 50:
        score += 6
        reasons.append(
            "RSI is neutral but improving."
        )
    elif 65 < rsi <= 75:
        score += 7
        reasons.append(
            "RSI is bullish but approaching overbought."
        )
    elif rsi < 30:
        score += 4
        reasons.append(
            "RSI is oversold; reversal is possible."
        )
    elif rsi > 75:
        score += 2
        reasons.append(
            "RSI is overbought."
        )
    else:
        score += 3
        reasons.append(
            "RSI momentum is weak."
        )

    # MACD score: maximum 10 points.
    if macd_value > 0:
        score += 10
        reasons.append(
            "MACD is positive."
        )
    elif macd_value == 0:
        score += 5
        reasons.append(
            "MACD is neutral."
        )
    else:
        reasons.append(
            "MACD is negative."
        )

    if score >= 17:
        momentum = "STRONG"
    elif score >= 13:
        momentum = "BULLISH"
    elif score >= 8:
        momentum = "NEUTRAL"
    elif score >= 4:
        momentum = "WEAK"
    else:
        momentum = "BEARISH"

    return {
        "momentum": momentum,
        "momentum_score": score,
        "rsi": rsi,
        "macd": macd_value,
        "fast_ema": macd_result["fast_ema"],
        "slow_ema": macd_result["slow_ema"],
        "reasons": reasons,
    }