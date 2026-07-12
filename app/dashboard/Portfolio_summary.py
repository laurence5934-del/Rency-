"""
Portfolio Summary Component
AI Trading Platform V4.7
"""

import streamlit as st


def show_portfolio_summary(account_data: dict) -> None:
    st.subheader("📈 Portfolio Summary")

    summary_rows = account_data.get("summary", [])

    if not summary_rows:
        st.warning("No account information available.")
        return

    values = {
        row.get("tag"): row.get("value")
        for row in summary_rows
    }

    def money(tag: str) -> str:
        try:
            return f"${float(values.get(tag, 0)):,.2f}"
        except (TypeError, ValueError):
            return "N/A"

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Net Liquidation", money("NetLiquidation"))
    c2.metric("Available Funds", money("AvailableFunds"))
    c3.metric("Buying Power", money("BuyingPower"))
    c4.metric("Cash", money("TotalCashValue"))