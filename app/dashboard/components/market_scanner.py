"""
Market Scanner Dashboard
AI Trading Platform Version 7.2
"""

import pandas as pd
import streamlit as st

from app.ai.trading_assistant import (
    build_trading_assistant_summary,
)
from app.dashboard.components.trading_assistant import (
    show_trading_assistant,
)
from app.ai.trade_candidate import build_trade_candidate
from app.dashboard.components.opportunity_card import (
    show_opportunity_card,
)
from app.dashboard.components.trade_candidate import (
    show_trade_candidate,
)
from app.dashboard.controllers.dashboard_controller import (
    get_market_results,
    get_top_opportunity,
    get_trade_candidate,
    save_market_results,
    save_trade_candidate,
    set_scan_error,
)
from app.scanner.market_scanner import scan_market


def show_market_scanner() -> None:
    st.subheader("AI Market Scanner")

    st.caption(
        "Live daily analysis powered by Yahoo Finance and the "
        "AI Master Scoring Engine. Prices may be delayed and are "
        "intended for research and paper trading."
    )

    scan_clicked = st.button(
        "Scan Market",
        type="primary",
        width="stretch",
    )

    if scan_clicked:
        try:
            with st.spinner("Scanning watchlist..."):
                results = scan_market()

            save_market_results(results)

        except Exception as exc:
            set_scan_error(str(exc))
            st.error(f"Market scan failed: {exc}")

    results = get_market_results()

    if not results:
        st.info("Click Scan Market to generate live analysis.")
        return

    df = pd.DataFrame(results)
    df.insert(0, "rank", range(1, len(df) + 1))

    buy_count = int(
        df["action"].isin(["BUY", "STRONG_BUY"]).sum()
    )
    watch_count = int((df["action"] == "WATCH").sum())
    ignore_count = int(
        df["action"].isin(
            [
                "IGNORE",
                "CAUTION",
                "DATA_ERROR",
                "SYSTEM_ERROR",
            ]
        ).sum()
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Symbols Scanned", len(df))
    c2.metric("BUY", buy_count)
    c3.metric("WATCH", watch_count)
    c4.metric("IGNORE", ignore_count)

    display_columns = [
        "rank",
        "symbol",
        "score",
        "grade",
        "action",
        "price",
        "trend",
        "trend_score",
        "momentum",
        "momentum_score",
        "rsi",
        "macd",
        "relative_volume",
        "volume_score",
        "volatility",
        "volatility_score",
        "risk",
        "risk_score",
        "news_score",
    ]

    available_columns = [
        column
        for column in display_columns
        if column in df.columns
    ]

    st.dataframe(
        df[available_columns],
        width="stretch",
        hide_index=True,
    )

    top_result = get_top_opportunity()

    if top_result is None:
        top_result = results[0]

    st.markdown("### Today's Top AI Opportunity")

    st.success(
        f"Top live-analysis result: "
        f"{top_result['symbol']} - "
        f"Score {top_result['score']} - "
        f"{top_result['action']}"
    )

    st.divider()
    show_opportunity_card(top_result)

    existing_candidate = get_trade_candidate()

    candidate_symbol = str(
        top_result.get("symbol", "")
    ).upper()

    if (
        existing_candidate is None
        or str(
            existing_candidate.get("symbol", "")
        ).upper() != candidate_symbol
    ):
        entry_price = float(
            top_result.get("price", 0) or 0
        )
        stop_loss = round(entry_price * 0.98, 2)
        target_price = round(entry_price * 1.08, 2)

        candidate = build_trade_candidate(
            symbol=candidate_symbol,
            score=int(
                top_result.get("score", 0) or 0
            ),
            action=str(
                top_result.get("action", "")
            ),
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            account_value=100_000.00,
            risk_per_trade_pct=1.0,
        )

        save_trade_candidate(candidate)

    candidate = get_trade_candidate()

    st.divider()
    show_trade_candidate(candidate)

    assistant_result = build_trading_assistant_summary(
        opportunity=top_result,
        candidate=candidate,
    )

    st.divider()
    show_trading_assistant(assistant_result)