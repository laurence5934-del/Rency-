from dataclasses import FrozenInstanceError
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
    RiskDecision,
    RiskEvaluationRequest,
    RiskEvaluationResult,
    RiskEvaluationStatus,
    RiskGatewayReport,
    RiskRuleType,
    RiskSeverity,
    RiskViolation,
)


NOW = datetime(
    2026,
    8,
    4,
    20,
    0,
    tzinfo=timezone.utc,
)


def order_request(
    *,
    order_id: str = "order-001",
    portfolio_id: str = "portfolio-001",
    side: OrderSide = OrderSide.BUY,
    quantity: str = "10",
) -> OrderRequest:
    return OrderRequest(
        order_id=order_id,
        client_order_id=f"client-{order_id}",
        portfolio_id=portfolio_id,
        symbol="NVDA",
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
    request: OrderRequest | None = None,
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
    effective_request = request or order_request()

    return RiskEvaluationRequest(
        evaluation_id=evaluation_id,
        request=effective_request,
        account_id="account-001",
        portfolio_id=effective_request.portfolio_id,
        requested_at=NOW + timedelta(seconds=1),
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
        gross_exposure=Decimal(gross_exposure),
        net_exposure=Decimal(net_exposure),
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
        metadata=(
            ("source", "order-manager"),
        ),
    )


def warning_violation(
    *,
    violation_id: str = "violation-001",
    evaluation_id: str = "evaluation-001",
    rule_type: RiskRuleType = (
        RiskRuleType.MAX_ORDER_NOTIONAL
    ),
    observed_value: str = "1250",
    limit_value: str = "1000",
    occurred_at: datetime = NOW + timedelta(
        seconds=2
    ),
) -> RiskViolation:
    return RiskViolation(
        violation_id=violation_id,
        evaluation_id=evaluation_id,
        rule_type=rule_type,
        severity=RiskSeverity.WARNING,
        message="Risk limit exceeded.",
        observed_value=Decimal(observed_value),
        limit_value=Decimal(limit_value),
        occurred_at=occurred_at,
        symbol="NVDA",
        rule_id="rule-001",
    )


def critical_violation(
    *,
    violation_id: str = "violation-002",
    evaluation_id: str = "evaluation-001",
) -> RiskViolation:
    return RiskViolation(
        violation_id=violation_id,
        evaluation_id=evaluation_id,
        rule_type=RiskRuleType.KILL_SWITCH,
        severity=RiskSeverity.CRITICAL,
        message="Emergency kill switch is active.",
        observed_value=Decimal("1"),
        limit_value=Decimal("0"),
        occurred_at=NOW + timedelta(seconds=2),
        symbol="NVDA",
        rule_id="kill-switch-rule",
    )


def approved_result() -> RiskEvaluationResult:
    return RiskEvaluationResult(
        evaluation_id="evaluation-001",
        status=RiskEvaluationStatus.COMPLETED,
        decision=RiskDecision.APPROVE,
        evaluated_at=NOW + timedelta(seconds=3),
        order_id="order-001",
        portfolio_id="portfolio-001",
        requested_quantity=Decimal("10"),
        approved_quantity=Decimal("10"),
        requested_notional=Decimal("1250"),
        approved_notional=Decimal("1250"),
        recommendation="Order may proceed.",
    )


def reduced_result() -> RiskEvaluationResult:
    return RiskEvaluationResult(
        evaluation_id="evaluation-001",
        status=RiskEvaluationStatus.COMPLETED,
        decision=RiskDecision.REDUCE,
        evaluated_at=NOW + timedelta(seconds=3),
        order_id="order-001",
        portfolio_id="portfolio-001",
        requested_quantity=Decimal("10"),
        approved_quantity=Decimal("8"),
        requested_notional=Decimal("1250"),
        approved_notional=Decimal("1000"),
        violations=(warning_violation(),),
        recommendation="Reduce the order quantity.",
    )


def rejected_result() -> RiskEvaluationResult:
    return RiskEvaluationResult(
        evaluation_id="evaluation-001",
        status=RiskEvaluationStatus.COMPLETED,
        decision=RiskDecision.REJECT,
        evaluated_at=NOW + timedelta(seconds=3),
        order_id="order-001",
        portfolio_id="portfolio-001",
        requested_quantity=Decimal("10"),
        approved_quantity=Decimal("0"),
        requested_notional=Decimal("1250"),
        approved_notional=Decimal("0"),
        violations=(critical_violation(),),
        recommendation="Do not submit the order.",
    )


def test_risk_violation() -> None:
    value = warning_violation()

    assert value.rule_type is (
        RiskRuleType.MAX_ORDER_NOTIONAL
    )
    assert value.severity is RiskSeverity.WARNING
    assert value.symbol == "NVDA"
    assert value.excess_value == Decimal("250")


def test_violation_text_is_normalized() -> None:
    value = RiskViolation(
        violation_id="  violation-001  ",
        evaluation_id="  evaluation-001  ",
        rule_type=RiskRuleType.MAX_ORDER_NOTIONAL,
        severity=RiskSeverity.WARNING,
        message="  Risk limit exceeded.  ",
        observed_value=Decimal("1250"),
        limit_value=Decimal("1000"),
        occurred_at=NOW,
        symbol="  nvda  ",
        rule_id="  rule-001  ",
        metadata=[
            ("  source  ", "  engine  "),
        ],
    )

    assert value.violation_id == "violation-001"
    assert value.evaluation_id == "evaluation-001"
    assert value.message == "Risk limit exceeded."
    assert value.symbol == "NVDA"
    assert value.rule_id == "rule-001"
    assert value.metadata == (
        ("source", "engine"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "violation_id",
        "evaluation_id",
        "message",
    ],
)
def test_violation_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "violation_id": "violation-001",
        "evaluation_id": "evaluation-001",
        "rule_type": RiskRuleType.MAX_ORDER_NOTIONAL,
        "severity": RiskSeverity.WARNING,
        "message": "Risk limit exceeded.",
        "observed_value": Decimal("1250"),
        "limit_value": Decimal("1000"),
        "occurred_at": NOW,
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        RiskViolation(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "observed_value",
        "limit_value",
    ],
)
def test_violation_values_require_decimal(
    field_name: str,
) -> None:
    arguments = {
        "violation_id": "violation-001",
        "evaluation_id": "evaluation-001",
        "rule_type": RiskRuleType.MAX_ORDER_NOTIONAL,
        "severity": RiskSeverity.WARNING,
        "message": "Risk limit exceeded.",
        "observed_value": Decimal("1250"),
        "limit_value": Decimal("1000"),
        "occurred_at": NOW,
    }
    arguments[field_name] = 1000

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a Decimal",
    ):
        RiskViolation(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "observed_value",
        "limit_value",
    ],
)
def test_violation_values_must_not_be_negative(
    field_name: str,
) -> None:
    arguments = {
        "violation_id": "violation-001",
        "evaluation_id": "evaluation-001",
        "rule_type": RiskRuleType.MAX_ORDER_NOTIONAL,
        "severity": RiskSeverity.WARNING,
        "message": "Risk limit exceeded.",
        "observed_value": Decimal("1250"),
        "limit_value": Decimal("1000"),
        "occurred_at": NOW,
    }
    arguments[field_name] = Decimal("-1")

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be negative",
    ):
        RiskViolation(**arguments)


def test_violation_excess_never_goes_negative() -> None:
    value = warning_violation(
        observed_value="500",
        limit_value="1000",
    )

    assert value.excess_value == Decimal("0")


def test_violation_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="occurred_at must be timezone-aware",
    ):
        RiskViolation(
            violation_id="violation-001",
            evaluation_id="evaluation-001",
            rule_type=RiskRuleType.MAX_ORDER_NOTIONAL,
            severity=RiskSeverity.WARNING,
            message="Risk limit exceeded.",
            observed_value=Decimal("1250"),
            limit_value=Decimal("1000"),
            occurred_at=datetime(2026, 8, 4, 20, 0),
        )


def test_risk_evaluation_request() -> None:
    value = evaluation_request()

    assert value.evaluation_id == "evaluation-001"
    assert value.request.order_id == "order-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.order_notional == Decimal("1250")
    assert (
        value.projected_position_quantity
        == Decimal("30")
    )
    assert value.projected_daily_pnl == Decimal("400")


def test_request_text_is_normalized() -> None:
    request = order_request()

    value = RiskEvaluationRequest(
        evaluation_id="  evaluation-001  ",
        request=request,
        account_id="  account-001  ",
        portfolio_id="  portfolio-001  ",
        requested_at=NOW + timedelta(seconds=1),
        market_price=Decimal("125"),
        current_position_quantity=Decimal("20"),
        current_position_notional=Decimal("2500"),
        available_buying_power=Decimal("50000"),
        available_margin=Decimal("25000"),
        gross_exposure=Decimal("100000"),
        net_exposure=Decimal("60000"),
        daily_realized_pnl=Decimal("500"),
        daily_unrealized_pnl=Decimal("-100"),
        trading_session_allowed=True,
        short_selling_allowed=True,
        metadata=[
            ("  source  ", "  oms  "),
        ],
    )

    assert value.evaluation_id == "evaluation-001"
    assert value.account_id == "account-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.metadata == (
        ("source", "oms"),
    )


def test_request_requires_order_request_model() -> None:
    with pytest.raises(
        TypeError,
        match="request must be an OrderRequest",
    ):
        RiskEvaluationRequest(
            evaluation_id="evaluation-001",
            request=object(),
            account_id="account-001",
            portfolio_id="portfolio-001",
            requested_at=NOW,
            market_price=Decimal("125"),
            current_position_quantity=Decimal("0"),
            current_position_notional=Decimal("0"),
            available_buying_power=Decimal("50000"),
            available_margin=Decimal("25000"),
            gross_exposure=Decimal("0"),
            net_exposure=Decimal("0"),
            daily_realized_pnl=Decimal("0"),
            daily_unrealized_pnl=Decimal("0"),
            trading_session_allowed=True,
            short_selling_allowed=True,
        )


def test_request_portfolio_id_must_match_order() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "portfolio_id must match request portfolio_id"
        ),
    ):
        RiskEvaluationRequest(
            evaluation_id="evaluation-001",
            request=order_request(),
            account_id="account-001",
            portfolio_id="different-portfolio",
            requested_at=NOW + timedelta(seconds=1),
            market_price=Decimal("125"),
            current_position_quantity=Decimal("0"),
            current_position_notional=Decimal("0"),
            available_buying_power=Decimal("50000"),
            available_margin=Decimal("25000"),
            gross_exposure=Decimal("0"),
            net_exposure=Decimal("0"),
            daily_realized_pnl=Decimal("0"),
            daily_unrealized_pnl=Decimal("0"),
            trading_session_allowed=True,
            short_selling_allowed=True,
        )


def test_requested_at_must_follow_order_creation() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "requested_at must not be earlier than "
            "request created_at"
        ),
    ):
        evaluation_request(
            request=order_request()
        ).__class__(
            evaluation_id="evaluation-001",
            request=order_request(),
            account_id="account-001",
            portfolio_id="portfolio-001",
            requested_at=NOW - timedelta(seconds=1),
            market_price=Decimal("125"),
            current_position_quantity=Decimal("0"),
            current_position_notional=Decimal("0"),
            available_buying_power=Decimal("50000"),
            available_margin=Decimal("25000"),
            gross_exposure=Decimal("0"),
            net_exposure=Decimal("0"),
            daily_realized_pnl=Decimal("0"),
            daily_unrealized_pnl=Decimal("0"),
            trading_session_allowed=True,
            short_selling_allowed=True,
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "market_price",
        "current_position_quantity",
        "current_position_notional",
        "available_buying_power",
        "available_margin",
        "gross_exposure",
        "net_exposure",
        "daily_realized_pnl",
        "daily_unrealized_pnl",
    ],
)
def test_request_financial_fields_require_decimal(
    field_name: str,
) -> None:
    arguments = {
        "evaluation_id": "evaluation-001",
        "request": order_request(),
        "account_id": "account-001",
        "portfolio_id": "portfolio-001",
        "requested_at": NOW + timedelta(seconds=1),
        "market_price": Decimal("125"),
        "current_position_quantity": Decimal("20"),
        "current_position_notional": Decimal("2500"),
        "available_buying_power": Decimal("50000"),
        "available_margin": Decimal("25000"),
        "gross_exposure": Decimal("100000"),
        "net_exposure": Decimal("60000"),
        "daily_realized_pnl": Decimal("500"),
        "daily_unrealized_pnl": Decimal("-100"),
        "trading_session_allowed": True,
        "short_selling_allowed": True,
    }
    arguments[field_name] = 100

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a Decimal",
    ):
        RiskEvaluationRequest(**arguments)


def test_market_price_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="market_price must be greater than zero",
    ):
        evaluation_request(market_price="0")


@pytest.mark.parametrize(
    "field_name",
    [
        "current_position_quantity",
        "current_position_notional",
        "available_buying_power",
        "available_margin",
        "gross_exposure",
    ],
)
def test_nonnegative_request_fields(
    field_name: str,
) -> None:
    arguments = {
        "evaluation_id": "evaluation-001",
        "request": order_request(),
        "account_id": "account-001",
        "portfolio_id": "portfolio-001",
        "requested_at": NOW + timedelta(seconds=1),
        "market_price": Decimal("125"),
        "current_position_quantity": Decimal("20"),
        "current_position_notional": Decimal("2500"),
        "available_buying_power": Decimal("50000"),
        "available_margin": Decimal("25000"),
        "gross_exposure": Decimal("100000"),
        "net_exposure": Decimal("60000"),
        "daily_realized_pnl": Decimal("500"),
        "daily_unrealized_pnl": Decimal("-100"),
        "trading_session_allowed": True,
        "short_selling_allowed": True,
    }
    arguments[field_name] = Decimal("-1")

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be negative",
    ):
        RiskEvaluationRequest(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "trading_session_allowed",
        "short_selling_allowed",
        "kill_switch_active",
    ],
)
def test_request_flags_require_bool(
    field_name: str,
) -> None:
    arguments = {
        "evaluation_id": "evaluation-001",
        "request": order_request(),
        "account_id": "account-001",
        "portfolio_id": "portfolio-001",
        "requested_at": NOW + timedelta(seconds=1),
        "market_price": Decimal("125"),
        "current_position_quantity": Decimal("20"),
        "current_position_notional": Decimal("2500"),
        "available_buying_power": Decimal("50000"),
        "available_margin": Decimal("25000"),
        "gross_exposure": Decimal("100000"),
        "net_exposure": Decimal("60000"),
        "daily_realized_pnl": Decimal("500"),
        "daily_unrealized_pnl": Decimal("-100"),
        "trading_session_allowed": True,
        "short_selling_allowed": True,
        "kill_switch_active": False,
    }
    arguments[field_name] = "yes"

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a bool",
    ):
        RiskEvaluationRequest(**arguments)


def test_sell_reduces_projected_position_quantity() -> None:
    request = order_request(
        side=OrderSide.SELL,
        quantity="5",
    )

    value = evaluation_request(
        request=request,
        current_position_quantity="20",
    )

    assert (
        value.projected_position_quantity
        == Decimal("15")
    )


def test_sell_cannot_project_negative_position() -> None:
    request = order_request(
        side=OrderSide.SELL,
        quantity="25",
    )

    value = evaluation_request(
        request=request,
        current_position_quantity="20",
    )

    assert (
        value.projected_position_quantity
        == Decimal("0")
    )


def test_approved_result() -> None:
    value = approved_result()

    assert value.status is (
        RiskEvaluationStatus.COMPLETED
    )
    assert value.decision is RiskDecision.APPROVE
    assert value.violations == ()
    assert value.is_terminal is True
    assert value.has_critical_violation is False


def test_reduced_result() -> None:
    value = reduced_result()

    assert value.decision is RiskDecision.REDUCE
    assert value.approved_quantity == Decimal("8")
    assert len(value.violations) == 1
    assert value.has_critical_violation is False


def test_rejected_result() -> None:
    value = rejected_result()

    assert value.decision is RiskDecision.REJECT
    assert value.approved_quantity == Decimal("0")
    assert value.has_critical_violation is True


@pytest.mark.parametrize(
    "field_name",
    [
        "requested_quantity",
        "approved_quantity",
        "requested_notional",
        "approved_notional",
    ],
)
def test_result_financial_fields_require_decimal(
    field_name: str,
) -> None:
    arguments = {
        "evaluation_id": "evaluation-001",
        "status": RiskEvaluationStatus.COMPLETED,
        "decision": RiskDecision.APPROVE,
        "evaluated_at": NOW,
        "order_id": "order-001",
        "portfolio_id": "portfolio-001",
        "requested_quantity": Decimal("10"),
        "approved_quantity": Decimal("10"),
        "requested_notional": Decimal("1250"),
        "approved_notional": Decimal("1250"),
    }
    arguments[field_name] = 10

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a Decimal",
    ):
        RiskEvaluationResult(**arguments)


def test_approved_quantity_cannot_exceed_requested() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "approved_quantity must not exceed "
            "requested_quantity"
        ),
    ):
        RiskEvaluationResult(
            evaluation_id="evaluation-001",
            status=RiskEvaluationStatus.COMPLETED,
            decision=RiskDecision.REDUCE,
            evaluated_at=NOW,
            order_id="order-001",
            portfolio_id="portfolio-001",
            requested_quantity=Decimal("10"),
            approved_quantity=Decimal("11"),
            requested_notional=Decimal("1250"),
            approved_notional=Decimal("1000"),
            violations=(warning_violation(),),
        )


def test_approved_notional_cannot_exceed_requested() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "approved_notional must not exceed "
            "requested_notional"
        ),
    ):
        RiskEvaluationResult(
            evaluation_id="evaluation-001",
            status=RiskEvaluationStatus.COMPLETED,
            decision=RiskDecision.REDUCE,
            evaluated_at=NOW,
            order_id="order-001",
            portfolio_id="portfolio-001",
            requested_quantity=Decimal("10"),
            approved_quantity=Decimal("8"),
            requested_notional=Decimal("1250"),
            approved_notional=Decimal("1300"),
            violations=(warning_violation(),),
        )


def test_violation_evaluation_id_must_match() -> None:
    violation = warning_violation(
        evaluation_id="different-evaluation"
    )

    with pytest.raises(
        ValueError,
        match=(
            "violation evaluation_id must match "
            "result evaluation_id"
        ),
    ):
        RiskEvaluationResult(
            evaluation_id="evaluation-001",
            status=RiskEvaluationStatus.COMPLETED,
            decision=RiskDecision.REDUCE,
            evaluated_at=NOW + timedelta(seconds=3),
            order_id="order-001",
            portfolio_id="portfolio-001",
            requested_quantity=Decimal("10"),
            approved_quantity=Decimal("8"),
            requested_notional=Decimal("1250"),
            approved_notional=Decimal("1000"),
            violations=(violation,),
        )


def test_violation_ids_must_be_unique() -> None:
    violation = warning_violation()

    with pytest.raises(
        ValueError,
        match="violation_id values must be unique",
    ):
        RiskEvaluationResult(
            evaluation_id="evaluation-001",
            status=RiskEvaluationStatus.COMPLETED,
            decision=RiskDecision.REDUCE,
            evaluated_at=NOW + timedelta(seconds=3),
            order_id="order-001",
            portfolio_id="portfolio-001",
            requested_quantity=Decimal("10"),
            approved_quantity=Decimal("8"),
            requested_notional=Decimal("1250"),
            approved_notional=Decimal("1000"),
            violations=(violation, violation),
        )


def test_violation_must_not_follow_evaluation_time() -> None:
    violation = warning_violation(
        occurred_at=NOW + timedelta(seconds=5)
    )

    with pytest.raises(
        ValueError,
        match=(
            "violation occurred_at must not be later "
            "than evaluated_at"
        ),
    ):
        RiskEvaluationResult(
            evaluation_id="evaluation-001",
            status=RiskEvaluationStatus.COMPLETED,
            decision=RiskDecision.REDUCE,
            evaluated_at=NOW + timedelta(seconds=3),
            order_id="order-001",
            portfolio_id="portfolio-001",
            requested_quantity=Decimal("10"),
            approved_quantity=Decimal("8"),
            requested_notional=Decimal("1250"),
            approved_notional=Decimal("1000"),
            violations=(violation,),
        )


def test_failed_result_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed evaluations must include an error"
        ),
    ):
        RiskEvaluationResult(
            evaluation_id="evaluation-001",
            status=RiskEvaluationStatus.FAILED,
            decision=RiskDecision.REJECT,
            evaluated_at=NOW,
            order_id="order-001",
            portfolio_id="portfolio-001",
            requested_quantity=Decimal("10"),
            approved_quantity=Decimal("0"),
            requested_notional=Decimal("1250"),
            approved_notional=Decimal("0"),
        )


def test_approved_result_rejects_violations() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "approved evaluations must not include "
            "violations"
        ),
    ):
        RiskEvaluationResult(
            evaluation_id="evaluation-001",
            status=RiskEvaluationStatus.COMPLETED,
            decision=RiskDecision.APPROVE,
            evaluated_at=NOW + timedelta(seconds=3),
            order_id="order-001",
            portfolio_id="portfolio-001",
            requested_quantity=Decimal("10"),
            approved_quantity=Decimal("10"),
            requested_notional=Decimal("1250"),
            approved_notional=Decimal("1250"),
            violations=(warning_violation(),),
        )


def test_approved_result_requires_full_quantity() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "approved evaluations require the full "
            "requested quantity"
        ),
    ):
        RiskEvaluationResult(
            evaluation_id="evaluation-001",
            status=RiskEvaluationStatus.COMPLETED,
            decision=RiskDecision.APPROVE,
            evaluated_at=NOW,
            order_id="order-001",
            portfolio_id="portfolio-001",
            requested_quantity=Decimal("10"),
            approved_quantity=Decimal("8"),
            requested_notional=Decimal("1250"),
            approved_notional=Decimal("1250"),
        )


def test_reduce_requires_violations() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "reduced evaluations must include violations"
        ),
    ):
        RiskEvaluationResult(
            evaluation_id="evaluation-001",
            status=RiskEvaluationStatus.COMPLETED,
            decision=RiskDecision.REDUCE,
            evaluated_at=NOW,
            order_id="order-001",
            portfolio_id="portfolio-001",
            requested_quantity=Decimal("10"),
            approved_quantity=Decimal("8"),
            requested_notional=Decimal("1250"),
            approved_notional=Decimal("1000"),
        )


@pytest.mark.parametrize(
    "decision",
    [
        RiskDecision.HOLD,
        RiskDecision.REJECT,
    ],
)
def test_hold_and_reject_require_zero_approval(
    decision: RiskDecision,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "held and rejected evaluations must have "
            "zero approved quantity"
        ),
    ):
        RiskEvaluationResult(
            evaluation_id="evaluation-001",
            status=RiskEvaluationStatus.COMPLETED,
            decision=decision,
            evaluated_at=NOW + timedelta(seconds=3),
            order_id="order-001",
            portfolio_id="portfolio-001",
            requested_quantity=Decimal("10"),
            approved_quantity=Decimal("1"),
            requested_notional=Decimal("1250"),
            approved_notional=Decimal("125"),
            violations=(warning_violation(),),
        )


def test_risk_gateway_report() -> None:
    request = evaluation_request()
    result = approved_result()

    report = RiskGatewayReport(
        report_id="report-001",
        request=request,
        result=result,
        reported_at=NOW + timedelta(seconds=4),
        message="Risk evaluation completed.",
    )

    assert report.request == request
    assert report.result == result
    assert report.report_id == "report-001"


def test_report_text_is_normalized() -> None:
    report = RiskGatewayReport(
        report_id="  report-001  ",
        request=evaluation_request(),
        result=approved_result(),
        reported_at=NOW + timedelta(seconds=4),
        message="  Risk evaluation completed.  ",
        metadata=[
            ("  source  ", "  gateway  "),
        ],
        warnings=[
            "  Review exposure.  ",
        ],
    )

    assert report.report_id == "report-001"
    assert report.message == (
        "Risk evaluation completed."
    )
    assert report.metadata == (
        ("source", "gateway"),
    )
    assert report.warnings == (
        "Review exposure.",
    )


def test_report_evaluation_ids_must_match() -> None:
    result = RiskEvaluationResult(
        evaluation_id="different-evaluation",
        status=RiskEvaluationStatus.COMPLETED,
        decision=RiskDecision.APPROVE,
        evaluated_at=NOW + timedelta(seconds=3),
        order_id="order-001",
        portfolio_id="portfolio-001",
        requested_quantity=Decimal("10"),
        approved_quantity=Decimal("10"),
        requested_notional=Decimal("1250"),
        approved_notional=Decimal("1250"),
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result evaluation_id values "
            "must match"
        ),
    ):
        RiskGatewayReport(
            report_id="report-001",
            request=evaluation_request(),
            result=result,
            reported_at=NOW + timedelta(seconds=4),
            message="Risk evaluation completed.",
        )


def test_report_order_id_must_match_request() -> None:
    result = RiskEvaluationResult(
        evaluation_id="evaluation-001",
        status=RiskEvaluationStatus.COMPLETED,
        decision=RiskDecision.APPROVE,
        evaluated_at=NOW + timedelta(seconds=3),
        order_id="different-order",
        portfolio_id="portfolio-001",
        requested_quantity=Decimal("10"),
        approved_quantity=Decimal("10"),
        requested_notional=Decimal("1250"),
        approved_notional=Decimal("1250"),
    )

    with pytest.raises(
        ValueError,
        match=(
            "result order_id must match request order_id"
        ),
    ):
        RiskGatewayReport(
            report_id="report-001",
            request=evaluation_request(),
            result=result,
            reported_at=NOW + timedelta(seconds=4),
            message="Risk evaluation completed.",
        )


def test_result_must_not_precede_request() -> None:
    result = RiskEvaluationResult(
        evaluation_id="evaluation-001",
        status=RiskEvaluationStatus.COMPLETED,
        decision=RiskDecision.APPROVE,
        evaluated_at=NOW,
        order_id="order-001",
        portfolio_id="portfolio-001",
        requested_quantity=Decimal("10"),
        approved_quantity=Decimal("10"),
        requested_notional=Decimal("1250"),
        approved_notional=Decimal("1250"),
    )

    with pytest.raises(
        ValueError,
        match=(
            "result evaluated_at must not be earlier "
            "than request requested_at"
        ),
    ):
        RiskGatewayReport(
            report_id="report-001",
            request=evaluation_request(),
            result=result,
            reported_at=NOW + timedelta(seconds=4),
            message="Risk evaluation completed.",
        )


def test_reported_at_must_follow_result() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier than "
            "result evaluated_at"
        ),
    ):
        RiskGatewayReport(
            report_id="report-001",
            request=evaluation_request(),
            result=approved_result(),
            reported_at=NOW + timedelta(seconds=2),
            message="Risk evaluation completed.",
        )


def test_models_are_immutable() -> None:
    value = evaluation_request()

    with pytest.raises(FrozenInstanceError):
        value.market_price = Decimal("130")