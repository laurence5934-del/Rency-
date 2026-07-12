"""
Open Orders Panel
AI Trading Platform V4.6
"""

import pandas as pd
import streamlit as st

from app.broker.ibkr_official import cancel_order
from app.broker.open_orders import get_open_orders


def show_open_orders():
    st.subheader("📋 Open Orders")

    try:
        result = get_open_orders()
    except Exception as exc:
        st.error(f"Could not read IBKR open orders: {exc}")
        return

    orders = result.get("orders", [])

    if not orders:
        st.info("No open orders found in the IBKR paper account.")
        return

    df_orders = pd.DataFrame(orders)

    st.dataframe(
        df_orders,
        width="stretch",
        hide_index=True,
    )

    order_options = {
        (
            f"Order #{order['order_id']} — "
            f"{order['symbol']} — "
            f"{order['action']} {order['quantity']:g} — "
            f"{order['status']}"
        ): order
        for order in orders
    }

    selected_label = st.selectbox(
        "Select an order",
        options=list(order_options.keys()),
    )

    selected_order = order_options[selected_label]
    order_id = int(selected_order["order_id"])

    confirm_cancel = st.checkbox(
        f"I confirm cancellation of paper order #{order_id}.",
        key=f"confirm_cancel_{order_id}",
    )

    if st.button(
        "Cancel Selected Order",
        width="stretch",
        disabled=not confirm_cancel,
        key=f"cancel_order_{order_id}",
    ):
        with st.spinner(f"Cancelling order #{order_id}..."):
            try:
                cancel_result = cancel_order(order_id)

                if cancel_result.get("cancel_requested"):
                    st.success(
                        f"Cancellation requested for order #{order_id}. "
                        f"Status: {cancel_result.get('status')}"
                    )
                else:
                    st.error(f"Cancellation failed: {cancel_result}")

                st.json(cancel_result)

            except Exception as exc:
                st.error(f"Cancellation failed: {exc}")

        st.rerun()