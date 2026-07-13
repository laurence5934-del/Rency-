"""
Risk Analysis Engine
AI Trading Platform Version 6.1
"""

from typing import Any


def calculate_risk_score(
    *,
    current_price: float,
    stop_loss: float,
    account_risk_pct: float = 2.0,
) -> dict[str, Any]:
    """
    Calculates a risk score (0-10)
    based on distance to stop loss.
    """

    if current_price <= 0:
        raise ValueError(
            "current_price must be greater than zero."
        )

    if stop_loss <= 0:
        raise ValueError(
            "stop_loss must be greater than zero."
        )

    stop_distance_pct = (
        abs(current_price - stop_loss)
        / current_price
        * 100
    )

    score = 0
    reasons = []

    if stop_distance_pct <= account_risk_pct:

        score = 10

        status = "LOW"

        reasons.append(
            "Risk is within the configured limit."
        )

    elif stop_distance_pct <= account_risk_pct * 2:

        score = 7

        status = "MODERATE"

        reasons.append(
            "Risk is slightly above the preferred limit."
        )

    elif stop_distance_pct <= account_risk_pct * 3:

        score = 4

        status = "HIGH"

        reasons.append(
            "Risk is elevated."
        )

    else:

        score = 1

        status = "EXTREME"

        reasons.append(
            "Risk is far above the preferred limit."
        )

    return {
        "risk_score": score,
        "risk_status": status,
        "stop_distance_pct": round(
            stop_distance_pct,
            2,
        ),
        "reasons": reasons,
    }