"""
Live Position Manager
AI Trading Platform V5.0
"""

import pandas as pd
import streamlit as st


def show_live_positions(positions_data: dict) -> None:
    st.subheader("Live Position Manager")

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

    df["costBasis"] = (
        df["position"].abs()
        * df["avgCost"]
    )

    total_positions = len(df)
    total_shares = df["position"].abs().sum()
    total_cost_basis = df["costBasis"].sum()

    long_positions = int((df["position"] > 0).sum())
    short_positions = int((df["position"] < 0).sum())

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Open Positions", total_positions)
    c2.metric("Total Shares", f"{total_shares:,.0f}")
    c3.metric("Long Positions", long_positions)
    c4.metric("Short Positions", short_positions)
    c5.metric("Total Cost Basis", f"${total_cost_basis:,.2f}")

    display_columns = [
        "account",
        "symbol",
        "secType",
        "currency",
        "position",
        "avgCost",
        "costBasis",
    ]

    st.dataframe(
        df[display_columns],
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "Live market value and unrealized P/L will be added after "
        "IBKR market-data access or TradingView price synchronization "
        "is available."
    )