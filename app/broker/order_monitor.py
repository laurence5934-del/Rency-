"""
IBKR Order Monitor
AI Trading Platform Version 7.4.2

Reads active and recently completed IBKR paper orders,
normalizes their lifecycle states, and produces a monitoring
snapshot for the dashboard and persistence layer.

This module does not submit orders.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.broker.ibkr_official import get_order_snapshot
from app.utils.config import PAPER_TRADING_ONLY


ACTIVE_STATUSES = {
    "PENDINGSUBMIT",
    "PRESUBMITTED",
    "SUBMITTED",
    "PENDINGCANCEL",
}

FILLED_STATUSES = {
    "FILLED",
}

CANCELLED_STATUSES = {
    "CANCELLED",
    "APICANCELLED",
}

REJECTED_STATUSES = {
    "INACTIVE",
}

TERMINAL_STATUSES = (
    FILLED_STATUSES
    | CANCELLED_STATUSES
    | REJECTED_STATUSES
)


def normalize_status(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def classify_order_status(status: Any) -> str:
    normalized = normalize_status(status)

    if normalized in ACTIVE_STATUSES:
        return "ACTIVE"

    if normalized in FILLED_STATUSES:
        return "FILLED"

    if normalized in CANCELLED_STATUSES:
        return "CANCELLED"

    if normalized in REJECTED_STATUSES:
        return "REJECTED"

    return "UNKNOWN"


def latest_status_by_order(
    statuses: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """
    Return the latest status callback received for each order.
    """

    latest: dict[int, dict[str, Any]] = {}

    for status in statuses:
        try:
            order_id = int(
                status.get(
                    "order_id",
                    status.get("orderId"),
                )
            )
        except (TypeError, ValueError):
            continue

        latest[order_id] = status

    return latest


def fills_by_order(
    fills: list[dict[str, Any]],
) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for fill in fills:
        try:
            order_id = int(
                fill.get(
                    "order_id",
                    fill.get("orderId"),
                )
            )
        except (TypeError, ValueError):
            continue

        grouped[order_id].append(fill)

    return dict(grouped)


def commissions_by_execution(
    commissions: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("execution_id")): item
        for item in commissions
        if item.get("execution_id")
    }


def enrich_fills_with_commissions(
    fills: list[dict[str, Any]],
    commissions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    commission_map = commissions_by_execution(commissions)
    enriched: list[dict[str, Any]] = []

    for fill in fills:
        record = dict(fill)
        execution_id = str(fill.get("execution_id", ""))

        commission = commission_map.get(execution_id)

        if commission:
            record["commission"] = commission.get("commission")
            record["commission_currency"] = commission.get(
                "currency"
            )
            record["realized_pnl"] = commission.get(
                "realized_pnl"
            )

        enriched.append(record)

    return enriched


def build_order_records(
    snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    open_orders = snapshot.get("open_orders", [])
    statuses = snapshot.get("order_statuses", [])
    fills = snapshot.get("fills", [])
    commissions = snapshot.get("commissions", [])

    latest_statuses = latest_status_by_order(statuses)
    grouped_fills = fills_by_order(
        enrich_fills_with_commissions(
            fills,
            commissions,
        )
    )

    order_records: list[dict[str, Any]] = []
    observed_order_ids: set[int] = set()

    for open_order in open_orders:
        try:
            order_id = int(open_order["order_id"])
        except (KeyError, TypeError, ValueError):
            continue

        observed_order_ids.add(order_id)

        status_record = latest_statuses.get(order_id, {})
        status = normalize_status(
            status_record.get(
                "status",
                open_order.get("status"),
            )
        )

        filled = float(status_record.get("filled", 0) or 0)
        remaining = float(
            status_record.get(
                "remaining",
                open_order.get("quantity", 0),
            )
            or 0
        )

        order_records.append(
            {
                **open_order,
                "order_id": order_id,
                "status": status,
                "lifecycle": classify_order_status(status),
                "filled": filled,
                "remaining": remaining,
                "average_fill_price": float(
                    status_record.get(
                        "average_fill_price",
                        0,
                    )
                    or 0
                ),
                "last_fill_price": float(
                    status_record.get(
                        "last_fill_price",
                        0,
                    )
                    or 0
                ),
                "fills": grouped_fills.get(order_id, []),
            }
        )

    # Some status callbacks may exist even when openOrder did not
    # return a corresponding order record.
    for order_id, status_record in latest_statuses.items():
        if order_id in observed_order_ids:
            continue

        status = normalize_status(status_record.get("status"))

        order_records.append(
            {
                "order_id": order_id,
                "symbol": "UNKNOWN",
                "action": "UNKNOWN",
                "order_type": "UNKNOWN",
                "quantity": (
                    float(status_record.get("filled", 0) or 0)
                    + float(
                        status_record.get("remaining", 0) or 0
                    )
                ),
                "status": status,
                "lifecycle": classify_order_status(status),
                "filled": float(
                    status_record.get("filled", 0) or 0
                ),
                "remaining": float(
                    status_record.get("remaining", 0) or 0
                ),
                "average_fill_price": float(
                    status_record.get(
                        "average_fill_price",
                        0,
                    )
                    or 0
                ),
                "last_fill_price": float(
                    status_record.get(
                        "last_fill_price",
                        0,
                    )
                    or 0
                ),
                "fills": grouped_fills.get(order_id, []),
            }
        )

    return sorted(
        order_records,
        key=lambda item: int(item.get("order_id", 0)),
        reverse=True,
    )


def summarize_orders(
    orders: list[dict[str, Any]],
) -> dict[str, int]:
    summary = {
        "total": len(orders),
        "active": 0,
        "filled": 0,
        "cancelled": 0,
        "rejected": 0,
        "unknown": 0,
    }

    for order in orders:
        lifecycle = str(
            order.get("lifecycle", "UNKNOWN")
        ).lower()

        if lifecycle in summary:
            summary[lifecycle] += 1
        else:
            summary["unknown"] += 1

    return summary


def synchronize_ibkr_orders(
    *,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """
    Retrieve and normalize the current IBKR order lifecycle.

    This method is read-only. Database synchronization can be
    connected after the trade repository schema is available.
    """

    if not PAPER_TRADING_ONLY:
        return {
            "success": False,
            "status": "LIVE_TRADING_MODE_BLOCKED",
            "message": (
                "Order monitoring is currently restricted to "
                "paper-trading mode."
            ),
            "orders": [],
            "summary": summarize_orders([]),
        }

    snapshot = get_order_snapshot(
        timeout=timeout,
        include_completed=True,
    )

    if snapshot.get("status") == "ERROR":
        return {
            "success": False,
            "status": "ERROR",
            "message": snapshot.get(
                "message",
                "Unable to retrieve IBKR orders.",
            ),
            "orders": [],
            "summary": summarize_orders([]),
            "errors": snapshot.get("errors", []),
        }

    orders = build_order_records(snapshot)

    return {
        "success": True,
        "status": "SYNCHRONIZED",
        "message": (
            f"Retrieved {len(orders)} observable IBKR orders."
        ),
        "orders": orders,
        "completed_orders": snapshot.get(
            "completed_orders",
            [],
        ),
        "fills": enrich_fills_with_commissions(
            snapshot.get("fills", []),
            snapshot.get("commissions", []),
        ),
        "summary": summarize_orders(orders),
        "accounts": snapshot.get("accounts", []),
        "request_completion": snapshot.get(
            "request_completion",
            {},
        ),
        "errors": snapshot.get("errors", []),
    }