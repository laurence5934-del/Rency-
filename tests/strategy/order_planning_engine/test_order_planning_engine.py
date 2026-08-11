from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


from app.strategy.order_planning_engine import (
    EnterpriseOrderPlanningEngine,
    OrderPlanAction,
    OrderPlanSide,
    OrderPlanTimeInForce,
    OrderPlanType,
    OrderPlanningDecision,
    OrderPlanningRequest,
    OrderPlanningStatus,
)


NOW = datetime(
    2026,
    8,
    11,
    12,
    0,
    tzinfo=timezone.utc,
)


def fixed_clock() -> datetime:
    return NOW


def order_planning_request(
    *,
    request_id: str = "request-001",
    correlation_id: str = "correlation-001",
    strategy_id: str = "strategy-001",
    portfolio_id: str = "portfolio-001",
    allocation_id: str = "allocation-001",
    signal_id: str = "signal-001",
    intent_id: str = "trade-intent-000001",
    symbol: str = "NVDA",
    action: OrderPlanAction = OrderPlanAction.CREATE,
    side: OrderPlanSide = OrderPlanSide.BUY,
    order_type: OrderPlanType = OrderPlanType.MARKET,
    time_in_force: OrderPlanTimeInForce = OrderPlanTimeInForce.DAY,
    quantity: int = 10,
    confidence: int = 90,
    created_at: datetime = NOW,
    sequence_number: int = 0,
) -> OrderPlanningRequest:
    return OrderPlanningRequest(
        request_id=request_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        allocation_id=allocation_id,
        signal_id=signal_id,
        intent_id=intent_id,
        symbol=symbol,
        action=action,
        side=side,
        order_type=order_type,
        time_in_force=time_in_force,
        quantity=quantity,
        confidence=confidence,
        created_at=created_at,
        sequence_number=sequence_number,
        requested_by="trade-intent-engine",
    )


def started_engine(
    *,
    request: OrderPlanningRequest | None = None,
) -> tuple[
    EnterpriseOrderPlanningEngine,
    OrderPlanningRequest,
]:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    value = request or order_planning_request()

    engine.register_request(value)
    engine.start_planning(value.request_id)

    return engine, value


def generated_engine() -> EnterpriseOrderPlanningEngine:
    engine, request = started_engine()

    engine.attach_plan(
        request.request_id,
        rationale=(
            "Approved trade intent supports "
            "order construction."
        ),
    )

    return engine


def test_create_order_planning_engine() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    assert engine.request_ids == ()
    assert engine.plan_ids == ()
    assert engine.report_history == ()


def test_engine_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterpriseOrderPlanningEngine(
            clock="not-callable"
        )


def test_register_order_planning_request() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()

    registered = engine.register_request(
        request
    )

    assert registered is request
    assert engine.request_ids == (
        "request-001",
    )

    assert engine.get_request(
        "request-001"
    ) is request


def test_register_request_requires_model() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        TypeError,
        match=(
            "request must be an "
            "OrderPlanningRequest"
        ),
    ):
        engine.register_request(
            object()
        )


def test_duplicate_request_id_is_rejected() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    engine.register_request(
        order_planning_request()
    )

    with pytest.raises(
        ValueError,
        match="request_id is already registered",
    ):
        engine.register_request(
            order_planning_request(
                correlation_id="correlation-002",
            )
        )


def test_duplicate_correlation_id_is_rejected() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    engine.register_request(
        order_planning_request()
    )

    with pytest.raises(
        ValueError,
        match=(
            "correlation_id is already registered"
        ),
    ):
        engine.register_request(
            order_planning_request(
                request_id="request-002",
            )
        )


def test_register_multiple_requests() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    first = order_planning_request()

    second = order_planning_request(
        request_id="request-002",
        correlation_id="correlation-002",
        allocation_id="allocation-002",
        signal_id="signal-002",
        intent_id="trade-intent-000002",
        symbol="AAPL",
    )

    engine.register_request(first)
    engine.register_request(second)

    assert engine.request_ids == (
        "request-001",
        "request-002",
    )


def test_request_ids_are_sorted() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    engine.register_request(
        order_planning_request(
            request_id="request-003",
            correlation_id="correlation-003",
        )
    )

    engine.register_request(
        order_planning_request(
            request_id="request-001",
            correlation_id="correlation-001",
        )
    )

    engine.register_request(
        order_planning_request(
            request_id="request-002",
            correlation_id="correlation-002",
        )
    )

    assert engine.request_ids == (
        "request-001",
        "request-002",
        "request-003",
    )


def test_get_request_normalizes_identifier() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()
    engine.register_request(request)

    assert engine.get_request(
        "  request-001  "
    ) is request


def test_get_unknown_request_is_rejected() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        KeyError,
        match="order planning request not found",
    ):
        engine.get_request(
            "request-999"
        )


def test_request_for_correlation() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()
    engine.register_request(request)

    assert engine.request_for_correlation(
        "correlation-001"
    ) is request


def test_request_for_correlation_normalizes_identifier() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()
    engine.register_request(request)

    assert engine.request_for_correlation(
        "  correlation-001  "
    ) is request


def test_unknown_correlation_is_rejected() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        KeyError,
        match=(
            "order planning request not found "
            "for correlation_id"
        ),
    ):
        engine.request_for_correlation(
            "correlation-999"
        )


def test_unregister_request() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()
    engine.register_request(request)

    removed = engine.unregister_request(
        request.request_id
    )

    assert removed is request
    assert engine.request_ids == ()

    with pytest.raises(KeyError):
        engine.get_request(
            request.request_id
        )


def test_unregister_request_normalizes_identifier() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()
    engine.register_request(request)

    assert engine.unregister_request(
        "  request-001  "
    ) is request


def test_unregister_releases_correlation_id() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()
    engine.register_request(request)

    engine.unregister_request(
        request.request_id
    )

    replacement = order_planning_request(
        request_id="request-002",
    )

    engine.register_request(
        replacement
    )

    assert (
        engine.request_for_correlation(
            "correlation-001"
        )
        is replacement
    )


def test_start_planning() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()
    engine.register_request(request)

    report = engine.start_planning(
        request.request_id
    )

    assert report.request is request
    assert report.request_id == request.request_id

    assert (
        report.status
        is OrderPlanningStatus.ACTIVE
    )

    assert (
        report.decision
        is OrderPlanningDecision.PROCEED
    )

    assert report.plan is None

    assert report.message == (
        "Order planning evaluation started."
    )

    result = engine.get_result(
        request.request_id
    )

    assert (
        result.status
        is OrderPlanningStatus.ACTIVE
    )

    assert (
        result.decision
        is OrderPlanningDecision.PROCEED
    )

    assert result.started_at == NOW
    assert result.updated_at == NOW


def test_start_planning_normalizes_identifier() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()
    engine.register_request(request)

    report = engine.start_planning(
        "  request-001  "
    )

    assert report.request_id == (
        "request-001"
    )


def test_start_planning_is_idempotent() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()
    engine.register_request(request)

    first = engine.start_planning(
        request.request_id
    )

    second = engine.start_planning(
        request.request_id
    )

    assert second is first

    assert len(
        engine.results_for_request(
            request.request_id
        )
    ) == 1

    assert len(
        engine.report_history
    ) == 1


def test_start_unknown_request_is_rejected() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        KeyError,
        match="order planning request not found",
    ):
        engine.start_planning(
            "request-999"
        )


def test_start_time_must_not_precede_request() -> None:
    request = order_planning_request(
        created_at=(
            NOW + timedelta(seconds=1)
        ),
    )

    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    engine.register_request(request)

    with pytest.raises(
        ValueError,
        match=(
            "order planning start time must not "
            "be earlier than request created_at"
        ),
    ):
        engine.start_planning(
            request.request_id
        )


def test_unregister_started_request_is_rejected() -> None:
    engine, request = started_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "started order planning requests "
            "cannot be unregistered"
        ),
    ):
        engine.unregister_request(
            request.request_id
        )


def test_get_result() -> None:
    engine, request = started_engine()

    result = engine.get_result(
        request.request_id
    )

    assert (
        result.request_id
        == request.request_id
    )

    assert (
        result.status
        is OrderPlanningStatus.ACTIVE
    )


def test_get_result_normalizes_identifier() -> None:
    engine, _ = started_engine()

    result = engine.get_result(
        "  request-001  "
    )

    assert result.request_id == (
        "request-001"
    )


def test_get_result_before_start_is_rejected() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()
    engine.register_request(request)

    with pytest.raises(
        KeyError,
        match=(
            "order planning request has no result"
        ),
    ):
        engine.get_result(
            request.request_id
        )


def test_get_report() -> None:
    engine, request = started_engine()

    report = engine.get_report(
        request.request_id
    )

    assert (
        report.request_id
        == request.request_id
    )

    assert (
        report.status
        is OrderPlanningStatus.ACTIVE
    )


def test_get_report_before_start_is_rejected() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()
    engine.register_request(request)

    with pytest.raises(
        KeyError,
        match=(
            "order planning request has no report"
        ),
    ):
        engine.get_report(
            request.request_id
        )


def test_results_for_request() -> None:
    engine, request = started_engine()

    history = engine.results_for_request(
        request.request_id
    )

    assert len(history) == 1

    assert (
        history[0]
        is engine.get_result(
            request.request_id
        )
    )


def test_results_for_unstarted_request_returns_empty() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()
    engine.register_request(request)

    assert engine.results_for_request(
        request.request_id
    ) == ()


def test_latest_report() -> None:
    engine, request = started_engine()

    assert (
        engine.latest_report()
        is engine.get_report(
            request.request_id
        )
    )


def test_latest_report_without_history_is_rejected() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        KeyError,
        match=(
            "order planning engine has no reports"
        ),
    ):
        engine.latest_report()


def test_attach_plan() -> None:
    engine, request = started_engine()

    report = engine.attach_plan(
        request.request_id,
        rationale=(
            "Approved trade intent supports "
            "order construction."
        ),
    )

    plan = report.plan

    assert plan is not None
    assert plan.plan_id == "order-plan-000001"
    assert plan.request_id == "request-001"
    assert plan.correlation_id == "correlation-001"
    assert plan.strategy_id == "strategy-001"
    assert plan.portfolio_id == "portfolio-001"
    assert plan.allocation_id == "allocation-001"
    assert plan.signal_id == "signal-001"
    assert plan.intent_id == "trade-intent-000001"
    assert plan.symbol == "NVDA"
    assert plan.action is OrderPlanAction.CREATE
    assert plan.side is OrderPlanSide.BUY
    assert plan.order_type is OrderPlanType.MARKET

    assert (
        plan.time_in_force
        is OrderPlanTimeInForce.DAY
    )

    assert plan.quantity == 10
    assert plan.confidence == 90
    assert plan.generated_at == NOW

    assert plan.rationale == (
        "Approved trade intent supports "
        "order construction."
    )

    assert (
        report.status
        is OrderPlanningStatus.ACTIVE
    )

    assert (
        report.decision
        is OrderPlanningDecision.PROCEED
    )

    assert report.message == (
        "Order plan generated."
    )


def test_attach_plan_requires_started_request() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()
    engine.register_request(request)

    with pytest.raises(
        KeyError,
        match=(
            "order planning request has no result"
        ),
    ):
        engine.attach_plan(
            request.request_id,
            rationale="Order plan.",
        )


def test_attach_plan_rejects_duplicate_plan() -> None:
    engine = generated_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "order plan is already attached to request"
        ),
    ):
        engine.attach_plan(
            "request-001",
            rationale="Duplicate order plan.",
        )


def test_plan_generation_time_must_follow_update() -> None:
    times = iter(
        [
            NOW,
            NOW - timedelta(seconds=1),
        ]
    )

    engine = EnterpriseOrderPlanningEngine(
        clock=lambda: next(times)
    )

    request = order_planning_request()

    engine.register_request(request)
    engine.start_planning(
        request.request_id
    )

    with pytest.raises(
        ValueError,
        match=(
            "order plan generation time must not be "
            "earlier than latest result update"
        ),
    ):
        engine.attach_plan(
            request.request_id,
            rationale="Order plan.",
        )


def test_plan_ids_are_deterministic() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    first = order_planning_request(
        request_id="request-001",
        correlation_id="correlation-001",
        intent_id="trade-intent-000001",
    )

    second = order_planning_request(
        request_id="request-002",
        correlation_id="correlation-002",
        allocation_id="allocation-002",
        signal_id="signal-002",
        intent_id="trade-intent-000002",
        symbol="AAPL",
    )

    engine.register_request(first)
    engine.start_planning(
        first.request_id
    )

    first_report = engine.attach_plan(
        first.request_id,
        rationale="First plan.",
    )

    engine.register_request(second)
    engine.start_planning(
        second.request_id
    )

    second_report = engine.attach_plan(
        second.request_id,
        rationale="Second plan.",
    )

    assert first_report.plan is not None
    assert second_report.plan is not None

    assert (
        first_report.plan.plan_id
        == "order-plan-000001"
    )

    assert (
        second_report.plan.plan_id
        == "order-plan-000002"
    )


def test_get_plan() -> None:
    engine = generated_engine()

    plan = engine.plan_for_request(
        "request-001"
    )

    assert engine.get_plan(
        plan.plan_id
    ) is plan


def test_get_plan_normalizes_identifier() -> None:
    engine = generated_engine()

    plan = engine.plan_for_request(
        "request-001"
    )

    assert engine.get_plan(
        f"  {plan.plan_id}  "
    ) is plan


def test_get_unknown_plan_is_rejected() -> None:
    engine = generated_engine()

    with pytest.raises(
        KeyError,
        match="order plan not found",
    ):
        engine.get_plan(
            "order-plan-999999"
        )


def test_plan_for_request() -> None:
    engine = generated_engine()

    plan = engine.plan_for_request(
        "request-001"
    )

    assert plan.request_id == "request-001"


def test_plan_for_request_before_generation_is_rejected() -> None:
    engine, request = started_engine()

    with pytest.raises(
        KeyError,
        match=(
            "order planning request has no plan"
        ),
    ):
        engine.plan_for_request(
            request.request_id
        )


def test_plan_ids_property() -> None:
    engine = generated_engine()

    assert engine.plan_ids == (
        "order-plan-000001",
    )


def test_result_history_tracks_plan_generation() -> None:
    engine = generated_engine()

    history = engine.results_for_request(
        "request-001"
    )

    assert len(history) == 2
    assert history[0].plan is None
    assert history[1].plan is not None


def test_report_history_tracks_plan_generation() -> None:
    engine = generated_engine()

    assert len(
        engine.report_history
    ) == 2

    assert (
        engine.report_history[0].message
        == "Order planning evaluation started."
    )

    assert (
        engine.report_history[1].message
        == "Order plan generated."
    )


def test_report_ids_are_deterministic() -> None:
    engine = generated_engine()

    assert (
        engine.report_history[0].report_id
        == "order-planning-report-000001"
    )

    assert (
        engine.report_history[1].report_id
        == "order-planning-report-000002"
    )


def test_reports_for_strategy() -> None:
    engine = generated_engine()

    reports = engine.reports_for_strategy(
        "strategy-001"
    )

    assert len(reports) == 2

    assert all(
        report.strategy_id == "strategy-001"
        for report in reports
    )


def test_reports_for_portfolio() -> None:
    engine = generated_engine()

    reports = engine.reports_for_portfolio(
        "portfolio-001"
    )

    assert len(reports) == 2


def test_reports_for_allocation() -> None:
    engine = generated_engine()

    reports = engine.reports_for_allocation(
        "allocation-001"
    )

    assert len(reports) == 2


def test_reports_for_signal() -> None:
    engine = generated_engine()

    reports = engine.reports_for_signal(
        "signal-001"
    )

    assert len(reports) == 2


def test_reports_for_intent() -> None:
    engine = generated_engine()

    reports = engine.reports_for_intent(
        "trade-intent-000001"
    )

    assert len(reports) == 2


def test_reports_for_symbol_normalizes_symbol() -> None:
    engine = generated_engine()

    reports = engine.reports_for_symbol(
        "  nvda  "
    )

    assert len(reports) == 2

    assert all(
        report.symbol == "NVDA"
        for report in reports
    )


def test_unknown_report_queries_return_empty() -> None:
    engine = generated_engine()

    assert engine.reports_for_strategy(
        "unknown"
    ) == ()

    assert engine.reports_for_portfolio(
        "unknown"
    ) == ()

    assert engine.reports_for_allocation(
        "unknown"
    ) == ()

    assert engine.reports_for_signal(
        "unknown"
    ) == ()

    assert engine.reports_for_intent(
        "unknown"
    ) == ()

    assert engine.reports_for_symbol(
        "UNKNOWN"
    ) == ()


def test_report_contains_request_metadata() -> None:
    engine, request = started_engine()

    report = engine.get_report(
        request.request_id
    )

    assert report.metadata == (
        ("strategy_id", "strategy-001"),
        ("portfolio_id", "portfolio-001"),
        ("allocation_id", "allocation-001"),
        ("signal_id", "signal-001"),
        ("intent_id", "trade-intent-000001"),
        ("symbol", "NVDA"),
    )


@pytest.mark.parametrize(
    ("method_name", "argument", "message"),
    [
        (
            "get_request",
            "",
            "request_id must not be empty",
        ),
        (
            "request_for_correlation",
            "   ",
            "correlation_id must not be empty",
        ),
        (
            "get_plan",
            "",
            "plan_id must not be empty",
        ),
        (
            "reports_for_strategy",
            "",
            "strategy_id must not be empty",
        ),
        (
            "reports_for_portfolio",
            "",
            "portfolio_id must not be empty",
        ),
        (
            "reports_for_allocation",
            "",
            "allocation_id must not be empty",
        ),
        (
            "reports_for_signal",
            "",
            "signal_id must not be empty",
        ),
        (
            "reports_for_intent",
            "",
            "intent_id must not be empty",
        ),
        (
            "reports_for_symbol",
            "",
            "symbol must not be empty",
        ),
    ],
)
def test_identifier_must_not_be_empty(
    method_name: str,
    argument: str,
    message: str,
) -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    method = getattr(
        engine,
        method_name,
    )

    with pytest.raises(
        ValueError,
        match=message,
    ):
        method(argument)


@pytest.mark.parametrize(
    ("method_name", "message"),
    [
        (
            "get_request",
            "request_id must be a string",
        ),
        (
            "request_for_correlation",
            "correlation_id must be a string",
        ),
        (
            "get_plan",
            "plan_id must be a string",
        ),
        (
            "reports_for_strategy",
            "strategy_id must be a string",
        ),
        (
            "reports_for_portfolio",
            "portfolio_id must be a string",
        ),
        (
            "reports_for_allocation",
            "allocation_id must be a string",
        ),
        (
            "reports_for_signal",
            "signal_id must be a string",
        ),
        (
            "reports_for_intent",
            "intent_id must be a string",
        ),
        (
            "reports_for_symbol",
            "symbol must be a string",
        ),
    ],
)
def test_identifier_must_be_string(
    method_name: str,
    message: str,
) -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    method = getattr(
        engine,
        method_name,
    )

    with pytest.raises(
        TypeError,
        match=message,
    ):
        method(123)


def test_clock_must_return_datetime() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=lambda: "not-a-datetime",
    )

    request = order_planning_request()
    engine.register_request(request)

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        engine.start_planning(
            request.request_id
        )


def test_clock_must_return_timezone_aware_datetime() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=lambda: datetime(
            2026,
            8,
            11,
            12,
            0,
        ),
    )

    request = order_planning_request()
    engine.register_request(request)

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a "
            "timezone-aware datetime"
        ),
    ):
        engine.start_planning(
            request.request_id
        )

# ---------------------------------------------------------------------------
# Phase 2B Part B
# Terminal lifecycle contracts
# ---------------------------------------------------------------------------


def test_approve_request() -> None:
    engine = generated_engine()

    report = engine.approve_request(
        "request-001"
    )

    assert (
        report.status
        is OrderPlanningStatus.APPROVED
    )
    assert (
        report.decision
        is OrderPlanningDecision.APPROVE
    )
    assert report.plan is not None
    assert report.result.completed_at == NOW
    assert report.message == "Order plan approved."

    result = engine.get_result(
        "request-001"
    )

    assert (
        result.status
        is OrderPlanningStatus.APPROVED
    )
    assert result.completed_at == NOW


def test_approve_request_requires_plan() -> None:
    engine, request = started_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "order planning request cannot be approved "
            "without a plan"
        ),
    ):
        engine.approve_request(
            request.request_id
        )


def test_approve_request_custom_message_is_normalized() -> None:
    engine = generated_engine()

    report = engine.approve_request(
        "request-001",
        message="  Approved by risk controls.  ",
    )

    assert report.message == (
        "Approved by risk controls."
    )


def test_approve_request_rejects_empty_message() -> None:
    engine = generated_engine()

    with pytest.raises(
        ValueError,
        match="message must not be empty",
    ):
        engine.approve_request(
            "request-001",
            message="   ",
        )


def test_reject_request() -> None:
    engine, request = started_engine()

    report = engine.reject_request(
        request.request_id,
        reason="Risk threshold exceeded.",
    )

    assert (
        report.status
        is OrderPlanningStatus.REJECTED
    )
    assert (
        report.decision
        is OrderPlanningDecision.REJECT
    )
    assert report.result.completed_at == NOW
    assert report.plan is None
    assert report.message == (
        "Risk threshold exceeded."
    )


def test_reject_request_preserves_plan() -> None:
    engine = generated_engine()

    plan = engine.plan_for_request(
        "request-001"
    )

    report = engine.reject_request(
        "request-001",
        reason="Final risk review rejected plan.",
    )

    assert report.plan is plan


def test_reject_reason_is_normalized() -> None:
    engine, request = started_engine()

    report = engine.reject_request(
        request.request_id,
        reason="  Risk threshold exceeded.  ",
    )

    assert report.message == (
        "Risk threshold exceeded."
    )


def test_reject_reason_must_not_be_empty() -> None:
    engine, request = started_engine()

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        engine.reject_request(
            request.request_id,
            reason="   ",
        )


def test_cancel_request() -> None:
    engine, request = started_engine()

    report = engine.cancel_request(
        request.request_id,
        reason="Strategy cancelled order planning.",
    )

    assert (
        report.status
        is OrderPlanningStatus.CANCELLED
    )
    assert (
        report.decision
        is OrderPlanningDecision.CANCEL
    )
    assert report.result.completed_at == NOW
    assert report.message == (
        "Strategy cancelled order planning."
    )


def test_cancel_request_preserves_plan() -> None:
    engine = generated_engine()

    plan = engine.plan_for_request(
        "request-001"
    )

    report = engine.cancel_request(
        "request-001",
        reason="Order plan cancelled.",
    )

    assert report.plan is plan


def test_cancel_reason_must_not_be_empty() -> None:
    engine, request = started_engine()

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        engine.cancel_request(
            request.request_id,
            reason="",
        )


def test_fail_request_non_retryable() -> None:
    engine, request = started_engine()

    report = engine.fail_request(
        request.request_id,
        error="Order construction failed.",
    )

    assert (
        report.status
        is OrderPlanningStatus.FAILED
    )
    assert (
        report.decision
        is OrderPlanningDecision.NO_ACTION
    )
    assert report.result.completed_at == NOW
    assert report.result.error == (
    "Order construction failed."
)
    assert report.message == (
        "Order construction failed."
    )


def test_fail_request_retryable() -> None:
    engine, request = started_engine()

    report = engine.fail_request(
        request.request_id,
        error="Temporary planning dependency failure.",
        retryable=True,
    )

    assert (
        report.status
        is OrderPlanningStatus.FAILED
    )
    assert (
        report.decision
        is OrderPlanningDecision.RETRY
    )

    assert report.result.error == (
    "Temporary planning dependency failure."
    )


def test_fail_request_preserves_plan() -> None:
    engine = generated_engine()

    plan = engine.plan_for_request(
        "request-001"
    )

    report = engine.fail_request(
        "request-001",
        error="Downstream validation failure.",
    )

    assert report.plan is plan


def test_fail_request_error_is_normalized() -> None:
    engine, request = started_engine()

    report = engine.fail_request(
        request.request_id,
        error="  Planning dependency failed.  ",
    )

    assert report.result.error == (
        "Planning dependency failed."
    )
    assert report.message == (
        "Planning dependency failed."
    )


def test_fail_request_error_must_not_be_empty() -> None:
    engine, request = started_engine()

    with pytest.raises(
        ValueError,
        match="error must not be empty",
    ):
        engine.fail_request(
            request.request_id,
            error="   ",
        )


def test_fail_request_retryable_requires_bool() -> None:
    engine, request = started_engine()

    with pytest.raises(
        TypeError,
        match="retryable must be a bool",
    ):
        engine.fail_request(
            request.request_id,
            error="Planning failed.",
            retryable=1,
        )


@pytest.mark.parametrize(
    "terminal_action",
    [
        "approve",
        "reject",
        "cancel",
        "fail",
    ],
)
def test_terminal_request_cannot_attach_another_plan(
    terminal_action: str,
) -> None:
    engine = generated_engine()

    if terminal_action == "approve":
        engine.approve_request(
            "request-001"
        )
    elif terminal_action == "reject":
        engine.reject_request(
            "request-001",
            reason="Rejected.",
        )
    elif terminal_action == "cancel":
        engine.cancel_request(
            "request-001",
            reason="Cancelled.",
        )
    else:
        engine.fail_request(
            "request-001",
            error="Failed.",
        )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal order planning requests "
            "cannot be modified"
        ),
    ):
        engine.attach_plan(
            "request-001",
            rationale="Replacement plan.",
        )


@pytest.mark.parametrize(
    "terminal_action",
    [
        "approve",
        "reject",
        "cancel",
        "fail",
    ],
)
def test_terminal_request_cannot_be_approved_again(
    terminal_action: str,
) -> None:
    engine = generated_engine()

    if terminal_action == "approve":
        engine.approve_request(
            "request-001"
        )
    elif terminal_action == "reject":
        engine.reject_request(
            "request-001",
            reason="Rejected.",
        )
    elif terminal_action == "cancel":
        engine.cancel_request(
            "request-001",
            reason="Cancelled.",
        )
    else:
        engine.fail_request(
            "request-001",
            error="Failed.",
        )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal order planning requests "
            "cannot be modified"
        ),
    ):
        engine.approve_request(
            "request-001"
        )


@pytest.mark.parametrize(
    "first_action",
    [
        "approve",
        "reject",
        "cancel",
        "fail",
    ],
)
def test_terminal_request_cannot_be_rejected_again(
    first_action: str,
) -> None:
    engine = generated_engine()

    if first_action == "approve":
        engine.approve_request(
            "request-001"
        )
    elif first_action == "reject":
        engine.reject_request(
            "request-001",
            reason="Rejected.",
        )
    elif first_action == "cancel":
        engine.cancel_request(
            "request-001",
            reason="Cancelled.",
        )
    else:
        engine.fail_request(
            "request-001",
            error="Failed.",
        )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal order planning requests "
            "cannot be modified"
        ),
    ):
        engine.reject_request(
            "request-001",
            reason="Second rejection.",
        )


def test_plan_warnings_survive_approval() -> None:
    engine, request = started_engine()

    engine.attach_plan(
        request.request_id,
        rationale="Generate guarded order.",
        warnings=(
            "Liquidity is below preferred level.",
            "Spread is elevated.",
        ),
    )

    report = engine.approve_request(
        request.request_id
    )

    assert report.warnings == (
        "Liquidity is below preferred level.",
        "Spread is elevated.",
    )

    assert report.result.warnings == (
        "Liquidity is below preferred level.",
        "Spread is elevated.",
    )


def test_plan_warnings_survive_rejection() -> None:
    engine, request = started_engine()

    engine.attach_plan(
        request.request_id,
        rationale="Generate guarded order.",
        warnings=("Liquidity warning.",),
    )

    report = engine.reject_request(
        request.request_id,
        reason="Risk rejected.",
    )

    assert report.warnings == (
        "Liquidity warning.",
    )


def test_terminal_transition_adds_history_entry() -> None:
    engine = generated_engine()

    assert len(
        engine.results_for_request(
            "request-001"
        )
    ) == 2

    assert len(engine.report_history) == 2

    engine.approve_request(
        "request-001"
    )

    results = engine.results_for_request(
        "request-001"
    )

    assert len(results) == 3
    assert len(engine.report_history) == 3

    assert (
        results[-1].status
        is OrderPlanningStatus.APPROVED
    )

    assert (
        engine.report_history[-1].status
        is OrderPlanningStatus.APPROVED
    )


def test_latest_report_tracks_terminal_transition() -> None:
    engine = generated_engine()

    terminal = engine.approve_request(
        "request-001"
    )

    assert engine.latest_report() is terminal
    assert (
        engine.get_report("request-001")
        is terminal
    )


def test_completed_at_is_only_set_for_terminal_result() -> None:
    engine = generated_engine()

    active = engine.get_result(
        "request-001"
    )

    assert active.completed_at is None

    engine.approve_request(
        "request-001"
    )

    terminal = engine.get_result(
        "request-001"
    )

    assert terminal.completed_at == NOW


def test_approval_time_cannot_precede_latest_update() -> None:
    times = iter(
        [
            NOW,
            NOW,
            NOW - timedelta(seconds=1),
        ]
    )

    engine = EnterpriseOrderPlanningEngine(
        clock=lambda: next(times)
    )

    request = order_planning_request()

    engine.register_request(request)
    engine.start_planning(
        request.request_id
    )

    engine.attach_plan(
        request.request_id,
        rationale="Order plan.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "approval time must not be earlier "
            "than latest result update"
        ),
    ):
        engine.approve_request(
            request.request_id
        )


def test_terminal_transition_time_cannot_precede_latest_update() -> None:
    times = iter(
        [
            NOW,
            NOW - timedelta(seconds=1),
        ]
    )

    engine = EnterpriseOrderPlanningEngine(
        clock=lambda: next(times)
    )

    request = order_planning_request()

    engine.register_request(request)
    engine.start_planning(
        request.request_id
    )

    with pytest.raises(
        ValueError,
        match=(
            "terminal transition time must not be "
            "earlier than latest result update"
        ),
    ):
        engine.reject_request(
            request.request_id,
            reason="Rejected.",
        )


def test_complete_approved_order_planning_lifecycle() -> None:
    engine = EnterpriseOrderPlanningEngine(
        clock=fixed_clock,
    )

    request = order_planning_request()

    engine.register_request(request)

    started = engine.start_planning(
        request.request_id
    )

    planned = engine.attach_plan(
        request.request_id,
        rationale=(
            "Trade intent translated into "
            "executable order plan."
        ),
    )

    approved = engine.approve_request(
        request.request_id,
        message="Order plan cleared for execution.",
    )

    assert (
        started.status
        is OrderPlanningStatus.ACTIVE
    )

    assert planned.plan is not None

    assert (
        approved.status
        is OrderPlanningStatus.APPROVED
    )

    assert (
        approved.decision
        is OrderPlanningDecision.APPROVE
    )

    assert approved.plan is planned.plan

    assert engine.plan_for_request(
        request.request_id
    ) is planned.plan

    history = engine.results_for_request(
        request.request_id
    )

    assert len(history) == 3

    assert tuple(
        result.status
        for result in history
    ) == (
        OrderPlanningStatus.ACTIVE,
        OrderPlanningStatus.ACTIVE,
        OrderPlanningStatus.APPROVED,
    )

    assert len(engine.report_history) == 3

    assert tuple(
        report.report_id
        for report in engine.report_history
    ) == (
        "order-planning-report-000001",
        "order-planning-report-000002",
        "order-planning-report-000003",
    )


def test_complete_rejected_order_planning_lifecycle() -> None:
    engine = generated_engine()

    terminal = engine.reject_request(
        "request-001",
        reason="Portfolio risk limit exceeded.",
    )

    assert (
        terminal.status
        is OrderPlanningStatus.REJECTED
    )

    assert (
        terminal.decision
        is OrderPlanningDecision.REJECT
    )

    assert terminal.plan is not None

    assert len(
        engine.results_for_request(
            "request-001"
        )
    ) == 3


def test_complete_failed_order_planning_lifecycle() -> None:
    engine = generated_engine()

    terminal = engine.fail_request(
        "request-001",
        error="Broker preparation dependency failed.",
        retryable=True,
    )

    assert (
        terminal.status
        is OrderPlanningStatus.FAILED
    )

    assert (
        terminal.decision
        is OrderPlanningDecision.RETRY
    )

    assert terminal.plan is not None
    assert terminal.result.completed_at == NOW