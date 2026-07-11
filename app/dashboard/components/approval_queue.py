"""
Manual Approval Panel
AI Trading Platform V4 Professional
"""

import streamlit as st

from app.broker.ibkr_official import place_paper_buy
from app.db.approvals import (
    get_pending_manual_reviews,
    get_review_history,
    record_review,
)


def show_approval_queue() -> None:
    st.subheader("✅ Manual Approval Queue")

    try:
        pending_reviews = get_pending_manual_reviews(limit=20)
    except Exception as exc:
        st.error(f"Could not load the approval queue: {exc}")
        return

    if not pending_reviews:
        st.info("No signals are currently waiting for manual approval.")
    else:
        signal_options = {
            (
                f"Signal #{signal['id']} — {signal['symbol']} — "
                f"Score {signal['ai_score']} — Qty {signal['quantity']}"
            ): signal
            for signal in pending_reviews
        }

        selected_label = st.selectbox(
            "Select a signal to review",
            options=list(signal_options.keys()),
        )

        selected_signal = signal_options[selected_label]

        signal_id = int(selected_signal["id"])
        symbol = str(selected_signal["symbol"]).upper()
        quantity = int(selected_signal.get("quantity", 0) or 0)
        ai_score = int(selected_signal.get("ai_score", 0) or 0)
        ai_decision = str(selected_signal.get("ai_decision", "N/A"))
        ai_risk = str(selected_signal.get("ai_risk", "N/A"))
        ai_reason = str(selected_signal.get("ai_reason", ""))
        price = selected_signal.get("price")

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric("Symbol", symbol)
        c2.metric("AI Decision", ai_decision)
        c3.metric("AI Score", f"{ai_score}/100")
        c4.metric("Risk", ai_risk)
        c5.metric("Quantity", quantity)

        st.write(
            {
                "Signal ID": signal_id,
                "Price": price,
                "Timeframe": selected_signal.get("timeframe"),
                "Signal": selected_signal.get("signal"),
                "Created": selected_signal.get("created_at"),
            }
        )

        st.info(f"AI reason: {ai_reason}")

        approval_confirmed = st.checkbox(
            "I confirm this is an IBKR paper-trading order.",
            key=f"paper_confirmation_{signal_id}",
        )

        note = st.text_input(
            "Review note",
            key=f"review_note_{signal_id}",
            placeholder="Optional reason or comment",
        )

        approve_column, reject_column = st.columns(2)

        with approve_column:
            approve_clicked = st.button(
                "✅ Approve Paper Trade",
                type="primary",
                width="stretch",
                disabled=not approval_confirmed,
                key=f"approve_{signal_id}",
            )

        with reject_column:
            reject_clicked = st.button(
                "❌ Reject Signal",
                width="stretch",
                key=f"reject_{signal_id}",
            )

        if approve_clicked:
            if quantity <= 0:
                st.error("The order quantity must be greater than zero.")
                return

            with st.spinner(
                f"Submitting {quantity} share(s) of {symbol} to IBKR Paper Trading..."
            ):
                try:
                    broker_result = place_paper_buy(symbol, quantity)

                    broker_submitted = bool(
                        broker_result.get("submitted")
                    )

                    review_status = (
                        "ORDER_SUBMITTED"
                        if broker_submitted
                        else "ORDER_FAILED"
                    )

                    record_review(
                        signal_id=signal_id,
                        review_status=review_status,
                        note=note,
                        broker_result=broker_result,
                    )

                    if broker_submitted:
                        st.success(
                            f"Paper order submitted. "
                            f"Order ID: {broker_result.get('order_id')} — "
                            f"Status: {broker_result.get('status')}"
                        )
                    else:
                        st.error(
                            f"IBKR did not accept the paper order: "
                            f"{broker_result}"
                        )

                    st.json(broker_result)

                except Exception as exc:
                    record_review(
                        signal_id=signal_id,
                        review_status="ORDER_FAILED",
                        note=f"{note} Error: {exc}".strip(),
                    )
                    st.error(f"Paper order submission failed: {exc}")

            st.rerun()

        if reject_clicked:
            record_review(
                signal_id=signal_id,
                review_status="REJECTED",
                note=note or "Rejected manually from dashboard.",
            )

            st.warning(
                f"Signal #{signal_id} for {symbol} was rejected."
            )

            st.rerun()

    st.markdown("#### Review History")

    try:
        history = get_review_history(limit=25)
    except Exception as exc:
        st.error(f"Could not load review history: {exc}")
        return

    if history:
        st.dataframe(
            history,
            width="stretch",
            hide_index=True,
        )
    else:
        st.caption("No approval or rejection history yet.")