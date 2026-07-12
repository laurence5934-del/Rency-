"""
Stop-Loss and Take-Profit Planner
AI Trading Platform V5.4

Recommendation-only.
This module does not submit or modify IBKR orders.
"""

from typing import Any


def plan_exit_levels(
    *,
    quantity: float,
    entry_price: float,
    current_price: float,
    health_score: int,
    ai_risk: str,
    stop_loss_pct: float = 5.0,
    take_profit_pct: float = 15.0,
    trailing_stop_pct: float = 4.0,
) -> dict[str, Any]:
    if entry_price <= 0:
        raise ValueError("entry_price must be greater than zero.")

    if current_price <= 0:
        raise ValueError("current_price must be greater than zero.")

    if quantity == 0:
        raise ValueError("quantity cannot be zero.")

    is_long = quantity > 0
    position_side = "LONG" if is_long else "SHORT"

    if is_long:
        gain_pct = (
            (current_price - entry_price)
            / entry_price
            * 100
        )

        initial_stop = entry_price * (
            1 - stop_loss_pct / 100
        )

        take_profit = entry_price * (
            1 + take_profit_pct / 100
        )

        trailing_stop = current_price * (
            1 - trailing_stop_pct / 100
        )

        break_even_stop = entry_price

    else:
        gain_pct = (
            (entry_price - current_price)
            / entry_price
            * 100
        )

        initial_stop = entry_price * (
            1 + stop_loss_pct / 100
        )

        take_profit = entry_price * (
            1 - take_profit_pct / 100
        )

        trailing_stop = current_price * (
            1 + trailing_stop_pct / 100
        )

        break_even_stop = entry_price

    ai_risk = str(ai_risk or "").upper()
    recommendation = "HOLD"
    stop_mode = "INITIAL_STOP"
    reasons: list[str] = []

    suggested_stop = initial_stop

    if gain_pct >= 10:
        suggested_stop = trailing_stop
        stop_mode = "TRAILING_STOP"
        recommendation = "PROTECT_PROFIT"
        reasons.append(
            "Position gain is at least 10%; "
            "a trailing stop may protect profits."
        )

    elif gain_pct >= 5:
        suggested_stop = break_even_stop
        stop_mode = "BREAK_EVEN_STOP"
        recommendation = "MOVE_STOP_TO_BREAK_EVEN"
        reasons.append(
            "Position gain is at least 5%; "
            "consider moving the stop to break-even."
        )

    elif gain_pct <= -stop_loss_pct:
        recommendation = "EXIT"
        stop_mode = "STOP_THRESHOLD_REACHED"
        reasons.append(
            "The configured maximum-loss threshold "
            "has been reached."
        )

    else:
        reasons.append(
            "Position remains within the planned "
            "risk and reward range."
        )

    if health_score < 25:
        recommendation = "EXIT"
        reasons.append(
            "Position health is critical."
        )

    elif health_score < 45 and recommendation != "EXIT":
        recommendation = "REDUCE"
        reasons.append(
            "Position health is weak."
        )

    if ai_risk == "HIGH":
        if recommendation == "HOLD":
            recommendation = "REDUCE"

        reasons.append(
            "Latest AI risk rating is high."
        )

    risk_per_share = abs(
        entry_price - suggested_stop
    )

    reward_per_share = abs(
        take_profit - entry_price
    )

    risk_reward_ratio = None

    if risk_per_share > 0:
        risk_reward_ratio = (
            reward_per_share / risk_per_share
        )

    stop_distance_pct = (
        abs(current_price - suggested_stop)
        / current_price
        * 100
    )

    target_distance_pct = (
        abs(take_profit - current_price)
        / current_price
        * 100
    )

    return {
        "position_side": position_side,
        "gain_pct": round(gain_pct, 2),
        "initial_stop": round(initial_stop, 2),
        "break_even_stop": round(
            break_even_stop,
            2,
        ),
        "trailing_stop": round(
            trailing_stop,
            2,
        ),
        "suggested_stop": round(
            suggested_stop,
            2,
        ),
        "stop_mode": stop_mode,
        "take_profit": round(
            take_profit,
            2,
        ),
        "risk_reward_ratio": (
            None
            if risk_reward_ratio is None
            else round(risk_reward_ratio, 2)
        ),
        "stop_distance_pct": round(
            stop_distance_pct,
            2,
        ),
        "target_distance_pct": round(
            target_distance_pct,
            2,
        ),
        "recommendation": recommendation,
        "reasons": reasons,
    }