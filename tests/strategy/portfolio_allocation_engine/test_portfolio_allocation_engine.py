from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.portfolio_allocation_engine import (
    AllocationAction,
    AllocationDecision,
    AllocationDirection,
    AllocationStatus,
    AllocationStrength,
    EnterprisePortfolioAllocationEngine,
    PortfolioAllocationRequest,
)


NOW = datetime(
    2026,
    8,
    11,
    3,
    30,
    tzinfo=timezone.utc,
)


def clock_at(value: datetime):
    return lambda: value


def allocation_request(
    *,
    request_id: str = "request-001",
    correlation_id: str = "correlation-001",
    strategy_id: str = "strategy-001",
    portfolio_id: str = "portfolio-001",
    signal_id: str = "signal-001",
    symbol: str = "NVDA",
    created_at: datetime = NOW,
) -> PortfolioAllocationRequest:
    return PortfolioAllocationRequest(
        request_id=request_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        signal_id=signal_id,
        symbol=symbol,
        action=AllocationAction.OPEN,
        direction=AllocationDirection.LONG,
        strength=AllocationStrength.HIGH,
        target_allocation_percent=10,
        confidence=85,
        created_at=created_at,
        sequence_number=1,
        requested_by="strategy-signal-engine",
        metadata=(
            ("environment", "paper"),
        ),
    )


def started_engine(
    *,
    request: PortfolioAllocationRequest | None = None,
    now: datetime = NOW,
) -> EnterprisePortfolioAllocationEngine:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(now)
    )
    engine.register_request(
        request or allocation_request()
    )
    engine.start_evaluation("request-001")
    return engine


def test_create_portfolio_allocation_engine() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    assert engine.request_ids == ()
    assert engine.allocation_ids == ()
    assert engine.report_history == ()


def test_engine_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterprisePortfolioAllocationEngine(
            clock=123
        )


def test_register_allocation_request() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    request = allocation_request()

    returned = engine.register_request(request)

    assert returned is request
    assert engine.request_ids == ("request-001",)


def test_register_request_requires_model() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    with pytest.raises(
        TypeError,
        match=(
            "request must be a "
            "PortfolioAllocationRequest"
        ),
    ):
        engine.register_request(object())


def test_duplicate_request_id_is_rejected() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    engine.register_request(allocation_request())

    with pytest.raises(
        ValueError,
        match="request_id is already registered",
    ):
        engine.register_request(
            allocation_request(
                correlation_id="correlation-002",
            )
        )


def test_duplicate_correlation_id_is_rejected() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    engine.register_request(allocation_request())

    with pytest.raises(
        ValueError,
        match="correlation_id is already registered",
    ):
        engine.register_request(
            allocation_request(
                request_id="request-002",
            )
        )


def test_register_multiple_allocation_requests() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    engine.register_request(
        allocation_request(
            request_id="request-002",
            correlation_id="correlation-002",
        )
    )
    engine.register_request(
        allocation_request(
            request_id="request-001",
            correlation_id="correlation-001",
        )
    )

    assert engine.request_ids == (
        "request-001",
        "request-002",
    )


def test_request_ids_are_sorted() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    for request_id, correlation_id in (
        ("request-003", "correlation-003"),
        ("request-001", "correlation-001"),
        ("request-002", "correlation-002"),
    ):
        engine.register_request(
            allocation_request(
                request_id=request_id,
                correlation_id=correlation_id,
            )
        )

    assert engine.request_ids == (
        "request-001",
        "request-002",
        "request-003",
    )


def test_unregister_request() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    request = allocation_request()

    engine.register_request(request)

    returned = engine.unregister_request(
        "request-001"
    )

    assert returned is request
    assert engine.request_ids == ()


def test_unregister_request_normalizes_identifier() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    engine.register_request(allocation_request())

    returned = engine.unregister_request(
        "  request-001  "
    )

    assert returned.request_id == "request-001"


def test_unregister_unknown_request_is_rejected() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    with pytest.raises(KeyError):
        engine.unregister_request("unknown")


def test_unregister_started_request_is_rejected() -> None:
    engine = started_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "started allocation requests cannot "
            "be unregistered"
        ),
    ):
        engine.unregister_request("request-001")


def test_unregister_releases_correlation_id() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    engine.register_request(allocation_request())
    engine.unregister_request("request-001")

    replacement = allocation_request(
        request_id="request-002",
        correlation_id="correlation-001",
    )

    engine.register_request(replacement)

    assert (
        engine.request_for_correlation(
            "correlation-001"
        )
        is replacement
    )


def test_get_request() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    request = allocation_request()

    engine.register_request(request)

    assert engine.get_request("request-001") is request


def test_get_request_normalizes_identifier() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    request = allocation_request()

    engine.register_request(request)

    assert (
        engine.get_request("  request-001  ")
        is request
    )


def test_get_unknown_request_is_rejected() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    with pytest.raises(
        KeyError,
        match="portfolio allocation request not found",
    ):
        engine.get_request("unknown")


def test_request_for_correlation() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    request = allocation_request()

    engine.register_request(request)

    assert (
        engine.request_for_correlation(
            "correlation-001"
        )
        is request
    )


def test_request_for_correlation_normalizes_identifier(
) -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    request = allocation_request()

    engine.register_request(request)

    assert (
        engine.request_for_correlation(
            "  correlation-001  "
        )
        is request
    )


def test_unknown_correlation_is_rejected() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    with pytest.raises(
        KeyError,
        match=(
            "portfolio allocation request not found "
            "for correlation_id"
        ),
    ):
        engine.request_for_correlation("unknown")


def test_start_evaluation() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    request = allocation_request()

    engine.register_request(request)

    report = engine.start_evaluation(
        "request-001"
    )

    assert report.request is request
    assert report.result.status is AllocationStatus.ACTIVE
    assert (
        report.result.decision
        is AllocationDecision.PROCEED
    )
    assert report.result.started_at == NOW
    assert report.result.updated_at == NOW
    assert report.result.completed_at is None
    assert report.message == (
        "Portfolio allocation evaluation started."
    )


def test_start_evaluation_normalizes_identifier() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    engine.register_request(allocation_request())

    report = engine.start_evaluation(
        "  request-001  "
    )

    assert report.request_id == "request-001"


def test_start_evaluation_is_idempotent() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    engine.register_request(allocation_request())

    first = engine.start_evaluation("request-001")
    second = engine.start_evaluation("request-001")

    assert second is first
    assert len(engine.report_history) == 1
    assert len(
        engine.results_for_request("request-001")
    ) == 1


def test_start_unknown_request_is_rejected() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    with pytest.raises(KeyError):
        engine.start_evaluation("unknown")


def test_start_time_must_not_precede_request() -> None:
    request = allocation_request(
        created_at=NOW + timedelta(seconds=1)
    )

    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    engine.register_request(request)

    with pytest.raises(
        ValueError,
        match=(
            "allocation evaluation start time must not "
            "be earlier than request created_at"
        ),
    ):
        engine.start_evaluation("request-001")


def test_get_result() -> None:
    engine = started_engine()

    result = engine.get_result("request-001")

    assert result.status is AllocationStatus.ACTIVE


def test_get_result_normalizes_identifier() -> None:
    engine = started_engine()

    result = engine.get_result(
        "  request-001  "
    )

    assert result.request_id == "request-001"


def test_get_result_before_start_is_rejected() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    engine.register_request(allocation_request())

    with pytest.raises(
        KeyError,
        match=(
            "portfolio allocation request has no result"
        ),
    ):
        engine.get_result("request-001")


def test_get_report() -> None:
    engine = started_engine()

    report = engine.get_report("request-001")

    assert report.request_id == "request-001"


def test_get_report_before_start_is_rejected() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    engine.register_request(allocation_request())

    with pytest.raises(
        KeyError,
        match=(
            "portfolio allocation request has no report"
        ),
    ):
        engine.get_report("request-001")


def test_latest_report() -> None:
    engine = started_engine()

    assert (
        engine.latest_report()
        is engine.get_report("request-001")
    )


def test_latest_report_without_history_is_rejected() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    with pytest.raises(
        KeyError,
        match=(
            "portfolio allocation engine has no reports"
        ),
    ):
        engine.latest_report()


def test_results_for_request() -> None:
    engine = started_engine()

    results = engine.results_for_request(
        "request-001"
    )

    assert len(results) == 1
    assert results[0].status is AllocationStatus.ACTIVE


def test_results_for_unstarted_request_returns_empty() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    engine.register_request(allocation_request())

    assert (
        engine.results_for_request("request-001")
        == ()
    )


def test_attach_allocation() -> None:
    engine = started_engine()

    report = engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
    )

    allocation = report.allocation

    assert allocation is not None
    assert allocation.request_id == "request-001"
    assert allocation.correlation_id == "correlation-001"
    assert allocation.strategy_id == "strategy-001"
    assert allocation.portfolio_id == "portfolio-001"
    assert allocation.signal_id == "signal-001"
    assert allocation.symbol == "NVDA"
    assert allocation.action is AllocationAction.OPEN
    assert (
        allocation.direction
        is AllocationDirection.LONG
    )
    assert (
        allocation.strength
        is AllocationStrength.HIGH
    )
    assert allocation.target_allocation_percent == 10
    assert allocation.confidence == 85
    assert allocation.generated_at == NOW
    assert allocation.rationale == (
        "Portfolio sizing approved."
    )


def test_attach_allocation_requires_started_request() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )
    engine.register_request(allocation_request())

    with pytest.raises(KeyError):
        engine.attach_allocation(
            "request-001",
            rationale="Portfolio sizing approved.",
        )


def test_attach_allocation_rejects_duplicate_allocation() -> None:
    engine = started_engine()

    engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "allocation is already attached to request"
        ),
    ):
        engine.attach_allocation(
            "request-001",
            rationale="Second allocation.",
        )


def test_allocation_generation_time_must_follow_update() -> None:
    times = iter(
        [
            NOW,
            NOW - timedelta(seconds=1),
        ]
    )

    engine = EnterprisePortfolioAllocationEngine(
        clock=lambda: next(times)
    )
    engine.register_request(allocation_request())
    engine.start_evaluation("request-001")

    with pytest.raises(
        ValueError,
        match=(
            "allocation generation time must not be "
            "earlier than latest result update"
        ),
    ):
        engine.attach_allocation(
            "request-001",
            rationale="Portfolio sizing approved.",
        )


def test_allocation_ids_are_deterministic() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    engine.register_request(
        allocation_request(
            request_id="request-001",
            correlation_id="correlation-001",
        )
    )
    engine.start_evaluation("request-001")
    first = engine.attach_allocation(
        "request-001",
        rationale="First allocation.",
    )

    engine.register_request(
        allocation_request(
            request_id="request-002",
            correlation_id="correlation-002",
            signal_id="signal-002",
            symbol="AAPL",
        )
    )
    engine.start_evaluation("request-002")
    second = engine.attach_allocation(
        "request-002",
        rationale="Second allocation.",
    )

    assert first.allocation is not None
    assert second.allocation is not None

    assert first.allocation.allocation_id == (
        "portfolio-allocation-000001"
    )
    assert second.allocation.allocation_id == (
        "portfolio-allocation-000002"
    )


def test_get_allocation() -> None:
    engine = started_engine()

    report = engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
    )

    allocation = report.allocation
    assert allocation is not None

    assert (
        engine.get_allocation(
            allocation.allocation_id
        )
        is allocation
    )


def test_get_allocation_normalizes_identifier() -> None:
    engine = started_engine()

    report = engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
    )

    allocation = report.allocation
    assert allocation is not None

    assert (
        engine.get_allocation(
            f"  {allocation.allocation_id}  "
        )
        is allocation
    )


def test_get_unknown_allocation_is_rejected() -> None:
    engine = started_engine()

    with pytest.raises(
        KeyError,
        match="portfolio allocation not found",
    ):
        engine.get_allocation("unknown")


def test_allocation_for_request() -> None:
    engine = started_engine()

    report = engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
    )

    assert report.allocation is not None

    assert (
        engine.allocation_for_request(
            "request-001"
        )
        is report.allocation
    )


def test_allocation_for_request_before_generation_is_rejected(
) -> None:
    engine = started_engine()

    with pytest.raises(
        KeyError,
        match=(
            "portfolio allocation request has no allocation"
        ),
    ):
        engine.allocation_for_request(
            "request-001"
        )


def test_allocation_ids_property() -> None:
    engine = started_engine()

    report = engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
    )

    assert report.allocation is not None

    assert engine.allocation_ids == (
        report.allocation.allocation_id,
    )


def test_result_history_tracks_allocation_generation() -> None:
    engine = started_engine()

    engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
    )

    history = engine.results_for_request(
        "request-001"
    )

    assert len(history) == 2
    assert history[0].allocation is None
    assert history[1].allocation is not None


def test_report_history_tracks_allocation_generation() -> None:
    engine = started_engine()

    engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
    )

    history = engine.report_history

    assert len(history) == 2
    assert history[0].message == (
        "Portfolio allocation evaluation started."
    )
    assert history[1].message == (
        "Portfolio allocation generated."
    )


def test_report_ids_are_deterministic() -> None:
    engine = started_engine()

    engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
    )

    assert engine.report_history[0].report_id == (
        "portfolio-allocation-report-000001"
    )
    assert engine.report_history[1].report_id == (
        "portfolio-allocation-report-000002"
    )


def test_report_ids_continue_across_requests() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    engine.register_request(
        allocation_request(
            request_id="request-001",
            correlation_id="correlation-001",
        )
    )
    first = engine.start_evaluation("request-001")

    engine.register_request(
        allocation_request(
            request_id="request-002",
            correlation_id="correlation-002",
            strategy_id="strategy-002",
            portfolio_id="portfolio-002",
            signal_id="signal-002",
            symbol="AAPL",
        )
    )
    second = engine.start_evaluation("request-002")

    assert first.report_id == (
        "portfolio-allocation-report-000001"
    )
    assert second.report_id == (
        "portfolio-allocation-report-000002"
    )


def test_reports_for_strategy() -> None:
    engine = started_engine()

    reports = engine.reports_for_strategy(
        "strategy-001"
    )

    assert len(reports) == 1
    assert reports[0].strategy_id == "strategy-001"


def test_reports_for_unknown_strategy_returns_empty() -> None:
    engine = started_engine()

    assert engine.reports_for_strategy(
        "unknown"
    ) == ()


def test_reports_for_portfolio() -> None:
    engine = started_engine()

    reports = engine.reports_for_portfolio(
        "portfolio-001"
    )

    assert len(reports) == 1
    assert reports[0].portfolio_id == "portfolio-001"


def test_reports_for_unknown_portfolio_returns_empty() -> None:
    engine = started_engine()

    assert engine.reports_for_portfolio(
        "unknown"
    ) == ()


def test_reports_for_signal() -> None:
    engine = started_engine()

    reports = engine.reports_for_signal(
        "signal-001"
    )

    assert len(reports) == 1
    assert reports[0].signal_id == "signal-001"


def test_reports_for_unknown_signal_returns_empty() -> None:
    engine = started_engine()

    assert engine.reports_for_signal(
        "unknown"
    ) == ()


def test_reports_for_symbol() -> None:
    engine = started_engine()

    reports = engine.reports_for_symbol("NVDA")

    assert len(reports) == 1
    assert reports[0].symbol == "NVDA"


def test_reports_for_symbol_normalizes_symbol() -> None:
    engine = started_engine()

    reports = engine.reports_for_symbol(
        "  nvda  "
    )

    assert len(reports) == 1
    assert reports[0].symbol == "NVDA"


def test_reports_for_unknown_symbol_returns_empty() -> None:
    engine = started_engine()

    assert engine.reports_for_symbol(
        "UNKNOWN"
    ) == ()


def test_report_contains_request_metadata() -> None:
    engine = started_engine()

    report = engine.get_report("request-001")

    assert report.metadata == (
        ("strategy_id", "strategy-001"),
        ("portfolio_id", "portfolio-001"),
        ("signal_id", "signal-001"),
        ("symbol", "NVDA"),
    )


@pytest.mark.parametrize(
    "method_name",
    [
        "get_request",
        "unregister_request",
        "start_evaluation",
        "get_result",
        "get_report",
        "allocation_for_request",
        "results_for_request",
    ],
)
def test_request_identifier_must_not_be_empty(
    method_name: str,
) -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    method = getattr(engine, method_name)

    with pytest.raises(
        ValueError,
        match="request_id must not be empty",
    ):
        method("   ")


def test_request_identifier_must_be_string() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    with pytest.raises(
        TypeError,
        match="request_id must be a string",
    ):
        engine.get_request(123)


def test_correlation_identifier_must_not_be_empty() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    with pytest.raises(
        ValueError,
        match="correlation_id must not be empty",
    ):
        engine.request_for_correlation("   ")


def test_allocation_identifier_must_not_be_empty() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    with pytest.raises(
        ValueError,
        match="allocation_id must not be empty",
    ):
        engine.get_allocation("   ")


@pytest.mark.parametrize(
    ("method_name", "field_name"),
    [
        ("reports_for_strategy", "strategy_id"),
        ("reports_for_portfolio", "portfolio_id"),
        ("reports_for_signal", "signal_id"),
        ("reports_for_symbol", "symbol"),
    ],
)
def test_report_query_identifier_must_not_be_empty(
    method_name: str,
    field_name: str,
) -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    method = getattr(engine, method_name)

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        method("   ")


def test_clock_must_return_datetime() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=lambda: "not-a-datetime"
    )
    engine.register_request(allocation_request())

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        engine.start_evaluation("request-001")


def test_clock_must_return_timezone_aware_datetime() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=lambda: datetime(
            2026,
            8,
            11,
            3,
            30,
        )
    )
    engine.register_request(allocation_request())

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        engine.start_evaluation("request-001")

def generated_engine(
) -> EnterprisePortfolioAllocationEngine:
    engine = started_engine()

    engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
    )

    return engine


def approved_engine(
) -> EnterprisePortfolioAllocationEngine:
    engine = generated_engine()

    engine.approve_request(
        "request-001"
    )

    return engine


def rejected_engine(
) -> EnterprisePortfolioAllocationEngine:
    engine = started_engine()

    engine.reject_request(
        "request-001",
        reason="Allocation policy rejected request.",
    )

    return engine


def cancelled_engine(
) -> EnterprisePortfolioAllocationEngine:
    engine = started_engine()

    engine.cancel_request(
        "request-001",
        reason="Allocation request cancelled.",
    )

    return engine


def failed_engine(
    *,
    retryable: bool = False,
) -> EnterprisePortfolioAllocationEngine:
    engine = started_engine()

    engine.fail_request(
        "request-001",
        error="Allocation evaluation failed.",
        retryable=retryable,
    )

    return engine


def test_approve_request() -> None:
    engine = generated_engine()

    report = engine.approve_request(
        "request-001"
    )

    assert report.status is AllocationStatus.APPROVED
    assert report.decision is AllocationDecision.APPROVE
    assert report.is_terminal is True
    assert report.allocation is not None
    assert report.result.completed_at == NOW
    assert report.message == "Portfolio allocation approved."


def test_approve_request_requires_allocation() -> None:
    engine = started_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "allocation request cannot be approved "
            "without an allocation"
        ),
    ):
        engine.approve_request(
            "request-001"
        )


def test_approval_time_must_follow_latest_update() -> None:
    times = iter(
        [
            NOW,
            NOW + timedelta(seconds=2),
            NOW + timedelta(seconds=1),
        ]
    )

    engine = EnterprisePortfolioAllocationEngine(
        clock=lambda: next(times)
    )
    engine.register_request(allocation_request())
    engine.start_evaluation("request-001")

    engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "approval time must not be earlier "
            "than latest result update"
        ),
    ):
        engine.approve_request(
            "request-001"
        )


def test_approve_message_is_normalized() -> None:
    engine = generated_engine()

    report = engine.approve_request(
        "request-001",
        message="  Approved by allocation policy.  ",
    )

    assert report.message == (
        "Approved by allocation policy."
    )


def test_reject_request() -> None:
    engine = started_engine()

    report = engine.reject_request(
        "request-001",
        reason="Exposure threshold exceeded.",
    )

    assert report.status is AllocationStatus.REJECTED
    assert report.decision is AllocationDecision.REJECT
    assert report.is_terminal is True
    assert report.allocation is None
    assert report.message == (
        "Exposure threshold exceeded."
    )


def test_reject_request_preserves_allocation() -> None:
    engine = generated_engine()

    report = engine.reject_request(
        "request-001",
        reason="Risk policy rejected allocation.",
    )

    assert report.allocation is not None
    assert report.allocation.allocation_id == (
        "portfolio-allocation-000001"
    )


def test_reject_reason_is_normalized() -> None:
    engine = started_engine()

    report = engine.reject_request(
        "request-001",
        reason="  Allocation rejected.  ",
    )

    assert report.message == "Allocation rejected."


def test_reject_reason_must_not_be_empty() -> None:
    engine = started_engine()

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        engine.reject_request(
            "request-001",
            reason="   ",
        )


def test_cancel_request() -> None:
    engine = started_engine()

    report = engine.cancel_request(
        "request-001",
        reason="Supervisor cancelled request.",
    )

    assert report.status is AllocationStatus.CANCELLED
    assert report.decision is AllocationDecision.CANCEL
    assert report.is_terminal is True


def test_cancel_request_preserves_allocation() -> None:
    engine = generated_engine()

    report = engine.cancel_request(
        "request-001",
        reason="Allocation cancelled before execution.",
    )

    assert report.allocation is not None
    assert report.allocation.allocation_id == (
        "portfolio-allocation-000001"
    )


def test_cancel_reason_is_normalized() -> None:
    engine = started_engine()

    report = engine.cancel_request(
        "request-001",
        reason="  Cancelled by supervisor.  ",
    )

    assert report.message == (
        "Cancelled by supervisor."
    )


def test_cancel_reason_must_not_be_empty() -> None:
    engine = started_engine()

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        engine.cancel_request(
            "request-001",
            reason="   ",
        )


def test_fail_request_retryable() -> None:
    engine = started_engine()

    report = engine.fail_request(
        "request-001",
        error="Portfolio service unavailable.",
        retryable=True,
    )

    assert report.status is AllocationStatus.FAILED
    assert report.decision is AllocationDecision.RETRY
    assert report.result.error == (
        "Portfolio service unavailable."
    )
    assert report.is_terminal is True


def test_fail_request_non_retryable() -> None:
    engine = started_engine()

    report = engine.fail_request(
        "request-001",
        error="Permanent allocation failure.",
        retryable=False,
    )

    assert report.status is AllocationStatus.FAILED
    assert (
        report.decision
        is AllocationDecision.NO_ACTION
    )


def test_fail_request_preserves_allocation() -> None:
    engine = generated_engine()

    report = engine.fail_request(
        "request-001",
        error="Post-allocation validation failed.",
    )

    assert report.allocation is not None
    assert report.result.error == (
        "Post-allocation validation failed."
    )


def test_fail_request_retryable_requires_bool() -> None:
    engine = started_engine()

    with pytest.raises(
        TypeError,
        match="retryable must be a bool",
    ):
        engine.fail_request(
            "request-001",
            error="Allocation failed.",
            retryable="yes",
        )


def test_fail_request_error_is_normalized() -> None:
    engine = started_engine()

    report = engine.fail_request(
        "request-001",
        error="  Allocation failed.  ",
    )

    assert report.result.error == "Allocation failed."
    assert report.message == "Allocation failed."


def test_fail_request_error_must_not_be_empty() -> None:
    engine = started_engine()

    with pytest.raises(
        ValueError,
        match="error must not be empty",
    ):
        engine.fail_request(
            "request-001",
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

    engine = EnterprisePortfolioAllocationEngine(
        clock=lambda: next(times)
    )
    engine.register_request(allocation_request())
    engine.start_evaluation("request-001")

    engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "failure time must not be earlier "
            "than latest result update"
        ),
    ):
        engine.fail_request(
            "request-001",
            error="Allocation failed.",
        )


@pytest.mark.parametrize(
    "operation",
    [
        "approve",
        "reject",
        "cancel",
        "fail",
        "attach",
    ],
)
def test_terminal_request_rejects_further_modification(
    operation: str,
) -> None:
    engine = rejected_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal allocation requests cannot be modified"
        ),
    ):
        if operation == "approve":
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
        elif operation == "fail":
            engine.fail_request(
                "request-001",
                error="Failure after terminal state.",
            )
        else:
            engine.attach_allocation(
                "request-001",
                rationale="Late allocation.",
            )


def test_terminal_transition_time_must_follow_update() -> None:
    times = iter(
        [
            NOW,
            NOW + timedelta(seconds=2),
            NOW + timedelta(seconds=1),
        ]
    )

    engine = EnterprisePortfolioAllocationEngine(
        clock=lambda: next(times)
    )
    engine.register_request(allocation_request())
    engine.start_evaluation("request-001")

    engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "terminal transition time must not be "
            "earlier than latest result update"
        ),
    ):
        engine.reject_request(
            "request-001",
            reason="Rejected.",
        )


def test_approve_request_preserves_warnings() -> None:
    engine = started_engine()

    engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
        warnings=(
            "Portfolio concentration elevated.",
        ),
    )

    report = engine.approve_request(
        "request-001"
    )

    assert report.warnings == (
        "Portfolio concentration elevated.",
    )
    assert report.result.warnings == (
        "Portfolio concentration elevated.",
    )


def test_reject_request_preserves_warnings() -> None:
    engine = started_engine()

    engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
        warnings=(
            "Sector exposure elevated.",
        ),
    )

    report = engine.reject_request(
        "request-001",
        reason="Risk rejected allocation.",
    )

    assert report.warnings == (
        "Sector exposure elevated.",
    )


def test_cancel_request_preserves_warnings() -> None:
    engine = started_engine()

    engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
        warnings=(
            "Liquidity lower than ideal.",
        ),
    )

    report = engine.cancel_request(
        "request-001",
        reason="Supervisor cancelled.",
    )

    assert report.warnings == (
        "Liquidity lower than ideal.",
    )


def test_failure_preserves_warnings() -> None:
    engine = started_engine()

    engine.attach_allocation(
        "request-001",
        rationale="Portfolio sizing approved.",
        warnings=(
            "Allocation dependency degraded.",
        ),
    )

    report = engine.fail_request(
        "request-001",
        error="Risk dependency unavailable.",
        retryable=True,
    )

    assert report.warnings == (
        "Allocation dependency degraded.",
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

    assert history[0].status is AllocationStatus.ACTIVE
    assert history[0].allocation is None

    assert history[1].status is AllocationStatus.ACTIVE
    assert history[1].allocation is not None

    assert (
        history[2].status
        is AllocationStatus.APPROVED
    )


def test_report_history_tracks_approval() -> None:
    engine = generated_engine()

    engine.approve_request(
        "request-001"
    )

    assert len(engine.report_history) == 3

    assert (
        engine.report_history[-1].status
        is AllocationStatus.APPROVED
    )

    assert engine.report_history[-1].report_id == (
        "portfolio-allocation-report-000003"
    )


def test_latest_report_tracks_terminal_state() -> None:
    engine = generated_engine()

    expected = engine.approve_request(
        "request-001"
    )

    assert engine.latest_report() == expected
    assert engine.get_report(
        "request-001"
    ) == expected


def test_reports_for_strategy_include_all_states() -> None:
    engine = generated_engine()

    engine.approve_request(
        "request-001"
    )

    reports = engine.reports_for_strategy(
        "strategy-001"
    )

    assert len(reports) == 3
    assert (
        reports[-1].status
        is AllocationStatus.APPROVED
    )


def test_reports_for_portfolio_include_all_states() -> None:
    engine = generated_engine()

    engine.reject_request(
        "request-001",
        reason="Risk rejected allocation.",
    )

    reports = engine.reports_for_portfolio(
        "portfolio-001"
    )

    assert len(reports) == 3
    assert (
        reports[-1].status
        is AllocationStatus.REJECTED
    )


def test_reports_for_signal_include_all_states() -> None:
    engine = generated_engine()

    engine.cancel_request(
        "request-001",
        reason="Supervisor cancelled.",
    )

    reports = engine.reports_for_signal(
        "signal-001"
    )

    assert len(reports) == 3
    assert (
        reports[-1].status
        is AllocationStatus.CANCELLED
    )


def test_reports_for_symbol_include_all_states() -> None:
    engine = generated_engine()

    engine.fail_request(
        "request-001",
        error="Risk dependency unavailable.",
        retryable=True,
    )

    reports = engine.reports_for_symbol(
        "NVDA"
    )

    assert len(reports) == 3
    assert (
        reports[-1].status
        is AllocationStatus.FAILED
    )


def test_report_and_result_histories_remain_aligned(
) -> None:
    engine = generated_engine()

    engine.fail_request(
        "request-001",
        error="Risk dependency unavailable.",
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

    assert len(results) == len(reports)

    assert tuple(
        report.result
        for report in reports
    ) == results


def test_allocation_lookup_survives_terminal_state() -> None:
    engine = approved_engine()

    allocation = engine.allocation_for_request(
        "request-001"
    )

    assert allocation.allocation_id == (
        "portfolio-allocation-000001"
    )

    assert engine.get_allocation(
        "portfolio-allocation-000001"
    ) == allocation


def test_terminal_request_cannot_be_unregistered() -> None:
    engine = rejected_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "started allocation requests cannot be "
            "unregistered"
        ),
    ):
        engine.unregister_request(
            "request-001"
        )


def test_clock_validation_during_allocation_generation() -> None:
    engine = started_engine()

    engine._clock = lambda: "now"

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        engine.attach_allocation(
            "request-001",
            rationale="Portfolio sizing approved.",
        )


def test_clock_validation_during_terminal_transition(
) -> None:
    engine = started_engine()

    engine._clock = lambda: datetime(
        2026,
        8,
        11,
        3,
        30,
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        engine.reject_request(
            "request-001",
            reason="Rejected.",
        )


def test_full_successful_allocation_lifecycle() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    engine.register_request(
        allocation_request()
    )

    started = engine.start_evaluation(
        "request-001"
    )

    generated = engine.attach_allocation(
        "request-001",
        rationale=(
            "Portfolio exposure and sizing "
            "support the allocation."
        ),
        expires_at=(
            NOW + timedelta(minutes=5)
        ),
    )

    approved = engine.approve_request(
        "request-001"
    )

    assert started.status is AllocationStatus.ACTIVE
    assert started.allocation is None

    assert generated.status is AllocationStatus.ACTIVE
    assert generated.allocation is not None

    assert (
        approved.status
        is AllocationStatus.APPROVED
    )
    assert approved.is_terminal is True
    assert approved.allocation is not None

    assert len(
        engine.results_for_request(
            "request-001"
        )
    ) == 3

    assert len(engine.report_history) == 3
    assert len(engine.allocation_ids) == 1


def test_full_rejected_allocation_lifecycle() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    engine.register_request(
        allocation_request()
    )

    engine.start_evaluation(
        "request-001"
    )

    generated = engine.attach_allocation(
        "request-001",
        rationale="Candidate portfolio allocation.",
    )

    rejected = engine.reject_request(
        "request-001",
        reason="Portfolio risk policy rejected candidate.",
    )

    assert generated.allocation is not None

    assert (
        rejected.status
        is AllocationStatus.REJECTED
    )
    assert rejected.allocation is not None
    assert rejected.is_terminal is True


def test_full_failed_allocation_lifecycle() -> None:
    engine = EnterprisePortfolioAllocationEngine(
        clock=clock_at(NOW)
    )

    engine.register_request(
        allocation_request()
    )

    engine.start_evaluation(
        "request-001"
    )

    failed = engine.fail_request(
        "request-001",
        error="Allocation dependency failed.",
        retryable=True,
    )

    assert failed.status is AllocationStatus.FAILED
    assert failed.decision is AllocationDecision.RETRY

    assert failed.result.error == (
        "Allocation dependency failed."
    )

    assert failed.allocation is None
    assert failed.is_terminal is True