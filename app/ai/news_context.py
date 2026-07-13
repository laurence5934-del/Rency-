"""
News and AI Context Engine
AI Trading Platform Version 6.1
"""

from typing import Any


def calculate_news_context_score(
    *,
    sentiment: str,
    relevance: float,
    event_risk: str,
    catalyst_strength: str,
    source_quality: str = "MEDIUM",
) -> dict[str, Any]:
    """
    Calculate a news/context score from 0 to 15.

    This first version accepts structured inputs.
    Later, live news feeds and OpenAI can populate them.
    """

    normalized_sentiment = str(sentiment or "").upper()
    normalized_event_risk = str(event_risk or "").upper()
    normalized_catalyst = str(catalyst_strength or "").upper()
    normalized_source = str(source_quality or "").upper()

    relevance = max(0.0, min(1.0, float(relevance)))

    score = 0
    catalysts: list[str] = []
    warnings: list[str] = []
    reasons: list[str] = []

    # Sentiment: up to 5 points
    if normalized_sentiment == "BULLISH":
        score += 5
        reasons.append("News sentiment is bullish.")
    elif normalized_sentiment == "NEUTRAL":
        score += 2
        reasons.append("News sentiment is neutral.")
    elif normalized_sentiment == "BEARISH":
        warnings.append("News sentiment is bearish.")
        reasons.append("Bearish sentiment reduced the score.")

    # Relevance: up to 3 points
    relevance_points = round(relevance * 3)
    score += relevance_points
    reasons.append(
        f"News relevance contributed {relevance_points} point(s)."
    )

    # Catalyst strength: up to 4 points
    if normalized_catalyst == "STRONG":
        score += 4
        catalysts.append("Strong positive catalyst.")
    elif normalized_catalyst == "MEDIUM":
        score += 2
        catalysts.append("Moderate positive catalyst.")
    elif normalized_catalyst == "WEAK":
        score += 1
        catalysts.append("Weak positive catalyst.")

    # Source quality: up to 2 points
    if normalized_source == "HIGH":
        score += 2
        reasons.append("Source quality is high.")
    elif normalized_source == "MEDIUM":
        score += 1
        reasons.append("Source quality is medium.")
    else:
        warnings.append("Source quality is low.")

    # Event risk penalty: up to -4 points
    if normalized_event_risk == "HIGH":
        score -= 4
        warnings.append("High event risk.")
    elif normalized_event_risk == "MEDIUM":
        score -= 2
        warnings.append("Moderate event risk.")
    elif normalized_event_risk == "LOW":
        reasons.append("Event risk is low.")

    score = max(0, min(15, score))

    if score >= 12:
        context_status = "STRONG_BULLISH"
    elif score >= 9:
        context_status = "BULLISH"
    elif score >= 6:
        context_status = "NEUTRAL"
    elif score >= 3:
        context_status = "CAUTION"
    else:
        context_status = "BEARISH"

    return {
        "news_score": score,
        "context_status": context_status,
        "sentiment": normalized_sentiment,
        "relevance": round(relevance, 2),
        "event_risk": normalized_event_risk,
        "catalyst_strength": normalized_catalyst,
        "source_quality": normalized_source,
        "catalysts": catalysts,
        "warnings": warnings,
        "reasons": reasons,
    }