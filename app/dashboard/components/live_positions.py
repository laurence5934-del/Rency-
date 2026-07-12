"""
Live Position Analytics
AI Trading Platform V5.1
"""

import pandas as pd
import streamlit as st

from app.ai.position_health import score_position
from app.db.database import get_latest_signal_for_symbol


def show_live_positions(positions_data: dict) -> None:
    st.subheader("Live Position Analytics")

    positions = positions_data.get("positions", [])

    if not positions:
        st.info("No open positions found in the IBKR paper account.")
        return

    df = pd.DataFrame(positions)

    required_defaults = {
        "account": "",
        "symbol": "",
        "secType": "",
        "currency": "USD",
        "position": 0,
        "avgCost": 0,
    }

    for column, default_value in required_defaults.items():
        if column not in df.columns:
            df[column] = default_value

    df["position"] = pd.to_numeric(
        df["position"],
        errors="coerce",
    ).fillna(0)

    df["avgCost"] = pd.to_numeric(
        df["avgCost"],
        errors="coerce",
    ).fillna(0)

    latest_prices = []
    price_sources = []

    for symbol in df["symbol"]:
        latest_signal = get_latest_signal_for_symbol(str(symbol))

        latest_ai_scores = []
        latest_ai_decisions = []
        latest_ai_risks = []
        health_scores = []
        health_statuses = []
        recommendations = []
        health_reasons = []
    
    if latest_signal:
        latest_ai_score = latest_signal.get("ai_score")
        latest_ai_decision = latest_signal.get("ai_decision")
        latest_ai_risk = latest_signal.get("ai_risk")

        "latestAiScore",
        "latestAiDecision",
        "latestAiRisk",
        "healthScore",
        "healthStatus",
        "recommendation",
        "healthReasons",
    
    else:
        latest_ai_score = None
        latest_ai_decision = None
        latest_ai_risk = None

        latest_ai_scores.append(latest_ai_score)
        latest_ai_decisions.append(latest_ai_decision)
        latest_ai_risks.append(latest_ai_risk)

        if latest_signal and latest_signal.get("price") is not None:
            latest_prices.append(float(latest_signal["price"]))
            price_sources.append("TradingView signal")
        else:
            latest_prices.append(None)
            price_sources.append("Unavailable")

    df["currentPrice"] = latest_prices
    df["priceSource"] = price_sources

    df["costBasis"] = (
        df["position"].abs()
        * df["avgCost"]
    )

    df["marketValue"] = (
        df["position"]
        * df["currentPrice"]
    )

    df["unrealizedPnL"] = (
        df["marketValue"]
        - (df["position"] * df["avgCost"])
    )

    df["pnlPct"] = 0.0

    valid_cost = df["avgCost"] != 0

    df.loc[valid_cost, "pnlPct"] = (
        (
            df.loc[valid_cost, "currentPrice"]
            - df.loc[valid_cost, "avgCost"]
        )
        / df.loc[valid_cost, "avgCost"]
        * 100
    )

    def position_status(pnl_value) -> str:
        if pd.isna(pnl_value):
            return "NO PRICE"
        if pnl_value > 0:
            return "WINNING"
        if pnl_value < 0:
            return "LOSING"
        return "BREAK EVEN"

    df["status"] = df["unrealizedPnL"].apply(position_status)

    total_positions = len(df)
    total_market_value = pd.to_numeric(
        df["marketValue"],
        errors="coerce",
    ).fillna(0).sum()

    total_unrealized_pnl = pd.to_numeric(
        df["unrealizedPnL"],
        errors="coerce",
    ).fillna(0).sum()

    winning_positions = int(
        (df["status"] == "WINNING").sum()
    )

    losing_positions = int(
        (df["status"] == "LOSING").sum()
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Open Positions", total_positions)
    c2.metric("Market Value", f"${total_market_value:,.2f}")
    c3.metric("Unrealized P/L", f"${total_unrealized_pnl:,.2f}")
    c4.metric("Winning", winning_positions)
    c5.metric("Losing", losing_positions)

    display_columns = [
        "symbol",
        "position",
        "avgCost",
        "currentPrice",
        "marketValue",
        "unrealizedPnL",
        "pnlPct",
        "status",
        "priceSource",
    ]

    st.dataframe(
        df[display_columns],
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "Current prices are taken from the latest stored TradingView "
        "signal for each symbol. These prices may be stale and are not "
        "a substitute for live broker market data."
    )