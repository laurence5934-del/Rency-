"""
Paper Order Builder
AI Trading Platform Version 7.4

Builds and validates IBKR paper-order requests.
This module does not transmit orders.
"""

from __future__ import annotations

from typing import Any


SUPPORTED_ACTIONS = {"BUY", "SELL"}
SUPPORTED_ORDER_TYPES = {"MKT", "LMT"}


def build_paper_order(
    *,
    candidate: dict[str, Any],
    order_type: str = "MKT",
    limit_price: float | None = None,
) -> dict[str, Any]:
    symbol = str(candidate.get("symbol", "")).strip().upper()
    action = str(candidate.get("action", "")).strip().upper()
    quantity = int(candidate.get("quantity", 0) or 0)
    entry_price = float(candidate.get("entry_price", 0) or 0)

    normalized_order_type = str(order_type or "").strip().upper()

    if not symbol:
        raise ValueError("Order symbol cannot be empty.")

    if action not in SUPPORTED_ACTIONS:
        raise ValueError(
            f"Unsupported order action: {action}. "
            "Expected BUY or SELL."
        )

    if quantity <= 0:
        raise ValueError(
            "Order quantity must be greater than zero."
        )

    if normalized_order_type not in SUPPORTED_ORDER_TYPES:
        raise ValueError(
            f"Unsupported order type: {normalized_order_type}."
        )

    normalized_limit_price: float | None = None

    if normalized_order_type == "LMT":
        normalized_limit_price = float(
            limit_price if limit_price is not None else entry_price
        )

        if normalized_limit_price <= 0:
            raise ValueError(
                "Limit price must be greater than zero."
            )

    return {
        "symbol": symbol,
        "action": action,
        "quantity": quantity,
        "order_type": normalized_order_type,
        "limit_price": normalized_limit_price,
        "time_in_force": "DAY",
        "paper_only": True,
        "transmit": False,
        "source_candidate_id": candidate.get("id"),
        "source_status": candidate.get("status"),
    }