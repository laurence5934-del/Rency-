from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.market_data import MarketQuote
from app.strategy.market_data_pipeline import (
    EnterpriseMarketDataPipeline,
    MarketDataPipelineRequest,
    PipelineDecision,
    PipelineEventType,
    PipelineStage,
    PipelineStatus,
)

NOW = datetime(
    2026,
    8,
    6,
    22,
    0,
    tzinfo=timezone.utc,
)

PAYLOAD_TIME = NOW - timedelta(seconds=1)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def quote_payload(
    *,
    symbol: str = "NVDA",
    timestamp: datetime = PAYLOAD_TIME,
) -> MarketQuote:
    return MarketQuote(
        symbol=symbol,
        bid=Decimal("125.10"),
        ask=Decimal("125.20"),
        bid_size=Decimal("100"),
        ask_size=Decimal("120"),
        timestamp=timestamp,
    )


def pipeline_request(
    *,
    event_id: str = "event-001",
    correlation_id: str = "correlation-001",
    source: str = "ibkr-adapter",
    symbol: str = "NVDA",
    received_at: datetime = NOW,
    sequence_number: int = 1,
) -> MarketDataPipelineRequest:
    return MarketDataPipelineRequest(
        event_id=event_id,
        correlation_id=correlation_id,
        source=source,
        event_type=PipelineEventType.QUOTE,
        payload=quote_payload(symbol=symbol),
        received_at=received_at,
        sequence_number=sequence_number,
        metadata=(
            ("environment", "paper"),
        ),
    )


def pipeline(
    *,
    current_time: datetime = NOW,
) -> EnterpriseMarketDataPipeline:
    return EnterpriseMarketDataPipeline(
        clock=FixedClock(current_time)
    )


def registered_pipeline(
) -> EnterpriseMarketDataPipeline:
    value = pipeline()
    value.register_request(
        pipeline_request()
    )
    return value


def started_pipeline(
) -> EnterpriseMarketDataPipeline:
    value = registered_pipeline()
    value.start_processing("event-001")
    return value


def test_create_pipeline() -> None:
    value = pipeline()

    assert value.event_ids == ()
    assert value.report_history == ()


def test_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterpriseMarketDataPipeline(
            clock=NOW
        )


def test_register_request() -> None:
    value = pipeline()
    request = pipeline_request()

    result = value.register_request(request)

    assert result == request
    assert value.event_ids == ("event-001",)


def test_register_request_requires_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "request must be a "
            "MarketDataPipelineRequest"
        ),
    ):
        pipeline().register_request(object())


def test_duplicate_event_id_is_rejected() -> None:
    value = registered_pipeline()

    with pytest.raises(
        ValueError,
        match="event_id is already registered",
    ):
        value.register_request(
            pipeline_request(
                correlation_id="correlation-002",
            )
        )


def test_duplicate_correlation_id_is_rejected() -> None:
    value = registered_pipeline()

    with pytest.raises(
        ValueError,
        match=(
            "correlation_id is already registered"
        ),
    ):
        value.register_request(
            pipeline_request(
                event_id="event-002",
            )
        )


def test_register_multiple_requests() -> None:
    value = pipeline()

    value.register_request(
        pipeline_request()
    )

    value.register_request(
        pipeline_request(
            event_id="event-002",
            correlation_id="correlation-002",
            symbol="AAPL",
            sequence_number=2,
        )
    )

    assert value.event_ids == (
        "event-001",
        "event-002",
    )


def test_event_ids_are_sorted() -> None:
    value = pipeline()

    value.register_request(
        pipeline_request(
            event_id="event-002",
            correlation_id="correlation-002",
        )
    )

    value.register_request(
        pipeline_request(
            event_id="event-001",
            correlation_id="correlation-001",
        )
    )

    assert value.event_ids == (
        "event-001",
        "event-002",
    )


def test_unregister_request() -> None:
    value = registered_pipeline()

    removed = value.unregister_request(
        "event-001"
    )

    assert removed.event_id == "event-001"
    assert value.event_ids == ()


def test_unregister_request_normalizes_identifier(
) -> None:
    value = registered_pipeline()

    removed = value.unregister_request(
        "  event-001  "
    )

    assert removed.event_id == "event-001"


def test_unregister_unknown_request_is_rejected(
) -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market-data pipeline request not found"
        ),
    ):
        pipeline().unregister_request(
            "missing"
        )


def test_unregister_started_request_is_rejected(
) -> None:
    value = started_pipeline()

    with pytest.raises(
        RuntimeError,
        match=(
            "started pipeline events cannot be "
            "unregistered"
        ),
    ):
        value.unregister_request(
            "event-001"
        )


def test_unregister_releases_correlation_id() -> None:
    value = registered_pipeline()

    value.unregister_request(
        "event-001"
    )

    replacement = value.register_request(
        pipeline_request(
            event_id="event-002",
            correlation_id="correlation-001",
        )
    )

    assert replacement.event_id == "event-002"


def test_get_request() -> None:
    value = registered_pipeline()

    request = value.get_request(
        "event-001"
    )

    assert request.event_id == "event-001"
    assert request.correlation_id == (
        "correlation-001"
    )


def test_get_request_normalizes_identifier() -> None:
    value = registered_pipeline()

    request = value.get_request(
        "  event-001  "
    )

    assert request.event_id == "event-001"


def test_get_unknown_request_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market-data pipeline request not found"
        ),
    ):
        pipeline().get_request("missing")


def test_request_for_correlation() -> None:
    value = registered_pipeline()

    request = value.request_for_correlation(
        "correlation-001"
    )

    assert request.event_id == "event-001"


def test_request_for_correlation_normalizes_identifier(
) -> None:
    value = registered_pipeline()

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
            "market-data pipeline request not found "
            "for correlation_id"
        ),
    ):
        pipeline().request_for_correlation(
            "missing"
        )


def test_start_processing() -> None:
    value = registered_pipeline()

    report = value.start_processing(
        "event-001"
    )

    assert report.event_id == "event-001"
    assert report.status is (
        PipelineStatus.PROCESSING
    )
    assert report.decision is (
        PipelineDecision.PROCEED
    )
    assert report.report_id == (
        "pipeline-report-000001"
    )
    assert report.reported_at == NOW


def test_start_processing_normalizes_identifier(
) -> None:
    value = registered_pipeline()

    report = value.start_processing(
        "  event-001  "
    )

    assert report.event_id == "event-001"


def test_start_processing_is_idempotent() -> None:
    value = registered_pipeline()

    first = value.start_processing(
        "event-001"
    )
    second = value.start_processing(
        "event-001"
    )

    assert first == second
    assert len(value.report_history) == 1
    assert len(
        value.results_for_event("event-001")
    ) == 1


def test_start_unknown_event_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market-data pipeline request not found"
        ),
    ):
        pipeline().start_processing(
            "missing"
        )


def test_start_time_must_not_precede_receipt() -> None:
    value = pipeline(
        current_time=NOW
    )

    value.register_request(
        pipeline_request(
            received_at=(
                NOW + timedelta(seconds=1)
            )
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "pipeline start time must not be earlier "
            "than request received_at"
        ),
    ):
        value.start_processing(
            "event-001"
        )


def test_get_result() -> None:
    value = started_pipeline()

    result = value.get_result(
        "event-001"
    )

    assert result.status is (
        PipelineStatus.PROCESSING
    )
    assert result.started_at == NOW
    assert result.updated_at == NOW


def test_get_result_normalizes_identifier() -> None:
    value = started_pipeline()

    result = value.get_result(
        "  event-001  "
    )

    assert result.event_id == "event-001"


def test_get_result_before_start_is_rejected(
) -> None:
    value = registered_pipeline()

    with pytest.raises(
        KeyError,
        match=(
            "market-data pipeline event has no result"
        ),
    ):
        value.get_result(
            "event-001"
        )


def test_get_report() -> None:
    value = started_pipeline()

    report = value.get_report(
        "event-001"
    )

    assert report.status is (
        PipelineStatus.PROCESSING
    )
    assert report.report_id == (
        "pipeline-report-000001"
    )


def test_get_report_before_start_is_rejected(
) -> None:
    value = registered_pipeline()

    with pytest.raises(
        KeyError,
        match=(
            "market-data pipeline event has no report"
        ),
    ):
        value.get_report(
            "event-001"
        )


def test_latest_report() -> None:
    value = started_pipeline()

    latest = value.latest_report()

    assert latest.report_id == (
        "pipeline-report-000001"
    )


def test_latest_report_without_history_is_rejected(
) -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market-data pipeline has no reports"
        ),
    ):
        pipeline().latest_report()


def test_results_for_event() -> None:
    value = started_pipeline()

    result = value.get_result(
        "event-001"
    )

    assert value.results_for_event(
        "event-001"
    ) == (result,)


def test_results_for_unstarted_event_returns_empty(
) -> None:
    value = registered_pipeline()

    assert value.results_for_event(
        "event-001"
    ) == ()


def test_results_for_unknown_event_is_rejected(
) -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market-data pipeline request not found"
        ),
    ):
        pipeline().results_for_event(
            "missing"
        )


def test_reports_for_symbol() -> None:
    value = pipeline()

    value.register_request(
        pipeline_request()
    )
    value.start_processing(
        "event-001"
    )

    value.register_request(
        pipeline_request(
            event_id="event-002",
            correlation_id="correlation-002",
            symbol="AAPL",
            sequence_number=2,
        )
    )
    value.start_processing(
        "event-002"
    )

    reports = value.reports_for_symbol(
        "NVDA"
    )

    assert len(reports) == 1
    assert reports[0].event_id == "event-001"


def test_reports_for_symbol_normalizes_symbol() -> None:
    value = started_pipeline()

    reports = value.reports_for_symbol(
        "  nvda  "
    )

    assert len(reports) == 1
    assert reports[0].symbol == "NVDA"


def test_reports_for_unknown_symbol_returns_empty(
) -> None:
    assert pipeline().reports_for_symbol(
        "AAPL"
    ) == ()


def test_reports_for_source() -> None:
    value = started_pipeline()

    reports = value.reports_for_source(
        "ibkr-adapter"
    )

    assert len(reports) == 1
    assert reports[0].request.source == (
        "ibkr-adapter"
    )


def test_reports_for_source_normalizes_identifier(
) -> None:
    value = started_pipeline()

    reports = value.reports_for_source(
        "  ibkr-adapter  "
    )

    assert len(reports) == 1


def test_reports_for_unknown_source_returns_empty(
) -> None:
    assert pipeline().reports_for_source(
        "replay-feed"
    ) == ()


def test_report_history_property() -> None:
    value = started_pipeline()

    assert len(value.report_history) == 1
    assert value.report_history[0].report_id == (
        "pipeline-report-000001"
    )


def test_report_history_is_immutable_tuple() -> None:
    value = started_pipeline()

    history = value.report_history

    assert isinstance(history, tuple)


def test_report_ids_are_deterministic() -> None:
    value = pipeline()

    value.register_request(
        pipeline_request()
    )
    first = value.start_processing(
        "event-001"
    )

    value.register_request(
        pipeline_request(
            event_id="event-002",
            correlation_id="correlation-002",
            symbol="AAPL",
            sequence_number=2,
        )
    )
    second = value.start_processing(
        "event-002"
    )

    assert first.report_id == (
        "pipeline-report-000001"
    )
    assert second.report_id == (
        "pipeline-report-000002"
    )


def test_report_contains_request_metadata() -> None:
    value = started_pipeline()

    report = value.get_report(
        "event-001"
    )

    assert report.metadata == (
        (
            "correlation_id",
            "correlation-001",
        ),
        (
            "source",
            "ibkr-adapter",
        ),
        (
            "event_type",
            "QUOTE",
        ),
    )


def test_event_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="event_id must not be empty",
    ):
        pipeline().get_request("   ")


def test_event_identifier_must_be_string() -> None:
    with pytest.raises(
        TypeError,
        match="event_id must be a string",
    ):
        pipeline().get_request(123)


def test_correlation_identifier_must_not_be_empty(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "correlation_id must not be empty"
        ),
    ):
        pipeline().request_for_correlation(
            "   "
        )


def test_symbol_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="symbol must not be empty",
    ):
        pipeline().reports_for_symbol(
            "   "
        )


def test_source_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="source must not be empty",
    ):
        pipeline().reports_for_source(
            "   "
        )


def test_clock_must_return_datetime() -> None:
    value = EnterpriseMarketDataPipeline(
        clock=lambda: "now"
    )

    value.register_request(
        pipeline_request()
    )

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        value.start_processing(
            "event-001"
        )


def test_clock_must_return_timezone_aware_datetime(
) -> None:
    value = EnterpriseMarketDataPipeline(
        clock=lambda: datetime(
            2026,
            8,
            6,
            22,
            0,
        )
    )

    value.register_request(
        pipeline_request()
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        value.start_processing(
            "event-001"
        )

def record_all_successful_checkpoints(
    value: EnterpriseMarketDataPipeline,
    *,
    event_id: str = "event-001",
) -> None:
    stages = (
        PipelineStage.RECEIVED,
        PipelineStage.VALIDATION,
        PipelineStage.DEDUPLICATION,
        PipelineStage.ORDERING,
        PipelineStage.ROUTING,
        PipelineStage.PERSISTENCE,
        PipelineStage.PUBLICATION,
    )

    for stage in stages:
        value.record_checkpoint(
            event_id,
            stage=stage,
            decision=PipelineDecision.PROCEED,
            successful=True,
            message=f"{stage.value} completed.",
        )


def test_record_checkpoint() -> None:
    value = started_pipeline()

    report = value.record_checkpoint(
        "event-001",
        stage=PipelineStage.RECEIVED,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Event received.",
        reference_id="adapter-event-001",
        warnings=("Minor timing drift.",),
        metadata=(
            ("provider", "ibkr"),
        ),
    )

    result = report.result
    checkpoint = result.latest_checkpoint

    assert checkpoint is not None
    assert checkpoint.checkpoint_id == (
        "pipeline-checkpoint-000001"
    )
    assert checkpoint.stage is PipelineStage.RECEIVED
    assert checkpoint.successful is True
    assert checkpoint.reference_id == "adapter-event-001"
    assert checkpoint.metadata == (
        ("provider", "ibkr"),
    )
    assert result.status is PipelineStatus.PROCESSING
    assert result.warnings == (
        "Minor timing drift.",
    )


def test_record_checkpoint_requires_started_event() -> None:
    value = registered_pipeline()

    with pytest.raises(
        KeyError,
        match=(
            "market-data pipeline event has no result"
        ),
    ):
        value.record_checkpoint(
            "event-001",
            stage=PipelineStage.RECEIVED,
            decision=PipelineDecision.PROCEED,
            successful=True,
            message="Event received.",
        )


def test_record_checkpoint_requires_stage_enum() -> None:
    value = started_pipeline()

    with pytest.raises(
        TypeError,
        match="stage must be a PipelineStage",
    ):
        value.record_checkpoint(
            "event-001",
            stage="RECEIVED",
            decision=PipelineDecision.PROCEED,
            successful=True,
            message="Event received.",
        )


def test_record_checkpoint_requires_decision_enum() -> None:
    value = started_pipeline()

    with pytest.raises(
        TypeError,
        match="decision must be a PipelineDecision",
    ):
        value.record_checkpoint(
            "event-001",
            stage=PipelineStage.RECEIVED,
            decision="PROCEED",
            successful=True,
            message="Event received.",
        )


def test_record_checkpoint_successful_requires_bool(
) -> None:
    value = started_pipeline()

    with pytest.raises(
        TypeError,
        match="successful must be a bool",
    ):
        value.record_checkpoint(
            "event-001",
            stage=PipelineStage.RECEIVED,
            decision=PipelineDecision.PROCEED,
            successful="yes",
            message="Event received.",
        )


def test_checkpoint_ids_are_deterministic() -> None:
    value = started_pipeline()

    first = value.record_checkpoint(
        "event-001",
        stage=PipelineStage.RECEIVED,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Event received.",
    )

    second = value.record_checkpoint(
        "event-001",
        stage=PipelineStage.VALIDATION,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Validation completed.",
    )

    assert (
        first.result.latest_checkpoint.checkpoint_id
        == "pipeline-checkpoint-000001"
    )
    assert (
        second.result.latest_checkpoint.checkpoint_id
        == "pipeline-checkpoint-000002"
    )


def test_checkpoint_ids_continue_across_events() -> None:
    value = pipeline()

    value.register_request(
        pipeline_request()
    )
    value.start_processing("event-001")

    first = value.record_checkpoint(
        "event-001",
        stage=PipelineStage.RECEIVED,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Event received.",
    )

    value.register_request(
        pipeline_request(
            event_id="event-002",
            correlation_id="correlation-002",
            symbol="AAPL",
            sequence_number=2,
        )
    )
    value.start_processing("event-002")

    second = value.record_checkpoint(
        "event-002",
        stage=PipelineStage.RECEIVED,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Event received.",
    )

    assert (
        first.result.latest_checkpoint.checkpoint_id
        == "pipeline-checkpoint-000001"
    )
    assert (
        second.result.latest_checkpoint.checkpoint_id
        == "pipeline-checkpoint-000002"
    )


def test_duplicate_pipeline_stage_is_rejected() -> None:
    value = started_pipeline()

    value.record_checkpoint(
        "event-001",
        stage=PipelineStage.RECEIVED,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Event received.",
    )

    with pytest.raises(
        ValueError,
        match="pipeline stage is already recorded",
    ):
        value.record_checkpoint(
            "event-001",
            stage=PipelineStage.RECEIVED,
            decision=PipelineDecision.PROCEED,
            successful=True,
            message="Event received again.",
        )


def test_pipeline_stages_must_be_recorded_in_order(
) -> None:
    value = started_pipeline()

    value.record_checkpoint(
        "event-001",
        stage=PipelineStage.VALIDATION,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Validation completed.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "pipeline stages must be recorded "
            "in pipeline order"
        ),
    ):
        value.record_checkpoint(
            "event-001",
            stage=PipelineStage.RECEIVED,
            decision=PipelineDecision.PROCEED,
            successful=True,
            message="Event received.",
        )


def test_pipeline_may_skip_forward_stages() -> None:
    value = started_pipeline()

    report = value.record_checkpoint(
        "event-001",
        stage=PipelineStage.ROUTING,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Event routed.",
    )

    assert report.result.latest_checkpoint.stage is (
        PipelineStage.ROUTING
    )


def test_checkpoint_time_must_follow_latest_update(
) -> None:
    value = pipeline(
        current_time=NOW
    )

    value.register_request(
        pipeline_request()
    )
    value.start_processing("event-001")

    value._clock.value = NOW + timedelta(seconds=2)

    value.record_checkpoint(
        "event-001",
        stage=PipelineStage.RECEIVED,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Event received.",
    )

    value._clock.value = NOW + timedelta(seconds=1)

    with pytest.raises(
        ValueError,
        match=(
            "checkpoint time must not be earlier "
            "than the latest result update"
        ),
    ):
        value.record_checkpoint(
            "event-001",
            stage=PipelineStage.VALIDATION,
            decision=PipelineDecision.PROCEED,
            successful=True,
            message="Validation completed.",
        )


def test_checkpoint_warnings_are_accumulated() -> None:
    value = started_pipeline()

    value.record_checkpoint(
        "event-001",
        stage=PipelineStage.RECEIVED,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Event received.",
        warnings=(
            "Minor delay.",
            "Feed degraded.",
        ),
    )

    report = value.record_checkpoint(
        "event-001",
        stage=PipelineStage.VALIDATION,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Validation completed.",
        warnings=(
            "Minor delay.",
            "Price precision adjusted.",
        ),
    )

    assert report.result.warnings == (
        "Minor delay.",
        "Feed degraded.",
        "Price precision adjusted.",
    )


def test_result_history_tracks_checkpoint_states() -> None:
    value = started_pipeline()

    value.record_checkpoint(
        "event-001",
        stage=PipelineStage.RECEIVED,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Event received.",
    )

    value.record_checkpoint(
        "event-001",
        stage=PipelineStage.VALIDATION,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Validation completed.",
    )

    history = value.results_for_event(
        "event-001"
    )

    assert len(history) == 3
    assert history[0].checkpoints == ()
    assert len(history[1].checkpoints) == 1
    assert len(history[2].checkpoints) == 2


def test_complete_event() -> None:
    value = started_pipeline()

    record_all_successful_checkpoints(value)

    report = value.complete_event(
        "event-001"
    )

    assert report.status is PipelineStatus.COMPLETED
    assert report.decision is PipelineDecision.ACCEPT
    assert report.is_terminal is True
    assert report.result.completed_at == NOW
    assert len(report.result.checkpoints) == 7


def test_complete_event_requires_started_event() -> None:
    value = registered_pipeline()

    with pytest.raises(
        KeyError,
        match=(
            "market-data pipeline event has no result"
        ),
    ):
        value.complete_event("event-001")


def test_complete_event_requires_checkpoints() -> None:
    value = started_pipeline()

    with pytest.raises(
        RuntimeError,
        match=(
            "pipeline event cannot complete without "
            "checkpoints"
        ),
    ):
        value.complete_event("event-001")


def test_complete_event_requires_publication_stage(
) -> None:
    value = started_pipeline()

    value.record_checkpoint(
        "event-001",
        stage=PipelineStage.PERSISTENCE,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Persistence completed.",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "pipeline event must reach the "
            "publication stage before completion"
        ),
    ):
        value.complete_event("event-001")


def test_completion_time_must_follow_latest_update(
) -> None:
    value = pipeline(
        current_time=NOW
    )

    value.register_request(
        pipeline_request()
    )
    value.start_processing("event-001")

    value._clock.value = NOW + timedelta(seconds=2)

    record_all_successful_checkpoints(value)

    value._clock.value = NOW + timedelta(seconds=1)

    with pytest.raises(
        ValueError,
        match=(
            "completion time must not be earlier "
            "than the latest result update"
        ),
    ):
        value.complete_event("event-001")


def test_complete_event_message_is_normalized() -> None:
    value = started_pipeline()
    record_all_successful_checkpoints(value)

    report = value.complete_event(
        "event-001",
        message="  Event completed successfully.  ",
    )

    assert report.message == (
        "Event completed successfully."
    )


def test_reject_event() -> None:
    value = started_pipeline()

    report = value.reject_event(
        "event-001",
        stage=PipelineStage.VALIDATION,
        reason="Validation rejected the event.",
        reference_id="validation-001",
        warnings=("Invalid spread.",),
    )

    checkpoint = report.result.failed_checkpoint

    assert report.status is PipelineStatus.REJECTED
    assert report.decision is PipelineDecision.REJECT
    assert report.is_terminal is True
    assert checkpoint is not None
    assert checkpoint.stage is PipelineStage.VALIDATION
    assert checkpoint.successful is False
    assert checkpoint.error == (
        "Validation rejected the event."
    )
    assert report.result.error is None


def test_reject_reason_is_normalized() -> None:
    value = started_pipeline()

    report = value.reject_event(
        "event-001",
        stage=PipelineStage.VALIDATION,
        reason="  Invalid quote.  ",
    )

    assert report.message == "Invalid quote."
    assert (
        report.result.failed_checkpoint.error
        == "Invalid quote."
    )


def test_reject_reason_must_not_be_empty() -> None:
    value = started_pipeline()

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        value.reject_event(
            "event-001",
            stage=PipelineStage.VALIDATION,
            reason="   ",
        )


def test_drop_event() -> None:
    value = started_pipeline()

    report = value.drop_event(
        "event-001",
        stage=PipelineStage.DEDUPLICATION,
        reason="Duplicate event detected.",
    )

    assert report.status is PipelineStatus.DROPPED
    assert report.decision is PipelineDecision.DROP
    assert report.result.failed_checkpoint.stage is (
        PipelineStage.DEDUPLICATION
    )


def test_fail_event_retryable() -> None:
    value = started_pipeline()

    report = value.fail_event(
        "event-001",
        stage=PipelineStage.PERSISTENCE,
        error="Persistence service unavailable.",
        retryable=True,
    )

    assert report.status is PipelineStatus.FAILED
    assert report.decision is PipelineDecision.RETRY
    assert report.result.error == (
        "Persistence service unavailable."
    )


def test_fail_event_non_retryable() -> None:
    value = started_pipeline()

    report = value.fail_event(
        "event-001",
        stage=PipelineStage.PUBLICATION,
        error="Publication permanently failed.",
        retryable=False,
    )

    assert report.status is PipelineStatus.FAILED
    assert report.decision is (
        PipelineDecision.NO_ACTION
    )


def test_fail_event_retryable_requires_bool() -> None:
    value = started_pipeline()

    with pytest.raises(
        TypeError,
        match="retryable must be a bool",
    ):
        value.fail_event(
            "event-001",
            stage=PipelineStage.PERSISTENCE,
            error="Persistence failed.",
            retryable="yes",
        )


def test_fail_event_error_must_not_be_empty() -> None:
    value = started_pipeline()

    with pytest.raises(
        ValueError,
        match="error must not be empty",
    ):
        value.fail_event(
            "event-001",
            stage=PipelineStage.PERSISTENCE,
            error="   ",
        )


@pytest.mark.parametrize(
    "method_name",
    [
        "reject_event",
        "drop_event",
        "fail_event",
    ],
)
def test_terminal_transition_requires_stage_enum(
    method_name: str,
) -> None:
    value = started_pipeline()
    method = getattr(value, method_name)

    arguments = {
        "event_id": "event-001",
        "stage": "VALIDATION",
    }

    if method_name == "fail_event":
        arguments["error"] = "Failure."
    else:
        arguments["reason"] = "Rejected."

    with pytest.raises(
        TypeError,
        match="stage must be a PipelineStage",
    ):
        method(**arguments)


def test_terminal_transition_time_must_follow_update(
) -> None:
    value = pipeline(
        current_time=NOW
    )

    value.register_request(
        pipeline_request()
    )
    value.start_processing("event-001")

    value._clock.value = NOW + timedelta(seconds=2)

    value.record_checkpoint(
        "event-001",
        stage=PipelineStage.RECEIVED,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Event received.",
    )

    value._clock.value = NOW + timedelta(seconds=1)

    with pytest.raises(
        ValueError,
        match=(
            "terminal transition time must not be "
            "earlier than the latest result update"
        ),
    ):
        value.reject_event(
            "event-001",
            stage=PipelineStage.VALIDATION,
            reason="Validation rejected event.",
        )


def test_terminal_event_cannot_record_checkpoint(
) -> None:
    value = started_pipeline()

    value.reject_event(
        "event-001",
        stage=PipelineStage.VALIDATION,
        reason="Validation rejected event.",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal pipeline events cannot be "
            "modified"
        ),
    ):
        value.record_checkpoint(
            "event-001",
            stage=PipelineStage.ROUTING,
            decision=PipelineDecision.PROCEED,
            successful=True,
            message="Event routed.",
        )


@pytest.mark.parametrize(
    "operation",
    [
        "complete",
        "reject",
        "drop",
        "fail",
    ],
)
def test_terminal_event_rejects_further_transitions(
    operation: str,
) -> None:
    value = started_pipeline()

    value.reject_event(
        "event-001",
        stage=PipelineStage.VALIDATION,
        reason="Initial rejection.",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "terminal pipeline events cannot be "
            "modified"
        ),
    ):
        if operation == "complete":
            value.complete_event("event-001")
        elif operation == "reject":
            value.reject_event(
                "event-001",
                stage=PipelineStage.ROUTING,
                reason="Rejected again.",
            )
        elif operation == "drop":
            value.drop_event(
                "event-001",
                stage=PipelineStage.ROUTING,
                reason="Dropped later.",
            )
        else:
            value.fail_event(
                "event-001",
                stage=PipelineStage.ROUTING,
                error="Failed later.",
            )


def test_reports_for_symbol_include_all_state_changes(
) -> None:
    value = started_pipeline()

    value.record_checkpoint(
        "event-001",
        stage=PipelineStage.RECEIVED,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Event received.",
    )

    value.reject_event(
        "event-001",
        stage=PipelineStage.VALIDATION,
        reason="Validation rejected event.",
    )

    reports = value.reports_for_symbol("NVDA")

    assert len(reports) == 3
    assert reports[-1].status is (
        PipelineStatus.REJECTED
    )


def test_latest_report_tracks_terminal_state() -> None:
    value = started_pipeline()

    expected = value.drop_event(
        "event-001",
        stage=PipelineStage.DEDUPLICATION,
        reason="Duplicate event.",
    )

    assert value.latest_report() == expected
    assert value.get_report("event-001") == expected


def test_report_and_result_histories_remain_aligned(
) -> None:
    value = started_pipeline()

    value.record_checkpoint(
        "event-001",
        stage=PipelineStage.RECEIVED,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Event received.",
    )

    value.fail_event(
        "event-001",
        stage=PipelineStage.VALIDATION,
        error="Validation service failed.",
        retryable=True,
    )

    results = value.results_for_event(
        "event-001"
    )

    reports = tuple(
        report
        for report in value.report_history
        if report.event_id == "event-001"
    )

    assert len(results) == len(reports)
    assert tuple(
        report.result
        for report in reports
    ) == results


def test_pipeline_clock_validation_during_checkpoint(
) -> None:
    value = EnterpriseMarketDataPipeline(
        clock=lambda: "now"
    )

    value.register_request(
        pipeline_request()
    )

    value._clock = FixedClock(NOW)
    value.start_processing("event-001")
    value._clock = lambda: "now"

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        value.record_checkpoint(
            "event-001",
            stage=PipelineStage.RECEIVED,
            decision=PipelineDecision.PROCEED,
            successful=True,
            message="Event received.",
        )


def test_pipeline_clock_must_be_aware_during_completion(
) -> None:
    value = started_pipeline()
    record_all_successful_checkpoints(value)

    value._clock = lambda: datetime(
        2026,
        8,
        6,
        22,
        0,
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        value.complete_event("event-001")


def test_complete_event_preserves_warnings() -> None:
    value = started_pipeline()

    value.record_checkpoint(
        "event-001",
        stage=PipelineStage.RECEIVED,
        decision=PipelineDecision.PROCEED,
        successful=True,
        message="Event received.",
        warnings=("Feed latency elevated.",),
    )

    for stage in (
        PipelineStage.VALIDATION,
        PipelineStage.DEDUPLICATION,
        PipelineStage.ORDERING,
        PipelineStage.ROUTING,
        PipelineStage.PERSISTENCE,
        PipelineStage.PUBLICATION,
    ):
        value.record_checkpoint(
            "event-001",
            stage=stage,
            decision=PipelineDecision.PROCEED,
            successful=True,
            message=f"{stage.value} completed.",
        )

    report = value.complete_event("event-001")

    assert report.warnings == (
        "Feed latency elevated.",
    )
    assert report.result.warnings == (
        "Feed latency elevated.",
    )


def test_full_successful_pipeline_lifecycle() -> None:
    value = registered_pipeline()

    started = value.start_processing(
        "event-001"
    )

    record_all_successful_checkpoints(value)

    completed = value.complete_event(
        "event-001"
    )

    assert started.status is PipelineStatus.PROCESSING
    assert completed.status is PipelineStatus.COMPLETED
    assert completed.is_terminal is True
    assert len(completed.result.checkpoints) == 7
    assert len(
        value.results_for_event("event-001")
    ) == 9
    assert len(value.report_history) == 9