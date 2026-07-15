"""
Persistent Approval Queue
AI Trading Platform Version 7.2
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parent / "ai_trading_platform.db"

ACTIVE_STATUSES = (
    "PENDING",
    "APPROVED",
    "ORDER_SUBMITTED",
)

ALLOWED_STATUSES = {
    "PENDING",
    "APPROVED",
    "REJECTED",
    "ORDER_SUBMITTED",
    "ORDER_FAILED",
}


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_approval_queue() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                score INTEGER NOT NULL,
                action TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                target_price REAL NOT NULL,
                risk_budget REAL NOT NULL,
                risk_reward REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()


def candidate_exists(
    symbol: str,
    *,
    statuses: tuple[str, ...] = ACTIVE_STATUSES,
) -> bool:
    init_approval_queue()

    normalized_symbol = str(symbol or "").strip().upper()

    if not normalized_symbol:
        raise ValueError("symbol cannot be empty.")

    placeholders = ", ".join("?" for _ in statuses)

    query = f"""
        SELECT 1
        FROM approval_queue
        WHERE UPPER(symbol) = ?
          AND status IN ({placeholders})
        LIMIT 1
    """

    with get_connection() as connection:
        row = connection.execute(
            query,
            (normalized_symbol, *statuses),
        ).fetchone()

    return row is not None


def add_candidate(candidate: dict[str, Any]) -> int:
    init_approval_queue()

    symbol = str(candidate.get("symbol", "")).strip().upper()

    if not symbol:
        raise ValueError("Candidate symbol cannot be empty.")

    if candidate_exists(symbol):
        raise ValueError(
            f"A pending or active candidate already exists for {symbol}."
        )

    quantity = int(candidate.get("quantity", 0) or 0)
    entry_price = float(candidate.get("entry_price", 0) or 0)
    stop_loss = float(candidate.get("stop_loss", 0) or 0)
    target_price = float(candidate.get("target_price", 0) or 0)

    if quantity <= 0:
        raise ValueError("Candidate quantity must be greater than zero.")

    if min(entry_price, stop_loss, target_price) <= 0:
        raise ValueError(
            "Entry, stop-loss, and target prices must be greater than zero."
        )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO approval_queue (
                symbol,
                score,
                action,
                quantity,
                entry_price,
                stop_loss,
                target_price,
                risk_budget,
                risk_reward,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
            """,
            (
                symbol,
                int(candidate.get("score", 0) or 0),
                str(candidate.get("action", "")).upper(),
                quantity,
                entry_price,
                stop_loss,
                target_price,
                float(candidate.get("risk_budget", 0) or 0),
                float(candidate.get("risk_reward_ratio", 0) or 0),
            ),
        )
        connection.commit()

        if cursor.lastrowid is None:
            raise RuntimeError("Approval queue insert returned no ID.")

        return int(cursor.lastrowid)


def get_pending_candidates() -> list[dict[str, Any]]:
    init_approval_queue()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM approval_queue
            WHERE status = 'PENDING'
            ORDER BY id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def update_status(candidate_id: int, status: str) -> None:
    init_approval_queue()

    normalized_status = str(status or "").strip().upper()

    if normalized_status not in ALLOWED_STATUSES:
        raise ValueError(
            f"Unsupported approval status: {normalized_status}"
        )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE approval_queue
            SET status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (normalized_status, int(candidate_id)),
        )
        connection.commit()

        if cursor.rowcount == 0:
            raise ValueError(
                f"No approval candidate found with ID {candidate_id}."
            )