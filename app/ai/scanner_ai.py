"""
Scanner AI
Version 6.0
"""

import random


def score_symbol(symbol: str) -> dict:
    """
    Temporary AI scoring engine.

    Later this will use:
        - TradingView indicators
        - Volume
        - Trend
        - News
        - OpenAI
    """

    score = random.randint(60, 99)

    if score >= 90:
        action = "BUY"

    elif score >= 80:
        action = "WATCH"

    else:
        action = "IGNORE"

    return {
        "symbol": symbol,
        "score": score,
        "action": action,
    }