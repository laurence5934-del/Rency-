from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class DecisionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REDUCED = "REDUCED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


class TradeDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    SHORT = "SHORT"
    COVER = "COVER"


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    decision_id: str
    timestamp_utc: str
    symbol: str
    direction: TradeDirection
    status: DecisionStatus
    market_regime: str
    selected_strategy: str
    alternative_strategies: tuple[str, ...]
    confidence_score: float
    risk_score: float
    portfolio_risk_mode: str
    requested_position_value: float
    approved_position_value: float
    quantity: float
    entry_price: float | None
    exit_price: float | None
    stop_price: float | None
    expected_reward_risk: float | None
    realized_pnl: float | None
    unrealized_pnl: float | None
    return_pct: float | None
    portfolio_value: float | None
    cash_available: float | None
    gross_exposure: float | None
    portfolio_heat: float | None
    explanation: str
    reasons: tuple[str, ...]
    feature_snapshot: dict[str, Any]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["direction"] = self.direction.value
        data["status"] = self.status.value
        data["alternative_strategies"] = list(self.alternative_strategies)
        data["reasons"] = list(self.reasons)
        return data


@dataclass(frozen=True, slots=True)
class DecisionQuery:
    symbol: str | None = None
    status: DecisionStatus | None = None
    strategy: str | None = None
    market_regime: str | None = None
    start_time_utc: str | None = None
    end_time_utc: str | None = None
    minimum_confidence: float | None = None
    maximum_confidence: float | None = None
    limit: int = 100
    newest_first: bool = True


@dataclass(frozen=True, slots=True)
class DecisionSummary:
    total_records: int
    closed_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    realized_pnl: float
    average_return_pct: float
    average_confidence: float
    by_status: dict[str, int]
    by_strategy: dict[str, int]
    by_market_regime: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AIDecisionLogger:
    """Version 9.8.0.7 - persistent, searchable AI decision audit trail."""

    def __init__(self, database_path: str | Path = "data/ai_decisions.db") -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=30.0,
            isolation_level=None,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _initialize_database(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_decisions (
                    decision_id TEXT PRIMARY KEY,
                    timestamp_utc TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    status TEXT NOT NULL,
                    market_regime TEXT NOT NULL,
                    selected_strategy TEXT NOT NULL,
                    alternative_strategies_json TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    risk_score REAL NOT NULL,
                    portfolio_risk_mode TEXT NOT NULL,
                    requested_position_value REAL NOT NULL,
                    approved_position_value REAL NOT NULL,
                    quantity REAL NOT NULL,
                    entry_price REAL,
                    exit_price REAL,
                    stop_price REAL,
                    expected_reward_risk REAL,
                    realized_pnl REAL,
                    unrealized_pnl REAL,
                    return_pct REAL,
                    portfolio_value REAL,
                    cash_available REAL,
                    gross_exposure REAL,
                    portfolio_heat REAL,
                    explanation TEXT NOT NULL,
                    reasons_json TEXT NOT NULL,
                    feature_snapshot_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            for statement in (
                "CREATE INDEX IF NOT EXISTS idx_decision_symbol ON ai_decisions(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_decision_time ON ai_decisions(timestamp_utc)",
                "CREATE INDEX IF NOT EXISTS idx_decision_status ON ai_decisions(status)",
                "CREATE INDEX IF NOT EXISTS idx_decision_strategy ON ai_decisions(selected_strategy)",
                "CREATE INDEX IF NOT EXISTS idx_decision_regime ON ai_decisions(market_regime)",
            ):
                connection.execute(statement)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _score(name: str, value: float) -> float:
        value = float(value)
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be between 0 and 1")
        return value

    @staticmethod
    def _non_negative(name: str, value: float) -> float:
        value = float(value)
        if value < 0:
            raise ValueError(f"{name} cannot be negative")
        return value

    @staticmethod
    def _symbol(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("symbol must be a string")
        value = value.strip().upper()
        if not value:
            raise ValueError("symbol cannot be empty")
        return value

    @staticmethod
    def _dump(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)

    def log_decision(
        self,
        *,
        symbol: str,
        direction: TradeDirection | str,
        market_regime: str,
        selected_strategy: str,
        confidence_score: float,
        risk_score: float,
        portfolio_risk_mode: str,
        requested_position_value: float,
        approved_position_value: float,
        quantity: float,
        explanation: str,
        status: DecisionStatus | str = DecisionStatus.PROPOSED,
        alternative_strategies: Sequence[str] = (),
        reasons: Sequence[str] = (),
        entry_price: float | None = None,
        exit_price: float | None = None,
        stop_price: float | None = None,
        expected_reward_risk: float | None = None,
        realized_pnl: float | None = None,
        unrealized_pnl: float | None = None,
        return_pct: float | None = None,
        portfolio_value: float | None = None,
        cash_available: float | None = None,
        gross_exposure: float | None = None,
        portfolio_heat: float | None = None,
        feature_snapshot: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        decision_id: str | None = None,
        timestamp_utc: str | None = None,
    ) -> DecisionRecord:
        requested = self._non_negative(
            "requested_position_value", requested_position_value
        )
        approved = self._non_negative(
            "approved_position_value", approved_position_value
        )
        if approved > requested:
            raise ValueError("approved position cannot exceed requested position")
        if not market_regime.strip():
            raise ValueError("market_regime cannot be empty")
        if not selected_strategy.strip():
            raise ValueError("selected_strategy cannot be empty")
        if not explanation.strip():
            raise ValueError("explanation cannot be empty")

        record = DecisionRecord(
            decision_id=decision_id or str(uuid.uuid4()),
            timestamp_utc=timestamp_utc or self._utc_now(),
            symbol=self._symbol(symbol),
            direction=TradeDirection(direction),
            status=DecisionStatus(status),
            market_regime=market_regime.strip(),
            selected_strategy=selected_strategy.strip(),
            alternative_strategies=tuple(alternative_strategies),
            confidence_score=self._score("confidence_score", confidence_score),
            risk_score=self._score("risk_score", risk_score),
            portfolio_risk_mode=portfolio_risk_mode.strip(),
            requested_position_value=requested,
            approved_position_value=approved,
            quantity=self._non_negative("quantity", quantity),
            entry_price=None if entry_price is None else float(entry_price),
            exit_price=None if exit_price is None else float(exit_price),
            stop_price=None if stop_price is None else float(stop_price),
            expected_reward_risk=None if expected_reward_risk is None else float(expected_reward_risk),
            realized_pnl=None if realized_pnl is None else float(realized_pnl),
            unrealized_pnl=None if unrealized_pnl is None else float(unrealized_pnl),
            return_pct=None if return_pct is None else float(return_pct),
            portfolio_value=None if portfolio_value is None else float(portfolio_value),
            cash_available=None if cash_available is None else float(cash_available),
            gross_exposure=None if gross_exposure is None else float(gross_exposure),
            portfolio_heat=None if portfolio_heat is None else float(portfolio_heat),
            explanation=explanation.strip(),
            reasons=tuple(str(item) for item in reasons),
            feature_snapshot=dict(feature_snapshot or {}),
            metadata=dict(metadata or {}),
        )

        values = (
            record.decision_id, record.timestamp_utc, record.symbol,
            record.direction.value, record.status.value, record.market_regime,
            record.selected_strategy, self._dump(record.alternative_strategies),
            record.confidence_score, record.risk_score,
            record.portfolio_risk_mode, record.requested_position_value,
            record.approved_position_value, record.quantity, record.entry_price,
            record.exit_price, record.stop_price, record.expected_reward_risk,
            record.realized_pnl, record.unrealized_pnl, record.return_pct,
            record.portfolio_value, record.cash_available, record.gross_exposure,
            record.portfolio_heat, record.explanation, self._dump(record.reasons),
            self._dump(record.feature_snapshot), self._dump(record.metadata),
        )

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ai_decisions VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                values,
            )
        return record

    def _row_to_record(self, row: sqlite3.Row) -> DecisionRecord:
        return DecisionRecord(
            decision_id=row["decision_id"],
            timestamp_utc=row["timestamp_utc"],
            symbol=row["symbol"],
            direction=TradeDirection(row["direction"]),
            status=DecisionStatus(row["status"]),
            market_regime=row["market_regime"],
            selected_strategy=row["selected_strategy"],
            alternative_strategies=tuple(json.loads(row["alternative_strategies_json"])),
            confidence_score=row["confidence_score"],
            risk_score=row["risk_score"],
            portfolio_risk_mode=row["portfolio_risk_mode"],
            requested_position_value=row["requested_position_value"],
            approved_position_value=row["approved_position_value"],
            quantity=row["quantity"],
            entry_price=row["entry_price"],
            exit_price=row["exit_price"],
            stop_price=row["stop_price"],
            expected_reward_risk=row["expected_reward_risk"],
            realized_pnl=row["realized_pnl"],
            unrealized_pnl=row["unrealized_pnl"],
            return_pct=row["return_pct"],
            portfolio_value=row["portfolio_value"],
            cash_available=row["cash_available"],
            gross_exposure=row["gross_exposure"],
            portfolio_heat=row["portfolio_heat"],
            explanation=row["explanation"],
            reasons=tuple(json.loads(row["reasons_json"])),
            feature_snapshot=dict(json.loads(row["feature_snapshot_json"])),
            metadata=dict(json.loads(row["metadata_json"])),
        )

    def get(self, decision_id: str) -> DecisionRecord | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM ai_decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
        return None if row is None else self._row_to_record(row)

    def update_decision(
        self,
        decision_id: str,
        *,
        status: DecisionStatus | str | None = None,
        entry_price: float | None = None,
        exit_price: float | None = None,
        realized_pnl: float | None = None,
        unrealized_pnl: float | None = None,
        return_pct: float | None = None,
        explanation: str | None = None,
        metadata_updates: Mapping[str, Any] | None = None,
    ) -> DecisionRecord:
        current = self.get(decision_id)
        if current is None:
            raise KeyError(f"decision not found: {decision_id}")

        metadata = dict(current.metadata)
        metadata.update(metadata_updates or {})

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE ai_decisions SET
                    status = ?, entry_price = ?, exit_price = ?,
                    realized_pnl = ?, unrealized_pnl = ?, return_pct = ?,
                    explanation = ?, metadata_json = ?
                WHERE decision_id = ?
                """,
                (
                    current.status.value if status is None else DecisionStatus(status).value,
                    current.entry_price if entry_price is None else float(entry_price),
                    current.exit_price if exit_price is None else float(exit_price),
                    current.realized_pnl if realized_pnl is None else float(realized_pnl),
                    current.unrealized_pnl if unrealized_pnl is None else float(unrealized_pnl),
                    current.return_pct if return_pct is None else float(return_pct),
                    current.explanation if explanation is None else explanation.strip(),
                    self._dump(metadata),
                    decision_id,
                ),
            )
        updated = self.get(decision_id)
        if updated is None:
            raise RuntimeError("decision disappeared after update")
        return updated

    def search(self, query: DecisionQuery | None = None) -> list[DecisionRecord]:
        query = query or DecisionQuery()
        clauses: list[str] = []
        params: list[Any] = []

        filters = (
            ("symbol", self._symbol(query.symbol) if query.symbol else None),
            ("status", query.status.value if query.status else None),
            ("selected_strategy", query.strategy),
            ("market_regime", query.market_regime),
        )
        for column, value in filters:
            if value is not None:
                clauses.append(f"{column} = ?")
                params.append(value)

        if query.start_time_utc:
            clauses.append("timestamp_utc >= ?")
            params.append(query.start_time_utc)
        if query.end_time_utc:
            clauses.append("timestamp_utc <= ?")
            params.append(query.end_time_utc)
        if query.minimum_confidence is not None:
            clauses.append("confidence_score >= ?")
            params.append(self._score("minimum_confidence", query.minimum_confidence))
        if query.maximum_confidence is not None:
            clauses.append("confidence_score <= ?")
            params.append(self._score("maximum_confidence", query.maximum_confidence))

        limit = min(max(int(query.limit), 1), 10000)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        order = "DESC" if query.newest_first else "ASC"
        params.append(limit)

        with self._lock, self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM ai_decisions{where} ORDER BY timestamp_utc {order} LIMIT ?",
                params,
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def summarize(
        self,
        records: Iterable[DecisionRecord] | None = None,
    ) -> DecisionSummary:
        items = list(records) if records is not None else self.search(
            DecisionQuery(limit=10000)
        )
        closed = [
            item for item in items
            if item.status == DecisionStatus.CLOSED
            and item.realized_pnl is not None
        ]
        winners = [item for item in closed if item.realized_pnl > 0]
        losers = [item for item in closed if item.realized_pnl < 0]
        returns = [item.return_pct for item in closed if item.return_pct is not None]

        by_status: dict[str, int] = {}
        by_strategy: dict[str, int] = {}
        by_regime: dict[str, int] = {}
        for item in items:
            by_status[item.status.value] = by_status.get(item.status.value, 0) + 1
            by_strategy[item.selected_strategy] = by_strategy.get(item.selected_strategy, 0) + 1
            by_regime[item.market_regime] = by_regime.get(item.market_regime, 0) + 1

        return DecisionSummary(
            total_records=len(items),
            closed_trades=len(closed),
            winning_trades=len(winners),
            losing_trades=len(losers),
            win_rate=round(len(winners) / len(closed), 6) if closed else 0.0,
            realized_pnl=round(sum(item.realized_pnl or 0.0 for item in closed), 8),
            average_return_pct=round(sum(returns) / len(returns), 8) if returns else 0.0,
            average_confidence=round(
                sum(item.confidence_score for item in items) / len(items), 6
            ) if items else 0.0,
            by_status=by_status,
            by_strategy=by_strategy,
            by_market_regime=by_regime,
        )

    def explain(self, decision_id: str) -> str:
        record = self.get(decision_id)
        if record is None:
            raise KeyError(f"decision not found: {decision_id}")
        lines = [
            f"{record.direction.value} {record.symbol}",
            f"Status: {record.status.value}",
            f"Market Regime: {record.market_regime}",
            f"Strategy: {record.selected_strategy}",
            f"Confidence: {record.confidence_score:.1%}",
            f"Risk Score: {record.risk_score:.1%}",
            f"Risk Mode: {record.portfolio_risk_mode}",
            f"Approved Position: ${record.approved_position_value:,.2f}",
            "",
            "Explanation:",
            record.explanation,
        ]
        if record.reasons:
            lines.extend(["", "Reasons:"])
            lines.extend(f"- {reason}" for reason in record.reasons)
        return "\n".join(lines)

    def export_jsonl(
        self,
        destination: str | Path,
        records: Iterable[DecisionRecord] | None = None,
    ) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        items = list(records) if records is not None else self.search(
            DecisionQuery(limit=10000)
        )
        with path.open("w", encoding="utf-8") as handle:
            for item in items:
                handle.write(self._dump(item.to_dict()) + "\n")
        return path

    def delete(self, decision_id: str) -> bool:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM ai_decisions WHERE decision_id = ?",
                (decision_id,),
            )
        return cursor.rowcount > 0

    def clear(self) -> int:
        with self._lock, self._connect() as connection:
            cursor = connection.execute("DELETE FROM ai_decisions")
        return cursor.rowcount

    def __len__(self) -> int:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM ai_decisions"
            ).fetchone()
        return int(row["total"])
