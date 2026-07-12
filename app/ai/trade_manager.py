"""
AI Trade Manager
AI Trading Platform V5.3
"""


def analyze_trade(
    *,
    entry_price: float,
    current_price: float,
    health_score: int,
    ai_decision: str,
    ai_risk: str,
):
    gain_pct = ((current_price - entry_price) / entry_price) * 100

    recommendation = "WATCH"
    confidence = 75
    reasons = []

    if gain_pct >= 15:
        recommendation = "TAKE_PROFIT"
        confidence = 95
        reasons.append("Position has exceeded the profit target.")

    elif gain_pct <= -7:
        recommendation = "EXIT"
        confidence = 95
        reasons.append("Maximum loss threshold reached.")

    elif health_score >= 80 and ai_decision.upper() == "BUY":
        recommendation = "HOLD"
        confidence = 90
        reasons.append("AI continues to support the position.")

    elif health_score < 40:
        recommendation = "EXIT"
        confidence = 90
        reasons.append("Position health has deteriorated.")

    stop_loss = round(entry_price * 0.95, 2)
    take_profit = round(entry_price * 1.15, 2)

    return {
        "gain_pct": round(gain_pct, 2),
        "recommendation": recommendation,
        "confidence": confidence,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "reasons": reasons,
    }