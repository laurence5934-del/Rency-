"""
Dashboard State Controller
AI Trading Platform Version 7.2
"""

import streamlit as st


def initialize_dashboard_state() -> None:
    defaults = {
        "market_results": [],
        "top_opportunity": None,
        "trade_candidate": None,
        "approval_queue_refresh": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value