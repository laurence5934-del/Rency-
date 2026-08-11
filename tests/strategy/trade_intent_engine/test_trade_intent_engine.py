from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.trade_intent_engine import (
    EnterpriseTradeIntentEngine,
    TradeIntentAction,
    TradeIntentDecision,
    TradeIntentRequest,
    TradeIntentStatus,
    TradeOrderType,
    TradeSide,
    TradeTimeInForce,
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


def trade_intent_request(
    *,
    request_id: str = "request-001",
    correlation_id: str = "correlation-001",
    strategy_id: str = "strategy-001",
    portfolio_id: str = "portfolio-001",
    allocation_id: str = "allocation-001",
    signal_id: str = "signal-001",
    symbol: str = "NVDA",
    action: TradeIntentAction = TradeIntentAction.OPEN,
    side: TradeSide = TradeSide.BUY,
    order_type: TradeOrderType = TradeOrderType.MARKET,
    time_in_force: TradeTimeInForce = TradeTimeInForce.DAY,
    quantity: int = 10,
    confidence: int = 90,
    created_at: datetime = NOW,
    sequence_number: int = 0,
) -> TradeIntentRequest:
    return TradeIntentRequest(
        request_id=request_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        allocation_id=allocation_id,
        signal_id=signal_id,
        symbol=symbol,
        action=action,
        side=side,
        order_type=order_type,
        time_in_force=time_in_force,
        quantity=quantity,
        confidence=confidence,
        created_at=created_at,
        requested_by="strategy-engine",
        sequence_number=sequence_number,
    )

def started_engine(
    *,
    request: TradeIntentRequest | None = None,
) -> tuple[
    EnterpriseTradeIntentEngine,
    TradeIntentRequest,
]:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    value = request or trade_intent_request()

    engine.register_request(value)
    engine.start_evaluation(value.request_id)

    return engine, value


def test_create_trade_intent_engine() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    assert engine.request_ids == ()
    assert engine.intent_ids == ()
    assert engine.report_history == ()


def test_engine_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterpriseTradeIntentEngine(
            clock="not-callable"
        )


def test_register_trade_intent_request() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()

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
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        TypeError,
        match=(
            "request must be a "
            "TradeIntentRequest"
        ),
    ):
        engine.register_request(object())


def test_duplicate_request_id_is_rejected() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    engine.register_request(
        trade_intent_request()
    )

    with pytest.raises(
        ValueError,
        match="request_id is already registered",
    ):
        engine.register_request(
            trade_intent_request(
                correlation_id="correlation-002",
            )
        )


def test_duplicate_correlation_id_is_rejected() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    engine.register_request(
        trade_intent_request()
    )

    with pytest.raises(
        ValueError,
        match=(
            "correlation_id is already registered"
        ),
    ):
        engine.register_request(
            trade_intent_request(
                request_id="request-002",
            )
        )


def test_register_multiple_requests() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    first = trade_intent_request()

    second = trade_intent_request(
        request_id="request-002",
        correlation_id="correlation-002",
        allocation_id="allocation-002",
        signal_id="signal-002",
        symbol="AAPL",
    )

    engine.register_request(first)
    engine.register_request(second)

    assert engine.request_ids == (
        "request-001",
        "request-002",
    )


def test_request_ids_are_sorted() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    engine.register_request(
        trade_intent_request(
            request_id="request-003",
            correlation_id="correlation-003",
        )
    )

    engine.register_request(
        trade_intent_request(
            request_id="request-001",
            correlation_id="correlation-001",
        )
    )

    engine.register_request(
        trade_intent_request(
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
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
    engine.register_request(request)

    assert engine.get_request(
        "  request-001  "
    ) is request


def test_get_unknown_request_is_rejected() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        KeyError,
        match="trade intent request not found",
    ):
        engine.get_request("request-999")


def test_request_for_correlation() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
    engine.register_request(request)

    assert engine.request_for_correlation(
        "correlation-001"
    ) is request


def test_request_for_correlation_normalizes_identifier() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
    engine.register_request(request)

    assert engine.request_for_correlation(
        "  correlation-001  "
    ) is request


def test_unknown_correlation_is_rejected() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        KeyError,
        match=(
            "trade intent request not found for "
            "correlation_id"
        ),
    ):
        engine.request_for_correlation(
            "correlation-999"
        )


def test_unregister_request() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
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
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
    engine.register_request(request)

    assert engine.unregister_request(
        "  request-001  "
    ) is request


def test_unregister_releases_correlation_id() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
    engine.register_request(request)
    engine.unregister_request(
        request.request_id
    )

    replacement = trade_intent_request(
        request_id="request-002",
    )

    engine.register_request(replacement)

    assert (
        engine.request_for_correlation(
            "correlation-001"
        )
        is replacement
    )


def test_start_evaluation() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
    engine.register_request(request)

    report = engine.start_evaluation(
        request.request_id
    )

    assert report.request is request
    assert report.request_id == request.request_id
    assert report.status is TradeIntentStatus.ACTIVE
    assert (
        report.decision
        is TradeIntentDecision.PROCEED
    )
    assert report.intent is None
    assert report.message == (
        "Trade intent evaluation started."
    )

    result = engine.get_result(
        request.request_id
    )

    assert result.status is TradeIntentStatus.ACTIVE
    assert (
        result.decision
        is TradeIntentDecision.PROCEED
    )
    assert result.started_at == NOW
    assert result.updated_at == NOW


def test_start_evaluation_normalizes_identifier() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
    engine.register_request(request)

    report = engine.start_evaluation(
        "  request-001  "
    )

    assert report.request_id == "request-001"


def test_start_evaluation_is_idempotent() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
    engine.register_request(request)

    first = engine.start_evaluation(
        request.request_id
    )

    second = engine.start_evaluation(
        request.request_id
    )

    assert second is first

    assert len(
        engine.results_for_request(
            request.request_id
        )
    ) == 1

    assert len(engine.report_history) == 1


def test_start_unknown_request_is_rejected() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        KeyError,
        match="trade intent request not found",
    ):
        engine.start_evaluation(
            "request-999"
        )


def test_start_time_must_not_precede_request() -> None:
    request = trade_intent_request(
        created_at=(
            NOW + timedelta(seconds=1)
        ),
    )

    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    engine.register_request(request)

    with pytest.raises(
        ValueError,
        match=(
            "trade intent evaluation start time "
            "must not be earlier than request "
            "created_at"
        ),
    ):
        engine.start_evaluation(
            request.request_id
        )


def test_unregister_started_request_is_rejected() -> None:
    engine, request = started_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "started trade intent requests cannot "
            "be unregistered"
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

    assert result.request_id == request.request_id
    assert result.status is TradeIntentStatus.ACTIVE


def test_get_result_normalizes_identifier() -> None:
    engine, _ = started_engine()

    result = engine.get_result(
        "  request-001  "
    )

    assert result.request_id == "request-001"


def test_get_result_before_start_is_rejected() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
    engine.register_request(request)

    with pytest.raises(
        KeyError,
        match=(
            "trade intent request has no result"
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

    assert report.request_id == request.request_id
    assert report.status is TradeIntentStatus.ACTIVE


def test_get_report_before_start_is_rejected() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
    engine.register_request(request)

    with pytest.raises(
        KeyError,
        match=(
            "trade intent request has no report"
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
    assert history[0] is engine.get_result(
        request.request_id
    )


def test_results_for_unstarted_request_returns_empty() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
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
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    with pytest.raises(
        KeyError,
        match=(
            "trade intent engine has no reports"
        ),
    ):
        engine.latest_report()


@pytest.mark.parametrize(
    (
        "method_name",
        "argument",
        "message",
    ),
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
            "get_intent",
            "",
            "intent_id must not be empty",
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
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    method = getattr(engine, method_name)

    with pytest.raises(
        ValueError,
        match=message,
    ):
        method(argument)


@pytest.mark.parametrize(
    (
        "method_name",
        "message",
    ),
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
            "get_intent",
            "intent_id must be a string",
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
            "reports_for_symbol",
            "symbol must be a string",
        ),
    ],
)
def test_identifier_must_be_string(
    method_name: str,
    message: str,
) -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    method = getattr(engine, method_name)

    with pytest.raises(
        TypeError,
        match=message,
    ):
        method(123)


def test_clock_must_return_datetime() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=lambda: "not-a-datetime",
    )

    request = trade_intent_request()
    engine.register_request(request)

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        engine.start_evaluation(
            request.request_id
        )


def test_clock_must_return_timezone_aware_datetime() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=lambda: datetime(
            2026,
            8,
            11,
            12,
            0,
        ),
    )

    request = trade_intent_request()
    engine.register_request(request)

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware "
            "datetime"
        ),
    ):
        engine.start_evaluation(
            request.request_id
        )

def generated_engine(
) -> EnterpriseTradeIntentEngine:
    engine, request = started_engine()

    engine.attach_intent(
        request.request_id,
        rationale="Approved allocation supports trade execution.",
    )

    return engine


def approved_engine(
) -> EnterpriseTradeIntentEngine:
    engine = generated_engine()

    engine.approve_request(
        "request-001"
    )

    return engine


def rejected_engine(
) -> EnterpriseTradeIntentEngine:
    engine, request = started_engine()

    engine.reject_request(
        request.request_id,
        reason="Trade intent rejected by policy.",
    )

    return engine


def cancelled_engine(
) -> EnterpriseTradeIntentEngine:
    engine, request = started_engine()

    engine.cancel_request(
        request.request_id,
        reason="Trade intent cancelled.",
    )

    return engine


def failed_engine(
    *,
    retryable: bool = False,
) -> EnterpriseTradeIntentEngine:
    engine, request = started_engine()

    engine.fail_request(
        request.request_id,
        error="Trade intent processing failed.",
        retryable=retryable,
    )

    return engine


def test_attach_intent() -> None:
    engine, request = started_engine()

    report = engine.attach_intent(
        request.request_id,
        rationale="Approved allocation supports trade execution.",
    )

    intent = report.intent

    assert intent is not None
    assert intent.request_id == "request-001"
    assert intent.correlation_id == "correlation-001"
    assert intent.strategy_id == "strategy-001"
    assert intent.portfolio_id == "portfolio-001"
    assert intent.allocation_id == "allocation-001"
    assert intent.signal_id == "signal-001"
    assert intent.symbol == "NVDA"
    assert intent.action is TradeIntentAction.OPEN
    assert intent.side is TradeSide.BUY
    assert intent.order_type is TradeOrderType.MARKET
    assert intent.time_in_force is TradeTimeInForce.DAY
    assert intent.quantity == 10
    assert intent.confidence == 90
    assert intent.generated_at == NOW
    assert intent.rationale == (
        "Approved allocation supports trade execution."
    )

    assert report.status is TradeIntentStatus.ACTIVE
    assert report.decision is TradeIntentDecision.PROCEED
    assert report.message == "Trade intent generated."


def test_attach_intent_requires_started_request() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
    engine.register_request(request)

    with pytest.raises(
        KeyError,
        match="trade intent request has no result",
    ):
        engine.attach_intent(
            request.request_id,
            rationale="Trade intent.",
        )


def test_attach_intent_rejects_duplicate_intent() -> None:
    engine = generated_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "trade intent is already attached to request"
        ),
    ):
        engine.attach_intent(
            "request-001",
            rationale="Duplicate trade intent.",
        )


def test_intent_generation_time_must_follow_update() -> None:
    times = iter(
        [
            NOW,
            NOW - timedelta(seconds=1),
        ]
    )

    engine = EnterpriseTradeIntentEngine(
        clock=lambda: next(times)
    )

    request = trade_intent_request()
    engine.register_request(request)
    engine.start_evaluation(request.request_id)

    with pytest.raises(
        ValueError,
        match=(
            "trade intent generation time must not be "
            "earlier than latest result update"
        ),
    ):
        engine.attach_intent(
            request.request_id,
            rationale="Trade intent.",
        )


def test_intent_ids_are_deterministic() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    first = trade_intent_request(
        request_id="request-001",
        correlation_id="correlation-001",
        allocation_id="allocation-001",
        signal_id="signal-001",
    )

    second = trade_intent_request(
        request_id="request-002",
        correlation_id="correlation-002",
        allocation_id="allocation-002",
        signal_id="signal-002",
        symbol="AAPL",
    )

    engine.register_request(first)
    engine.start_evaluation(first.request_id)
    first_report = engine.attach_intent(
        first.request_id,
        rationale="First intent.",
    )

    engine.register_request(second)
    engine.start_evaluation(second.request_id)
    second_report = engine.attach_intent(
        second.request_id,
        rationale="Second intent.",
    )

    assert first_report.intent is not None
    assert second_report.intent is not None

    assert first_report.intent.intent_id == (
        "trade-intent-000001"
    )
    assert second_report.intent.intent_id == (
        "trade-intent-000002"
    )


def test_get_intent() -> None:
    engine = generated_engine()

    intent = engine.intent_for_request(
        "request-001"
    )

    assert engine.get_intent(
        intent.intent_id
    ) is intent


def test_get_intent_normalizes_identifier() -> None:
    engine = generated_engine()

    intent = engine.intent_for_request(
        "request-001"
    )

    assert engine.get_intent(
        f"  {intent.intent_id}  "
    ) is intent


def test_get_unknown_intent_is_rejected() -> None:
    engine = generated_engine()

    with pytest.raises(
        KeyError,
        match="trade intent not found",
    ):
        engine.get_intent(
            "trade-intent-999999"
        )


def test_intent_for_request() -> None:
    engine = generated_engine()

    intent = engine.intent_for_request(
        "request-001"
    )

    assert intent.request_id == "request-001"


def test_intent_for_request_before_generation_is_rejected() -> None:
    engine, request = started_engine()

    with pytest.raises(
        KeyError,
        match=(
            "trade intent request has no intent"
        ),
    ):
        engine.intent_for_request(
            request.request_id
        )


def test_intent_ids_property() -> None:
    engine = generated_engine()

    assert engine.intent_ids == (
        "trade-intent-000001",
    )


def test_result_history_tracks_intent_generation() -> None:
    engine = generated_engine()

    history = engine.results_for_request(
        "request-001"
    )

    assert len(history) == 2
    assert history[0].intent is None
    assert history[1].intent is not None


def test_report_history_tracks_intent_generation() -> None:
    engine = generated_engine()

    assert len(engine.report_history) == 2

    assert engine.report_history[0].message == (
        "Trade intent evaluation started."
    )

    assert engine.report_history[1].message == (
        "Trade intent generated."
    )


def test_report_ids_are_deterministic() -> None:
    engine = generated_engine()

    assert engine.report_history[0].report_id == (
        "trade-intent-report-000001"
    )

    assert engine.report_history[1].report_id == (
        "trade-intent-report-000002"
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
        ("symbol", "NVDA"),
    )


def test_approve_request() -> None:
    engine = generated_engine()

    report = engine.approve_request(
        "request-001"
    )

    assert report.status is TradeIntentStatus.APPROVED
    assert report.decision is TradeIntentDecision.APPROVE
    assert report.is_terminal is True
    assert report.intent is not None
    assert report.result.completed_at == NOW
    assert report.message == "Trade intent approved."


def test_approve_request_requires_intent() -> None:
    engine, request = started_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "trade intent request cannot be approved "
            "without an intent"
        ),
    ):
        engine.approve_request(
            request.request_id
        )


def test_approve_message_is_normalized() -> None:
    engine = generated_engine()

    report = engine.approve_request(
        "request-001",
        message="  Approved by execution policy.  ",
    )

    assert report.message == (
        "Approved by execution policy."
    )


def test_approve_message_must_not_be_empty() -> None:
    engine = generated_engine()

    with pytest.raises(
        ValueError,
        match="message must not be empty",
    ):
        engine.approve_request(
            "request-001",
            message="   ",
        )


def test_approval_time_must_follow_latest_update() -> None:
    times = iter(
        [
            NOW,
            NOW + timedelta(seconds=2),
            NOW + timedelta(seconds=1),
        ]
    )

    engine = EnterpriseTradeIntentEngine(
        clock=lambda: next(times)
    )

    request = trade_intent_request()
    engine.register_request(request)
    engine.start_evaluation(request.request_id)

    engine.attach_intent(
        request.request_id,
        rationale="Generated trade intent.",
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


def test_reject_request() -> None:
    engine, request = started_engine()

    report = engine.reject_request(
        request.request_id,
        reason="Trade intent rejected by policy.",
    )

    assert report.status is TradeIntentStatus.REJECTED
    assert report.decision is TradeIntentDecision.REJECT
    assert report.is_terminal is True
    assert report.message == (
        "Trade intent rejected by policy."
    )


def test_reject_request_preserves_intent() -> None:
    engine = generated_engine()

    report = engine.reject_request(
        "request-001",
        reason="Risk policy rejected intent.",
    )

    assert report.intent is not None
    assert report.intent.intent_id == (
        "trade-intent-000001"
    )


def test_reject_reason_is_normalized() -> None:
    engine, request = started_engine()

    report = engine.reject_request(
        request.request_id,
        reason="  Rejected by policy.  ",
    )

    assert report.message == (
        "Rejected by policy."
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
        reason="Trade intent cancelled.",
    )

    assert report.status is TradeIntentStatus.CANCELLED
    assert report.decision is TradeIntentDecision.CANCEL
    assert report.is_terminal is True


def test_cancel_request_preserves_intent() -> None:
    engine = generated_engine()

    report = engine.cancel_request(
        "request-001",
        reason="Intent cancelled before risk routing.",
    )

    assert report.intent is not None


def test_cancel_reason_must_not_be_empty() -> None:
    engine, request = started_engine()

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        engine.cancel_request(
            request.request_id,
            reason="   ",
        )


def test_fail_request_retryable() -> None:
    engine, request = started_engine()

    report = engine.fail_request(
        request.request_id,
        error="Trade intent dependency unavailable.",
        retryable=True,
    )

    assert report.status is TradeIntentStatus.FAILED
    assert report.decision is TradeIntentDecision.RETRY
    assert report.result.error == (
        "Trade intent dependency unavailable."
    )
    assert report.is_terminal is True


def test_fail_request_non_retryable() -> None:
    engine, request = started_engine()

    report = engine.fail_request(
        request.request_id,
        error="Permanent trade intent failure.",
        retryable=False,
    )

    assert report.status is TradeIntentStatus.FAILED
    assert (
        report.decision
        is TradeIntentDecision.NO_ACTION
    )


def test_fail_request_preserves_intent() -> None:
    engine = generated_engine()

    report = engine.fail_request(
        "request-001",
        error="Post-generation validation failed.",
    )

    assert report.intent is not None


def test_fail_request_retryable_requires_bool() -> None:
    engine, request = started_engine()

    with pytest.raises(
        TypeError,
        match="retryable must be a bool",
    ):
        engine.fail_request(
            request.request_id,
            error="Trade intent failed.",
            retryable="yes",
        )


def test_fail_request_error_is_normalized() -> None:
    engine, request = started_engine()

    report = engine.fail_request(
        request.request_id,
        error="  Trade intent failed.  ",
    )

    assert report.result.error == (
        "Trade intent failed."
    )
    assert report.message == (
        "Trade intent failed."
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


def test_failure_time_must_follow_latest_update() -> None:
    times = iter(
        [
            NOW,
            NOW + timedelta(seconds=2),
            NOW + timedelta(seconds=1),
        ]
    )

    engine = EnterpriseTradeIntentEngine(
        clock=lambda: next(times)
    )

    request = trade_intent_request()
    engine.register_request(request)
    engine.start_evaluation(request.request_id)

    engine.attach_intent(
        request.request_id,
        rationale="Generated intent.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "failure time must not be earlier "
            "than latest result update"
        ),
    ):
        engine.fail_request(
            request.request_id,
            error="Trade intent failed.",
        )


def test_terminal_transition_time_must_follow_update() -> None:
    times = iter(
        [
            NOW,
            NOW + timedelta(seconds=2),
            NOW + timedelta(seconds=1),
        ]
    )

    engine = EnterpriseTradeIntentEngine(
        clock=lambda: next(times)
    )

    request = trade_intent_request()
    engine.register_request(request)
    engine.start_evaluation(request.request_id)

    engine.attach_intent(
        request.request_id,
        rationale="Generated intent.",
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


@pytest.mark.parametrize(
    "operation",
    [
        "attach",
        "approve",
        "reject",
        "cancel",
        "fail",
    ],
)
def test_terminal_request_rejects_further_modification(
    operation: str,
) -> None:
    engine = rejected_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal trade intent requests "
            "cannot be modified"
        ),
    ):
        if operation == "attach":
            engine.attach_intent(
                "request-001",
                rationale="Late intent.",
            )
        elif operation == "approve":
            engine.approve_request(
                "request-001"
            )
        elif operation == "reject":
            engine.reject_request(
                "request-001",
                reason="Rejected again.",
            )
        elif operation == "cancel":
            engine.cancel_request(
                "request-001",
                reason="Cancelled later.",
            )
        else:
            engine.fail_request(
                "request-001",
                error="Late failure.",
            )


def test_approval_preserves_warnings() -> None:
    engine, request = started_engine()

    engine.attach_intent(
        request.request_id,
        rationale="Generated intent.",
        warnings=(
            "Spread elevated.",
        ),
    )

    report = engine.approve_request(
        request.request_id
    )

    assert report.warnings == (
        "Spread elevated.",
    )
    assert report.result.warnings == (
        "Spread elevated.",
    )


def test_rejection_preserves_warnings() -> None:
    engine, request = started_engine()

    engine.attach_intent(
        request.request_id,
        rationale="Generated intent.",
        warnings=(
            "Liquidity constrained.",
        ),
    )

    report = engine.reject_request(
        request.request_id,
        reason="Rejected.",
    )

    assert report.warnings == (
        "Liquidity constrained.",
    )


def test_failure_preserves_warnings() -> None:
    engine, request = started_engine()

    engine.attach_intent(
        request.request_id,
        rationale="Generated intent.",
        warnings=(
            "Dependency degraded.",
        ),
    )

    report = engine.fail_request(
        request.request_id,
        error="Dependency failed.",
        retryable=True,
    )

    assert report.warnings == (
        "Dependency degraded.",
    )


def test_result_history_tracks_approval() -> None:
    engine = generated_engine()

    engine.approve_request(
        "request-001"
    )

    history = engine.results_for_request(
        "request-001"
    )

    assert len(history) == 3
    assert history[0].intent is None
    assert history[1].intent is not None
    assert (
        history[2].status
        is TradeIntentStatus.APPROVED
    )


def test_report_history_tracks_approval() -> None:
    engine = generated_engine()

    engine.approve_request(
        "request-001"
    )

    assert len(engine.report_history) == 3
    assert (
        engine.report_history[-1].status
        is TradeIntentStatus.APPROVED
    )

    assert engine.report_history[-1].report_id == (
        "trade-intent-report-000003"
    )


def test_latest_report_tracks_terminal_state() -> None:
    engine = generated_engine()

    expected = engine.approve_request(
        "request-001"
    )

    assert engine.latest_report() is expected
    assert engine.get_report(
        "request-001"
    ) is expected


def test_report_and_result_histories_remain_aligned() -> None:
    engine = generated_engine()

    engine.fail_request(
        "request-001",
        error="Dependency failed.",
        retryable=True,
    )

    results = engine.results_for_request(
        "request-001"
    )

    reports = tuple(
        report
        for report in engine.report_history
        if report.request_id == "request-001"
    )

    assert tuple(
        report.result
        for report in reports
    ) == results


def test_intent_lookup_survives_terminal_state() -> None:
    engine = approved_engine()

    intent = engine.intent_for_request(
        "request-001"
    )

    assert intent.intent_id == (
        "trade-intent-000001"
    )

    assert engine.get_intent(
        intent.intent_id
    ) is intent


def test_terminal_request_cannot_be_unregistered() -> None:
    engine = rejected_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "started trade intent requests cannot be "
            "unregistered"
        ),
    ):
        engine.unregister_request(
            "request-001"
        )


def test_full_successful_trade_intent_lifecycle() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
    engine.register_request(request)

    started = engine.start_evaluation(
        request.request_id
    )

    generated = engine.attach_intent(
        request.request_id,
        rationale=(
            "Approved portfolio allocation "
            "supports order construction."
        ),
        expires_at=(
            NOW + timedelta(minutes=5)
        ),
    )

    approved = engine.approve_request(
        request.request_id
    )

    assert started.status is TradeIntentStatus.ACTIVE
    assert started.intent is None

    assert generated.status is TradeIntentStatus.ACTIVE
    assert generated.intent is not None

    assert (
        approved.status
        is TradeIntentStatus.APPROVED
    )
    assert approved.is_terminal is True
    assert approved.intent is not None

    assert len(
        engine.results_for_request(
            request.request_id
        )
    ) == 3

    assert len(engine.report_history) == 3
    assert len(engine.intent_ids) == 1


def test_full_rejected_trade_intent_lifecycle() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
    engine.register_request(request)

    engine.start_evaluation(
        request.request_id
    )

    generated = engine.attach_intent(
        request.request_id,
        rationale="Candidate trade intent.",
    )

    rejected = engine.reject_request(
        request.request_id,
        reason="Execution policy rejected candidate.",
    )

    assert generated.intent is not None
    assert rejected.intent is not None

    assert (
        rejected.status
        is TradeIntentStatus.REJECTED
    )

    assert rejected.is_terminal is True


def test_full_failed_trade_intent_lifecycle() -> None:
    engine = EnterpriseTradeIntentEngine(
        clock=fixed_clock,
    )

    request = trade_intent_request()
    engine.register_request(request)

    engine.start_evaluation(
        request.request_id
    )

    failed = engine.fail_request(
        request.request_id,
        error="Trade intent dependency failed.",
        retryable=True,
    )

    assert failed.status is TradeIntentStatus.FAILED
    assert failed.decision is TradeIntentDecision.RETRY
    assert failed.result.error == (
        "Trade intent dependency failed."
    )
    assert failed.intent is None
    assert failed.is_terminal is True