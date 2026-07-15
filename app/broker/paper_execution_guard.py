"""
Paper Execution Guard
AI Trading Platform Version 7.4

Performs safety checks before any queued candidate
can move toward IBKR paper-order submission.
"""

from __future__ import annotations

from typing import Any


ALLOWED_QUEUE_STATUSES = {
    "PENDING",
    "APPROVED",
}


def validate_paper_execution(
    *,
    candidate: dict[str, Any],
    ibkr_connected: bool,
    paper_account_confirmed: bool,
    maximum_position_value: float = 25_000.00,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    symbol = str(
        candidate.get("symbol", "")
    ).strip().upper()

    action = str(
        candidate.get("action", "")
    ).strip().upper()

    status = str(
        candidate.get("status", "")
    ).strip().upper()

    quantity = int(
        candidate.get("quantity", 0) or 0
    )

    entry_price = float(
        candidate.get("entry_price", 0) or 0
    )

    position_value = quantity * entry_price

    if not symbol:
        errors.append("Candidate symbol is missing.")

    if action not in {"BUY", "SELL"}:
        errors.append(
            "Candidate action must be BUY or SELL."
        )

    if status not in ALLOWED_QUEUE_STATUSES:
        errors.append(
            f"Candidate status {status or 'UNKNOWN'} "
            "is not eligible for paper execution."
        )

    if quantity <= 0:
        errors.append(
            "Candidate quantity must be greater than zero."
        )

    if entry_price <= 0:
        errors.append(
            "Candidate entry price must be greater than zero."
        )

    if not ibkr_connected:
        errors.append(
            "IBKR is not connected."
        )

    if not paper_account_confirmed:
        errors.append(
            "Paper-account confirmation is required."
        )

    if maximum_position_value <= 0:
        errors.append(
            "Maximum position value must be greater than zero."
        )

    if (
        maximum_position_value > 0
        and position_value > maximum_position_value
    ):
        errors.append(
            "Planned position value exceeds the configured "
            f"maximum of ${maximum_position_value:,.2f}."
        )

    if position_value > maximum_position_value * 0.8:
        warnings.append(
            "Planned position value is above 80% of the "
            "configured maximum."
        )

    approved = not errors

    return {
        "approved": approved,
        "symbol": symbol,
        "action": action,
        "status": status,
        "quantity": quantity,
        "entry_price": round(entry_price, 2),
        "position_value": round(position_value, 2),
        "maximum_position_value": round(
            maximum_position_value,
            2,
        ),
        "errors": errors,
        "warnings": warnings,
    }