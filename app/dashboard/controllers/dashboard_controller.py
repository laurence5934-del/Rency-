"""
Dashboard State Controller
AI Trading Platform Version 7.2

Centralizes Streamlit session state for the market scanner,
opportunity center, trade candidate, and approval workflow.
"""

from copy import deepcopy
from typing import Any

import streamlit as st


DEFAULT_DASHBOARD_STATE: dict[str, Any] = {
    "market_results": [],
    "top_opportunity": None,
    "trade_candidate": None,
    "candidate_review_status": None,
    "candidate_queue_id": None,
    "approval_queue_refresh": False,
    "last_scan_error": None,
}


def initialize_dashboard_state() -> None:
    """
    Create missing dashboard session-state values.

    Existing values are preserved during Streamlit reruns.
    """

    for key, default_value in DEFAULT_DASHBOARD_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = deepcopy(default_value)


def save_market_results(
    results: list[dict[str, Any]],
) -> None:
    """
    Persist the latest market scan and top opportunity.
    """

    st.session_state["market_results"] = results
    st.session_state["top_opportunity"] = (
        results[0] if results else None
    )
    st.session_state["trade_candidate"] = None
    st.session_state["candidate_review_status"] = None
    st.session_state["candidate_queue_id"] = None
    st.session_state["last_scan_error"] = None


def get_market_results() -> list[dict[str, Any]]:
    return list(
        st.session_state.get(
            "market_results",
            [],
        )
    )


def get_top_opportunity() -> dict[str, Any] | None:
    return st.session_state.get("top_opportunity")


def save_trade_candidate(
    candidate: dict[str, Any] | None,
) -> None:
    st.session_state["trade_candidate"] = candidate


def get_trade_candidate() -> dict[str, Any] | None:
    return st.session_state.get("trade_candidate")


def set_candidate_review_status(
    status: str | None,
    *,
    queue_id: int | None = None,
) -> None:
    st.session_state["candidate_review_status"] = status
    st.session_state["candidate_queue_id"] = queue_id


def get_candidate_review_status() -> str | None:
    return st.session_state.get(
        "candidate_review_status"
    )


def get_candidate_queue_id() -> int | None:
    return st.session_state.get(
        "candidate_queue_id"
    )


def set_scan_error(
    message: str | None,
) -> None:
    st.session_state["last_scan_error"] = message


def get_scan_error() -> str | None:
    return st.session_state.get(
        "last_scan_error"
    )


def clear_market_scan() -> None:
    """
    Clear only scanner-related state.
    """

    st.session_state["market_results"] = []
    st.session_state["top_opportunity"] = None
    st.session_state["trade_candidate"] = None
    st.session_state["candidate_review_status"] = None
    st.session_state["candidate_queue_id"] = None
    st.session_state["last_scan_error"] = None