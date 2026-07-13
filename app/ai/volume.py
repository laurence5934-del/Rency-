"""
Volume Analysis Engine
AI Trading Platform Version 6.1
"""

from typing import Any


def calculate_volume_score(
    *,
    current_volume: float,
    average_volume: float,
) -> dict[str, Any]:
    """
    Calculates a volume score (0–20)
    using relative volume.
    """

    if average_volume <= 0:
        raise ValueError(
            "average_volume must be greater than zero."
        )

    relative_volume = (
        current_volume / average_volume
    )

    score = 0
    reasons = []

    if relative_volume >= 2.0:
        score = 20
        status = "EXTREMELY_HIGH"
        reasons.append(
            "Volume is at least 2× average."
        )

    elif relative_volume >= 1.5:
        score = 16
        status = "HIGH"
        reasons.append(
            "Volume is well above average."
        )

    elif relative_volume >= 1.2:
        score = 12
        status = "ABOVE_AVERAGE"
        reasons.append(
            "Volume is moderately above average."
        )

    elif relative_volume >= 1.0:
        score = 8
        status = "NORMAL"
        reasons.append(
            "Volume is near average."
        )

    elif relative_volume >= 0.8:
        score = 5
        status = "LIGHT"
        reasons.append(
            "Volume is below average."
        )

    else:
        score = 2
        status = "VERY_LIGHT"
        reasons.append(
            "Volume is significantly below average."
        )

    return {
        "volume_score": score,
        "relative_volume": round(relative_volume, 2),
        "volume_status": status,
        "reasons": reasons,
    }