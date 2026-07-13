"""
AI Trade Candidate Generator
AI Trading Platform Version 7.0

Creates a paper-trade proposal only.
It does not submit orders.
"""

from typing import Any


def build_trade_candidate(
    *,
    symbol: str,
    score: int,
    action: str,
    entry_price: float,
    stop_loss: float,
    target_price: float,
    account_value: float,
    risk_per_trade_pct: float = 1.0,
) -> dict[str, Any]:
    if entry_price <= 0:
        raise ValueError("entry_price must be greater than zero.")

    if stop_loss <= 0:
        raise ValueError("stop_loss must be greater than zero.")

    if target_price <= 0:
        raise ValueError("target_price must be greater than zero.")

    if account_value <= 0:
        raise ValueError("account_value must be greater than zero.")

    if risk_per_trade_pct <= 0:
        raise ValueError("risk_per_trade_pct must be greater than zero.")

    action = str(action or "").upper()
    symbol = str(symbol or "").upper()

    risk_budget = account_value * (risk_per_trade_pct / 100)
    risk_per_share = abs(entry_price - stop_loss)

    if risk_per_share <= 0:
        raise ValueError(
            "entry_price and stop_loss must be different."
        )

    quantity = int(risk_budget // risk_per_share)

    reward_per_share = abs(target_price - entry_price)
    risk_reward_ratio = reward_per_share / risk_per_share

    position_value = quantity * entry_price
    estimated_dollar_risk = quantity * risk_per_share
    estimated_reward = quantity * reward_per_share

    warnings: list[str] = []
    reasons: list[str] = []

    eligible = True

    if action not in {"BUY", "STRONG_BUY"}:
        eligible = False
        warnings.append(
            "Scanner action is not BUY or STRONG_BUY."
        )

    if score < 80:
        eligible = False
        warnings.append(
            "AI score is below the minimum threshold of 80."
        )

    if quantity <= 0:
        eligible = False
        warnings.append(
            "Risk budget is too small for one share."
        )

    if risk_reward_ratio < 2:
        eligible = False
        warnings.append(
            "Risk/reward ratio is below 2.0."
        )

    if eligible:
        reasons.append(
            "Candidate passed score, action, position-size, "
            "and risk/reward checks."
        )

    return {
        "symbol": symbol,
        "score": int(score),
        "action": action,
        "entry_price": round(entry_price, 2),
        "stop_loss": round(stop_loss, 2),
        "target_price": round(target_price, 2),
        "account_value": round(account_value, 2),
        "risk_per_trade_pct": round(risk_per_trade_pct, 2),
        "risk_budget": round(risk_budget, 2),
        "risk_per_share": round(risk_per_share, 2),
        "quantity": quantity,
        "position_value": round(position_value, 2),
        "estimated_dollar_risk": round(
            estimated_dollar_risk,
            2,
        ),
        "estimated_reward": round(
            estimated_reward,
            2,
        ),
        "risk_reward_ratio": round(
            risk_reward_ratio,
            2,
        ),
        "approval_eligible": eligible,
        "reasons": reasons,
        "warnings": warnings,
    }