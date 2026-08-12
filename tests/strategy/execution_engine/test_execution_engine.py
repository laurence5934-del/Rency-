from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.execution_engine import (
    EnterpriseExecutionEngine,
    ExecutionAction,
    ExecutionDecision,
    ExecutionOrderType,
    ExecutionRequest,
    ExecutionSide,
    ExecutionStatus,
    ExecutionTimeInForce,
)


NOW = datetime(
    2026,
    8,
    11,
    20,
    30,
    tzinfo=timezone.utc,
)


def fixed_clock() -> datetime:
    return NOW


def execution_request(
    *,
    request_id: str = "execution-request-001",
    correlation_id: str = "correlation-001",
    strategy_id: str = "strategy-001",
    portfolio_id: str = "portfolio-001",
    allocation_id: str = "allocation-001",
    signal_id: str = "signal-001",
    intent_id: str = "trade-intent-001",
    plan_id: str = "order-plan-001",
    symbol: str = "NVDA",
    action: ExecutionAction = ExecutionAction.SUBMIT,
    side: ExecutionSide = ExecutionSide.BUY,
    order_type: ExecutionOrderType = ExecutionOrderType.MARKET,
    time_in_force: ExecutionTimeInForce = ExecutionTimeInForce.DAY,
    quantity: int = 10,
    confidence: int = 90,
    created_at: datetime = NOW,
) -> ExecutionRequest:
    return ExecutionRequest(
        request_id=request_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        allocation_id=allocation_id,
        signal_id=signal_id,
        intent_id=intent_id,
        plan_id=plan_id,
        symbol=symbol,
        action=action,
        side=side,
        order_type=order_type,
        time_in_force=time_in_force,
        quantity=quantity,
        confidence=confidence,
        created_at=created_at,
        requested_by="order-planning-engine",
    )


def started_engine(
    *,
    request: ExecutionRequest | None = None,
) -> tuple[
    EnterpriseExecutionEngine,
    ExecutionRequest,
]:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    value = request or execution_request()

    engine.register_request(value)
    engine.start_execution(value.request_id)

    return engine, value


def prepared_engine() -> EnterpriseExecutionEngine:
    engine, request = started_engine()

    engine.prepare_order(
        request.request_id
    )

    return engine


def test_create_execution_engine() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    assert engine.request_ids == ()
    assert engine.report_history == ()
    assert engine.order_history == ()


def test_engine_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterpriseExecutionEngine(
            clock="not-callable"
        )


def test_register_execution_request() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    request = execution_request()

    registered = engine.register_request(
        request
    )

    assert registered is request
    assert engine.request_ids == (
        "execution-request-001",
    )
    assert engine.get_request(
        request.request_id
    ) is request


def test_register_request_requires_model() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        TypeError,
        match="request must be an ExecutionRequest",
    ):
        engine.register_request(
            object()
        )


def test_duplicate_request_id_is_rejected() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    engine.register_request(
        execution_request()
    )

    with pytest.raises(
        ValueError,
        match="request_id is already registered",
    ):
        engine.register_request(
            execution_request(
                correlation_id="correlation-002",
            )
        )


def test_duplicate_correlation_id_is_rejected() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    engine.register_request(
        execution_request()
    )

    with pytest.raises(
        ValueError,
        match=(
            "correlation_id is already registered"
        ),
    ):
        engine.register_request(
            execution_request(
                request_id="execution-request-002",
            )
        )


def test_register_multiple_requests() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    first = execution_request()

    second = execution_request(
        request_id="execution-request-002",
        correlation_id="correlation-002",
        allocation_id="allocation-002",
        signal_id="signal-002",
        intent_id="trade-intent-002",
        plan_id="order-plan-002",
        symbol="AAPL",
    )

    engine.register_request(first)
    engine.register_request(second)

    assert engine.request_ids == (
        "execution-request-001",
        "execution-request-002",
    )


def test_request_ids_are_sorted() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    engine.register_request(
        execution_request(
            request_id="execution-request-003",
            correlation_id="correlation-003",
        )
    )

    engine.register_request(
        execution_request(
            request_id="execution-request-001",
            correlation_id="correlation-001",
        )
    )

    engine.register_request(
        execution_request(
            request_id="execution-request-002",
            correlation_id="correlation-002",
        )
    )

    assert engine.request_ids == (
        "execution-request-001",
        "execution-request-002",
        "execution-request-003",
    )


def test_get_request_normalizes_identifier() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    request = execution_request()
    engine.register_request(request)

    assert engine.get_request(
        "  execution-request-001  "
    ) is request


def test_get_unknown_request_is_rejected() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        KeyError,
        match="execution request not found",
    ):
        engine.get_request(
            "execution-request-999"
        )


def test_request_for_correlation() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    request = execution_request()
    engine.register_request(request)

    assert engine.request_for_correlation(
        "correlation-001"
    ) is request


def test_request_for_correlation_normalizes_identifier() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    request = execution_request()
    engine.register_request(request)

    assert engine.request_for_correlation(
        "  correlation-001  "
    ) is request


def test_unknown_correlation_is_rejected() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        KeyError,
        match=(
            "execution request not found "
            "for correlation_id"
        ),
    ):
        engine.request_for_correlation(
            "correlation-999"
        )


def test_unregister_request() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    request = execution_request()
    engine.register_request(request)

    removed = engine.unregister_request(
        request.request_id
    )

    assert removed is request
    assert engine.request_ids == ()


def test_unregister_releases_correlation_id() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    request = execution_request()
    engine.register_request(request)

    engine.unregister_request(
        request.request_id
    )

    replacement = execution_request(
        request_id="execution-request-002",
    )

    engine.register_request(replacement)

    assert engine.request_for_correlation(
        "correlation-001"
    ) is replacement


def test_start_execution() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    request = execution_request()
    engine.register_request(request)

    report = engine.start_execution(
        request.request_id
    )

    assert report.request is request
    assert (
        report.status
        is ExecutionStatus.PENDING
    )
    assert (
        report.decision
        is ExecutionDecision.NO_ACTION
    )
    assert report.order is None
    assert report.message == (
        "Execution request received."
    )

    result = engine.get_result(
        request.request_id
    )

    assert (
        result.status
        is ExecutionStatus.PENDING
    )
    assert result.started_at == NOW
    assert result.updated_at == NOW


def test_start_execution_is_idempotent() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    request = execution_request()
    engine.register_request(request)

    first = engine.start_execution(
        request.request_id
    )

    second = engine.start_execution(
        request.request_id
    )

    assert second is first
    assert len(
        engine.results_for_request(
            request.request_id
        )
    ) == 1
    assert len(engine.report_history) == 1


def test_start_execution_before_request_time_is_rejected() -> None:
    request = execution_request(
        created_at=(
            NOW + timedelta(seconds=1)
        ),
    )

    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    engine.register_request(request)

    with pytest.raises(
        ValueError,
        match=(
            "execution start time must not "
            "be earlier than request created_at"
        ),
    ):
        engine.start_execution(
            request.request_id
        )


def test_unregister_started_request_is_rejected() -> None:
    engine, request = started_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "started execution requests "
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


def test_get_result_before_start_is_rejected() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    request = execution_request()
    engine.register_request(request)

    with pytest.raises(
        KeyError,
        match=(
            "execution request has no result"
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


def test_get_report_before_start_is_rejected() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    request = execution_request()
    engine.register_request(request)

    with pytest.raises(
        KeyError,
        match=(
            "execution request has no report"
        ),
    ):
        engine.get_report(
            request.request_id
        )


def test_latest_report() -> None:
    engine, request = started_engine()

    assert (
        engine.latest_report()
        is engine.get_report(
            request.request_id
        )
    )


def test_latest_report_without_history_is_rejected() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        KeyError,
        match=(
            "execution engine has no reports"
        ),
    ):
        engine.latest_report()


def test_prepare_order() -> None:
    engine, request = started_engine()

    report = engine.prepare_order(
        request.request_id
    )

    order = report.order

    assert order is not None
    assert (
        order.order_id
        == "execution-order-000001"
    )
    assert order.request_id == request.request_id
    assert order.correlation_id == request.correlation_id
    assert order.strategy_id == request.strategy_id
    assert order.portfolio_id == request.portfolio_id
    assert order.allocation_id == request.allocation_id
    assert order.signal_id == request.signal_id
    assert order.intent_id == request.intent_id
    assert order.plan_id == request.plan_id
    assert order.symbol == request.symbol
    assert order.quantity == request.quantity
    assert order.confidence == request.confidence
    assert order.prepared_at == NOW

    assert (
        report.status
        is ExecutionStatus.READY
    )
    assert (
        report.decision
        is ExecutionDecision.PROCEED
    )
    assert report.message == (
        "Execution order prepared."
    )


def test_prepare_order_requires_started_request() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    request = execution_request()
    engine.register_request(request)

    with pytest.raises(
        KeyError,
        match="execution request has no result",
    ):
        engine.prepare_order(
            request.request_id
        )


def test_prepare_order_is_idempotent() -> None:
    engine, request = started_engine()

    first = engine.prepare_order(
        request.request_id
    )

    second = engine.prepare_order(
        request.request_id
    )

    assert second is first
    assert len(engine.order_history) == 1
    assert len(
        engine.results_for_request(
            request.request_id
        )
    ) == 2


def test_order_ids_are_deterministic() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    first = execution_request()

    second = execution_request(
        request_id="execution-request-002",
        correlation_id="correlation-002",
        allocation_id="allocation-002",
        signal_id="signal-002",
        intent_id="trade-intent-002",
        plan_id="order-plan-002",
        symbol="AAPL",
    )

    engine.register_request(first)
    engine.start_execution(first.request_id)

    first_report = engine.prepare_order(
        first.request_id
    )

    engine.register_request(second)
    engine.start_execution(second.request_id)

    second_report = engine.prepare_order(
        second.request_id
    )

    assert first_report.order is not None
    assert second_report.order is not None

    assert (
        first_report.order.order_id
        == "execution-order-000001"
    )
    assert (
        second_report.order.order_id
        == "execution-order-000002"
    )


def test_get_order() -> None:
    engine = prepared_engine()

    order = engine.order_for_request(
        "execution-request-001"
    )

    assert engine.get_order(
        order.order_id
    ) is order


def test_get_unknown_order_is_rejected() -> None:
    engine = prepared_engine()

    with pytest.raises(
        KeyError,
        match="execution order not found",
    ):
        engine.get_order(
            "execution-order-999999"
        )


def test_order_for_request() -> None:
    engine = prepared_engine()

    order = engine.order_for_request(
        "execution-request-001"
    )

    assert (
        order.request_id
        == "execution-request-001"
    )


def test_order_for_request_before_preparation_is_rejected() -> None:
    engine, request = started_engine()

    with pytest.raises(
        KeyError,
        match=(
            "execution request has no order"
        ),
    ):
        engine.order_for_request(
            request.request_id
        )


def test_order_history_tracks_preparation() -> None:
    engine = prepared_engine()

    assert len(engine.order_history) == 1
    assert (
        engine.order_history[0].order_id
        == "execution-order-000001"
    )


def test_result_history_tracks_preparation() -> None:
    engine = prepared_engine()

    history = engine.results_for_request(
        "execution-request-001"
    )

    assert len(history) == 2
    assert history[0].order is None
    assert history[1].order is not None


def test_report_history_tracks_preparation() -> None:
    engine = prepared_engine()

    assert len(engine.report_history) == 2
    assert (
        engine.report_history[0].message
        == "Execution request received."
    )
    assert (
        engine.report_history[1].message
        == "Execution order prepared."
    )


def test_report_ids_are_deterministic() -> None:
    engine = prepared_engine()

    assert (
        engine.report_history[0].report_id
        == "execution-report-000001"
    )
    assert (
        engine.report_history[1].report_id
        == "execution-report-000002"
    )


def test_orders_for_symbol() -> None:
    engine = prepared_engine()

    orders = engine.orders_for_symbol(
        "NVDA"
    )

    assert len(orders) == 1
    assert orders[0].symbol == "NVDA"


def test_unknown_symbol_returns_empty() -> None:
    engine = prepared_engine()

    assert engine.orders_for_symbol(
        "AAPL"
    ) == ()


def test_report_contains_lineage_metadata() -> None:
    engine, request = started_engine()

    report = engine.get_report(
        request.request_id
    )

    assert report.metadata == (
        ("strategy_id", "strategy-001"),
        ("portfolio_id", "portfolio-001"),
        ("allocation_id", "allocation-001"),
        ("signal_id", "signal-001"),
        ("intent_id", "trade-intent-001"),
        ("plan_id", "order-plan-001"),
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
            "",
            "correlation_id must not be empty",
        ),
        (
            "get_order",
            "",
            "order_id must not be empty",
        ),
        (
            "orders_for_symbol",
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
    engine = EnterpriseExecutionEngine(
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
            "get_order",
            "order_id must be a string",
        ),
        (
            "orders_for_symbol",
            "symbol must be a string",
        ),
    ],
)
def test_identifier_must_be_string(
    method_name: str,
    message: str,
) -> None:
    engine = EnterpriseExecutionEngine(
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
    engine = EnterpriseExecutionEngine(
        clock=lambda: "not-a-datetime",
    )

    request = execution_request()
    engine.register_request(request)

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        engine.start_execution(
            request.request_id
        )


def test_clock_must_return_timezone_aware_datetime() -> None:
    engine = EnterpriseExecutionEngine(
        clock=lambda: datetime(
            2026,
            8,
            11,
            20,
            30,
        ),
    )

    request = execution_request()
    engine.register_request(request)

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a "
            "timezone-aware datetime"
        ),
    ):
        engine.start_execution(
            request.request_id
        )

def submitted_engine(
) -> tuple[
    EnterpriseExecutionEngine,
    ExecutionRequest,
]:
    engine, request = started_engine()

    engine.prepare_order(
        request.request_id
    )

    engine.submit_order(
        request.request_id
    )

    return engine, request


def test_submit_order() -> None:
    engine, request = started_engine()

    prepared = engine.prepare_order(
        request.request_id
    )

    submitted = engine.submit_order(
        request.request_id
    )

    assert (
        submitted.status
        is ExecutionStatus.SUBMITTED
    )

    assert (
        submitted.decision
        is ExecutionDecision.SUBMIT
    )

    assert submitted.order is prepared.order
    assert submitted.message == (
        "Execution order submitted."
    )

    assert (
        submitted.result.started_at
        == prepared.result.started_at
    )
    assert submitted.result.updated_at == NOW


def test_submit_order_updates_current_result() -> None:
    engine = prepared_engine()

    report = engine.submit_order(
        "execution-request-001"
    )

    result = engine.get_result(
        "execution-request-001"
    )

    assert result is report.result
    assert (
        result.status
        is ExecutionStatus.SUBMITTED
    )


def test_submit_order_updates_current_report() -> None:
    engine = prepared_engine()

    report = engine.submit_order(
        "execution-request-001"
    )

    assert (
        engine.get_report(
            "execution-request-001"
        )
        is report
    )


def test_submit_order_preserves_order() -> None:
    engine = prepared_engine()

    order = engine.order_for_request(
        "execution-request-001"
    )

    report = engine.submit_order(
        "execution-request-001"
    )

    assert report.order is order
    assert (
        engine.order_for_request(
            "execution-request-001"
        )
        is order
    )
    assert len(engine.order_history) == 1


def test_submit_order_tracks_result_history() -> None:
    engine = prepared_engine()

    engine.submit_order(
        "execution-request-001"
    )

    history = engine.results_for_request(
        "execution-request-001"
    )

    assert len(history) == 3

    assert (
        history[0].status
        is ExecutionStatus.PENDING
    )
    assert (
        history[1].status
        is ExecutionStatus.READY
    )
    assert (
        history[2].status
        is ExecutionStatus.SUBMITTED
    )


def test_submit_order_tracks_report_history() -> None:
    engine = prepared_engine()

    report = engine.submit_order(
        "execution-request-001"
    )

    assert len(engine.report_history) == 3
    assert engine.report_history[-1] is report

    assert (
        report.report_id
        == "execution-report-000003"
    )


def test_submit_order_is_idempotent() -> None:
    engine = prepared_engine()

    first = engine.submit_order(
        "execution-request-001"
    )

    second = engine.submit_order(
        "execution-request-001"
    )

    assert second is first

    assert len(
        engine.results_for_request(
            "execution-request-001"
        )
    ) == 3

    assert len(engine.report_history) == 3


def test_submit_order_before_preparation_is_rejected() -> None:
    engine, request = started_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "execution request must be READY "
            "before order submission"
        ),
    ):
        engine.submit_order(
            request.request_id
        )


def test_submit_order_for_unstarted_request_is_rejected() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    request = execution_request()

    engine.register_request(request)

    with pytest.raises(
        KeyError,
        match="execution request has no result",
    ):
        engine.submit_order(
            request.request_id
        )


def test_submit_order_for_unknown_request_is_rejected() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        KeyError,
        match="execution request not found",
    ):
        engine.submit_order(
            "execution-request-999"
        )


def test_submit_order_normalizes_request_id() -> None:
    engine = prepared_engine()

    report = engine.submit_order(
        "  execution-request-001  "
    )

    assert (
        report.request_id
        == "execution-request-001"
    )


def test_submit_order_requires_string_request_id() -> None:
    engine = prepared_engine()

    with pytest.raises(
        TypeError,
        match="request_id must be a string",
    ):
        engine.submit_order(123)


def test_submit_order_rejects_empty_request_id() -> None:
    engine = prepared_engine()

    with pytest.raises(
        ValueError,
        match="request_id must not be empty",
    ):
        engine.submit_order("   ")


def test_complete_submission_lifecycle() -> None:
    engine = EnterpriseExecutionEngine(
        clock=fixed_clock,
    )

    request = execution_request()

    engine.register_request(request)

    pending = engine.start_execution(
        request.request_id
    )

    ready = engine.prepare_order(
        request.request_id
    )

    submitted = engine.submit_order(
        request.request_id
    )

    assert (
        pending.status
        is ExecutionStatus.PENDING
    )
    assert (
        ready.status
        is ExecutionStatus.READY
    )
    assert (
        submitted.status
        is ExecutionStatus.SUBMITTED
    )

    assert pending.order is None
    assert ready.order is not None
    assert submitted.order is ready.order

    assert len(engine.order_history) == 1
    assert len(engine.report_history) == 3
    assert len(
        engine.results_for_request(
            request.request_id
        )
    ) == 3

def test_record_partial_fill() -> None:
    engine, request = submitted_engine()

    report = engine.record_fill(
        request.request_id,
        fill_quantity=4,
        fill_price=100.0,
    )

    assert (
        report.status
        is ExecutionStatus.PARTIALLY_FILLED
    )
    assert (
        report.decision
        is ExecutionDecision.PROCEED
    )
    assert report.result.filled_quantity == 4
    assert report.result.average_fill_price == 100.0
    assert report.result.remaining_quantity == 6
    assert report.result.completed_at is None


def test_record_full_fill_from_submitted() -> None:
    engine, request = submitted_engine()

    report = engine.record_fill(
        request.request_id,
        fill_quantity=10,
        fill_price=101.25,
    )

    assert (
        report.status
        is ExecutionStatus.FILLED
    )
    assert (
        report.decision
        is ExecutionDecision.NO_ACTION
    )
    assert report.result.filled_quantity == 10
    assert report.result.average_fill_price == 101.25
    assert report.result.remaining_quantity == 0
    assert report.result.completed_at == NOW


def test_record_multiple_partial_fills_uses_weighted_average() -> None:
    engine, request = submitted_engine()

    first = engine.record_fill(
        request.request_id,
        fill_quantity=4,
        fill_price=100.0,
    )

    second = engine.record_fill(
        request.request_id,
        fill_quantity=3,
        fill_price=102.0,
    )

    assert first.result.filled_quantity == 4
    assert second.result.filled_quantity == 7

    expected = (
        (4 * 100.0)
        + (3 * 102.0)
    ) / 7

    assert (
        second.result.average_fill_price
        == pytest.approx(expected)
    )


def test_partial_fill_to_filled() -> None:
    engine, request = submitted_engine()

    engine.record_fill(
        request.request_id,
        fill_quantity=4,
        fill_price=100.0,
    )

    report = engine.record_fill(
        request.request_id,
        fill_quantity=6,
        fill_price=102.0,
    )

    assert (
        report.status
        is ExecutionStatus.FILLED
    )

    expected = (
        (4 * 100.0)
        + (6 * 102.0)
    ) / 10

    assert (
        report.result.average_fill_price
        == pytest.approx(expected)
    )


def test_record_fill_rejects_overfill() -> None:
    engine, request = submitted_engine()

    with pytest.raises(
        ValueError,
        match=(
            "cumulative filled quantity must not "
            "exceed order quantity"
        ),
    ):
        engine.record_fill(
            request.request_id,
            fill_quantity=11,
            fill_price=100.0,
        )


@pytest.mark.parametrize(
    "fill_quantity",
    [0, -1],
)
def test_record_fill_quantity_must_be_positive(
    fill_quantity: int,
) -> None:
    engine, request = submitted_engine()

    with pytest.raises(
        ValueError,
        match="fill_quantity must be positive",
    ):
        engine.record_fill(
            request.request_id,
            fill_quantity=fill_quantity,
            fill_price=100.0,
        )


def test_record_fill_quantity_requires_integer() -> None:
    engine, request = submitted_engine()

    with pytest.raises(
        TypeError,
        match="fill_quantity must be an integer",
    ):
        engine.record_fill(
            request.request_id,
            fill_quantity=1.5,
            fill_price=100.0,
        )


@pytest.mark.parametrize(
    "fill_price",
    [0, -1],
)
def test_record_fill_price_must_be_positive(
    fill_price: int,
) -> None:
    engine, request = submitted_engine()

    with pytest.raises(
        ValueError,
        match="fill_price must be positive",
    ):
        engine.record_fill(
            request.request_id,
            fill_quantity=1,
            fill_price=fill_price,
        )


def test_record_fill_price_requires_number() -> None:
    engine, request = submitted_engine()

    with pytest.raises(
        TypeError,
        match="fill_price must be a number",
    ):
        engine.record_fill(
            request.request_id,
            fill_quantity=1,
            fill_price="100",
        )


def test_record_fill_before_submission_is_rejected() -> None:
    engine = prepared_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "execution request must be SUBMITTED "
            "or PARTIALLY_FILLED before recording fills"
        ),
    ):
        engine.record_fill(
            "execution-request-001",
            fill_quantity=1,
            fill_price=100.0,
        )


def test_filled_request_cannot_receive_more_fills() -> None:
    engine, request = submitted_engine()

    engine.record_fill(
        request.request_id,
        fill_quantity=10,
        fill_price=100.0,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal execution requests "
            "cannot record fills"
        ),
    ):
        engine.record_fill(
            request.request_id,
            fill_quantity=1,
            fill_price=100.0,
        )

def test_cancel_execution() -> None:
    engine, request = submitted_engine()

    report = engine.cancel_execution(
        request.request_id,
        reason="Execution cancelled by strategy.",
    )

    assert (
        report.status
        is ExecutionStatus.CANCELLED
    )
    assert (
        report.decision
        is ExecutionDecision.CANCEL
    )
    assert report.result.completed_at == NOW
    assert report.message == (
        "Execution cancelled by strategy."
    )


def test_reject_execution() -> None:
    engine, request = submitted_engine()

    report = engine.reject_execution(
        request.request_id,
        reason="Broker rejected execution.",
    )

    assert (
        report.status
        is ExecutionStatus.REJECTED
    )
    assert (
        report.decision
        is ExecutionDecision.REJECT
    )
    assert report.result.completed_at == NOW
    assert report.message == (
        "Broker rejected execution."
    )


def test_fail_execution_non_retryable() -> None:
    engine, request = submitted_engine()

    report = engine.fail_execution(
        request.request_id,
        error="Execution dependency failed.",
    )

    assert (
        report.status
        is ExecutionStatus.FAILED
    )
    assert (
        report.decision
        is ExecutionDecision.NO_ACTION
    )
    assert report.result.completed_at == NOW
    assert report.result.error == (
        "Execution dependency failed."
    )


def test_fail_execution_retryable() -> None:
    engine, request = submitted_engine()

    report = engine.fail_execution(
        request.request_id,
        error="Temporary broker outage.",
        retryable=True,
    )

    assert (
        report.status
        is ExecutionStatus.FAILED
    )
    assert (
        report.decision
        is ExecutionDecision.RETRY
    )
    assert report.result.error == (
        "Temporary broker outage."
    )


def test_fail_execution_retryable_requires_bool() -> None:
    engine, request = submitted_engine()

    with pytest.raises(
        TypeError,
        match="retryable must be a bool",
    ):
        engine.fail_execution(
            request.request_id,
            error="Execution failed.",
            retryable=1,
        )


def test_cancel_reason_is_normalized() -> None:
    engine, request = submitted_engine()

    report = engine.cancel_execution(
        request.request_id,
        reason="  Cancelled by strategy.  ",
    )

    assert report.message == (
        "Cancelled by strategy."
    )


def test_reject_reason_is_normalized() -> None:
    engine, request = submitted_engine()

    report = engine.reject_execution(
        request.request_id,
        reason="  Broker rejected order.  ",
    )

    assert report.message == (
        "Broker rejected order."
    )


def test_fail_error_is_normalized() -> None:
    engine, request = submitted_engine()

    report = engine.fail_execution(
        request.request_id,
        error="  Broker unavailable.  ",
    )

    assert report.result.error == (
        "Broker unavailable."
    )
    assert report.message == (
        "Broker unavailable."
    )


@pytest.mark.parametrize(
    "method_name",
    [
        "cancel_execution",
        "reject_execution",
    ],
)
def test_terminal_reason_must_not_be_empty(
    method_name: str,
) -> None:
    engine, request = submitted_engine()

    method = getattr(
        engine,
        method_name,
    )

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        method(
            request.request_id,
            reason="   ",
        )


def test_fail_error_must_not_be_empty() -> None:
    engine, request = submitted_engine()

    with pytest.raises(
        ValueError,
        match="error must not be empty",
    ):
        engine.fail_execution(
            request.request_id,
            error="   ",
        )


def test_terminal_transition_preserves_partial_fill() -> None:
    engine, request = submitted_engine()

    engine.record_fill(
        request.request_id,
        fill_quantity=4,
        fill_price=100.0,
    )

    report = engine.cancel_execution(
        request.request_id,
        reason="Cancel remainder.",
    )

    assert report.result.filled_quantity == 4
    assert report.result.average_fill_price == 100.0
    assert report.result.remaining_quantity == 6


def test_failure_preserves_partial_fill() -> None:
    engine, request = submitted_engine()

    engine.record_fill(
        request.request_id,
        fill_quantity=4,
        fill_price=100.0,
    )

    report = engine.fail_execution(
        request.request_id,
        error="Broker disconnected.",
        retryable=True,
    )

    assert report.result.filled_quantity == 4
    assert report.result.average_fill_price == 100.0
    assert report.result.remaining_quantity == 6


@pytest.mark.parametrize(
    "terminal_action",
    [
        "cancel",
        "reject",
        "fail",
    ],
)
def test_terminal_execution_cannot_receive_more_fills(
    terminal_action: str,
) -> None:
    engine, request = submitted_engine()

    if terminal_action == "cancel":
        engine.cancel_execution(
            request.request_id,
            reason="Cancelled.",
        )
    elif terminal_action == "reject":
        engine.reject_execution(
            request.request_id,
            reason="Rejected.",
        )
    else:
        engine.fail_execution(
            request.request_id,
            error="Failed.",
        )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal execution requests "
            "cannot record fills"
        ),
    ):
        engine.record_fill(
            request.request_id,
            fill_quantity=1,
            fill_price=100.0,
        )


@pytest.mark.parametrize(
    "terminal_action",
    [
        "cancel",
        "reject",
        "fail",
    ],
)
def test_terminal_execution_cannot_transition_again(
    terminal_action: str,
) -> None:
    engine, request = submitted_engine()

    if terminal_action == "cancel":
        engine.cancel_execution(
            request.request_id,
            reason="Cancelled.",
        )
    elif terminal_action == "reject":
        engine.reject_execution(
            request.request_id,
            reason="Rejected.",
        )
    else:
        engine.fail_execution(
            request.request_id,
            error="Failed.",
        )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal execution requests "
            "cannot be modified"
        ),
    ):
        engine.cancel_execution(
            request.request_id,
            reason="Second transition.",
        )


def test_terminal_transition_adds_history_entry() -> None:
    engine, request = submitted_engine()

    before = len(
        engine.results_for_request(
            request.request_id
        )
    )

    report = engine.cancel_execution(
        request.request_id,
        reason="Cancelled.",
    )

    history = engine.results_for_request(
        request.request_id
    )

    assert len(history) == before + 1
    assert history[-1] is report.result
    assert (
        history[-1].status
        is ExecutionStatus.CANCELLED
    )


def test_latest_report_tracks_terminal_transition() -> None:
    engine, request = submitted_engine()

    report = engine.reject_execution(
        request.request_id,
        reason="Rejected.",
    )

    assert engine.latest_report() is report
    assert (
        engine.get_report(
            request.request_id
        )
        is report
    )


def test_complete_cancelled_execution_lifecycle() -> None:
    engine, request = submitted_engine()

    terminal = engine.cancel_execution(
        request.request_id,
        reason="Strategy cancelled execution.",
    )

    assert (
        terminal.status
        is ExecutionStatus.CANCELLED
    )
    assert terminal.order is not None
    assert terminal.result.completed_at == NOW


def test_complete_failed_execution_lifecycle() -> None:
    engine, request = submitted_engine()

    terminal = engine.fail_execution(
        request.request_id,
        error="Broker unavailable.",
        retryable=True,
    )

    assert (
        terminal.status
        is ExecutionStatus.FAILED
    )
    assert (
        terminal.decision
        is ExecutionDecision.RETRY
    )
    assert terminal.order is not None
    assert terminal.result.completed_at == NOW

def test_partial_fill_history_is_cumulative() -> None:
    engine, request = submitted_engine()

    first = engine.record_fill(
        request.request_id,
        fill_quantity=2,
        fill_price=100.0,
    )

    second = engine.record_fill(
        request.request_id,
        fill_quantity=3,
        fill_price=102.0,
    )

    third = engine.record_fill(
        request.request_id,
        fill_quantity=1,
        fill_price=99.0,
    )

    assert first.result.filled_quantity == 2
    assert second.result.filled_quantity == 5
    assert third.result.filled_quantity == 6

    history = engine.results_for_request(
        request.request_id
    )

    assert tuple(
        result.filled_quantity
        for result in history[-3:]
    ) == (
        2,
        5,
        6,
    )


def test_partial_fill_preserves_single_order_identity() -> None:
    engine, request = submitted_engine()

    order = engine.order_for_request(
        request.request_id
    )

    first = engine.record_fill(
        request.request_id,
        fill_quantity=2,
        fill_price=100.0,
    )

    second = engine.record_fill(
        request.request_id,
        fill_quantity=3,
        fill_price=101.0,
    )

    assert first.order is order
    assert second.order is order
    assert len(engine.order_history) == 1


def test_fill_report_ids_remain_deterministic() -> None:
    engine, request = submitted_engine()

    first = engine.record_fill(
        request.request_id,
        fill_quantity=2,
        fill_price=100.0,
    )

    second = engine.record_fill(
        request.request_id,
        fill_quantity=8,
        fill_price=101.0,
    )

    assert (
        first.report_id
        == "execution-report-000004"
    )

    assert (
        second.report_id
        == "execution-report-000005"
    )


def test_weighted_average_fill_price_is_stable() -> None:
    engine, request = submitted_engine()

    engine.record_fill(
        request.request_id,
        fill_quantity=1,
        fill_price=100.10,
    )

    engine.record_fill(
        request.request_id,
        fill_quantity=2,
        fill_price=100.20,
    )

    report = engine.record_fill(
        request.request_id,
        fill_quantity=7,
        fill_price=100.30,
    )

    expected = (
        (1 * 100.10)
        + (2 * 100.20)
        + (7 * 100.30)
    ) / 10

    assert (
        report.result.average_fill_price
        == pytest.approx(expected)
    )


def test_zero_state_is_preserved_before_first_fill() -> None:
    engine, request = submitted_engine()

    result = engine.get_result(
        request.request_id
    )

    assert result.filled_quantity == 0
    assert result.average_fill_price is None
    assert result.remaining_quantity == 10


def test_fill_after_cancel_is_rejected() -> None:
    engine, request = submitted_engine()

    engine.cancel_execution(
        request.request_id,
        reason="Cancelled.",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal execution requests "
            "cannot record fills"
        ),
    ):
        engine.record_fill(
            request.request_id,
            fill_quantity=1,
            fill_price=100.0,
        )


def test_fill_after_rejection_is_rejected() -> None:
    engine, request = submitted_engine()

    engine.reject_execution(
        request.request_id,
        reason="Rejected.",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal execution requests "
            "cannot record fills"
        ),
    ):
        engine.record_fill(
            request.request_id,
            fill_quantity=1,
            fill_price=100.0,
        )


def test_fill_after_failure_is_rejected() -> None:
    engine, request = submitted_engine()

    engine.fail_execution(
        request.request_id,
        error="Failed.",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal execution requests "
            "cannot record fills"
        ),
    ):
        engine.record_fill(
            request.request_id,
            fill_quantity=1,
            fill_price=100.0,
        )


def test_fill_after_full_fill_is_rejected() -> None:
    engine, request = submitted_engine()

    engine.record_fill(
        request.request_id,
        fill_quantity=10,
        fill_price=100.0,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal execution requests "
            "cannot record fills"
        ),
    ):
        engine.record_fill(
            request.request_id,
            fill_quantity=1,
            fill_price=100.0,
        )


@pytest.mark.parametrize(
    "terminal_method",
    [
        "cancel_execution",
        "reject_execution",
    ],
)
def test_terminal_transition_after_fill_is_rejected(
    terminal_method: str,
) -> None:
    engine, request = submitted_engine()

    engine.record_fill(
        request.request_id,
        fill_quantity=10,
        fill_price=100.0,
    )

    method = getattr(
        engine,
        terminal_method,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal execution requests "
            "cannot be modified"
        ),
    ):
        method(
            request.request_id,
            reason="Late transition.",
        )


def test_failure_after_fill_is_rejected() -> None:
    engine, request = submitted_engine()

    engine.record_fill(
        request.request_id,
        fill_quantity=10,
        fill_price=100.0,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal execution requests "
            "cannot be modified"
        ),
    ):
        engine.fail_execution(
            request.request_id,
            error="Late failure.",
        )


def test_cancel_preserves_order_identity() -> None:
    engine, request = submitted_engine()

    order = engine.order_for_request(
        request.request_id
    )

    report = engine.cancel_execution(
        request.request_id,
        reason="Cancelled.",
    )

    assert report.order is order
    assert (
        engine.order_for_request(
            request.request_id
        )
        is order
    )


def test_reject_preserves_order_identity() -> None:
    engine, request = submitted_engine()

    order = engine.order_for_request(
        request.request_id
    )

    report = engine.reject_execution(
        request.request_id,
        reason="Rejected.",
    )

    assert report.order is order


def test_failure_preserves_order_identity() -> None:
    engine, request = submitted_engine()

    order = engine.order_for_request(
        request.request_id
    )

    report = engine.fail_execution(
        request.request_id,
        error="Failed.",
    )

    assert report.order is order


def test_partial_fill_then_cancel_history() -> None:
    engine, request = submitted_engine()

    engine.record_fill(
        request.request_id,
        fill_quantity=4,
        fill_price=100.0,
    )

    engine.cancel_execution(
        request.request_id,
        reason="Cancel remainder.",
    )

    history = engine.results_for_request(
        request.request_id
    )

    assert tuple(
        result.status
        for result in history
    ) == (
        ExecutionStatus.PENDING,
        ExecutionStatus.READY,
        ExecutionStatus.SUBMITTED,
        ExecutionStatus.PARTIALLY_FILLED,
        ExecutionStatus.CANCELLED,
    )


def test_partial_fill_then_failure_history() -> None:
    engine, request = submitted_engine()

    engine.record_fill(
        request.request_id,
        fill_quantity=4,
        fill_price=100.0,
    )

    engine.fail_execution(
        request.request_id,
        error="Broker disconnected.",
        retryable=True,
    )

    history = engine.results_for_request(
        request.request_id
    )

    assert tuple(
        result.status
        for result in history
    ) == (
        ExecutionStatus.PENDING,
        ExecutionStatus.READY,
        ExecutionStatus.SUBMITTED,
        ExecutionStatus.PARTIALLY_FILLED,
        ExecutionStatus.FAILED,
    )


def test_final_fill_completes_only_once() -> None:
    engine, request = submitted_engine()

    engine.record_fill(
        request.request_id,
        fill_quantity=5,
        fill_price=100.0,
    )

    final = engine.record_fill(
        request.request_id,
        fill_quantity=5,
        fill_price=101.0,
    )

    assert final.result.completed_at == NOW

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal execution requests "
            "cannot record fills"
        ),
    ):
        engine.record_fill(
            request.request_id,
            fill_quantity=1,
            fill_price=100.0,
        )


def test_terminal_result_is_latest_result() -> None:
    engine, request = submitted_engine()

    report = engine.cancel_execution(
        request.request_id,
        reason="Cancelled.",
    )

    assert (
        engine.get_result(
            request.request_id
        )
        is report.result
    )


def test_terminal_report_is_latest_report() -> None:
    engine, request = submitted_engine()

    report = engine.fail_execution(
        request.request_id,
        error="Failed.",
    )

    assert (
        engine.get_report(
            request.request_id
        )
        is report
    )

    assert engine.latest_report() is report


def test_result_history_objects_remain_immutable() -> None:
    engine, request = submitted_engine()

    before = engine.get_result(
        request.request_id
    )

    engine.record_fill(
        request.request_id,
        fill_quantity=4,
        fill_price=100.0,
    )

    after = engine.get_result(
        request.request_id
    )

    assert before is not after
    assert before.filled_quantity == 0
    assert after.filled_quantity == 4


def test_report_history_objects_remain_immutable() -> None:
    engine, request = submitted_engine()

    before = engine.get_report(
        request.request_id
    )

    engine.record_fill(
        request.request_id,
        fill_quantity=4,
        fill_price=100.0,
    )

    after = engine.get_report(
        request.request_id
    )

    assert before is not after
    assert (
        before.status
        is ExecutionStatus.SUBMITTED
    )
    assert (
        after.status
        is ExecutionStatus.PARTIALLY_FILLED
    )


def test_order_history_does_not_duplicate_across_lifecycle() -> None:
    engine, request = submitted_engine()

    engine.record_fill(
        request.request_id,
        fill_quantity=4,
        fill_price=100.0,
    )

    engine.record_fill(
        request.request_id,
        fill_quantity=6,
        fill_price=101.0,
    )

    assert len(engine.order_history) == 1


def test_complete_multi_fill_execution_lifecycle() -> None:
    engine, request = submitted_engine()

    engine.record_fill(
        request.request_id,
        fill_quantity=2,
        fill_price=100.0,
    )

    engine.record_fill(
        request.request_id,
        fill_quantity=3,
        fill_price=101.0,
    )

    final = engine.record_fill(
        request.request_id,
        fill_quantity=5,
        fill_price=102.0,
    )

    assert (
        final.status
        is ExecutionStatus.FILLED
    )
    assert final.result.filled_quantity == 10
    assert final.result.remaining_quantity == 0
    assert final.result.completed_at == NOW

    expected = (
        (2 * 100.0)
        + (3 * 101.0)
        + (5 * 102.0)
    ) / 10

    assert (
        final.result.average_fill_price
        == pytest.approx(expected)
    )

    assert len(engine.order_history) == 1

    assert tuple(
        result.status
        for result in engine.results_for_request(
            request.request_id
        )
    ) == (
        ExecutionStatus.PENDING,
        ExecutionStatus.READY,
        ExecutionStatus.SUBMITTED,
        ExecutionStatus.PARTIALLY_FILLED,
        ExecutionStatus.PARTIALLY_FILLED,
        ExecutionStatus.FILLED,
    )