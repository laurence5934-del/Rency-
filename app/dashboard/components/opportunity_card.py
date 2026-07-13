"""
AI Opportunity Card
AI Trading Platform Version 6.3
"""

import streamlit as st


def show_opportunity_card(opportunity: dict) -> None:
    """
    Display a professional AI Opportunity Card.
    """

    if not opportunity:
        st.info("No opportunity available.")
        return

    symbol = str(opportunity.get("symbol", "N/A"))
    score = int(opportunity.get("score", 0) or 0)
    action = str(opportunity.get("action", "N/A"))
    price = float(opportunity.get("price", 0) or 0)

    if score >= 90:
        confidence = 96
    elif score >= 80:
        confidence = 90
    elif score >= 70:
        confidence = 82
    else:
        confidence = 65

    st.subheader(f"AI Opportunity Center - {symbol}")

    c1, c2, c3 = st.columns(3)

    c1.metric("AI Score", f"{score}/100")
    c2.metric("Recommendation", action)
    c3.metric("Confidence", f"{confidence}%")

    st.divider()
    st.markdown("### Technical Score Breakdown")

    tc1, tc2, tc3 = st.columns(3)

    tc1.metric(
        "Trend",
        f"{opportunity.get('trend_score', 0)}/25",
    )

    tc2.metric(
        "Momentum",
        f"{opportunity.get('momentum_score', 0)}/20",
    )

    tc3.metric(
        "Volume",
        f"{opportunity.get('volume_score', 0)}/20",
    )

    tc4, tc5, tc6 = st.columns(3)

    tc4.metric(
        "Volatility",
        f"{opportunity.get('volatility_score', 0)}/10",
    )

    tc5.metric(
        "Risk",
        f"{opportunity.get('risk_score', 0)}/10",
    )

    tc6.metric(
        "News",
        f"{opportunity.get('news_score', 0)}/15",
    )

    st.divider()
    st.markdown("### AI Summary")

    reasons = opportunity.get("reasons", [])

    if reasons:
        for reason in reasons[:6]:
            st.success(str(reason))
    else:
        st.info("No AI reasons are available.")

    warnings = opportunity.get("warnings", [])

    if warnings:
        st.divider()
        st.markdown("### Warnings")

        for warning in warnings:
            st.warning(str(warning))

    st.divider()
    st.markdown("### Trade Plan")

    stop = price * 0.98 if price > 0 else 0
    target = price * 1.08 if price > 0 else 0

    p1, p2, p3 = st.columns(3)

    p1.metric("Entry", f"${price:,.2f}")
    p2.metric("Stop Loss", f"${stop:,.2f}")
    p3.metric("Target", f"${target:,.2f}")

    st.caption(
        "Research and paper-trading use only. "
        "The trade plan is a simple model and is not an execution instruction."
    )