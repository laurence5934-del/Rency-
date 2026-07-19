"""Portfolio Intelligence Dashboard - Version 9.1."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.services.portfolio_intelligence import (
    PortfolioIntelligence,
    build_portfolio_intelligence,
)


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def _percent(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def _health_message(intelligence: PortfolioIntelligence) -> None:
    message = (
        f"Portfolio Health: {intelligence.health_score}/100 — "
        f"{intelligence.health_status}"
    )
    if intelligence.health_score >= 85:
        st.success(message)
    elif intelligence.health_score >= 70:
        st.warning(message)
    else:
        st.error(message)


def show_portfolio_intelligence(
    account_data: dict,
    positions_data: dict,
    *,
    peak_net_liquidation: float | None = None,
) -> None:
    st.subheader("📊 Portfolio Intelligence")

    if not account_data.get("summary", []):
        st.warning(
            "Portfolio intelligence is unavailable because no IBKR account summary was received."
        )
        return

    try:
        intelligence = build_portfolio_intelligence(
            account_data=account_data,
            positions_data=positions_data,
            peak_net_liquidation=peak_net_liquidation,
        )
    except Exception as exc:
        st.error(f"Could not build portfolio intelligence: {exc}")
        return

    snapshot = intelligence.snapshot
    row1 = st.columns(4)
    row1[0].metric("Net Liquidation", _money(snapshot.net_liquidation))
    row1[1].metric("Available Funds", _money(intelligence.available_funds))
    row1[2].metric("Buying Power", _money(snapshot.buying_power))
    row1[3].metric("Cash", _money(intelligence.total_cash))

    row2 = st.columns(4)
    row2[0].metric("Today's P/L", _money(snapshot.daily_total_pnl))
    row2[1].metric("Exposure", _percent(intelligence.exposure_percent))
    row2[2].metric("Open Positions", snapshot.open_position_count)
    row2[3].metric(
        "Largest Position",
        intelligence.largest_position_symbol or "None",
        _percent(intelligence.largest_position_percent),
    )

    row3 = st.columns(4)
    row3[0].metric("Capital Utilization", _percent(intelligence.utilization_percent))
    row3[1].metric("Cash Percentage", _percent(intelligence.cash_percent))
    row3[2].metric("Buying Power %", _percent(intelligence.buying_power_percent))
    row3[3].metric("Drawdown", _percent(snapshot.drawdown_percent))

    _health_message(intelligence)
    st.markdown("#### 🤖 AI Portfolio Advisor")
    advisor_left, advisor_right = st.columns(2)

    with advisor_left:
        st.metric("Portfolio Risk", intelligence.advisor.risk_level)
        st.metric(
            "Suggested Maximum Position",
            _money(intelligence.advisor.suggested_position_size),
        )

    with advisor_right:
        for check in intelligence.advisor.checks:
            if "reached" in check or "too low" in check:
                st.warning(f"⚠️ {check}")
            else:
                st.write(f"✅ {check}")

    if intelligence.advisor.can_open_new_position:
        st.info(intelligence.advisor.recommendation)
    else:
        st.warning(intelligence.advisor.recommendation)

    with st.expander("Portfolio intelligence details"):
        st.json(intelligence.to_dict())
