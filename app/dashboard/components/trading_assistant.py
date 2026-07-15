"""
AI Trading Assistant Dashboard
AI Trading Platform Version 7.3
"""

from typing import Any

import streamlit as st


def show_trading_assistant(
    assistant_result: dict[str, Any],
) -> None:
    if not assistant_result:
        st.info("No AI Trading Assistant analysis is available.")
        return

    recommendation = str(
        assistant_result.get("recommendation", "N/A")
    )

    confidence = int(
        assistant_result.get("confidence", 0) or 0
    )

    summary = str(
        assistant_result.get("summary", "")
    )

    reasons = assistant_result.get("reasons", [])
    warnings = assistant_result.get("warnings", [])

    st.subheader("AI Trading Assistant")

    c1, c2 = st.columns(2)

    c1.metric(
        "Recommendation",
        recommendation,
    )

    c2.metric(
        "Confidence",
        f"{confidence}%",
    )

    st.info(summary)

    if reasons:
        st.markdown("### Supporting Factors")

        for reason in reasons:
            st.success(str(reason))

    if warnings:
        st.markdown("### Risk Warnings")

        for warning in warnings:
            st.warning(str(warning))

    st.caption(
        "This explanation is generated from the platform's existing "
        "technical, risk, and trade-candidate data. It does not submit orders."
    )