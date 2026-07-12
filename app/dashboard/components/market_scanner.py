"""
Market Scanner Dashboard
AI Trading Platform V6.0
"""

import pandas as pd
import streamlit as st

from app.scanner.market_scanner import scan_market


def show_market_scanner() -> None:
    st.subheader("AI Market Scanner")

    st.caption(
        "Development mode: scores are random placeholders "
        "and must not be used for trading decisions."
    )

    if st.button(
        "Scan Market",
        type="primary",
        width="stretch",
    ):
        with st.spinner("Scanning watchlist..."):
            results = scan_market()

        if not results:
            st.warning("No scanner results were produced.")
            return

        df = pd.DataFrame(results)
        df.insert(0, "rank", range(1, len(df) + 1))

        buy_count = int((df["action"] == "BUY").sum())
        watch_count = int((df["action"] == "WATCH").sum())
        ignore_count = int((df["action"] == "IGNORE").sum())

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Symbols Scanned", len(df))
        c2.metric("BUY", buy_count)
        c3.metric("WATCH", watch_count)
        c4.metric("IGNORE", ignore_count)

        st.dataframe(
            df,
            width="stretch",
            hide_index=True,
        )

        top_result = results[0]

        st.success(
            f"Top placeholder result: "
            f"{top_result['symbol']} — "
            f"Score {top_result['score']} — "
            f"{top_result['action']}"
        )