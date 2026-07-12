import sqlite3
from datetime import datetime
from app.utils.config import DATABASE_PATH


def get_conn():
    return sqlite3.connect(DATABASE_PATH)


def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            symbol TEXT,
            timeframe TEXT,
            signal TEXT,
            price REAL,
            ai_score INTEGER,
            ai_decision TEXT,
            ai_risk TEXT,
            ai_reason TEXT,
            final_action TEXT,
            quantity INTEGER,
            ibkr_status TEXT,
            raw_signal TEXT
        )
        """)
        conn.commit()


def log_signal(signal, ai_result: dict, decision: dict, ibkr_result: dict | None = None):
    init_db()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO signals (
                created_at, symbol, timeframe, signal, price,
                ai_score, ai_decision, ai_risk, ai_reason,
                final_action, quantity, ibkr_status, raw_signal
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                signal.symbol,
                signal.timeframe,
                signal.signal,
                signal.price,
                int(ai_result.get("score", 0)),
                ai_result.get("decision"),
                ai_result.get("risk"),
                ai_result.get("reason"),
                decision.get("final_action"),
                int(decision.get("quantity", 0)),
                None if ibkr_result is None else str(ibkr_result),
                signal.model_dump_json(),
            ),
        )
        conn.commit()


def get_signals(limit: int = 500):
    init_db()
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    
    
def get_latest_signal_for_symbol(symbol: str) -> dict | None:
    init_db()

    with get_conn() as conn:
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            """
            SELECT *
            FROM signals
            WHERE UPPER(symbol) = UPPER(?)
            ORDER BY id DESC
            LIMIT 1
            """,
            (symbol,),
        ).fetchone()

    return dict(row) if row else None