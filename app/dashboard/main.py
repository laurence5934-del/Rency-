import time

import pandas as pd
import streamlit as st

from app.dashboard.components.live_positions import show_live_positions
from app.dashboard.components.portfolio_summary import show_portfolio_summary
from app.dashboard.components.open_orders import show_open_orders
from app.dashboard.components.approval_queue import show_approval_queue
from app.broker.ibkr_official import get_account_summary, get_positions
from app.db.database import get_signals


st.set_page_config(
    page_title="AI Trading Platform V4 Professional",
    page_icon="📈",
    layout="wide",
)

st.title("AI Trading Platform V4 Professional")
st.caption(
    "OpenAI + Interactive Brokers + TradingView + Risk Management"
)


def safe_account_summary() -> dict:
    try:
        return get_account_summary()
    except Exception as exc:
        return {
            "connected": False,
            "accounts": [],
            "summary": [],
            "error": str(exc),
        }


def safe_positions() -> dict:
    try:
        return get_positions()
    except Exception as exc:
        return {
            "connected": False,
            "accounts": [],
            "positions": [],
            "error": str(exc),
        }


def format_money(value) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def signal_icon(decision: str) -> str:
    decision = str(decision or "").upper()

    if decision in {"BUY", "PAPER_BUY"}:
        return "🟢"
    if decision in {"WATCH", "MANUAL_REVIEW"}:
        return "🟡"
    if decision in {"REJECT", "NO_TRADE"}:
        return "🔴"

    return "⚪"


def risk_icon(risk: str) -> str:
    risk = str(risk or "").upper()

    if risk == "LOW":
        return "🟢"
    if risk == "MEDIUM":
        return "🟡"
    if risk == "HIGH":
        return "🔴"

    return "⚪"


with st.sidebar:
    st.header("Controls")

    auto_refresh = st.checkbox(
        "Auto refresh",
        value=False,
    )

    refresh_seconds = st.slider(
        "Refresh interval",
        min_value=5,
        max_value=60,
        value=15,
        step=5,
    )

    if st.button("Refresh now", width="stretch"):
        st.rerun()

    st.divider()

    signal_limit = st.selectbox(
        "Signals to display",
        options=[10, 25, 50, 100],
        index=1,
    )

    st.info(
        "Paper trading and manual approval remain enabled."
    )


account_data = safe_account_summary()
positions_data = safe_positions()


st.subheader("IBKR Paper Account Summary")

summary = account_data.get("summary", [])

if summary:
    df_summary = pd.DataFrame(summary)

    def get_account_value(tag: str):
        matching_rows = df_summary[df_summary["tag"] == tag]

        if matching_rows.empty:
            return None

        return matching_rows.iloc[0]["value"]

    net_liquidation = get_account_value("NetLiquidation")
    available_funds = get_account_value("AvailableFunds")
    buying_power = get_account_value("BuyingPower")
    total_cash = get_account_value("TotalCashValue")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Net Liquidation",
        format_money(net_liquidation),
    )

    c2.metric(
        "Available Funds",
        format_money(available_funds),
    )

    c3.metric(
        "Buying Power",
        format_money(buying_power),
    )

    c4.metric(
        "Cash",
        format_money(total_cash),
    )

    with st.expander("View raw account data"):
        st.dataframe(
            df_summary,
            width="stretch",
            hide_index=True,
        )

else:
    error_message = account_data.get(
        "error",
        "No account summary received.",
    )

    st.warning(
        f"IBKR account information is unavailable: {error_message}"
    )


st.divider()


st.subheader("🤖 AI Signal Center")

try:
    signals = get_signals(limit=int(signal_limit))
except Exception as exc:
    signals = []
    st.error(f"Could not read signal database: {exc}")

if signals:
    df_signals = pd.DataFrame(signals)

    latest_signal = df_signals.iloc[0]

    symbol = str(latest_signal.get("symbol", "N/A"))
    ai_decision = str(
        latest_signal.get("ai_decision", "N/A")
    ).upper()

    ai_risk = str(
        latest_signal.get("ai_risk", "N/A")
    ).upper()

    final_action = str(
        latest_signal.get("final_action", "N/A")
    ).upper()

    ai_score = int(
        latest_signal.get("ai_score", 0) or 0
    )

    quantity = int(
        latest_signal.get("quantity", 0) or 0
    )

    latest_price = latest_signal.get("price")
    latest_timeframe = latest_signal.get("timeframe", "N/A")
    latest_signal_type = latest_signal.get("signal", "N/A")
    latest_reason = latest_signal.get(
        "ai_reason",
        "No explanation available.",
    )

    st.markdown(
        f"### {signal_icon(ai_decision)} {symbol}"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "AI Decision",
        ai_decision,
    )

    c2.metric(
        "AI Score",
        f"{ai_score}/100",
    )

    c3.metric(
        "Risk",
        f"{risk_icon(ai_risk)} {ai_risk}",
    )

    c4.metric(
        "Final Action",
        final_action,
    )

    c5.metric(
        "Quantity",
        quantity,
    )

    info_left, info_right = st.columns(2)

    with info_left:
        st.write(
            {
                "Symbol": symbol,
                "Signal": latest_signal_type,
                "Timeframe": latest_timeframe,
                "Price": latest_price,
                "Created": latest_signal.get("created_at"),
            }
        )

    with info_right:
        st.write("**AI Reason**")
        st.info(str(latest_reason))

    if final_action == "MANUAL_REVIEW":
        st.warning(
            "Manual approval is required before any paper order is submitted."
        )
    elif final_action == "PAPER_BUY":
        st.success(
            "The signal passed the configured paper-trading rules."
        )
    elif final_action == "NO_TRADE":
        st.error(
            "The signal did not pass the configured trade rules."
        )

    st.markdown("#### Recent Signals")

    display_columns = [
        "created_at",
        "symbol",
        "timeframe",
        "signal",
        "price",
        "ai_score",
        "ai_decision",
        "ai_risk",
        "ai_reason",
        "final_action",
        "quantity",
        "ibkr_status",
    ]

    available_columns = [
        column
        for column in display_columns
        if column in df_signals.columns
    ]

    st.dataframe(
        df_signals[available_columns],
        width="stretch",
        hide_index=True,
    )

    signal_count = len(df_signals)
    manual_reviews = int(
        (
            df_signals["final_action"]
            == "MANUAL_REVIEW"
        ).sum()
    )

    paper_buys = int(
        (
            df_signals["final_action"]
            == "PAPER_BUY"
        ).sum()
    )

    no_trades = int(
        (
            df_signals["final_action"]
            == "NO_TRADE"
        ).sum()
    )

    average_ai_score = float(
        pd.to_numeric(
            df_signals["ai_score"],
            errors="coerce",
        ).fillna(0).mean()
    )

    m1, m2, m3, m4, m5 = st.columns(5)

    m1.metric("Signals", signal_count)
    m2.metric("Manual Reviews", manual_reviews)
    m3.metric("Paper Buys", paper_buys)
    m4.metric("No Trades", no_trades)
    m5.metric(
        "Average AI Score",
        f"{average_ai_score:.1f}",
    )

else:
    st.info(
        "No AI signals are stored yet. "
        "Send a TradingView webhook or run the webhook test."
    )


st.divider()
show_approval_queue()
st.divider()

st.divider()
show_open_orders()

st.divider()
show_portfolio_summary(account_data)

st.divider()
show_live_positions(positions_data)



positions = positions_data.get("positions", [])

if positions:
    df_positions = pd.DataFrame(positions)

    df_positions["position"] = pd.to_numeric(
        df_positions["position"],
        errors="coerce",
    ).fillna(0)

    df_positions["avgCost"] = pd.to_numeric(
        df_positions["avgCost"],
        errors="coerce",
    ).fillna(0)

    df_positions["costBasis"] = (
        df_positions["position"]
        * df_positions["avgCost"]
    )

    total_positions = len(df_positions)
    total_shares = float(
        df_positions["position"].sum()
    )

    total_cost_basis = float(
        df_positions["costBasis"].sum()
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Open Positions",
        total_positions,
    )

    c2.metric(
        "Total Shares",
        f"{total_shares:,.0f}",
    )

    c3.metric(
        "Total Cost Basis",
        format_money(total_cost_basis),
    )

    portfolio_columns = [
        "account",
        "symbol",
        "secType",
        "currency",
        "exchange",
        "position",
        "avgCost",
        "costBasis",
    ]

    available_portfolio_columns = [
        column
        for column in portfolio_columns
        if column in df_positions.columns
    ]

    st.dataframe(
        df_positions[available_portfolio_columns],
        width="stretch",
        hide_index=True,
    )

else:
    positions_error = positions_data.get("error")

    if positions_error:
        st.warning(
            f"Position reader unavailable: {positions_error}"
        )
    else:
        st.info(
            "No open positions found in the IBKR paper account."
        )


st.divider()




status_col1, status_col2, status_col3 = st.columns(3)

ibkr_connected = bool(
    account_data.get("connected")
)

position_reader_connected = bool(
    positions_data.get("connected")
)

signal_database_connected = signals is not None

status_col1.metric(
    "IBKR",
    "Connected" if ibkr_connected else "Disconnected",
)

status_col2.metric(
    "Position Reader",
    (
        "Connected"
        if position_reader_connected
        else "Disconnected"
    ),
)

status_col3.metric(
    "Signal Database",
    (
        "Connected"
        if signal_database_connected
        else "Disconnected"
    ),
)

with st.expander("Technical status"):
    st.json(
        {
            "ibkr_connected": ibkr_connected,
            "accounts": account_data.get("accounts", []),
            "position_reader_connected": (
                position_reader_connected
            ),
            "signal_count_loaded": len(signals),
            "paper_trading": True,
            "manual_approval": True,
        }
    )


if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()