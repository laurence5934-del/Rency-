"""
Position Health Engine
AI Trading Platform V5.2
"""

from typing import Any


def score_position(
    *,
    quantity: float,
    avg_cost: float,
    current_price: float | None,
    latest_ai_score: int | None,
    latest_ai_decision: str | None,
    latest_ai_risk: str | None,
) -> dict[str, Any]:
    """
    Return a transparent 0-100 position health score.

    This is a rule-based first version for paper-trading analysis.
    """

    score = 50
    reasons: list[str] = []

    if current_price is None or avg_cost <= 0:
        return {
            "health_score": 0,
            "health_status": "NO DATA",
            "recommendation": "WATCH",
            "reasons": ["Current price or average cost is unavailable."],
        }

    pnl_pct = ((current_price - avg_cost) / avg_cost) * 100

    if quantity < 0:
        pnl_pct = -pnl_pct

    if pnl_pct >= 5:
        score += 20
        reasons.append("Position is gaining at least 5%.")
    elif pnl_pct >= 2:
        score += 12
        reasons.append("Position has positive momentum.")
    elif pnl_pct > 0:
        score += 5
        reasons.append("Position is slightly profitable.")
    elif pnl_pct <= -5:
        score -= 25
        reasons.append("Position is losing at least 5%.")
    elif pnl_pct <= -2:
        score -= 15
        reasons.append("Position is under meaningful pressure.")
    elif pnl_pct < 0:
        score -= 5
        reasons.append("Position is slightly below average cost.")

    ai_decision = str(latest_ai_decision or "").upper()

    if ai_decision == "BUY":
        score += 12
        reasons.append("Latest AI decision remains BUY.")
    elif ai_decision in {"WATCH", "HOLD"}:
        score += 3
        reasons.append("Latest AI decision is neutral-to-positive.")
    elif ai_decision in {"SELL", "EXIT", "NO_TRADE", "REJECT"}:
        score -= 18
        reasons.append("Latest AI decision is negative.")

    if latest_ai_score is not None:
        ai_score = int(latest_ai_score)

        if ai_score >= 90:
            score += 12
            reasons.append("Latest AI score is very strong.")
        elif ai_score >= 80:
            score += 8
            reasons.append("Latest AI score is strong.")
        elif ai_score >= 70:
            score += 3
            reasons.append("Latest AI score is moderate.")
        elif ai_score < 50:
            score -= 10
            reasons.append("Latest AI score is weak.")

    ai_risk = str(latest_ai_risk or "").upper()

    if ai_risk == "LOW":
        score += 8
        reasons.append("Latest AI risk rating is low.")
    elif ai_risk == "MEDIUM":
        reasons.append("Latest AI risk rating is medium.")
    elif ai_risk == "HIGH":
        score -= 15
        reasons.append("Latest AI risk rating is high.")

    score = max(0, min(100, score))

    if score >= 80:
        health_status = "STRONG"
        recommendation = "HOLD"
    elif score >= 65:
        health_status = "HEALTHY"
        recommendation = "HOLD"
    elif score >= 45:
        health_status = "CAUTION"
        recommendation = "WATCH"
    elif score >= 25:
        health_status = "WEAK"
        recommendation = "REDUCE"
    else:
        health_status = "CRITICAL"
        recommendation = "EXIT"

    return {
        "health_score": score,
        "health_status": health_status,
        "recommendation": recommendation,
        "reasons": reasons,
    }