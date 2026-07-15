"""
AI Trading Assistant
AI Trading Platform Version 7.3

Generates a plain-English explanation from an
existing trade candidate and scanner analysis.

This module does not submit orders.
"""

from typing import Any


def build_trading_assistant_summary(
    *,
    opportunity: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    score = int(opportunity.get("score", 0) or 0)
    action = str(opportunity.get("action", "N/A")).upper()
    trend = str(opportunity.get("trend", "N/A"))
    momentum = str(opportunity.get("momentum", "N/A"))
    volume_score = int(opportunity.get("volume_score", 0) or 0)
    relative_volume = float(
        opportunity.get("relative_volume", 0) or 0
    )
    volatility = str(
        opportunity.get("volatility", "N/A")
    )
    risk = str(opportunity.get("risk", "N/A"))
    rsi = float(opportunity.get("rsi", 0) or 0)

    eligible = bool(
        candidate.get("approval_eligible", False)
    )
    risk_reward = float(
        candidate.get("risk_reward_ratio", 0) or 0
    )

    reasons: list[str] = []
    warnings: list[str] = []

    if trend in {"STRONG_BULL", "BULL"}:
        reasons.append(
            "The broader trend is bullish."
        )
    else:
        warnings.append(
            "The broader trend is not strongly bullish."
        )

    if momentum in {"STRONG", "BULLISH"}:
        reasons.append(
            "Momentum remains supportive."
        )
    else:
        warnings.append(
            "Momentum is not providing strong confirmation."
        )

    if relative_volume >= 1.2:
        reasons.append(
            "Trading volume is above average."
        )
    else:
        warnings.append(
            "Trading volume is below the preferred confirmation level."
        )

    if volatility == "HEALTHY":
        reasons.append(
            "Volatility is within a healthy trading range."
        )
    elif volatility in {"HIGH", "EXTREME"}:
        warnings.append(
            "Volatility is elevated and requires tighter risk control."
        )

    if risk == "LOW":
        reasons.append(
            "The current stop distance is within the preferred risk range."
        )
    else:
        warnings.append(
            f"Risk is currently classified as {risk}."
        )

    if rsi > 75:
        warnings.append(
            "RSI is overbought and entry timing may be unfavorable."
        )

    if risk_reward >= 2:
        reasons.append(
            f"The planned risk/reward ratio is {risk_reward:.2f}:1."
        )
    else:
        warnings.append(
            "The planned risk/reward ratio is below 2.0:1."
        )

    if eligible:
        recommendation = "APPROVE_FOR_REVIEW"
    elif action in {"WATCH", "CAUTION"}:
        recommendation = "WAIT"
    else:
        recommendation = "SKIP"

    if score >= 90 and eligible:
        confidence = 95
    elif score >= 80 and eligible:
        confidence = 88
    elif score >= 70:
        confidence = 75
    elif score >= 60:
        confidence = 65
    else:
        confidence = 50

    if recommendation == "APPROVE_FOR_REVIEW":
        summary = (
            "The setup meets the minimum score, action, "
            "position-size, and risk/reward requirements. "
            "It may proceed to paper-trade review."
        )
    elif recommendation == "WAIT":
        summary = (
            "The setup has some positive characteristics, "
            "but it does not yet meet all approval requirements. "
            "Wait for stronger confirmation."
        )
    else:
        summary = (
            "The setup does not currently meet the platform's "
            "minimum quality and risk standards."
        )

    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "summary": summary,
        "reasons": reasons,
        "warnings": warnings,
        "volume_score": volume_score,
    }