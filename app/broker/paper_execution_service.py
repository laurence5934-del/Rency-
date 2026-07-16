"""
Paper Execution Service
AI Trading Platform Version 7.5

Combines portfolio risk evaluation, execution safety checks,
and paper-order construction.

This module prepares a non-transmitting IBKR paper-order package.
It does not submit an order.
"""

from __future__ import annotations

from typing import Any

from app.broker.paper_execution_guard import (
    validate_paper_execution,
)
from app.broker.paper_order_builder import (
    build_paper_order,
)
from app.models.portfolio_risk_models import (
    PortfolioRiskLimits,
    PortfolioSnapshot,
)
from app.risk.portfolio_risk_manager import (
    evaluate_portfolio_risk,
)


def prepare_paper_execution(
    *,
    candidate: dict[str, Any],
    ibkr_connected: bool,
    paper_account_confirmed: bool,
    portfolio: PortfolioSnapshot | None = None,
    risk_limits: PortfolioRiskLimits | None = None,
    paper_trading_only: bool = True,
    emergency_lock_active: bool = False,
    order_type: str = "MKT",
    limit_price: float | None = None,
    maximum_position_value: float = 25_000.00,
) -> dict[str, Any]:
    """
    Prepare a validated, non-transmitting paper-order package.

    Processing order:

    1. Require a portfolio snapshot.
    2. Evaluate portfolio-level risk.
    3. Run paper-execution safety checks.
    4. Build the non-transmitting IBKR order package.
    """

    if portfolio is None:
        return {
            "ready": False,
            "portfolio_risk": {
                "approved": False,
                "decision": "REJECTED",
                "codes": ["PORTFOLIO_SNAPSHOT_REQUIRED"],
                "errors": [
                    "A current portfolio snapshot is required "
                    "before preparing a paper order."
                ],
                "warnings": [],
            },
            "guard": None,
            "order": None,
            "message": (
                "Paper execution preparation was blocked "
                "because portfolio data is unavailable."
            ),
        }

    portfolio_risk_result = evaluate_portfolio_risk(
        candidate=candidate,
        portfolio=portfolio,
        limits=risk_limits,
        paper_trading_only=paper_trading_only,
        emergency_lock_active=emergency_lock_active,
    )

    portfolio_risk = portfolio_risk_result.to_dict()

    if not portfolio_risk_result.approved:
        return {
            "ready": False,
            "portfolio_risk": portfolio_risk,
            "guard": None,
            "order": None,
            "message": (
                "Paper execution preparation was blocked "
                "by the Portfolio Risk Manager."
            ),
        }

    configured_maximum_position_value = (
        risk_limits.maximum_position_value
        if risk_limits is not None
        else maximum_position_value
    )

    guard_result = validate_paper_execution(
        candidate=candidate,
        ibkr_connected=ibkr_connected,
        paper_account_confirmed=paper_account_confirmed,
        maximum_position_value=(
            configured_maximum_position_value
        ),
    )

    if not guard_result["approved"]:
        return {
            "ready": False,
            "portfolio_risk": portfolio_risk,
            "guard": guard_result,
            "order": None,
            "message": (
                "Portfolio risk checks passed, but paper "
                "execution was blocked by a safety check."
            ),
        }

    order_request = build_paper_order(
        candidate=candidate,
        order_type=order_type,
        limit_price=limit_price,
    )

    return {
        "ready": True,
        "portfolio_risk": portfolio_risk,
        "guard": guard_result,
        "order": order_request,
        "message": (
            "Portfolio risk and paper-execution checks passed. "
            "The non-transmitting paper-order package is ready "
            "for explicit IBKR submission."
        ),
    }