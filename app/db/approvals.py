"""
Manual approval queue for AI Trading Platform V4.

Stores approval/rejection decisions separately from the original
TradingView signal records.
"""

import json
import sqlite3
from datetime import datetime
from typing import Any

from app.utils.config import DATABASE_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_approval_db() -> None:
    """Create the manual-review table if it does not already exist."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS signal_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER NOT NULL UNIQUE,
                review_status TEXT NOT NULL,
                reviewed_at TEXT NOT NULL,
                note TEXT,
                broker_order_id INTEGER,
                broker_status TEXT,
                broker_result TEXT,
                FOREIGN KEY (signal_id) REFERENCES signals(id)
            )
            """
        )
        conn.commit()


def get_signal_by_id(signal_id: int) -> dict[str, Any] | None:
    init_approval_db()

    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM signals WHERE id = ?",
            (signal_id,),
        ).fetchone()

    return dict(row) if row else None


def get_pending_manual_reviews(limit: int = 20) -> list[dict[str, Any]]:
    """
    Return MANUAL_REVIEW signals that have not yet been approved or rejected.
    """
    init_approval_db()

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT s.*
            FROM signals AS s
            LEFT JOIN signal_reviews AS r
                ON r.signal_id = s.id
            WHERE s.final_action = 'MANUAL_REVIEW'
              AND r.signal_id IS NULL
            ORDER BY s.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def record_review(
    signal_id: int,
    review_status: str,
    note: str = "",
    broker_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Record an APPROVED, REJECTED, ORDER_SUBMITTED, ORDER_FAILED,
    or other review status.

    The UNIQUE signal_id constraint prevents duplicate approvals.
    """
    init_approval_db()

    normalized_status = review_status.strip().upper()

    allowed_statuses = {
        "APPROVED",
        "REJECTED",
        "ORDER_SUBMITTED",
        "ORDER_FAILED",
        "CANCELLED",
    }

    if normalized_status not in allowed_statuses:
        raise ValueError(
            f"Invalid review status: {normalized_status}. "
            f"Allowed values: {sorted(allowed_statuses)}"
        )

    order_id = None
    broker_status = None
    broker_json = None

    if broker_result:
        order_id = broker_result.get("order_id")
        broker_status = broker_result.get("status")
        broker_json = json.dumps(broker_result, default=str)

    reviewed_at = datetime.now().isoformat(timespec="seconds")

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO signal_reviews (
                signal_id,
                review_status,
                reviewed_at,
                note,
                broker_order_id,
                broker_status,
                broker_result
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(signal_id) DO UPDATE SET
                review_status = excluded.review_status,
                reviewed_at = excluded.reviewed_at,
                note = excluded.note,
                broker_order_id = excluded.broker_order_id,
                broker_status = excluded.broker_status,
                broker_result = excluded.broker_result
            """,
            (
                signal_id,
                normalized_status,
                reviewed_at,
                note,
                order_id,
                broker_status,
                broker_json,
            ),
        )
        conn.commit()

    return {
        "signal_id": signal_id,
        "review_status": normalized_status,
        "reviewed_at": reviewed_at,
        "note": note,
        "broker_order_id": order_id,
        "broker_status": broker_status,
    }


def get_review_history(limit: int = 50) -> list[dict[str, Any]]:
    init_approval_db()

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                r.*,
                s.symbol,
                s.ai_score,
                s.ai_decision,
                s.ai_risk,
                s.final_action,
                s.quantity
            FROM signal_reviews AS r
            JOIN signals AS s
                ON s.id = r.signal_id
            ORDER BY r.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]