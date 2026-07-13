"""
AI Trade Candidate Review Card
AI Trading Platform Version 7.1

This component is review-only.
It does not submit, modify, or cancel IBKR orders.
"""

from typing import Any

import streamlit as st


def show_trade_candidate(
    candidate: dict[str, Any],
) -> str | None:
    """
    Display a trade candidate and return its current review status.

    Possible statuses:
    - APPROVED_FOR_REVIEW
    - REJECTED
    - None
    """

    if not candidate:
        st.info("No trade candidate is available.")
        return None

    symbol = str(
        candidate.get("symbol", "N/A")
    ).upper()

    score = int(
        candidate.get("score", 0) or 0
    )

    action = str(
        candidate.get("action", "N/A")
    ).upper()

    quantity = int(
        candidate.get("quantity", 0) or 0
    )

    entry_price = float(
        candidate.get("entry_price", 0) or 0
    )

    stop_loss = float(
        candidate.get("stop_loss", 0) or 0
    )

    target_price = float(
        candidate.get("target_price", 0) or 0
    )

    risk_budget = float(
        candidate.get("risk_budget", 0) or 0
    )

    estimated_risk = float(
        candidate.get(
            "estimated_dollar_risk",
            0,
        )
        or 0
    )

    estimated_reward = float(
        candidate.get(
            "estimated_reward",
            0,
        )
        or 0
    )

    risk_reward_ratio = float(
        candidate.get(
            "risk_reward_ratio",
            0,
        )
        or 0
    )

    eligible = bool(
        candidate.get(
            "approval_eligible",
            False,
        )
    )

    reasons = candidate.get("reasons", [])
    warnings = candidate.get("warnings", [])

    status_key = f"candidate_status_{symbol}"

    if status_key not in st.session_state:
        st.session_state[status_key] = None

    st.subheader(
        f"AI Trade Candidate - {symbol}"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "AI Score",
        f"{score}/100",
    )

    c2.metric(
        "Action",
        action,
    )

    c3.metric(
        "Quantity",
        f"{quantity:,}",
    )

    c4.metric(
        "Eligible",
        "YES" if eligible else "NO",
    )

    st.divider()
    st.markdown("### Trade Plan")

    p1, p2, p3 = st.columns(3)

    p1.metric(
        "Entry",
        f"${entry_price:,.2f}",
    )

    p2.metric(
        "Stop Loss",
        f"${stop_loss:,.2f}",
    )

    p3.metric(
        "Target",
        f"${target_price:,.2f}",
    )

    r1, r2, r3, r4 = st.columns(4)

    r1.metric(
        "Risk Budget",
        f"${risk_budget:,.2f}",
    )

    r2.metric(
        "Estimated Risk",
        f"${estimated_risk:,.2f}",
    )

    r3.metric(
        "Estimated Reward",
        f"${estimated_reward:,.2f}",
    )

    r4.metric(
        "Risk / Reward",
        f"{risk_reward_ratio:.2f}:1",
    )

    if reasons:
        st.markdown("### Reasons")

        for reason in reasons:
            st.success(str(reason))

    if warnings:
        st.markdown("### Warnings")

        for warning in warnings:
            st.warning(str(warning))

    confirmation = st.checkbox(
        (
            "I confirm that this candidate is for "
            "paper-trading review only."
        ),
        key=f"candidate_confirm_{symbol}",
    )

    approve_column, reject_column = st.columns(2)

    with approve_column:
        approve_clicked = st.button(
            "Approve for Paper-Trade Review",
            type="primary",
            width="stretch",
            disabled=(
                not confirmation
                or not eligible
            ),
            key=f"candidate_approve_{symbol}",
        )

    with reject_column:
        reject_clicked = st.button(
            "Reject Candidate",
            width="stretch",
            key=f"candidate_reject_{symbol}",
        )

    if approve_clicked:
        st.session_state[
            status_key
        ] = "APPROVED_FOR_REVIEW"

    if reject_clicked:
        st.session_state[
            status_key
        ] = "REJECTED"

    current_status = st.session_state[
        status_key
    ]

    if current_status == "APPROVED_FOR_REVIEW":
        st.success(
            "Candidate approved for paper-trade review. "
            "No broker order has been submitted."
        )

    elif current_status == "REJECTED":
        st.error(
            "Candidate rejected. "
            "No broker order has been submitted."
        )

    st.caption(
        "This component records only a temporary dashboard "
        "decision. IBKR execution will be added separately "
        "after database persistence and duplicate-order "
        "protection are implemented."
    )

    return current_status