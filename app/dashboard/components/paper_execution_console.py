"""
Paper Execution Console
AI Trading Platform Version 7.5

Allows a queued candidate to be validated and previewed
before explicit IBKR paper-order submission.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.broker.ibkr_official import (
    submit_prepared_paper_order,
)
from app.broker.paper_execution_service import (
    prepare_paper_execution,
)
from app.db.approval_queue import update_status


def show_paper_execution_console(
    candidate: dict[str, Any] | None,
    *,
    ibkr_connected: bool,
) -> None:
    st.subheader("Paper Execution Console")

    if not candidate:
        st.info(
            "Select a pending approval-queue candidate "
            "to prepare a paper order."
        )
        return

    candidate_id = candidate.get("id")
    symbol = str(candidate.get("symbol", "N/A")).upper()
    action = str(candidate.get("action", "N/A")).upper()
    quantity = int(candidate.get("quantity", 0) or 0)
    entry_price = float(candidate.get("entry_price", 0) or 0)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Queue ID", candidate_id or "N/A")
    c2.metric("Symbol", symbol)
    c3.metric("Action", action)
    c4.metric("Quantity", f"{quantity:,}")

    st.metric(
        "Planned Position Value",
        f"${quantity * entry_price:,.2f}",
    )

    order_type = st.selectbox(
        "Order Type",
        options=["MKT", "LMT"],
        key=f"paper_order_type_{candidate_id}",
    )

    limit_price: float | None = None

    if order_type == "LMT":
        limit_price = st.number_input(
            "Limit Price",
            min_value=0.01,
            value=max(entry_price, 0.01),
            step=0.01,
            key=f"paper_limit_price_{candidate_id}",
        )

    maximum_position_value = st.number_input(
        "Maximum Allowed Position Value",
        min_value=100.00,
        value=25_000.00,
        step=500.00,
        key=f"paper_max_position_{candidate_id}",
    )

    paper_account_confirmed = st.checkbox(
        "I confirm that TWS or IB Gateway is connected "
        "to an Interactive Brokers paper account.",
        key=f"paper_account_confirm_{candidate_id}",
    )

    preview_clicked = st.button(
        "Preview Paper Order",
        type="primary",
        use_container_width=True,
        key=f"preview_paper_order_{candidate_id}",
    )

    preview_key = f"paper_execution_preview_{candidate_id}"
    submission_key = f"paper_order_submission_{candidate_id}"

    if preview_clicked:
        try:
            preview = prepare_paper_execution(
                candidate=candidate,
                ibkr_connected=ibkr_connected,
                paper_account_confirmed=paper_account_confirmed,
                order_type=order_type,
                limit_price=limit_price,
                maximum_position_value=maximum_position_value,
            )

            st.session_state[preview_key] = preview
            st.session_state.pop(submission_key, None)

        except Exception as exc:
            st.session_state[preview_key] = {
                "ready": False,
                "guard": {
                    "errors": [str(exc)],
                    "warnings": [],
                },
                "order": None,
                "message": "Paper-order preview failed.",
            }

    preview = st.session_state.get(preview_key)

    if not preview:
        st.caption(
            "Previewing validates the candidate and builds "
            "a non-transmitting order package."
        )
        return

    if not preview.get("ready"):
        st.error(str(preview.get("message", "")))

        guard = preview.get("guard", {})

        for error in guard.get("errors", []):
            st.error(str(error))

        for warning in guard.get("warnings", []):
            st.warning(str(warning))

        return

    st.success(str(preview.get("message", "")))

    guard = preview.get("guard", {})
    order = preview.get("order", {})

    st.markdown("### Safety Check")

    g1, g2, g3 = st.columns(3)

    g1.metric(
        "Guard Status",
        "PASS",
    )

    g2.metric(
        "Position Value",
        f"${float(guard.get('position_value', 0)):,.2f}",
    )

    g3.metric(
        "Maximum",
        f"${float(guard.get('maximum_position_value', 0)):,.2f}",
    )

    for warning in guard.get("warnings", []):
        st.warning(str(warning))

    st.markdown("### Prepared Paper Order")
    st.json(order)

    st.warning(
        "The preview package contains transmit=False. "
        "The final button below submits it only to the "
        "connected IBKR paper account."
    )

    st.divider()
    st.markdown("### Submit to IBKR Paper Account")

    final_confirmation = st.checkbox(
        "I confirm this is the IBKR paper account and "
        "I authorize submission of this paper order.",
        key=f"final_paper_submit_confirm_{candidate_id}",
    )

    submit_clicked = st.button(
        "Submit Paper Order",
        type="primary",
        use_container_width=True,
        disabled=not final_confirmation,
        key=f"submit_paper_order_{candidate_id}",
    )

    if submit_clicked:
        try:
            submission = submit_prepared_paper_order(
                order,
                paper_account_confirmed=True,
            )

            st.session_state[submission_key] = submission

            if (
                submission.get("submitted")
                and candidate_id is not None
            ):
                update_status(
                    int(candidate_id),
                    "ORDER_SUBMITTED",
                )

        except Exception as exc:
            st.session_state[submission_key] = {
                "submitted": False,
                "status": "ERROR",
                "message": str(exc),
            }

    submission = st.session_state.get(submission_key)

    if not submission:
        return

    if submission.get("submitted"):
        st.success(
            f"Queue candidate #{candidate_id} "
            "was submitted to the IBKR paper account."
        )

        s1, s2, s3 = st.columns(3)

        s1.metric(
            "IBKR Order ID",
            submission.get("order_id", "N/A"),
        )

        s2.metric(
            "Status",
            submission.get("status", "UNKNOWN"),
        )

        s3.metric(
            "Quantity",
            submission.get("quantity", 0),
        )

        st.json(submission)

    else:
        st.error(
            "Paper order was not submitted."
        )
        st.json(submission)