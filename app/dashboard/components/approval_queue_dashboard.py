"""
Approval Queue Dashboard
AI Trading Platform Version 7.3

Displays persistent trade candidates waiting for review.
This component does not submit IBKR orders.
"""

import pandas as pd
import streamlit as st

from app.db.approval_queue import (
    get_pending_candidates,
    update_status,
)


def show_approval_queue_dashboard() -> None:
    st.subheader("AI Approval Queue")

    try:
        pending_candidates = get_pending_candidates()
    except Exception as exc:
        st.error(
            f"Could not load the persistent approval queue: {exc}"
        )
        return

    if not pending_candidates:
        st.info("No pending trade candidates are in the queue.")
        return

    df = pd.DataFrame(pending_candidates)

    display_columns = [
        "id",
        "symbol",
        "score",
        "action",
        "quantity",
        "entry_price",
        "stop_loss",
        "target_price",
        "risk_budget",
        "risk_reward",
        "status",
        "created_at",
    ]

    available_columns = [
        column
        for column in display_columns
        if column in df.columns
    ]

    c1, c2, c3 = st.columns(3)

    c1.metric("Pending Candidates", len(df))
    c2.metric(
        "Average Score",
        f"{df['score'].mean():.1f}",
    )
    c3.metric(
        "Total Planned Risk",
        f"${df['risk_budget'].sum():,.2f}",
    )

    st.dataframe(
        df[available_columns],
        width="stretch",
        hide_index=True,
    )

    candidate_options = {
        (
            f"Queue #{row['id']} - "
            f"{row['symbol']} - "
            f"Score {row['score']} - "
            f"Qty {row['quantity']}"
        ): row
        for row in pending_candidates
    }

    selected_label = st.selectbox(
        "Select a pending candidate",
        options=list(candidate_options.keys()),
    )

    selected_candidate = candidate_options[selected_label]
    candidate_id = int(selected_candidate["id"])
    symbol = str(selected_candidate["symbol"]).upper()

    st.markdown("### Selected Candidate")

    d1, d2, d3, d4 = st.columns(4)

    d1.metric("Symbol", symbol)
    d2.metric("Score", selected_candidate["score"])
    d3.metric("Quantity", selected_candidate["quantity"])
    d4.metric(
        "Risk / Reward",
        f"{float(selected_candidate['risk_reward']):.2f}:1",
    )

    st.write(
        {
            "Entry": selected_candidate["entry_price"],
            "Stop Loss": selected_candidate["stop_loss"],
            "Target": selected_candidate["target_price"],
            "Risk Budget": selected_candidate["risk_budget"],
            "Status": selected_candidate["status"],
            "Created": selected_candidate["created_at"],
        }
    )

    confirm_reject = st.checkbox(
        f"I confirm rejection of queue candidate #{candidate_id}.",
        key=f"queue_reject_confirm_{candidate_id}",
    )

    if st.button(
        "Reject Selected Candidate",
        width="stretch",
        disabled=not confirm_reject,
        key=f"queue_reject_{candidate_id}",
    ):
        try:
            update_status(
                candidate_id,
                "REJECTED",
            )

            st.warning(
                f"Queue candidate #{candidate_id} for {symbol} "
                "was rejected."
            )

            st.rerun()

        except Exception as exc:
            st.error(
                f"Could not reject queue candidate: {exc}"
            )

    st.caption(
        "Execution controls are not enabled yet. "
        "Version 7.3 will add a separate paper-order submission step."
    )