"""
Market Scanner Dashboard
AI Trading Platform V6.0
"""

import pandas as pd
import streamlit as st

from app.ai.trade_candidate import build_trade_candidate
from app.scanner.market_scanner import scan_market
from app.dashboard.components.trade_candidate import show_trade_candidate
from app.dashboard.components.opportunity_card import (
    show_opportunity_card,
)

def show_market_scanner() -> None:
    st.subheader("AI Market Scanner")

    st.caption(
        "Live daily analysis powered by Yahoo Finance and the AI Master Scoring Engine. "
        "Prices may be delayed and are intended for research and paper trading."
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
            return None

        df = pd.DataFrame(results)
        df.insert(0, "rank", range(1, len(df) + 1))

        top_result = results[0]

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

        st.markdown("### Today's Top AI Opportunity")

        st.success(
            f"Top live-analysis result: "
            f"{top_result['symbol']} - "
            f"Score {top_result['score']} - "
            f"{top_result['action']}"
        )
        
        st.divider()
        show_opportunity_card(top_result)

        account_value = 100_000.00

        entry_price = float(top_result.get("price", 0) or 0)
        stop_loss = round(entry_price * 0.98, 2)
        target_price = round(entry_price * 1.08, 2)

        candidate = build_trade_candidate(
            symbol=str(top_result.get("symbol", "")),
            score=int(top_result.get("score", 0) or 0),
            action=str(top_result.get("action", "")),
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            account_value=account_value,
            risk_per_trade_pct=1.0,
        )

        st.divider()
        show_trade_candidate(candidate)