from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.order_manager import (
    OrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)
from app.strategy.portfolio_manager import AssetClass
from app.strategy.risk_gateway import (
    EnterpriseRiskGateway,
    RiskDecision,
    RiskEvaluationRequest,
    RiskPolicy,
    RiskRuleType,
    RiskSeverity,
)


NOW = datetime(
    2026,
    8,
    4,
    21,
    0,
    tzinfo=timezone.utc,
)

REQUESTED_AT = NOW + timedelta(seconds=1)
EVALUATED_AT = NOW + timedelta(seconds=2)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def policy(
    *,
    policy_id: str = "policy-001",
    max_order_quantity: str = "100",
    max_order_notional: str = "100000",
    max_position_quantity: str = "1000",
    max_position_notional: str = "1000000",
    max_gross_exposure: str = "5000000",
    max_net_exposure: str = "2500000",
    minimum_buying_power: str = "0",
    minimum_available_margin: str = "0",
    daily_loss_limit: str = "25000",
    allow_short_selling: bool = True,
    allow_trading_outside_session: bool = False,
    reduction_allowed: bool = True,
    enabled: bool = True,
) -> RiskPolicy:
    return RiskPolicy(
        policy_id=policy_id,
        name="Default Pre-Trade Risk Policy",
        max_order_quantity=Decimal(
            max_order_quantity
        ),
        max_order_notional=Decimal(
            max_order_notional
        ),
        max_position_quantity=Decimal(
            max_position_quantity
        ),
        max_position_notional=Decimal(
            max_position_notional
        ),
        max_gross_exposure=Decimal(
            max_gross_exposure
        ),
        max_net_exposure=Decimal(
            max_net_exposure
        ),
        minimum_buying_power=Decimal(
            minimum_buying_power
        ),
        minimum_available_margin=Decimal(
            minimum_available_margin
        ),
        daily_loss_limit=Decimal(
            daily_loss_limit
        ),
        allow_short_selling=allow_short_selling,
        allow_trading_outside_session=(
            allow_trading_outside_session
        ),
        reduction_allowed=reduction_allowed,
        enabled=enabled,
    )


def order_request(
    *,
    order_id: str = "order-001",
    client_order_id: str = "client-order-001",
    portfolio_id: str = "portfolio-001",
    symbol: str = "NVDA",
    side: OrderSide = OrderSide.BUY,
    quantity: str = "10",
) -> OrderRequest:
    return OrderRequest(
        order_id=order_id,
        client_order_id=client_order_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        asset_class=AssetClass.EQUITY,
        side=side,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal(quantity),
        created_at=NOW,
        strategy_id="momentum-001",
    )


def evaluation_request(
    *,
    evaluation_id: str = "evaluation-001",
    order: OrderRequest | None = None,
    market_price: str = "125",
    current_position_quantity: str = "20",
    current_position_notional: str = "2500",
    available_buying_power: str = "50000",
    available_margin: str = "25000",
    gross_exposure: str = "100000",
    net_exposure: str = "60000",
    daily_realized_pnl: str = "500",
    daily_unrealized_pnl: str = "-100",
    trading_session_allowed: bool = True,
    short_selling_allowed: bool = True,
    kill_switch_active: bool = False,
) -> RiskEvaluationRequest:
    effective_order = order or order_request()

    return RiskEvaluationRequest(
        evaluation_id=evaluation_id,
        request=effective_order,
        account_id="account-001",
        portfolio_id=effective_order.portfolio_id,
        requested_at=REQUESTED_AT,
        market_price=Decimal(market_price),
        current_position_quantity=Decimal(
            current_position_quantity
        ),
        current_position_notional=Decimal(
            current_position_notional
        ),
        available_buying_power=Decimal(
            available_buying_power
        ),
        available_margin=Decimal(
            available_margin
        ),
        gross_exposure=Decimal(
            gross_exposure
        ),
        net_exposure=Decimal(
            net_exposure
        ),
        daily_realized_pnl=Decimal(
            daily_realized_pnl
        ),
        daily_unrealized_pnl=Decimal(
            daily_unrealized_pnl
        ),
        trading_session_allowed=(
            trading_session_allowed
        ),
        short_selling_allowed=(
            short_selling_allowed
        ),
        kill_switch_active=kill_switch_active,
    )


def gateway(
    *,
    risk_policy: RiskPolicy | None = None,
    current_time: datetime = EVALUATED_AT,
) -> EnterpriseRiskGateway:
    return EnterpriseRiskGateway(
        policy=risk_policy or policy(),
        clock=FixedClock(current_time),
    )


def test_create_gateway() -> None:
    risk_policy = policy()

    value = gateway(
        risk_policy=risk_policy
    )

    assert value.policy == risk_policy
    assert value.kill_switch_active is False
    assert value.kill_switch_reason is None
    assert value.evaluation_ids == ()
    assert value.report_history == ()


def test_gateway_requires_policy() -> None:
    with pytest.raises(
        TypeError,
        match="policy must be a RiskPolicy",
    ):
        EnterpriseRiskGateway(
            policy=object()
        )


def test_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterpriseRiskGateway(
            policy=policy(),
            clock=EVALUATED_AT,
        )


def test_replace_policy() -> None:
    value = gateway()
    replacement = policy(
        policy_id="policy-002",
        max_order_quantity="50",
    )

    result = value.replace_policy(
        replacement
    )

    assert result == replacement
    assert value.policy == replacement


def test_replace_policy_requires_policy_model() -> None:
    value = gateway()

    with pytest.raises(
        TypeError,
        match="policy must be a RiskPolicy",
    ):
        value.replace_policy(object())


def test_activate_kill_switch() -> None:
    value = gateway()

    value.activate_kill_switch(
        reason="Emergency risk shutdown."
    )

    assert value.kill_switch_active is True
    assert value.kill_switch_reason == (
        "Emergency risk shutdown."
    )


def test_kill_switch_reason_is_normalized() -> None:
    value = gateway()

    value.activate_kill_switch(
        reason="  Emergency shutdown.  "
    )

    assert value.kill_switch_reason == (
        "Emergency shutdown."
    )


def test_kill_switch_reason_must_not_be_empty() -> None:
    value = gateway()

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        value.activate_kill_switch(
            reason="   "
        )


def test_duplicate_kill_switch_activation_is_rejected() -> None:
    value = gateway()

    value.activate_kill_switch(
        reason="Emergency shutdown."
    )

    with pytest.raises(
        RuntimeError,
        match="kill switch is already active",
    ):
        value.activate_kill_switch(
            reason="Second activation."
        )


def test_deactivate_kill_switch() -> None:
    value = gateway()

    value.activate_kill_switch(
        reason="Emergency shutdown."
    )
    value.deactivate_kill_switch()

    assert value.kill_switch_active is False
    assert value.kill_switch_reason is None


def test_deactivate_inactive_kill_switch_is_rejected() -> None:
    value = gateway()

    with pytest.raises(
        RuntimeError,
        match="kill switch is not active",
    ):
        value.deactivate_kill_switch()


def test_approve_order() -> None:
    value = gateway()

    report = value.evaluate(
        evaluation_request()
    )

    assert report.result.decision is (
        RiskDecision.APPROVE
    )
    assert report.result.approved_quantity == (
        Decimal("10")
    )
    assert report.result.approved_notional == (
        Decimal("1250")
    )
    assert report.result.violations == ()
    assert report.result.is_terminal is True


def test_approved_report_contains_policy_metadata() -> None:
    value = gateway()

    report = value.evaluate(
        evaluation_request()
    )

    assert report.metadata == (
        ("policy_id", "policy-001"),
    )


def test_evaluation_requires_request_model() -> None:
    value = gateway()

    with pytest.raises(
        TypeError,
        match=(
            "request must be a RiskEvaluationRequest"
        ),
    ):
        value.evaluate(object())


def test_evaluation_is_idempotent() -> None:
    value = gateway()
    request = evaluation_request()

    first = value.evaluate(request)
    second = value.evaluate(request)

    assert first == second
    assert len(value.report_history) == 1
    assert value.evaluation_ids == (
        "evaluation-001",
    )


def test_get_result() -> None:
    value = gateway()

    report = value.evaluate(
        evaluation_request()
    )

    result = value.get_result(
        "evaluation-001"
    )

    assert result == report.result


def test_get_result_normalizes_identifier() -> None:
    value = gateway()

    value.evaluate(
        evaluation_request()
    )

    result = value.get_result(
        "  evaluation-001  "
    )

    assert result.evaluation_id == (
        "evaluation-001"
    )


def test_get_unknown_result_is_rejected() -> None:
    value = gateway()

    with pytest.raises(
        KeyError,
        match="risk evaluation not found",
    ):
        value.get_result("missing")


def test_get_report() -> None:
    value = gateway()

    expected = value.evaluate(
        evaluation_request()
    )

    result = value.get_report(
        "evaluation-001"
    )

    assert result == expected


def test_get_unknown_report_is_rejected() -> None:
    value = gateway()

    with pytest.raises(
        KeyError,
        match="risk report not found",
    ):
        value.get_report("missing")


def test_reports_for_order() -> None:
    value = gateway()

    value.evaluate(
        evaluation_request(
            evaluation_id="evaluation-001",
        )
    )

    value.evaluate(
        evaluation_request(
            evaluation_id="evaluation-002",
        )
    )

    reports = value.reports_for_order(
        "order-001"
    )

    assert len(reports) == 2
    assert tuple(
        report.result.evaluation_id
        for report in reports
    ) == (
        "evaluation-001",
        "evaluation-002",
    )


def test_reports_for_unknown_order_returns_empty_tuple() -> None:
    value = gateway()

    assert value.reports_for_order(
        "missing-order"
    ) == ()


def test_violations_for_evaluation() -> None:
    value = gateway(
        risk_policy=policy(
            max_order_quantity="5"
        )
    )

    value.evaluate(
        evaluation_request()
    )

    violations = (
        value.violations_for_evaluation(
            "evaluation-001"
        )
    )

    assert len(violations) == 1
    assert violations[0].rule_type is (
        RiskRuleType.MAX_ORDER_QUANTITY
    )


def test_disabled_policy_holds_order() -> None:
    value = gateway(
        risk_policy=policy(enabled=False)
    )

    report = value.evaluate(
        evaluation_request()
    )

    assert report.result.decision is (
        RiskDecision.HOLD
    )
    assert report.result.approved_quantity == (
        Decimal("0")
    )
    assert report.result.approved_notional == (
        Decimal("0")
    )
    assert report.result.violations == ()
    assert report.result.warnings == (
        "The active risk policy is disabled.",
    )


def test_order_quantity_is_reduced() -> None:
    value = gateway(
        risk_policy=policy(
            max_order_quantity="8"
        )
    )

    report = value.evaluate(
        evaluation_request()
    )

    assert report.result.decision is (
        RiskDecision.REDUCE
    )
    assert report.result.approved_quantity == (
        Decimal("8.00000000")
    )
    assert report.result.approved_notional == (
        Decimal("1000.00000000")
    )
    assert (
        report.result.violations[0].rule_type
        is RiskRuleType.MAX_ORDER_QUANTITY
    )


def test_order_notional_is_reduced() -> None:
    value = gateway(
        risk_policy=policy(
            max_order_notional="1000"
        )
    )

    report = value.evaluate(
        evaluation_request()
    )

    assert report.result.decision is (
        RiskDecision.REDUCE
    )
    assert report.result.approved_quantity == (
        Decimal("8.00000000")
    )
    assert any(
        violation.rule_type
        is RiskRuleType.MAX_ORDER_NOTIONAL
        for violation in report.result.violations
    )


def test_buying_power_reduces_order() -> None:
    value = gateway()

    report = value.evaluate(
        evaluation_request(
            available_buying_power="500"
        )
    )

    assert report.result.decision is (
        RiskDecision.REDUCE
    )
    assert report.result.approved_quantity == (
        Decimal("4.00000000")
    )
    assert any(
        violation.rule_type
        is RiskRuleType.BUYING_POWER
        for violation in report.result.violations
    )


def test_position_quantity_reduces_order() -> None:
    value = gateway(
        risk_policy=policy(
            max_position_quantity="25"
        )
    )

    report = value.evaluate(
        evaluation_request(
            current_position_quantity="20"
        )
    )

    assert report.result.decision is (
        RiskDecision.REDUCE
    )
    assert report.result.approved_quantity == (
        Decimal("5.00000000")
    )
    assert any(
        violation.rule_type
        is RiskRuleType.MAX_POSITION_QUANTITY
        for violation in report.result.violations
    )


def test_position_notional_reduces_order() -> None:
    value = gateway(
        risk_policy=policy(
            max_position_notional="3000"
        )
    )

    report = value.evaluate(
        evaluation_request(
            current_position_notional="2500"
        )
    )

    assert report.result.decision is (
        RiskDecision.REDUCE
    )
    assert report.result.approved_quantity == (
        Decimal("4.00000000")
    )
    assert any(
        violation.rule_type
        is RiskRuleType.MAX_POSITION_NOTIONAL
        for violation in report.result.violations
    )


def test_gross_exposure_reduces_order() -> None:
    value = gateway(
        risk_policy=policy(
            max_gross_exposure="100500"
        )
    )

    report = value.evaluate(
        evaluation_request(
            gross_exposure="100000"
        )
    )

    assert report.result.decision is (
        RiskDecision.REDUCE
    )
    assert report.result.approved_quantity == (
        Decimal("4.00000000")
    )


def test_net_exposure_reduces_buy_order() -> None:
    value = gateway(
        risk_policy=policy(
            max_net_exposure="60500"
        )
    )

    report = value.evaluate(
        evaluation_request(
            net_exposure="60000"
        )
    )

    assert report.result.decision is (
        RiskDecision.REDUCE
    )
    assert report.result.approved_quantity == (
        Decimal("4.00000000")
    )


def test_reduction_disabled_rejects_limit_violation() -> None:
    value = gateway(
        risk_policy=policy(
            max_order_quantity="5",
            reduction_allowed=False,
        )
    )

    report = value.evaluate(
        evaluation_request()
    )

    assert report.result.decision is (
        RiskDecision.REJECT
    )
    assert report.result.approved_quantity == (
        Decimal("0")
    )
    assert (
        report.result.violations[0].severity
        is RiskSeverity.CRITICAL
    )


def test_closed_trading_session_rejects_order() -> None:
    value = gateway()

    report = value.evaluate(
        evaluation_request(
            trading_session_allowed=False
        )
    )

    assert report.result.decision is (
        RiskDecision.REJECT
    )
    assert any(
        violation.rule_type
        is RiskRuleType.TRADING_SESSION
        for violation in report.result.violations
    )


def test_policy_can_allow_outside_session_trading() -> None:
    value = gateway(
        risk_policy=policy(
            allow_trading_outside_session=True
        )
    )

    report = value.evaluate(
        evaluation_request(
            trading_session_allowed=False
        )
    )

    assert report.result.decision is (
        RiskDecision.APPROVE
    )


def test_short_selling_policy_rejects_short_order() -> None:
    value = gateway(
        risk_policy=policy(
            allow_short_selling=False
        )
    )

    short_order = order_request(
        side=OrderSide.SELL_SHORT
    )

    report = value.evaluate(
        evaluation_request(
            order=short_order
        )
    )

    assert report.result.decision is (
        RiskDecision.REJECT
    )
    assert any(
        violation.rule_type
        is RiskRuleType.SHORT_SELLING
        for violation in report.result.violations
    )


def test_request_short_selling_restriction_rejects() -> None:
    value = gateway()

    short_order = order_request(
        side=OrderSide.SELL_SHORT
    )

    report = value.evaluate(
        evaluation_request(
            order=short_order,
            short_selling_allowed=False,
        )
    )

    assert report.result.decision is (
        RiskDecision.REJECT
    )


def test_gateway_kill_switch_rejects_order() -> None:
    value = gateway()

    value.activate_kill_switch(
        reason="Emergency shutdown."
    )

    report = value.evaluate(
        evaluation_request()
    )

    assert report.result.decision is (
        RiskDecision.REJECT
    )
    assert report.result.has_critical_violation is True
    assert any(
        violation.rule_type
        is RiskRuleType.KILL_SWITCH
        for violation in report.result.violations
    )


def test_request_kill_switch_rejects_order() -> None:
    value = gateway()

    report = value.evaluate(
        evaluation_request(
            kill_switch_active=True
        )
    )

    assert report.result.decision is (
        RiskDecision.REJECT
    )


def test_daily_loss_limit_rejects_order() -> None:
    value = gateway(
        risk_policy=policy(
            daily_loss_limit="1000"
        )
    )

    report = value.evaluate(
        evaluation_request(
            daily_realized_pnl="-800",
            daily_unrealized_pnl="-500",
        )
    )

    assert report.result.decision is (
        RiskDecision.REJECT
    )
    assert any(
        violation.rule_type
        is RiskRuleType.DAILY_LOSS
        for violation in report.result.violations
    )


def test_minimum_buying_power_rejects_order() -> None:
    value = gateway(
        risk_policy=policy(
            minimum_buying_power="10000"
        )
    )

    report = value.evaluate(
        evaluation_request(
            available_buying_power="5000"
        )
    )

    assert report.result.decision is (
        RiskDecision.REJECT
    )


def test_minimum_margin_rejects_order() -> None:
    value = gateway(
        risk_policy=policy(
            minimum_available_margin="10000"
        )
    )

    report = value.evaluate(
        evaluation_request(
            available_margin="5000"
        )
    )

    assert report.result.decision is (
        RiskDecision.REJECT
    )
    assert any(
        violation.rule_type
        is RiskRuleType.MARGIN
        for violation in report.result.violations
    )


def test_critical_violation_overrides_reduction() -> None:
    value = gateway(
        risk_policy=policy(
            max_order_quantity="8"
        )
    )

    report = value.evaluate(
        evaluation_request(
            trading_session_allowed=False
        )
    )

    assert report.result.decision is (
        RiskDecision.REJECT
    )
    assert report.result.approved_quantity == (
        Decimal("0")
    )
    assert any(
        violation.severity
        is RiskSeverity.WARNING
        for violation in report.result.violations
    )
    assert any(
        violation.severity
        is RiskSeverity.CRITICAL
        for violation in report.result.violations
    )


def test_violation_ids_are_deterministic() -> None:
    value = gateway(
        risk_policy=policy(
            max_order_quantity="5"
        )
    )

    first = value.evaluate(
        evaluation_request(
            evaluation_id="evaluation-001"
        )
    )

    second = value.evaluate(
        evaluation_request(
            evaluation_id="evaluation-002"
        )
    )

    assert (
        first.result.violations[0].violation_id
        == "violation-000001"
    )
    assert (
        second.result.violations[0].violation_id
        == "violation-000002"
    )


def test_report_ids_are_deterministic() -> None:
    value = gateway()

    first = value.evaluate(
        evaluation_request(
            evaluation_id="evaluation-001"
        )
    )

    second = value.evaluate(
        evaluation_request(
            evaluation_id="evaluation-002"
        )
    )

    assert first.report_id == (
        "risk-report-000001"
    )
    assert second.report_id == (
        "risk-report-000002"
    )


def test_global_report_history_is_ordered() -> None:
    value = gateway()

    value.evaluate(
        evaluation_request(
            evaluation_id="evaluation-001"
        )
    )

    value.evaluate(
        evaluation_request(
            evaluation_id="evaluation-002"
        )
    )

    assert tuple(
        report.result.evaluation_id
        for report in value.report_history
    ) == (
        "evaluation-001",
        "evaluation-002",
    )


def test_evaluation_time_must_follow_request() -> None:
    value = gateway(
        current_time=NOW
    )

    with pytest.raises(
        ValueError,
        match=(
            "evaluation time must not be earlier "
            "than request requested_at"
        ),
    ):
        value.evaluate(
            evaluation_request()
        )


def test_clock_must_return_datetime() -> None:
    value = EnterpriseRiskGateway(
        policy=policy(),
        clock=lambda: "now",
    )

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        value.evaluate(
            evaluation_request()
        )


def test_clock_must_return_timezone_aware_datetime() -> None:
    value = EnterpriseRiskGateway(
        policy=policy(),
        clock=lambda: datetime(
            2026,
            8,
            4,
            21,
            0,
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        value.evaluate(
            evaluation_request()
        )


def test_evaluation_identifier_must_not_be_empty() -> None:
    value = gateway()

    with pytest.raises(
        ValueError,
        match="evaluation_id must not be empty",
    ):
        value.get_result("   ")


def test_order_identifier_must_not_be_empty() -> None:
    value = gateway()

    with pytest.raises(
        ValueError,
        match="order_id must not be empty",
    ):
        value.reports_for_order("   ")