"""
Master Technical and Context Scoring Engine
AI Trading Platform Version 6.1

Combines:
- Trend
- Momentum
- Volume
- Volatility
- Risk
- News and AI Context

Maximum total score: 100
"""

from typing import Any

from app.ai.technical_analysis import calculate_trend_score
from app.ai.momentum import calculate_momentum_score
from app.ai.volume import calculate_volume_score
from app.ai.volatility import calculate_volatility_score
from app.ai.risk import calculate_risk_score
from app.ai.news_context import calculate_news_context_score


def analyze_symbol(
    *,
    symbol: str,
    current_price: float,
    sma20: float,
    sma50: float,
    sma200: float,
    closing_prices: list[float],
    current_volume: float,
    average_volume: float,
    highs: list[float],
    lows: list[float],
    closes: list[float],
    stop_loss: float,
    sentiment: str,
    relevance: float,
    event_risk: str,
    catalyst_strength: str,
    source_quality: str = "MEDIUM",
) -> dict[str, Any]:
    trend_result = calculate_trend_score(
        current_price=current_price,
        sma20=sma20,
        sma50=sma50,
        sma200=sma200,
    )

    momentum_result = calculate_momentum_score(
        closing_prices
    )

    volume_result = calculate_volume_score(
        current_volume=current_volume,
        average_volume=average_volume,
    )

    volatility_result = calculate_volatility_score(
        highs=highs,
        lows=lows,
        closes=closes,
    )

    risk_result = calculate_risk_score(
        current_price=current_price,
        stop_loss=stop_loss,
    )

    news_result = calculate_news_context_score(
        sentiment=sentiment,
        relevance=relevance,
        event_risk=event_risk,
        catalyst_strength=catalyst_strength,
        source_quality=source_quality,
    )

    component_scores = {
        "trend": int(trend_result["trend_score"]),
        "momentum": int(momentum_result["momentum_score"]),
        "volume": int(volume_result["volume_score"]),
        "volatility": int(
            volatility_result["volatility_score"]
        ),
        "risk": int(risk_result["risk_score"]),
        "news": int(news_result["news_score"]),
    }

    total_score = sum(component_scores.values())
    total_score = max(0, min(100, total_score))

    if total_score >= 90:
        grade = "A+"
        action = "STRONG_BUY"
    elif total_score >= 80:
        grade = "A"
        action = "BUY"
    elif total_score >= 70:
        grade = "B"
        action = "WATCH"
    elif total_score >= 60:
        grade = "C"
        action = "CAUTION"
    else:
        grade = "D"
        action = "IGNORE"

    reasons = (
        trend_result["reasons"]
        + momentum_result["reasons"]
        + volume_result["reasons"]
        + volatility_result["reasons"]
        + risk_result["reasons"]
        + news_result["reasons"]
    )

    warnings = list(news_result["warnings"])

    if momentum_result["rsi"] > 75:
        warnings.append(
            "RSI is overbought; entry timing may be unfavorable."
        )

    if volatility_result["volatility_status"] == "EXTREME":
        warnings.append(
            "Volatility is extreme."
        )

    if risk_result["risk_status"] in {"HIGH", "EXTREME"}:
        warnings.append(
            "Stop-loss distance indicates elevated risk."
        )

    return {
        "symbol": symbol.upper(),
        "total_score": total_score,
        "grade": grade,
        "action": action,
        "component_scores": component_scores,
        "trend": trend_result,
        "momentum": momentum_result,
        "volume": volume_result,
        "volatility": volatility_result,
        "risk": risk_result,
        "news_context": news_result,
        "reasons": reasons,
        "warnings": warnings,
    }