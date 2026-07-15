"""
Portfolio Risk Manager
AI Trading Platform Version 7.5

Performs portfolio-level checks before an approved candidate
can move to the paper-execution guard and order builder.

This module does not transmit orders.
"""

from __future__ import annotations

from typing import Any

from app.models.portfolio_risk_models import (
    PortfolioRiskLimits,
    PortfolioRiskResult,
    PortfolioSnapshot,
    RiskCode,
    RiskDecision,
)


def evaluate_portfolio_risk(
    *,
    candidate: dict[str, Any],
    portfolio: PortfolioSnapshot,
    limits: PortfolioRiskLimits | None = None,
    paper_trading_only: bool = True,
    emergency_lock_active: bool = False,
) -> PortfolioRiskResult:
    configured_limits = limits or PortfolioRiskLimits()

    errors: list[str] = []
    warnings: list[str] = []
    codes: list[RiskCode] = []

    symbol = str(
        candidate.get("symbol", "")
    ).strip().upper()

    action = str(
        candidate.get("action", "")
    ).strip().upper()

    quantity = int(
        candidate.get("quantity", 0) or 0
    )

    entry_price = float(
        candidate.get("entry_price", 0) or 0
    )

    order_value = max(
        quantity * entry_price,
        0.0,
    )

    existing_symbol_value = float(
        portfolio.symbol_position_values.get(
            symbol,
            0.0,
        )
    )

    if action == "BUY":
        projected_symbol_value = (
            existing_symbol_value + order_value
        )
        projected_portfolio_value = (
            float(portfolio.total_position_value)
            + order_value
        )
    elif action == "SELL":
        projected_symbol_value = max(
            existing_symbol_value - order_value,
            0.0,
        )
        projected_portfolio_value = max(
            float(portfolio.total_position_value)
            - order_value,
            0.0,
        )
    else:
        projected_symbol_value = existing_symbol_value
        projected_portfolio_value = float(
            portfolio.total_position_value
        )

    if portfolio.net_liquidation > 0:
        projected_exposure_percent = (
            projected_portfolio_value
            / portfolio.net_liquidation
            * 100.0
        )
    else:
        projected_exposure_percent = 0.0

    if not paper_trading_only:
        errors.append(
            "Portfolio risk approval requires "
            "paper-trading-only mode."
        )
        codes.append(
            RiskCode.PAPER_TRADING_REQUIRED
        )

    if emergency_lock_active:
        errors.append(
            "The emergency trading lock is active."
        )
        codes.append(
            RiskCode.EMERGENCY_LOCK_ACTIVE
        )

    if not symbol:
        errors.append(
            "Candidate symbol is missing."
        )
        codes.append(
            RiskCode.INVALID_SYMBOL
        )

    if action not in {"BUY", "SELL"}:
        errors.append(
            "Candidate action must be BUY or SELL."
        )
        codes.append(
            RiskCode.INVALID_ACTION
        )

    if quantity <= 0:
        errors.append(
            "Candidate quantity must be greater than zero."
        )
        codes.append(
            RiskCode.INVALID_QUANTITY
        )

    if entry_price <= 0:
        errors.append(
            "Candidate entry price must be greater than zero."
        )
        codes.append(
            RiskCode.INVALID_ENTRY_PRICE
        )

    if portfolio.net_liquidation <= 0:
        errors.append(
            "Net liquidation value must be greater than zero."
        )
        codes.append(
            RiskCode.INVALID_ACCOUNT_VALUE
        )

    if (
        order_value
        > configured_limits.maximum_order_value
    ):
        errors.append(
            "Planned order value exceeds the configured "
            f"maximum of "
            f"${configured_limits.maximum_order_value:,.2f}."
        )
        codes.append(
            RiskCode.ORDER_VALUE_EXCEEDED
        )

    if (
        projected_symbol_value
        > configured_limits.maximum_position_value
    ):
        errors.append(
            "Projected symbol position exceeds the "
            f"configured maximum of "
            f"${configured_limits.maximum_position_value:,.2f}."
        )
        codes.append(
            RiskCode.POSITION_VALUE_EXCEEDED
        )

    if (
        projected_exposure_percent
        > configured_limits
        .maximum_portfolio_exposure_percent
    ):
        errors.append(
            "Projected portfolio exposure exceeds the "
            f"configured maximum of "
            f"{configured_limits.maximum_portfolio_exposure_percent:.2f}%."
        )
        codes.append(
            RiskCode.PORTFOLIO_EXPOSURE_EXCEEDED
        )

    adding_new_position = (
        action == "BUY"
        and existing_symbol_value <= 0
    )

    if (
        adding_new_position
        and portfolio.open_position_count
        >= configured_limits.maximum_open_positions
    ):
        errors.append(
            "Maximum number of open positions has "
            "already been reached."
        )
        codes.append(
            RiskCode.OPEN_POSITION_LIMIT_REACHED
        )

    if (
        action == "BUY"
        and portfolio.buying_power - order_value
        < configured_limits.minimum_buying_power
    ):
        errors.append(
            "The order would reduce buying power below "
            f"${configured_limits.minimum_buying_power:,.2f}."
        )
        codes.append(
            RiskCode.BUYING_POWER_INSUFFICIENT
        )

    if (
        portfolio.daily_total_pnl
        <= -abs(
            configured_limits.maximum_daily_loss
        )
    ):
        errors.append(
            "The configured daily loss limit has "
            "been reached."
        )
        codes.append(
            RiskCode.DAILY_LOSS_LIMIT_REACHED
        )

    if (
        portfolio.drawdown_percent
        >= configured_limits.maximum_drawdown_percent
    ):
        errors.append(
            "The configured maximum drawdown limit "
            "has been reached."
        )
        codes.append(
            RiskCode.MAXIMUM_DRAWDOWN_REACHED
        )

    if (
        action == "BUY"
        and existing_symbol_value > 0
        and not configured_limits
        .allow_existing_symbol_additions
    ):
        errors.append(
            f"An existing position already exists for "
            f"{symbol}. Additional exposure is disabled."
        )
        codes.append(
            RiskCode.EXISTING_SYMBOL_EXPOSURE
        )

    if (
        configured_limits.maximum_order_value > 0
        and order_value
        >= configured_limits.maximum_order_value * 0.8
    ):
        warnings.append(
            "Planned order value is at least 80% of "
            "the configured maximum order value."
        )

    if (
        configured_limits.maximum_position_value > 0
        and projected_symbol_value
        >= configured_limits.maximum_position_value * 0.8
    ):
        warnings.append(
            "Projected symbol exposure is at least 80% "
            "of the configured maximum position value."
        )

    if (
        configured_limits
        .maximum_portfolio_exposure_percent > 0
        and projected_exposure_percent
        >= configured_limits
        .maximum_portfolio_exposure_percent
        * 0.8
    ):
        warnings.append(
            "Projected portfolio exposure is at least "
            "80% of the configured maximum."
        )

    approved = not errors

    if approved:
        decision = RiskDecision.APPROVED
        codes.append(
            RiskCode.APPROVED
        )
    else:
        decision = RiskDecision.REJECTED

    return PortfolioRiskResult(
        approved=approved,
        decision=decision,
        symbol=symbol,
        action=action,
        quantity=quantity,
        entry_price=entry_price,
        order_value=order_value,
        projected_symbol_value=projected_symbol_value,
        projected_portfolio_value=projected_portfolio_value,
        projected_exposure_percent=(
            projected_exposure_percent
        ),
        errors=tuple(errors),
        warnings=tuple(warnings),
        codes=tuple(codes),
    )