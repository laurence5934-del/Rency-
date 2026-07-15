"""
Paper Execution Service
AI Trading Platform Version 7.4

Combines order building and execution safety checks.
This version prepares an IBKR paper-order package only.
It does not submit the order.
"""

from __future__ import annotations

from typing import Any

from app.broker.paper_execution_guard import (
    validate_paper_execution,
)
from app.broker.paper_order_builder import (
    build_paper_order,
)


def prepare_paper_execution(
    *,
    candidate: dict[str, Any],
    ibkr_connected: bool,
    paper_account_confirmed: bool,
    order_type: str = "MKT",
    limit_price: float | None = None,
    maximum_position_value: float = 25_000.00,
) -> dict[str, Any]:
    guard_result = validate_paper_execution(
        candidate=candidate,
        ibkr_connected=ibkr_connected,
        paper_account_confirmed=paper_account_confirmed,
        maximum_position_value=maximum_position_value,
    )

    if not guard_result["approved"]:
        return {
            "ready": False,
            "guard": guard_result,
            "order": None,
            "message": (
                "Paper execution preparation was blocked "
                "by one or more safety checks."
            ),
        }

    order_request = build_paper_order(
        candidate=candidate,
        order_type=order_type,
        limit_price=limit_price,
    )

    return {
        "ready": True,
        "guard": guard_result,
        "order": order_request,
        "message": (
            "Paper order package is validated and ready "
            "for explicit IBKR submission."
        ),
    }