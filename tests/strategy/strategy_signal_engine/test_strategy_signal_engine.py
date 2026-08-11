from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.strategy_signal_engine import (
    EnterpriseStrategySignalEngine,
    SignalDecision,
    SignalDirection,
    SignalStatus,
    SignalStrength,
    SignalType,
    StrategySignalRequest,
)


NOW = datetime(
    2026,
    8,
    10,
    22,
    30,
    tzinfo=timezone.utc,
)


class FixedClock:
    def __init__(
        self,
        value: datetime,
    ) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def signal_request(
    *,
    request_id: str = "request-001",
    correlation_id: str = "correlation-001",
    strategy_id: str = "strategy-001",
    portfolio_id: str = "portfolio-001",
    symbol: str = "NVDA",
    signal_type: SignalType = SignalType.ENTRY,
    direction: SignalDirection = SignalDirection.LONG,
    strength: SignalStrength = SignalStrength.STRONG,
    confidence: int = 85,
    market_data_correlation_id: str = (
        "market-correlation-001"
    ),
    created_at: datetime = NOW,
    sequence_number: int = 1,
    requested_by: str = "strategy-engine",
) -> StrategySignalRequest:
    return StrategySignalRequest(
        request_id=request_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        signal_type=signal_type,
        direction=direction,
        strength=strength,
        confidence=confidence,
        market_data_correlation_id=(
            market_data_correlation_id
        ),
        created_at=created_at,
        sequence_number=sequence_number,
        requested_by=requested_by,
        metadata=(
            ("environment", "paper"),
        ),
    )


def engine(
    *,
    current_time: datetime = NOW,
) -> EnterpriseStrategySignalEngine:
    return EnterpriseStrategySignalEngine(
        clock=FixedClock(current_time)
    )


def registered_engine(
) -> EnterpriseStrategySignalEngine:
    value = engine()

    value.register_request(
        signal_request()
    )

    return value


def started_engine(
) -> EnterpriseStrategySignalEngine:
    value = registered_engine()

    value.start_evaluation(
        "request-001"
    )

    return value


def generated_engine(
) -> EnterpriseStrategySignalEngine:
    value = started_engine()

    value.attach_signal(
        "request-001",
        rationale=(
            "Momentum and market context support entry."
        ),
    )

    return value


def test_create_strategy_signal_engine() -> None:
    value = engine()

    assert value.request_ids == ()
    assert value.signal_ids == ()
    assert value.report_history == ()


def test_engine_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterpriseStrategySignalEngine(
            clock=NOW
        )


def test_register_signal_request() -> None:
    value = engine()
    request = signal_request()

    result = value.register_request(
        request
    )

    assert result == request
    assert value.request_ids == (
        "request-001",
    )


def test_register_request_requires_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "request must be a StrategySignalRequest"
        ),
    ):
        engine().register_request(
            object()
        )


def test_duplicate_request_id_is_rejected() -> None:
    value = registered_engine()

    with pytest.raises(
        ValueError,
        match="request_id is already registered",
    ):
        value.register_request(
            signal_request(
                correlation_id="correlation-002",
            )
        )


def test_duplicate_correlation_id_is_rejected() -> None:
    value = registered_engine()

    with pytest.raises(
        ValueError,
        match=(
            "correlation_id is already registered"
        ),
    ):
        value.register_request(
            signal_request(
                request_id="request-002",
            )
        )


def test_register_multiple_signal_requests() -> None:
    value = engine()

    value.register_request(
        signal_request()
    )

    value.register_request(
        signal_request(
            request_id="request-002",
            correlation_id="correlation-002",
            strategy_id="strategy-002",
            portfolio_id="portfolio-002",
            symbol="AAPL",
            market_data_correlation_id=(
                "market-correlation-002"
            ),
            sequence_number=2,
        )
    )

    assert value.request_ids == (
        "request-001",
        "request-002",
    )


def test_request_ids_are_sorted() -> None:
    value = engine()

    value.register_request(
        signal_request(
            request_id="request-002",
            correlation_id="correlation-002",
        )
    )

    value.register_request(
        signal_request(
            request_id="request-001",
            correlation_id="correlation-001",
        )
    )

    assert value.request_ids == (
        "request-001",
        "request-002",
    )


def test_unregister_request() -> None:
    value = registered_engine()

    removed = value.unregister_request(
        "request-001"
    )

    assert removed.request_id == "request-001"
    assert value.request_ids == ()


def test_unregister_request_normalizes_identifier(
) -> None:
    value = registered_engine()

    removed = value.unregister_request(
        "  request-001  "
    )

    assert removed.request_id == "request-001"


def test_unregister_unknown_request_is_rejected(
) -> None:
    with pytest.raises(
        KeyError,
        match=(
            "strategy signal request not found"
        ),
    ):
        engine().unregister_request(
            "missing"
        )


def test_unregister_started_request_is_rejected(
) -> None:
    value = started_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "started signal requests cannot be "
            "unregistered"
        ),
    ):
        value.unregister_request(
            "request-001"
        )


def test_unregister_releases_correlation_id() -> None:
    value = registered_engine()

    value.unregister_request(
        "request-001"
    )

    replacement = value.register_request(
        signal_request(
            request_id="request-002",
            correlation_id="correlation-001",
        )
    )

    assert replacement.request_id == "request-002"


def test_get_request() -> None:
    value = registered_engine()

    request = value.get_request(
        "request-001"
    )

    assert request.request_id == "request-001"
    assert request.strategy_id == "strategy-001"


def test_get_request_normalizes_identifier() -> None:
    value = registered_engine()

    request = value.get_request(
        "  request-001  "
    )

    assert request.request_id == "request-001"


def test_get_unknown_request_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "strategy signal request not found"
        ),
    ):
        engine().get_request(
            "missing"
        )


def test_request_for_correlation() -> None:
    value = registered_engine()

    request = value.request_for_correlation(
        "correlation-001"
    )

    assert request.request_id == "request-001"


def test_request_for_correlation_normalizes_identifier(
) -> None:
    value = registered_engine()

    request = value.request_for_correlation(
        "  correlation-001  "
    )

    assert request.correlation_id == (
        "correlation-001"
    )


def test_unknown_correlation_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "strategy signal request not found for "
            "correlation_id"
        ),
    ):
        engine().request_for_correlation(
            "missing"
        )


def test_start_evaluation() -> None:
    value = registered_engine()

    report = value.start_evaluation(
        "request-001"
    )

    assert report.request_id == "request-001"
    assert report.status is SignalStatus.ACTIVE
    assert report.decision is SignalDecision.PROCEED
    assert report.signal is None
    assert report.is_terminal is False
    assert report.report_id == (
        "strategy-signal-report-000001"
    )
    assert report.reported_at == NOW


def test_start_evaluation_normalizes_identifier(
) -> None:
    value = registered_engine()

    report = value.start_evaluation(
        "  request-001  "
    )

    assert report.request_id == "request-001"


def test_start_evaluation_is_idempotent() -> None:
    value = registered_engine()

    first = value.start_evaluation(
        "request-001"
    )

    second = value.start_evaluation(
        "request-001"
    )

    assert first == second
    assert len(value.report_history) == 1
    assert len(
        value.results_for_request(
            "request-001"
        )
    ) == 1


def test_start_unknown_request_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "strategy signal request not found"
        ),
    ):
        engine().start_evaluation(
            "missing"
        )


def test_start_time_must_not_precede_request() -> None:
    value = engine(
        current_time=NOW
    )

    value.register_request(
        signal_request(
            created_at=(
                NOW + timedelta(seconds=1)
            )
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "signal evaluation start time must not "
            "be earlier than request created_at"
        ),
    ):
        value.start_evaluation(
            "request-001"
        )


def test_get_result() -> None:
    value = started_engine()

    result = value.get_result(
        "request-001"
    )

    assert result.status is SignalStatus.ACTIVE
    assert result.decision is SignalDecision.PROCEED
    assert result.started_at == NOW
    assert result.updated_at == NOW


def test_get_result_normalizes_identifier() -> None:
    value = started_engine()

    result = value.get_result(
        "  request-001  "
    )

    assert result.request_id == "request-001"


def test_get_result_before_start_is_rejected() -> None:
    value = registered_engine()

    with pytest.raises(
        KeyError,
        match=(
            "strategy signal request has no result"
        ),
    ):
        value.get_result(
            "request-001"
        )


def test_get_report() -> None:
    value = started_engine()

    report = value.get_report(
        "request-001"
    )

    assert report.report_id == (
        "strategy-signal-report-000001"
    )
    assert report.status is SignalStatus.ACTIVE


def test_get_report_before_start_is_rejected() -> None:
    value = registered_engine()

    with pytest.raises(
        KeyError,
        match=(
            "strategy signal request has no report"
        ),
    ):
        value.get_report(
            "request-001"
        )


def test_latest_report() -> None:
    value = started_engine()

    latest = value.latest_report()

    assert latest.report_id == (
        "strategy-signal-report-000001"
    )


def test_latest_report_without_history_is_rejected(
) -> None:
    with pytest.raises(
        KeyError,
        match=(
            "strategy signal engine has no reports"
        ),
    ):
        engine().latest_report()


def test_results_for_request() -> None:
    value = started_engine()

    result = value.get_result(
        "request-001"
    )

    assert value.results_for_request(
        "request-001"
    ) == (result,)


def test_results_for_unstarted_request_returns_empty(
) -> None:
    value = registered_engine()

    assert value.results_for_request(
        "request-001"
    ) == ()


def test_attach_signal() -> None:
    value = started_engine()

    report = value.attach_signal(
        "request-001",
        rationale=(
            "Momentum and market context support entry."
        ),
        warnings=(
            "Spread slightly elevated.",
        ),
        metadata=(
            ("model", "momentum-v1"),
        ),
    )

    signal = report.signal

    assert signal is not None
    assert signal.signal_id == (
        "strategy-signal-000001"
    )
    assert signal.request_id == "request-001"
    assert signal.strategy_id == "strategy-001"
    assert signal.portfolio_id == "portfolio-001"
    assert signal.symbol == "NVDA"
    assert signal.signal_type is SignalType.ENTRY
    assert signal.direction is SignalDirection.LONG
    assert signal.strength is SignalStrength.STRONG
    assert signal.confidence == 85

    assert report.status is SignalStatus.ACTIVE
    assert report.decision is SignalDecision.PROCEED
    assert report.warnings == (
        "Spread slightly elevated.",
    )


def test_attach_signal_requires_started_request() -> None:
    value = registered_engine()

    with pytest.raises(
        KeyError,
        match=(
            "strategy signal request has no result"
        ),
    ):
        value.attach_signal(
            "request-001",
            rationale="Momentum confirmed.",
        )


def test_attach_signal_rejects_duplicate_signal() -> None:
    value = generated_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "signal is already attached to request"
        ),
    ):
        value.attach_signal(
            "request-001",
            rationale="Second signal.",
        )


def test_signal_generation_time_must_follow_update(
) -> None:
    clock = FixedClock(NOW)

    value = EnterpriseStrategySignalEngine(
        clock=clock
    )

    value.register_request(
        signal_request()
    )

    value.start_evaluation(
        "request-001"
    )

    clock.value = (
        NOW - timedelta(seconds=1)
    )

    with pytest.raises(
        ValueError,
        match=(
            "signal generation time must not be "
            "earlier than latest result update"
        ),
    ):
        value.attach_signal(
            "request-001",
            rationale="Momentum confirmed.",
        )


def test_signal_ids_are_deterministic() -> None:
    value = engine()

    value.register_request(
        signal_request()
    )
    value.start_evaluation(
        "request-001"
    )

    first = value.attach_signal(
        "request-001",
        rationale="First signal.",
    )

    value.register_request(
        signal_request(
            request_id="request-002",
            correlation_id="correlation-002",
            strategy_id="strategy-002",
            portfolio_id="portfolio-002",
            symbol="AAPL",
            market_data_correlation_id=(
                "market-correlation-002"
            ),
            sequence_number=2,
        )
    )
    value.start_evaluation(
        "request-002"
    )

    second = value.attach_signal(
        "request-002",
        rationale="Second signal.",
    )

    assert first.signal.signal_id == (
        "strategy-signal-000001"
    )
    assert second.signal.signal_id == (
        "strategy-signal-000002"
    )


def test_get_signal() -> None:
    value = generated_engine()

    signal = value.get_signal(
        "strategy-signal-000001"
    )

    assert signal.request_id == "request-001"


def test_get_signal_normalizes_identifier() -> None:
    value = generated_engine()

    signal = value.get_signal(
        "  strategy-signal-000001  "
    )

    assert signal.signal_id == (
        "strategy-signal-000001"
    )


def test_get_unknown_signal_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="strategy signal not found",
    ):
        engine().get_signal(
            "missing"
        )


def test_signal_for_request() -> None:
    value = generated_engine()

    signal = value.signal_for_request(
        "request-001"
    )

    assert signal.signal_id == (
        "strategy-signal-000001"
    )


def test_signal_for_request_before_generation_is_rejected(
) -> None:
    value = started_engine()

    with pytest.raises(
        KeyError,
        match=(
            "strategy signal request has no signal"
        ),
    ):
        value.signal_for_request(
            "request-001"
        )


def test_signal_ids_property() -> None:
    value = generated_engine()

    assert value.signal_ids == (
        "strategy-signal-000001",
    )


def test_result_history_tracks_signal_generation(
) -> None:
    value = generated_engine()

    history = value.results_for_request(
        "request-001"
    )

    assert len(history) == 2
    assert history[0].signal is None
    assert history[1].signal is not None


def test_report_history_tracks_signal_generation(
) -> None:
    value = generated_engine()

    assert len(value.report_history) == 2
    assert value.report_history[0].signal is None
    assert value.report_history[1].signal is not None


def test_report_ids_are_deterministic() -> None:
    value = generated_engine()

    assert value.report_history[0].report_id == (
        "strategy-signal-report-000001"
    )
    assert value.report_history[1].report_id == (
        "strategy-signal-report-000002"
    )


def test_report_ids_continue_across_requests() -> None:
    value = engine()

    value.register_request(
        signal_request()
    )

    first = value.start_evaluation(
        "request-001"
    )

    value.register_request(
        signal_request(
            request_id="request-002",
            correlation_id="correlation-002",
            strategy_id="strategy-002",
            portfolio_id="portfolio-002",
            symbol="AAPL",
            market_data_correlation_id=(
                "market-correlation-002"
            ),
            sequence_number=2,
        )
    )

    second = value.start_evaluation(
        "request-002"
    )

    assert first.report_id == (
        "strategy-signal-report-000001"
    )
    assert second.report_id == (
        "strategy-signal-report-000002"
    )


def test_reports_for_strategy() -> None:
    value = started_engine()

    reports = value.reports_for_strategy(
        "strategy-001"
    )

    assert len(reports) == 1
    assert reports[0].strategy_id == (
        "strategy-001"
    )


def test_reports_for_unknown_strategy_returns_empty(
) -> None:
    assert engine().reports_for_strategy(
        "missing-strategy"
    ) == ()


def test_reports_for_portfolio() -> None:
    value = started_engine()

    reports = value.reports_for_portfolio(
        "portfolio-001"
    )

    assert len(reports) == 1
    assert reports[0].portfolio_id == (
        "portfolio-001"
    )


def test_reports_for_unknown_portfolio_returns_empty(
) -> None:
    assert engine().reports_for_portfolio(
        "missing-portfolio"
    ) == ()


def test_reports_for_symbol() -> None:
    value = started_engine()

    reports = value.reports_for_symbol(
        "NVDA"
    )

    assert len(reports) == 1
    assert reports[0].symbol == "NVDA"


def test_reports_for_symbol_normalizes_symbol() -> None:
    value = started_engine()

    reports = value.reports_for_symbol(
        "  nvda  "
    )

    assert len(reports) == 1
    assert reports[0].symbol == "NVDA"


def test_reports_for_unknown_symbol_returns_empty(
) -> None:
    assert engine().reports_for_symbol(
        "AAPL"
    ) == ()


def test_report_contains_request_metadata() -> None:
    value = started_engine()

    report = value.get_report(
        "request-001"
    )

    assert report.metadata == (
        (
            "strategy_id",
            "strategy-001",
        ),
        (
            "portfolio_id",
            "portfolio-001",
        ),
        (
            "symbol",
            "NVDA",
        ),
    )


def test_request_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="request_id must not be empty",
    ):
        engine().get_request(
            "   "
        )


def test_request_identifier_must_be_string() -> None:
    with pytest.raises(
        TypeError,
        match="request_id must be a string",
    ):
        engine().get_request(
            123
        )


def test_correlation_identifier_must_not_be_empty(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "correlation_id must not be empty"
        ),
    ):
        engine().request_for_correlation(
            "   "
        )


def test_signal_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="signal_id must not be empty",
    ):
        engine().get_signal(
            "   "
        )


def test_strategy_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="strategy_id must not be empty",
    ):
        engine().reports_for_strategy(
            "   "
        )


def test_portfolio_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="portfolio_id must not be empty",
    ):
        engine().reports_for_portfolio(
            "   "
        )


def test_symbol_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="symbol must not be empty",
    ):
        engine().reports_for_symbol(
            "   "
        )


def test_clock_must_return_datetime() -> None:
    value = EnterpriseStrategySignalEngine(
        clock=lambda: "now"
    )

    value.register_request(
        signal_request()
    )

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        value.start_evaluation(
            "request-001"
        )


def test_clock_must_return_timezone_aware_datetime(
) -> None:
    value = EnterpriseStrategySignalEngine(
        clock=lambda: datetime(
            2026,
            8,
            10,
            22,
            30,
        )
    )

    value.register_request(
        signal_request()
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        value.start_evaluation(
            "request-001"
        )
def accepted_engine(
) -> EnterpriseStrategySignalEngine:
    value = generated_engine()

    value.accept_request(
        "request-001"
    )

    return value


def rejected_engine(
) -> EnterpriseStrategySignalEngine:
    value = started_engine()

    value.reject_request(
        "request-001",
        reason="Strategy conditions were not satisfied.",
    )

    return value


def cancelled_engine(
) -> EnterpriseStrategySignalEngine:
    value = started_engine()

    value.cancel_request(
        "request-001",
        reason="Request cancelled by strategy supervisor.",
    )

    return value


def failed_engine(
    *,
    retryable: bool = False,
) -> EnterpriseStrategySignalEngine:
    value = started_engine()

    value.fail_request(
        "request-001",
        error="Signal evaluation failed.",
        retryable=retryable,
    )

    return value


def expiring_engine(
) -> EnterpriseStrategySignalEngine:
    clock = FixedClock(NOW)

    value = EnterpriseStrategySignalEngine(
        clock=clock
    )

    value.register_request(
        signal_request()
    )

    value.start_evaluation(
        "request-001"
    )

    value.attach_signal(
        "request-001",
        rationale="Short-lived momentum opportunity.",
        expires_at=(
            NOW + timedelta(seconds=1)
        ),
    )

    clock.value = (
        NOW + timedelta(seconds=2)
    )

    return value


def test_accept_request() -> None:
    value = generated_engine()

    report = value.accept_request(
        "request-001"
    )

    assert report.status is SignalStatus.ACCEPTED
    assert report.decision is SignalDecision.ACCEPT
    assert report.is_terminal is True
    assert report.signal is not None
    assert report.result.completed_at == NOW
    assert report.message == "Strategy signal accepted."


def test_accept_request_requires_signal() -> None:
    value = started_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "signal request cannot be accepted "
            "without a signal"
        ),
    ):
        value.accept_request(
            "request-001"
        )


def test_acceptance_time_must_follow_latest_update(
) -> None:
    clock = FixedClock(NOW)

    value = EnterpriseStrategySignalEngine(
        clock=clock
    )

    value.register_request(
        signal_request()
    )

    value.start_evaluation(
        "request-001"
    )

    clock.value = (
        NOW + timedelta(seconds=2)
    )

    value.attach_signal(
        "request-001",
        rationale="Momentum confirmed.",
    )

    clock.value = (
        NOW + timedelta(seconds=1)
    )

    with pytest.raises(
        ValueError,
        match=(
            "acceptance time must not be earlier "
            "than latest result update"
        ),
    ):
        value.accept_request(
            "request-001"
        )


def test_accept_message_is_normalized() -> None:
    value = generated_engine()

    report = value.accept_request(
        "request-001",
        message="  Signal accepted by policy.  ",
    )

    assert report.message == (
        "Signal accepted by policy."
    )


def test_reject_request() -> None:
    value = started_engine()

    report = value.reject_request(
        "request-001",
        reason="Confidence below deployment threshold.",
    )

    assert report.status is SignalStatus.REJECTED
    assert report.decision is SignalDecision.REJECT
    assert report.is_terminal is True
    assert report.signal is None
    assert report.message == (
        "Confidence below deployment threshold."
    )


def test_reject_request_preserves_attached_signal(
) -> None:
    value = generated_engine()

    report = value.reject_request(
        "request-001",
        reason="Risk precheck rejected signal.",
    )

    assert report.status is SignalStatus.REJECTED
    assert report.signal is not None
    assert report.signal.signal_id == (
        "strategy-signal-000001"
    )


def test_reject_reason_is_normalized() -> None:
    value = started_engine()

    report = value.reject_request(
        "request-001",
        reason="  Strategy rejected signal.  ",
    )

    assert report.message == (
        "Strategy rejected signal."
    )


def test_reject_reason_must_not_be_empty() -> None:
    value = started_engine()

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        value.reject_request(
            "request-001",
            reason="   ",
        )


def test_cancel_request() -> None:
    value = started_engine()

    report = value.cancel_request(
        "request-001",
        reason="Strategy supervisor cancelled request.",
    )

    assert report.status is SignalStatus.CANCELLED
    assert report.decision is SignalDecision.CANCEL
    assert report.is_terminal is True


def test_cancel_request_preserves_signal() -> None:
    value = generated_engine()

    report = value.cancel_request(
        "request-001",
        reason="Signal cancelled before execution.",
    )

    assert report.signal is not None
    assert report.signal.signal_id == (
        "strategy-signal-000001"
    )


def test_cancel_reason_must_not_be_empty() -> None:
    value = started_engine()

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        value.cancel_request(
            "request-001",
            reason="   ",
        )


def test_expire_request() -> None:
    value = expiring_engine()

    report = value.expire_request(
        "request-001"
    )

    assert report.status is SignalStatus.EXPIRED
    assert report.decision is SignalDecision.NO_ACTION
    assert report.is_terminal is True
    assert report.signal is not None
    assert report.message == "Strategy signal expired."


def test_expire_request_requires_signal() -> None:
    value = started_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "signal request cannot expire "
            "without a signal"
        ),
    ):
        value.expire_request(
            "request-001"
        )


def test_expire_request_rejects_unexpired_signal() -> None:
    clock = FixedClock(NOW)

    value = EnterpriseStrategySignalEngine(
        clock=clock
    )

    value.register_request(
        signal_request()
    )

    value.start_evaluation(
        "request-001"
    )

    value.attach_signal(
        "request-001",
        rationale="Momentum signal.",
        expires_at=(
            NOW + timedelta(minutes=5)
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="strategy signal has not expired",
    ):
        value.expire_request(
            "request-001"
        )


def test_expire_request_without_expiration_is_rejected(
) -> None:
    value = generated_engine()

    with pytest.raises(
        RuntimeError,
        match="strategy signal has not expired",
    ):
        value.expire_request(
            "request-001"
        )


def test_expiration_message_is_normalized() -> None:
    value = expiring_engine()

    report = value.expire_request(
        "request-001",
        message="  Signal lifetime expired.  ",
    )

    assert report.message == (
        "Signal lifetime expired."
    )


def test_fail_request_retryable() -> None:
    value = started_engine()

    report = value.fail_request(
        "request-001",
        error="Strategy dependency unavailable.",
        retryable=True,
    )

    assert report.status is SignalStatus.FAILED
    assert report.decision is SignalDecision.RETRY
    assert report.result.error == (
        "Strategy dependency unavailable."
    )
    assert report.is_terminal is True


def test_fail_request_non_retryable() -> None:
    value = started_engine()

    report = value.fail_request(
        "request-001",
        error="Permanent strategy evaluation failure.",
        retryable=False,
    )

    assert report.status is SignalStatus.FAILED
    assert report.decision is SignalDecision.NO_ACTION


def test_fail_request_preserves_signal() -> None:
    value = generated_engine()

    report = value.fail_request(
        "request-001",
        error="Post-generation validation failed.",
    )

    assert report.signal is not None
    assert report.result.error == (
        "Post-generation validation failed."
    )


def test_fail_request_retryable_requires_bool() -> None:
    value = started_engine()

    with pytest.raises(
        TypeError,
        match="retryable must be a bool",
    ):
        value.fail_request(
            "request-001",
            error="Evaluation failed.",
            retryable="yes",
        )


def test_fail_request_error_is_normalized() -> None:
    value = started_engine()

    report = value.fail_request(
        "request-001",
        error="  Evaluation failed.  ",
    )

    assert report.result.error == (
        "Evaluation failed."
    )
    assert report.message == (
        "Evaluation failed."
    )


def test_fail_request_error_must_not_be_empty() -> None:
    value = started_engine()

    with pytest.raises(
        ValueError,
        match="error must not be empty",
    ):
        value.fail_request(
            "request-001",
            error="   ",
        )


def test_failure_time_must_follow_latest_update(
) -> None:
    clock = FixedClock(NOW)

    value = EnterpriseStrategySignalEngine(
        clock=clock
    )

    value.register_request(
        signal_request()
    )

    value.start_evaluation(
        "request-001"
    )

    clock.value = (
        NOW + timedelta(seconds=2)
    )

    value.attach_signal(
        "request-001",
        rationale="Momentum confirmed.",
    )

    clock.value = (
        NOW + timedelta(seconds=1)
    )

    with pytest.raises(
        ValueError,
        match=(
            "failure time must not be earlier "
            "than latest result update"
        ),
    ):
        value.fail_request(
            "request-001",
            error="Evaluation failed.",
        )


@pytest.mark.parametrize(
    "operation",
    [
        "accept",
        "reject",
        "cancel",
        "expire",
        "fail",
        "attach",
    ],
)
def test_terminal_request_rejects_further_modification(
    operation: str,
) -> None:
    value = rejected_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal signal requests cannot be modified"
        ),
    ):
        if operation == "accept":
            value.accept_request(
                "request-001"
            )
        elif operation == "reject":
            value.reject_request(
                "request-001",
                reason="Rejected again.",
            )
        elif operation == "cancel":
            value.cancel_request(
                "request-001",
                reason="Cancelled later.",
            )
        elif operation == "expire":
            value.expire_request(
                "request-001"
            )
        elif operation == "fail":
            value.fail_request(
                "request-001",
                error="Failure after terminal state.",
            )
        else:
            value.attach_signal(
                "request-001",
                rationale="Late signal.",
            )


def test_terminal_transition_time_must_follow_update(
) -> None:
    clock = FixedClock(NOW)

    value = EnterpriseStrategySignalEngine(
        clock=clock
    )

    value.register_request(
        signal_request()
    )

    value.start_evaluation(
        "request-001"
    )

    clock.value = (
        NOW + timedelta(seconds=2)
    )

    value.attach_signal(
        "request-001",
        rationale="Momentum confirmed.",
    )

    clock.value = (
        NOW + timedelta(seconds=1)
    )

    with pytest.raises(
        ValueError,
        match=(
            "terminal transition time must not be "
            "earlier than latest result update"
        ),
    ):
        value.reject_request(
            "request-001",
            reason="Rejected.",
        )


def test_accept_request_preserves_warnings() -> None:
    value = started_engine()

    value.attach_signal(
        "request-001",
        rationale="Momentum confirmed.",
        warnings=(
            "Spread slightly elevated.",
        ),
    )

    report = value.accept_request(
        "request-001"
    )

    assert report.warnings == (
        "Spread slightly elevated.",
    )
    assert report.result.warnings == (
        "Spread slightly elevated.",
    )


def test_reject_request_preserves_warnings() -> None:
    value = started_engine()

    value.attach_signal(
        "request-001",
        rationale="Momentum confirmed.",
        warnings=(
            "Liquidity below ideal level.",
        ),
    )

    report = value.reject_request(
        "request-001",
        reason="Risk rejected signal.",
    )

    assert report.warnings == (
        "Liquidity below ideal level.",
    )


def test_cancel_request_preserves_warnings() -> None:
    value = started_engine()

    value.attach_signal(
        "request-001",
        rationale="Momentum confirmed.",
        warnings=(
            "Market regime uncertain.",
        ),
    )

    report = value.cancel_request(
        "request-001",
        reason="Supervisor cancelled.",
    )

    assert report.warnings == (
        "Market regime uncertain.",
    )


def test_failure_preserves_warnings() -> None:
    value = started_engine()

    value.attach_signal(
        "request-001",
        rationale="Momentum confirmed.",
        warnings=(
            "Feed latency elevated.",
        ),
    )

    report = value.fail_request(
        "request-001",
        error="Risk service unavailable.",
        retryable=True,
    )

    assert report.warnings == (
        "Feed latency elevated.",
    )


def test_result_history_tracks_acceptance() -> None:
    value = generated_engine()

    value.accept_request(
        "request-001"
    )

    history = value.results_for_request(
        "request-001"
    )

    assert len(history) == 3
    assert history[0].status is SignalStatus.ACTIVE
    assert history[0].signal is None
    assert history[1].status is SignalStatus.ACTIVE
    assert history[1].signal is not None
    assert history[2].status is SignalStatus.ACCEPTED


def test_report_history_tracks_acceptance() -> None:
    value = generated_engine()

    value.accept_request(
        "request-001"
    )

    assert len(value.report_history) == 3

    assert value.report_history[-1].status is (
        SignalStatus.ACCEPTED
    )

    assert value.report_history[-1].report_id == (
        "strategy-signal-report-000003"
    )


def test_latest_report_tracks_terminal_state() -> None:
    value = generated_engine()

    expected = value.accept_request(
        "request-001"
    )

    assert value.latest_report() == expected
    assert value.get_report(
        "request-001"
    ) == expected


def test_reports_for_strategy_include_all_states() -> None:
    value = generated_engine()

    value.accept_request(
        "request-001"
    )

    reports = value.reports_for_strategy(
        "strategy-001"
    )

    assert len(reports) == 3
    assert reports[-1].status is SignalStatus.ACCEPTED


def test_reports_for_portfolio_include_all_states() -> None:
    value = generated_engine()

    value.reject_request(
        "request-001",
        reason="Risk rejected signal.",
    )

    reports = value.reports_for_portfolio(
        "portfolio-001"
    )

    assert len(reports) == 3
    assert reports[-1].status is SignalStatus.REJECTED


def test_reports_for_symbol_include_all_states() -> None:
    value = generated_engine()

    value.cancel_request(
        "request-001",
        reason="Supervisor cancelled.",
    )

    reports = value.reports_for_symbol(
        "NVDA"
    )

    assert len(reports) == 3
    assert reports[-1].status is SignalStatus.CANCELLED


def test_report_and_result_histories_remain_aligned(
) -> None:
    value = generated_engine()

    value.fail_request(
        "request-001",
        error="Risk service unavailable.",
        retryable=True,
    )

    results = value.results_for_request(
        "request-001"
    )

    reports = tuple(
        report
        for report in value.report_history
        if report.request_id == "request-001"
    )

    assert len(results) == len(reports)

    assert tuple(
        report.result
        for report in reports
    ) == results


def test_signal_lookup_survives_terminal_state() -> None:
    value = accepted_engine()

    signal = value.signal_for_request(
        "request-001"
    )

    assert signal.signal_id == (
        "strategy-signal-000001"
    )

    assert value.get_signal(
        "strategy-signal-000001"
    ) == signal


def test_terminal_request_cannot_be_unregistered() -> None:
    value = rejected_engine()

    with pytest.raises(
        RuntimeError,
        match=(
            "started signal requests cannot be "
            "unregistered"
        ),
    ):
        value.unregister_request(
            "request-001"
        )


def test_clock_validation_during_signal_generation() -> None:
    value = EnterpriseStrategySignalEngine(
        clock=FixedClock(NOW)
    )

    value.register_request(
        signal_request()
    )

    value.start_evaluation(
        "request-001"
    )

    value._clock = lambda: "now"

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        value.attach_signal(
            "request-001",
            rationale="Momentum confirmed.",
        )


def test_clock_validation_during_terminal_transition(
) -> None:
    value = started_engine()

    value._clock = lambda: datetime(
        2026,
        8,
        10,
        22,
        30,
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        value.reject_request(
            "request-001",
            reason="Rejected.",
        )


def test_full_successful_signal_lifecycle() -> None:
    value = registered_engine()

    started = value.start_evaluation(
        "request-001"
    )

    generated = value.attach_signal(
        "request-001",
        rationale=(
            "Momentum, trend, and market context "
            "support long entry."
        ),
        expires_at=(
            NOW + timedelta(minutes=5)
        ),
    )

    accepted = value.accept_request(
        "request-001"
    )

    assert started.status is SignalStatus.ACTIVE
    assert started.signal is None

    assert generated.status is SignalStatus.ACTIVE
    assert generated.signal is not None

    assert accepted.status is SignalStatus.ACCEPTED
    assert accepted.is_terminal is True
    assert accepted.signal is not None

    assert len(
        value.results_for_request(
            "request-001"
        )
    ) == 3

    assert len(value.report_history) == 3
    assert len(value.signal_ids) == 1


def test_full_rejected_signal_lifecycle() -> None:
    value = registered_engine()

    value.start_evaluation(
        "request-001"
    )

    generated = value.attach_signal(
        "request-001",
        rationale="Candidate long signal.",
    )

    rejected = value.reject_request(
        "request-001",
        reason="Pre-trade risk rejected candidate.",
    )

    assert generated.signal is not None
    assert rejected.status is SignalStatus.REJECTED
    assert rejected.signal is not None
    assert rejected.is_terminal is True


def test_full_failed_signal_lifecycle() -> None:
    value = registered_engine()

    value.start_evaluation(
        "request-001"
    )

    failed = value.fail_request(
        "request-001",
        error="Strategy evaluation dependency failed.",
        retryable=True,
    )

    assert failed.status is SignalStatus.FAILED
    assert failed.decision is SignalDecision.RETRY
    assert failed.result.error == (
        "Strategy evaluation dependency failed."
    )
    assert failed.signal is None
    assert failed.is_terminal is True