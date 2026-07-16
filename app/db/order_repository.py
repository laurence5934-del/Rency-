"""
OMS Order Repository
AI Trading Platform Version 7.7

Provides persistent SQLite storage for managed orders and
their complete lifecycle event history.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.broker.order_state_machine import (
    require_transition,
)
from app.models.order_models import (
    ACTIVE_ORDER_STATES,
    ManagedOrder,
    OrderEvent,
    OrderState,
    utc_now_iso,
)
from app.utils.config import DATABASE_PATH


class OrderRepository:
    """
    Persistent repository for OMS orders and order events.

    A custom database path may be supplied by tests. Production usage
    defaults to the configured DATABASE_PATH.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
    ) -> None:
        self.db_path = Path(
            db_path if db_path is not None else DATABASE_PATH
        )

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS managed_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    broker_order_id INTEGER,
                    candidate_id INTEGER,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    order_type TEXT NOT NULL,
                    limit_price REAL,
                    state TEXT NOT NULL,
                    filled_quantity REAL NOT NULL DEFAULT 0,
                    remaining_quantity REAL NOT NULL DEFAULT 0,
                    average_fill_price REAL NOT NULL DEFAULT 0,
                    last_fill_price REAL NOT NULL DEFAULT 0,
                    strategy TEXT,
                    paper_only INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS order_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    local_order_id INTEGER NOT NULL,
                    previous_state TEXT,
                    new_state TEXT NOT NULL,
                    source TEXT NOT NULL,
                    message TEXT,
                    broker_payload TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(local_order_id)
                        REFERENCES managed_orders(id)
                        ON DELETE CASCADE
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_managed_orders_broker_order_id
                ON managed_orders(broker_order_id)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_managed_orders_symbol_state
                ON managed_orders(symbol, state)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_order_events_local_order_id
                ON order_events(local_order_id)
                """
            )

            connection.commit()

    @staticmethod
    def _normalize_symbol(
        symbol: Any,
    ) -> str:
        normalized = str(symbol or "").strip().upper()

        if not normalized:
            raise ValueError(
                "Order symbol cannot be empty."
            )

        return normalized

    @staticmethod
    def _normalize_action(
        action: Any,
    ) -> str:
        normalized = str(action or "").strip().upper()

        if normalized not in {"BUY", "SELL"}:
            raise ValueError(
                "Order action must be BUY or SELL."
            )

        return normalized

    @staticmethod
    def _normalize_order_type(
        order_type: Any,
    ) -> str:
        normalized = str(
            order_type or ""
        ).strip().upper()

        if normalized not in {"MKT", "LMT"}:
            raise ValueError(
                "Order type must be MKT or LMT."
            )

        return normalized

    @staticmethod
    def _row_to_order(
        row: sqlite3.Row,
    ) -> ManagedOrder:
        return ManagedOrder(
            local_order_id=int(row["id"]),
            broker_order_id=(
                int(row["broker_order_id"])
                if row["broker_order_id"] is not None
                else None
            ),
            candidate_id=(
                int(row["candidate_id"])
                if row["candidate_id"] is not None
                else None
            ),
            symbol=str(row["symbol"]),
            action=str(row["action"]),
            quantity=float(row["quantity"]),
            order_type=str(row["order_type"]),
            limit_price=(
                float(row["limit_price"])
                if row["limit_price"] is not None
                else None
            ),
            state=OrderState(str(row["state"])),
            filled_quantity=float(
                row["filled_quantity"]
            ),
            remaining_quantity=float(
                row["remaining_quantity"]
            ),
            average_fill_price=float(
                row["average_fill_price"]
            ),
            last_fill_price=float(
                row["last_fill_price"]
            ),
            strategy=row["strategy"],
            paper_only=bool(row["paper_only"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _row_to_event(
        row: sqlite3.Row,
    ) -> OrderEvent:
        broker_payload = None

        if row["broker_payload"]:
            try:
                broker_payload = json.loads(
                    row["broker_payload"]
                )
            except json.JSONDecodeError:
                broker_payload = {
                    "raw": row["broker_payload"],
                }

        previous_state = (
            OrderState(str(row["previous_state"]))
            if row["previous_state"]
            else None
        )

        return OrderEvent(
            event_id=int(row["id"]),
            local_order_id=int(
                row["local_order_id"]
            ),
            previous_state=previous_state,
            new_state=OrderState(
                str(row["new_state"])
            ),
            source=str(row["source"]),
            message=row["message"],
            broker_payload=broker_payload,
            created_at=str(row["created_at"]),
        )

    def _insert_event(
        self,
        connection: sqlite3.Connection,
        *,
        local_order_id: int,
        previous_state: OrderState | None,
        new_state: OrderState,
        source: str,
        message: str | None = None,
        broker_payload: dict[str, Any] | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO order_events (
                local_order_id,
                previous_state,
                new_state,
                source,
                message,
                broker_payload,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                local_order_id,
                (
                    previous_state.value
                    if previous_state
                    else None
                ),
                new_state.value,
                str(source or "SYSTEM"),
                message,
                (
                    json.dumps(
                        broker_payload,
                        default=str,
                    )
                    if broker_payload is not None
                    else None
                ),
                utc_now_iso(),
            ),
        )

    def find_active_duplicate(
        self,
        *,
        symbol: str,
        action: str,
        strategy: str | None = None,
    ) -> ManagedOrder | None:
        normalized_symbol = self._normalize_symbol(
            symbol
        )
        normalized_action = self._normalize_action(
            action
        )

        active_values = tuple(
            state.value
            for state in ACTIVE_ORDER_STATES
        )

        placeholders = ", ".join(
            "?"
            for _ in active_values
        )

        query = f"""
            SELECT *
            FROM managed_orders
            WHERE UPPER(symbol) = ?
              AND action = ?
              AND state IN ({placeholders})
              AND (
                    strategy = ?
                    OR (
                        strategy IS NULL
                        AND ? IS NULL
                    )
              )
            ORDER BY id DESC
            LIMIT 1
        """

        with self._connect() as connection:
            row = connection.execute(
                query,
                (
                    normalized_symbol,
                    normalized_action,
                    *active_values,
                    strategy,
                    strategy,
                ),
            ).fetchone()

        return (
            self._row_to_order(row)
            if row is not None
            else None
        )

    def create_order(
        self,
        order_request: dict[str, Any],
        *,
        candidate_id: int | None = None,
        strategy: str | None = None,
        prevent_duplicate: bool = True,
    ) -> ManagedOrder:
        symbol = self._normalize_symbol(
            order_request.get("symbol")
        )
        action = self._normalize_action(
            order_request.get("action")
        )
        order_type = self._normalize_order_type(
            order_request.get("order_type")
        )

        quantity = float(
            order_request.get("quantity", 0) or 0
        )

        if quantity <= 0:
            raise ValueError(
                "Order quantity must be greater than zero."
            )

        limit_price_value = order_request.get(
            "limit_price"
        )

        limit_price = (
            float(limit_price_value)
            if limit_price_value is not None
            else None
        )

        if (
            order_type == "LMT"
            and (
                limit_price is None
                or limit_price <= 0
            )
        ):
            raise ValueError(
                "A positive limit price is required "
                "for LMT orders."
            )

        paper_only = bool(
            order_request.get(
                "paper_only",
                False,
            )
        )

        if not paper_only:
            raise ValueError(
                "OMS V1 accepts paper-only orders."
            )

        if prevent_duplicate:
            duplicate = self.find_active_duplicate(
                symbol=symbol,
                action=action,
                strategy=strategy,
            )

            if duplicate is not None:
                raise ValueError(
                    "An active duplicate order already "
                    f"exists for {symbol} {action}."
                )

        now = utc_now_iso()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO managed_orders (
                    broker_order_id,
                    candidate_id,
                    symbol,
                    action,
                    quantity,
                    order_type,
                    limit_price,
                    state,
                    filled_quantity,
                    remaining_quantity,
                    average_fill_price,
                    last_fill_price,
                    strategy,
                    paper_only,
                    created_at,
                    updated_at
                )
                VALUES (
                    NULL, ?, ?, ?, ?, ?, ?, ?, 0, ?, 0, 0,
                    ?, ?, ?, ?
                )
                """,
                (
                    candidate_id,
                    symbol,
                    action,
                    quantity,
                    order_type,
                    limit_price,
                    OrderState.CREATED.value,
                    quantity,
                    strategy,
                    int(paper_only),
                    now,
                    now,
                ),
            )

            local_order_id = int(
                cursor.lastrowid
            )

            self._insert_event(
                connection,
                local_order_id=local_order_id,
                previous_state=None,
                new_state=OrderState.CREATED,
                source="OMS",
                message="Managed order created.",
            )

            connection.commit()

        order = self.get_order(local_order_id)

        if order is None:
            raise RuntimeError(
                "Managed order could not be read "
                "after creation."
            )

        return order

    def get_order(
        self,
        local_order_id: int,
    ) -> ManagedOrder | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM managed_orders
                WHERE id = ?
                """,
                (int(local_order_id),),
            ).fetchone()

        return (
            self._row_to_order(row)
            if row is not None
            else None
        )

    def get_order_by_broker_id(
        self,
        broker_order_id: int,
    ) -> ManagedOrder | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM managed_orders
                WHERE broker_order_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (int(broker_order_id),),
            ).fetchone()

        return (
            self._row_to_order(row)
            if row is not None
            else None
        )

    def list_orders(
        self,
        *,
        limit: int = 100,
        active_only: bool = False,
    ) -> list[ManagedOrder]:
        parameters: list[Any] = []

        if active_only:
            active_values = tuple(
                state.value
                for state in ACTIVE_ORDER_STATES
            )

            placeholders = ", ".join(
                "?"
                for _ in active_values
            )

            query = f"""
                SELECT *
                FROM managed_orders
                WHERE state IN ({placeholders})
                ORDER BY id DESC
                LIMIT ?
            """

            parameters.extend(active_values)
        else:
            query = """
                SELECT *
                FROM managed_orders
                ORDER BY id DESC
                LIMIT ?
            """

        parameters.append(max(int(limit), 1))

        with self._connect() as connection:
            rows = connection.execute(
                query,
                tuple(parameters),
            ).fetchall()

        return [
            self._row_to_order(row)
            for row in rows
        ]

    def set_broker_order_id(
        self,
        local_order_id: int,
        broker_order_id: int,
    ) -> ManagedOrder:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE managed_orders
                SET broker_order_id = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    int(broker_order_id),
                    utc_now_iso(),
                    int(local_order_id),
                ),
            )

            if cursor.rowcount != 1:
                raise KeyError(
                    f"Managed order {local_order_id} "
                    "does not exist."
                )

            connection.commit()

        order = self.get_order(local_order_id)

        if order is None:
            raise RuntimeError(
                "Managed order could not be read "
                "after broker-ID update."
            )

        return order

    def transition_order(
        self,
        local_order_id: int,
        new_state: OrderState,
        *,
        source: str,
        message: str | None = None,
        broker_payload: dict[str, Any] | None = None,
    ) -> ManagedOrder:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM managed_orders
                WHERE id = ?
                """,
                (int(local_order_id),),
            ).fetchone()

            if row is None:
                raise KeyError(
                    f"Managed order {local_order_id} "
                    "does not exist."
                )

            current_state = OrderState(
                str(row["state"])
            )

            require_transition(
                current_state,
                new_state,
            )

            connection.execute(
                """
                UPDATE managed_orders
                SET state = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    new_state.value,
                    utc_now_iso(),
                    int(local_order_id),
                ),
            )

            self._insert_event(
                connection,
                local_order_id=int(
                    local_order_id
                ),
                previous_state=current_state,
                new_state=new_state,
                source=source,
                message=message,
                broker_payload=broker_payload,
            )

            connection.commit()

        order = self.get_order(local_order_id)

        if order is None:
            raise RuntimeError(
                "Managed order could not be read "
                "after transition."
            )

        return order

    def update_execution(
        self,
        local_order_id: int,
        *,
        filled_quantity: float,
        remaining_quantity: float,
        average_fill_price: float = 0.0,
        last_fill_price: float = 0.0,
        source: str = "IBKR",
        broker_payload: dict[str, Any] | None = None,
    ) -> ManagedOrder:
        normalized_filled = max(
            float(filled_quantity),
            0.0,
        )
        normalized_remaining = max(
            float(remaining_quantity),
            0.0,
        )

        current_order = self.get_order(
            local_order_id
        )

        if current_order is None:
            raise KeyError(
                f"Managed order {local_order_id} "
                "does not exist."
            )

        if (
            normalized_filled > 0
            and normalized_remaining > 0
        ):
            new_state = (
                OrderState.PARTIALLY_FILLED
            )
        elif (
            normalized_filled > 0
            and normalized_remaining == 0
        ):
            new_state = OrderState.FILLED
        else:
            new_state = current_order.state

        if new_state != current_order.state:
            require_transition(
                current_order.state,
                new_state,
            )

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE managed_orders
                SET state = ?,
                    filled_quantity = ?,
                    remaining_quantity = ?,
                    average_fill_price = ?,
                    last_fill_price = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    new_state.value,
                    normalized_filled,
                    normalized_remaining,
                    max(
                        float(
                            average_fill_price
                        ),
                        0.0,
                    ),
                    max(
                        float(last_fill_price),
                        0.0,
                    ),
                    utc_now_iso(),
                    int(local_order_id),
                ),
            )

            self._insert_event(
                connection,
                local_order_id=int(
                    local_order_id
                ),
                previous_state=current_order.state,
                new_state=new_state,
                source=source,
                message=(
                    "Execution quantities updated."
                ),
                broker_payload=broker_payload,
            )

            connection.commit()

        order = self.get_order(local_order_id)

        if order is None:
            raise RuntimeError(
                "Managed order could not be read "
                "after execution update."
            )

        return order

    def list_order_events(
        self,
        local_order_id: int,
    ) -> list[OrderEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM order_events
                WHERE local_order_id = ?
                ORDER BY id ASC
                """,
                (int(local_order_id),),
            ).fetchall()

        return [
            self._row_to_event(row)
            for row in rows
        ]

