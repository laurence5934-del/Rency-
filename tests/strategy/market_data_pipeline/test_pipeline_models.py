from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.market_data import (
    BarInterval,
    FeedStatus,
    MarketBar,
    MarketDataHealthReport,
    MarketQuote,
    MarketSnapshot,
    MarketTrade,
)

from app.strategy.market_data_pipeline import (
    MarketDataPipelineReport,
    MarketDataPipelineRequest,
    MarketDataPipelineResult,
    PipelineCheckpoint,
    PipelineDecision,
    PipelineEventType,
    PipelineStage,
    PipelineStatus,
)

NOW = datetime(
    2026,
    8,
    6,
    21,
    30,
    tzinfo=timezone.utc,
)

PAYLOAD_TIME = NOW - timedelta(seconds=1)


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


def trade_payload(
    *,
    symbol: str = "NVDA",
    timestamp: datetime = PAYLOAD_TIME,
) -> MarketTrade:
    return MarketTrade(
        symbol=symbol,
        price=Decimal("125.15"),
        quantity=Decimal("50"),
        timestamp=timestamp,
    )


def bar_payload(
    *,
    symbol: str = "NVDA",
    start_time: datetime = (
        PAYLOAD_TIME - timedelta(minutes=1)
    ),
    end_time: datetime = PAYLOAD_TIME,
) -> MarketBar:
    return MarketBar(
        symbol=symbol,
        interval=BarInterval.ONE_MINUTE,
        open=Decimal("125.00"),
        high=Decimal("126.00"),
        low=Decimal("124.50"),
        close=Decimal("125.50"),
        volume=Decimal("10000"),
        start_time=start_time,
        end_time=end_time,
    )


def snapshot_payload(
    *,
    symbol: str = "NVDA",
    timestamp: datetime = PAYLOAD_TIME,
) -> MarketSnapshot:
    return MarketSnapshot(
        symbol=symbol,
        last_price=Decimal("125.15"),
        bid=Decimal("125.10"),
        ask=Decimal("125.20"),
        volume=Decimal("250000"),
        timestamp=timestamp,
    )


def health_payload(
    *,
    evaluated_at: datetime = PAYLOAD_TIME,
) -> MarketDataHealthReport:
    return MarketDataHealthReport(
        feed_name="IBKR Market Data",
        status=FeedStatus.CONNECTED,
        evaluated_at=evaluated_at,
        latency_ms=Decimal("8.5"),
        active_subscriptions=4,
        message="Market data feed is healthy.",
    )


def pipeline_request(
    *,
    event_id: str = "event-001",
    correlation_id: str = "correlation-001",
    source: str = "ibkr-adapter",
    event_type: PipelineEventType = (
        PipelineEventType.QUOTE
    ),
    payload: object | None = None,
    received_at: datetime = NOW,
    sequence_number: int = 1,
    is_replay: bool = False,
) -> MarketDataPipelineRequest:
    effective_payload = (
        quote_payload()
        if payload is None
        else payload
    )

    return MarketDataPipelineRequest(
        event_id=event_id,
        correlation_id=correlation_id,
        source=source,
        event_type=event_type,
        payload=effective_payload,
        received_at=received_at,
        sequence_number=sequence_number,
        is_replay=is_replay,
        metadata=(
            ("environment", "paper"),
        ),
    )


def test_market_data_pipeline_request() -> None:
    value = pipeline_request()

    assert value.event_id == "event-001"
    assert value.correlation_id == "correlation-001"
    assert value.source == "ibkr-adapter"
    assert value.event_type is PipelineEventType.QUOTE
    assert value.symbol == "NVDA"
    assert value.payload_timestamp == PAYLOAD_TIME
    assert value.received_at == NOW
    assert value.sequence_number == 1
    assert value.is_replay is False
    assert value.is_health_event is False
    assert value.metadata == (
        ("environment", "paper"),
    )


def test_pipeline_request_text_is_normalized() -> None:
    value = MarketDataPipelineRequest(
        event_id="  event-001  ",
        correlation_id="  correlation-001  ",
        source="  ibkr-adapter  ",
        event_type=PipelineEventType.QUOTE,
        payload=quote_payload(),
        received_at=NOW,
        sequence_number=1,
        metadata=[
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.event_id == "event-001"
    assert value.correlation_id == "correlation-001"
    assert value.source == "ibkr-adapter"
    assert value.metadata == (
        ("environment", "paper"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "event_id",
        "correlation_id",
        "source",
    ],
)
def test_pipeline_request_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "event_id": "event-001",
        "correlation_id": "correlation-001",
        "source": "ibkr-adapter",
        "event_type": PipelineEventType.QUOTE,
        "payload": quote_payload(),
        "received_at": NOW,
        "sequence_number": 1,
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        MarketDataPipelineRequest(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "event_id",
        "correlation_id",
        "source",
    ],
)
def test_pipeline_request_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "event_id": "event-001",
        "correlation_id": "correlation-001",
        "source": "ibkr-adapter",
        "event_type": PipelineEventType.QUOTE,
        "payload": quote_payload(),
        "received_at": NOW,
        "sequence_number": 1,
    }
    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        MarketDataPipelineRequest(**arguments)


def test_pipeline_request_requires_event_type_enum() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "event_type must be a PipelineEventType"
        ),
    ):
        pipeline_request(
            event_type="QUOTE"
        )


@pytest.mark.parametrize(
    ("event_type", "payload"),
    [
        (
            PipelineEventType.QUOTE,
            trade_payload(),
        ),
        (
            PipelineEventType.TRADE,
            quote_payload(),
        ),
        (
            PipelineEventType.BAR,
            snapshot_payload(),
        ),
        (
            PipelineEventType.SNAPSHOT,
            bar_payload(),
        ),
        (
            PipelineEventType.HEALTH,
            quote_payload(),
        ),
    ],
)
def test_event_type_must_match_payload(
    event_type: PipelineEventType,
    payload: object,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "event_type must match the payload type"
        ),
    ):
        pipeline_request(
            event_type=event_type,
            payload=payload,
        )


def test_pipeline_request_rejects_unsupported_payload(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "payload must be a supported "
            "market-data model"
        ),
    ):
        pipeline_request(
            payload=object(),
        )


@pytest.mark.parametrize(
    ("event_type", "payload", "symbol"),
    [
        (
            PipelineEventType.QUOTE,
            quote_payload(),
            "NVDA",
        ),
        (
            PipelineEventType.TRADE,
            trade_payload(),
            "NVDA",
        ),
        (
            PipelineEventType.BAR,
            bar_payload(),
            "NVDA",
        ),
        (
            PipelineEventType.SNAPSHOT,
            snapshot_payload(),
            "NVDA",
        ),
        (
            PipelineEventType.HEALTH,
            health_payload(),
            None,
        ),
    ],
)
def test_pipeline_request_supports_all_payload_types(
    event_type: PipelineEventType,
    payload: object,
    symbol: str | None,
) -> None:
    value = pipeline_request(
        event_type=event_type,
        payload=payload,
    )

    assert value.event_type is event_type
    assert value.symbol == symbol


def test_health_request_is_identified() -> None:
    value = pipeline_request(
        event_type=PipelineEventType.HEALTH,
        payload=health_payload(),
    )

    assert value.is_health_event is True
    assert value.symbol is None


def test_received_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="received_at must be a datetime",
    ):
        MarketDataPipelineRequest(
            event_id="event-001",
            correlation_id="correlation-001",
            source="ibkr-adapter",
            event_type=PipelineEventType.QUOTE,
            payload=quote_payload(),
            received_at="2026-08-06",
            sequence_number=1,
        )


def test_received_at_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "received_at must be timezone-aware"
        ),
    ):
        pipeline_request(
            received_at=datetime(
                2026,
                8,
                6,
                21,
                30,
            )
        )


def test_received_at_must_follow_payload_timestamp(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "received_at must not be earlier "
            "than the payload timestamp"
        ),
    ):
        pipeline_request(
            received_at=(
                PAYLOAD_TIME - timedelta(seconds=1)
            )
        )


def test_received_at_may_equal_payload_timestamp(
) -> None:
    value = pipeline_request(
        received_at=PAYLOAD_TIME
    )

    assert value.received_at == value.payload_timestamp


def test_sequence_number_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "sequence_number must be an integer"
        ),
    ):
        pipeline_request(
            sequence_number="1"
        )


def test_sequence_number_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "sequence_number must be an integer"
        ),
    ):
        pipeline_request(
            sequence_number=True
        )


def test_sequence_number_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "sequence_number must not be negative"
        ),
    ):
        pipeline_request(
            sequence_number=-1
        )


def test_zero_sequence_number_is_allowed() -> None:
    value = pipeline_request(
        sequence_number=0
    )

    assert value.sequence_number == 0


def test_replay_flag_requires_bool() -> None:
    with pytest.raises(
        TypeError,
        match="is_replay must be a bool",
    ):
        pipeline_request(
            is_replay="yes"
        )


def test_replay_request() -> None:
    value = pipeline_request(
        is_replay=True
    )

    assert value.is_replay is True


def test_pipeline_request_metadata_is_normalized(
) -> None:
    value = MarketDataPipelineRequest(
        event_id="event-001",
        correlation_id="correlation-001",
        source="ibkr-adapter",
        event_type=PipelineEventType.QUOTE,
        payload=quote_payload(),
        received_at=NOW,
        sequence_number=1,
        metadata=[
            ("  environment  ", "  paper  "),
            ("  provider  ", "  ibkr  "),
        ],
    )

    assert value.metadata == (
        ("environment", "paper"),
        ("provider", "ibkr"),
    )


def test_pipeline_request_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        MarketDataPipelineRequest(
            event_id="event-001",
            correlation_id="correlation-001",
            source="ibkr-adapter",
            event_type=PipelineEventType.QUOTE,
            payload=quote_payload(),
            received_at=NOW,
            sequence_number=1,
            metadata=(
                ("source", "adapter"),
                ("source", "duplicate"),
            ),
        )


def test_pipeline_request_metadata_items_must_be_pairs(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        MarketDataPipelineRequest(
            event_id="event-001",
            correlation_id="correlation-001",
            source="ibkr-adapter",
            event_type=PipelineEventType.QUOTE,
            payload=quote_payload(),
            received_at=NOW,
            sequence_number=1,
            metadata=(
                ("source",),
            ),
        )


def test_pipeline_request_metadata_keys_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        MarketDataPipelineRequest(
            event_id="event-001",
            correlation_id="correlation-001",
            source="ibkr-adapter",
            event_type=PipelineEventType.QUOTE,
            payload=quote_payload(),
            received_at=NOW,
            sequence_number=1,
            metadata=(
                (123, "adapter"),
            ),
        )


def test_pipeline_request_metadata_values_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        MarketDataPipelineRequest(
            event_id="event-001",
            correlation_id="correlation-001",
            source="ibkr-adapter",
            event_type=PipelineEventType.QUOTE,
            payload=quote_payload(),
            received_at=NOW,
            sequence_number=1,
            metadata=(
                ("source", 123),
            ),
        )


def test_pipeline_request_is_immutable() -> None:
    value = pipeline_request()

    with pytest.raises(FrozenInstanceError):
        value.event_id = "changed"




def pipeline_checkpoint(
    *,
    checkpoint_id: str = "checkpoint-001",
    event_id: str = "event-001",
    stage: PipelineStage = PipelineStage.VALIDATION,
    decision: PipelineDecision = PipelineDecision.PROCEED,
    started_at: datetime = NOW,
    completed_at: datetime | None = (
        NOW + timedelta(seconds=1)
    ),
    successful: bool = True,
    message: str = "Validation completed.",
    reference_id: str | None = "validation-001",
    warnings: tuple[str, ...] = (),
    error: str | None = None,
) -> PipelineCheckpoint:
    return PipelineCheckpoint(
        checkpoint_id=checkpoint_id,
        event_id=event_id,
        stage=stage,
        decision=decision,
        started_at=started_at,
        completed_at=completed_at,
        successful=successful,
        message=message,
        reference_id=reference_id,
        warnings=warnings,
        error=error,
        metadata=(
            ("environment", "paper"),
        ),
    )


def test_pipeline_checkpoint() -> None:
    value = pipeline_checkpoint()

    assert value.checkpoint_id == "checkpoint-001"
    assert value.event_id == "event-001"
    assert value.stage is PipelineStage.VALIDATION
    assert value.decision is PipelineDecision.PROCEED
    assert value.successful is True
    assert value.is_complete is True
    assert value.stage_position == 2
    assert value.reference_id == "validation-001"


def test_checkpoint_text_is_normalized() -> None:
    value = PipelineCheckpoint(
        checkpoint_id="  checkpoint-001  ",
        event_id="  event-001  ",
        stage=PipelineStage.VALIDATION,
        decision=PipelineDecision.PROCEED,
        started_at=NOW,
        completed_at=NOW,
        successful=True,
        message="  Validation completed.  ",
        reference_id="  validation-001  ",
        metadata=[
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.checkpoint_id == "checkpoint-001"
    assert value.event_id == "event-001"
    assert value.message == "Validation completed."
    assert value.reference_id == "validation-001"


@pytest.mark.parametrize(
    "field_name",
    [
        "checkpoint_id",
        "event_id",
        "message",
    ],
)
def test_checkpoint_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = dict(
        checkpoint_id="checkpoint-001",
        event_id="event-001",
        stage=PipelineStage.VALIDATION,
        decision=PipelineDecision.PROCEED,
        started_at=NOW,
        completed_at=NOW,
        successful=True,
        message="Validation completed.",
    )

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        PipelineCheckpoint(**arguments)


def test_checkpoint_requires_stage_enum() -> None:
    with pytest.raises(
        TypeError,
        match="stage must be a PipelineStage",
    ):
        pipeline_checkpoint(stage="VALIDATION")


def test_checkpoint_requires_decision_enum() -> None:
    with pytest.raises(
        TypeError,
        match="decision must be a PipelineDecision",
    ):
        pipeline_checkpoint(decision="PROCEED")


def test_started_at_requires_timezone() -> None:
    with pytest.raises(
        ValueError,
        match="started_at must be timezone-aware",
    ):
        pipeline_checkpoint(
            started_at=datetime(
                2026,
                8,
                6,
                21,
                30,
            )
        )


def test_completed_at_requires_timezone() -> None:
    with pytest.raises(
        ValueError,
        match="completed_at must be timezone-aware",
    ):
        pipeline_checkpoint(
            completed_at=datetime(
                2026,
                8,
                6,
                21,
                31,
            )
        )


def test_completed_at_must_follow_started_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed_at must not be earlier "
            "than started_at"
        ),
    ):
        pipeline_checkpoint(
            completed_at=NOW - timedelta(seconds=1)
        )


def test_checkpoint_may_be_in_progress() -> None:
    value = pipeline_checkpoint(
        completed_at=None,
    )

    assert value.is_complete is False


def test_successful_checkpoint_rejects_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "successful checkpoints must not "
            "include an error"
        ),
    ):
        pipeline_checkpoint(
            error="failure"
        )


def test_unsuccessful_checkpoint_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "unsuccessful checkpoints require "
            "an error"
        ),
    ):
        pipeline_checkpoint(
            successful=False,
            decision=PipelineDecision.REJECT,
            error=None,
        )


def test_unsuccessful_checkpoint() -> None:
    value = pipeline_checkpoint(
        successful=False,
        decision=PipelineDecision.REJECT,
        error="Validation failed.",
    )

    assert value.successful is False
    assert value.error == "Validation failed."


def test_checkpoint_warnings_are_normalized() -> None:
    value = pipeline_checkpoint(
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        )
    )

    assert value.warnings == (
        "warning one",
        "warning two",
    )


def test_checkpoint_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        PipelineCheckpoint(
            checkpoint_id="checkpoint-001",
            event_id="event-001",
            stage=PipelineStage.VALIDATION,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            completed_at=NOW,
            successful=True,
            message="Validation completed.",
            metadata=(
                ("source", "one"),
                ("source", "two"),
            ),
        )


def test_checkpoint_is_immutable() -> None:
    value = pipeline_checkpoint()

    with pytest.raises(
        FrozenInstanceError
    ):
        value.message = "changed"

def successful_checkpoint(
    *,
    checkpoint_id: str = "checkpoint-001",
    stage: PipelineStage = PipelineStage.RECEIVED,
    started_at: datetime = NOW,
    completed_at: datetime = NOW,
) -> PipelineCheckpoint:
    return PipelineCheckpoint(
        checkpoint_id=checkpoint_id,
        event_id="event-001",
        stage=stage,
        decision=PipelineDecision.PROCEED,
        started_at=started_at,
        completed_at=completed_at,
        successful=True,
        message=f"{stage.value} completed.",
    )


def failed_checkpoint(
    *,
    checkpoint_id: str = "checkpoint-001",
    stage: PipelineStage = PipelineStage.VALIDATION,
    decision: PipelineDecision = PipelineDecision.REJECT,
    started_at: datetime = NOW,
    completed_at: datetime = NOW,
    error: str = "Pipeline validation failed.",
) -> PipelineCheckpoint:
    return PipelineCheckpoint(
        checkpoint_id=checkpoint_id,
        event_id="event-001",
        stage=stage,
        decision=decision,
        started_at=started_at,
        completed_at=completed_at,
        successful=False,
        message=f"{stage.value} failed.",
        error=error,
    )


def completed_result() -> MarketDataPipelineResult:
    stages = (
        PipelineStage.RECEIVED,
        PipelineStage.VALIDATION,
        PipelineStage.DEDUPLICATION,
        PipelineStage.ORDERING,
        PipelineStage.ROUTING,
        PipelineStage.PERSISTENCE,
        PipelineStage.PUBLICATION,
    )

    checkpoints = tuple(
        successful_checkpoint(
            checkpoint_id=f"checkpoint-{index:03d}",
            stage=stage,
        )
        for index, stage in enumerate(stages, start=1)
    )

    return MarketDataPipelineResult(
        event_id="event-001",
        status=PipelineStatus.COMPLETED,
        decision=PipelineDecision.ACCEPT,
        started_at=NOW,
        updated_at=NOW,
        completed_at=NOW,
        checkpoints=checkpoints,
    )


def test_processing_pipeline_result() -> None:
    value = MarketDataPipelineResult(
        event_id="event-001",
        status=PipelineStatus.PROCESSING,
        decision=PipelineDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW,
    )

    assert value.event_id == "event-001"
    assert value.status is PipelineStatus.PROCESSING
    assert value.decision is PipelineDecision.PROCEED
    assert value.is_terminal is False
    assert value.checkpoints == ()
    assert value.latest_checkpoint is None
    assert value.failed_checkpoint is None
    assert value.successful_checkpoint_count == 0


def test_pending_pipeline_result() -> None:
    value = MarketDataPipelineResult(
        event_id="event-001",
        status=PipelineStatus.PENDING,
        decision=PipelineDecision.NO_ACTION,
        started_at=NOW,
        updated_at=NOW,
    )

    assert value.status is PipelineStatus.PENDING
    assert value.is_terminal is False


def test_completed_pipeline_result() -> None:
    value = completed_result()

    assert value.status is PipelineStatus.COMPLETED
    assert value.decision is PipelineDecision.ACCEPT
    assert value.is_terminal is True
    assert value.successful_checkpoint_count == 7
    assert value.failed_checkpoint is None
    assert value.latest_checkpoint is not None
    assert value.latest_checkpoint.stage is (
        PipelineStage.PUBLICATION
    )


def test_rejected_pipeline_result() -> None:
    checkpoint = failed_checkpoint()

    value = MarketDataPipelineResult(
        event_id="event-001",
        status=PipelineStatus.REJECTED,
        decision=PipelineDecision.REJECT,
        started_at=NOW,
        updated_at=NOW,
        completed_at=NOW,
        checkpoints=(checkpoint,),
    )

    assert value.is_terminal is True
    assert value.failed_checkpoint == checkpoint


def test_dropped_pipeline_result() -> None:
    checkpoint = failed_checkpoint(
        stage=PipelineStage.DEDUPLICATION,
        decision=PipelineDecision.DROP,
        error="Duplicate market-data event.",
    )

    value = MarketDataPipelineResult(
        event_id="event-001",
        status=PipelineStatus.DROPPED,
        decision=PipelineDecision.DROP,
        started_at=NOW,
        updated_at=NOW,
        completed_at=NOW,
        checkpoints=(checkpoint,),
    )

    assert value.status is PipelineStatus.DROPPED
    assert value.failed_checkpoint == checkpoint


def test_failed_pipeline_result() -> None:
    checkpoint = failed_checkpoint(
        stage=PipelineStage.PERSISTENCE,
        decision=PipelineDecision.RETRY,
        error="Persistence service unavailable.",
    )

    value = MarketDataPipelineResult(
        event_id="event-001",
        status=PipelineStatus.FAILED,
        decision=PipelineDecision.RETRY,
        started_at=NOW,
        updated_at=NOW,
        completed_at=NOW,
        checkpoints=(checkpoint,),
        error="Persistence service unavailable.",
    )

    assert value.status is PipelineStatus.FAILED
    assert value.error == "Persistence service unavailable."
    assert value.failed_checkpoint == checkpoint


def test_result_event_id_is_normalized() -> None:
    value = MarketDataPipelineResult(
        event_id="  event-001  ",
        status=PipelineStatus.PROCESSING,
        decision=PipelineDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW,
    )

    assert value.event_id == "event-001"


def test_result_event_id_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="event_id must not be empty",
    ):
        MarketDataPipelineResult(
            event_id="   ",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
        )


def test_result_requires_status_enum() -> None:
    with pytest.raises(
        TypeError,
        match="status must be a PipelineStatus",
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status="PROCESSING",
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
        )


def test_result_requires_decision_enum() -> None:
    with pytest.raises(
        TypeError,
        match="decision must be a PipelineDecision",
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision="PROCEED",
            started_at=NOW,
            updated_at=NOW,
        )


def test_result_started_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="started_at must be a datetime",
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at="2026-08-06",
            updated_at=NOW,
        )


def test_result_updated_at_must_follow_start() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "updated_at must not be earlier than started_at"
        ),
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW - timedelta(seconds=1),
        )


def test_result_completed_at_must_follow_update() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed_at must not be earlier than updated_at"
        ),
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.FAILED,
            decision=PipelineDecision.NO_ACTION,
            started_at=NOW,
            updated_at=NOW,
            completed_at=NOW - timedelta(seconds=1),
            checkpoints=(
                failed_checkpoint(
                    decision=PipelineDecision.NO_ACTION,
                ),
            ),
            error="Pipeline failed.",
        )


def test_checkpoints_require_sequence() -> None:
    with pytest.raises(
        TypeError,
        match="checkpoints must be a tuple or list",
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            checkpoints="invalid",
        )


def test_checkpoints_require_models() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "every checkpoint must be a PipelineCheckpoint"
        ),
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            checkpoints=(object(),),
        )


def test_checkpoint_event_id_must_match_result() -> None:
    checkpoint = PipelineCheckpoint(
        checkpoint_id="checkpoint-001",
        event_id="different-event",
        stage=PipelineStage.RECEIVED,
        decision=PipelineDecision.PROCEED,
        started_at=NOW,
        completed_at=NOW,
        successful=True,
        message="Event received.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "checkpoint event_id must match result event_id"
        ),
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            checkpoints=(checkpoint,),
        )


def test_checkpoint_ids_must_be_unique() -> None:
    first = successful_checkpoint(
        checkpoint_id="duplicate",
        stage=PipelineStage.RECEIVED,
    )
    second = successful_checkpoint(
        checkpoint_id="duplicate",
        stage=PipelineStage.VALIDATION,
    )

    with pytest.raises(
        ValueError,
        match="checkpoint IDs must be unique",
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            checkpoints=(first, second),
        )


def test_pipeline_stages_must_be_unique() -> None:
    first = successful_checkpoint(
        checkpoint_id="checkpoint-001",
        stage=PipelineStage.RECEIVED,
    )
    second = successful_checkpoint(
        checkpoint_id="checkpoint-002",
        stage=PipelineStage.RECEIVED,
    )

    with pytest.raises(
        ValueError,
        match="pipeline stages must be unique",
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            checkpoints=(first, second),
        )


def test_checkpoints_must_be_ordered_by_stage() -> None:
    first = successful_checkpoint(
        checkpoint_id="checkpoint-001",
        stage=PipelineStage.VALIDATION,
    )
    second = successful_checkpoint(
        checkpoint_id="checkpoint-002",
        stage=PipelineStage.RECEIVED,
    )

    with pytest.raises(
        ValueError,
        match=(
            "checkpoints must be ordered by pipeline stage"
        ),
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            checkpoints=(first, second),
        )


def test_terminal_result_requires_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "terminal pipeline results require completed_at"
        ),
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.REJECTED,
            decision=PipelineDecision.REJECT,
            started_at=NOW,
            updated_at=NOW,
            completed_at=None,
            checkpoints=(failed_checkpoint(),),
        )


def test_non_terminal_result_rejects_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-terminal pipeline results must not include completed_at"
        ),
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            completed_at=NOW,
        )


def test_pending_result_requires_no_action() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "pending pipeline results require NO_ACTION decision"
        ),
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PENDING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
        )


def test_pending_result_rejects_checkpoints() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "pending pipeline results must not include checkpoints"
        ),
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PENDING,
            decision=PipelineDecision.NO_ACTION,
            started_at=NOW,
            updated_at=NOW,
            checkpoints=(successful_checkpoint(),),
        )


def test_processing_result_requires_proceed() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "processing pipeline results require PROCEED decision"
        ),
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.NO_ACTION,
            started_at=NOW,
            updated_at=NOW,
        )


def test_completed_result_requires_accept() -> None:
    value = completed_result()

    with pytest.raises(
        ValueError,
        match=(
            "completed pipeline results require ACCEPT decision"
        ),
    ):
        MarketDataPipelineResult(
            event_id=value.event_id,
            status=PipelineStatus.COMPLETED,
            decision=PipelineDecision.PROCEED,
            started_at=value.started_at,
            updated_at=value.updated_at,
            completed_at=value.completed_at,
            checkpoints=value.checkpoints,
        )


def test_completed_result_requires_publication_stage() -> None:
    checkpoint = successful_checkpoint(
        stage=PipelineStage.PERSISTENCE,
    )

    with pytest.raises(
        ValueError,
        match=(
            "completed pipeline results must reach the publication stage"
        ),
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.COMPLETED,
            decision=PipelineDecision.ACCEPT,
            started_at=NOW,
            updated_at=NOW,
            completed_at=NOW,
            checkpoints=(checkpoint,),
        )


def test_rejected_result_requires_failed_checkpoint() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "rejected pipeline results require an unsuccessful checkpoint"
        ),
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.REJECTED,
            decision=PipelineDecision.REJECT,
            started_at=NOW,
            updated_at=NOW,
            completed_at=NOW,
            checkpoints=(
                successful_checkpoint(),
            ),
        )


def test_failed_result_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed pipeline results require an error"
        ),
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.FAILED,
            decision=PipelineDecision.RETRY,
            started_at=NOW,
            updated_at=NOW,
            completed_at=NOW,
            checkpoints=(
                failed_checkpoint(
                    decision=PipelineDecision.RETRY,
                ),
            ),
        )


def test_only_failed_result_may_include_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only failed pipeline results may include an error"
        ),
    ):
        MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.REJECTED,
            decision=PipelineDecision.REJECT,
            started_at=NOW,
            updated_at=NOW,
            completed_at=NOW,
            checkpoints=(failed_checkpoint(),),
            error="Unexpected error.",
        )


def test_result_warnings_are_normalized() -> None:
    value = MarketDataPipelineResult(
        event_id="event-001",
        status=PipelineStatus.PROCESSING,
        decision=PipelineDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW,
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        ),
    )

    assert value.warnings == (
        "warning one",
        "warning two",
    )


def test_pipeline_result_is_immutable() -> None:
    value = completed_result()

    with pytest.raises(FrozenInstanceError):
        value.status = PipelineStatus.FAILED

def pipeline_report(
    *,
    report_id: str = "pipeline-report-001",
    request: MarketDataPipelineRequest | None = None,
    result: MarketDataPipelineResult | None = None,
    reported_at: datetime = NOW,
    message: str = "Market-data event processed.",
    warnings: tuple[str, ...] = (),
) -> MarketDataPipelineReport:
    return MarketDataPipelineReport(
        report_id=report_id,
        request=request or pipeline_request(),
        result=result or MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
        ),
        reported_at=reported_at,
        message=message,
        warnings=warnings,
        metadata=(
            ("source", "market-data-pipeline"),
        ),
    )


def test_market_data_pipeline_report() -> None:
    value = pipeline_report()

    assert value.report_id == "pipeline-report-001"
    assert value.event_id == "event-001"
    assert value.event_type is PipelineEventType.QUOTE
    assert value.symbol == "NVDA"
    assert value.status is PipelineStatus.PROCESSING
    assert value.decision is PipelineDecision.PROCEED
    assert value.is_terminal is False
    assert value.reported_at == NOW
    assert value.message == (
        "Market-data event processed."
    )
    assert value.metadata == (
        ("source", "market-data-pipeline"),
    )


def test_completed_pipeline_report() -> None:
    value = pipeline_report(
        result=completed_result(),
    )

    assert value.status is PipelineStatus.COMPLETED
    assert value.decision is PipelineDecision.ACCEPT
    assert value.is_terminal is True
    assert value.result.completed_at == NOW


def test_health_pipeline_report_has_no_symbol() -> None:
    request = pipeline_request(
        event_type=PipelineEventType.HEALTH,
        payload=health_payload(),
    )

    result = MarketDataPipelineResult(
        event_id="event-001",
        status=PipelineStatus.PROCESSING,
        decision=PipelineDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW,
    )

    value = pipeline_report(
        request=request,
        result=result,
    )

    assert value.event_type is PipelineEventType.HEALTH
    assert value.symbol is None


def test_pipeline_report_text_is_normalized() -> None:
    value = MarketDataPipelineReport(
        report_id="  pipeline-report-001  ",
        request=pipeline_request(),
        result=MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
        ),
        reported_at=NOW,
        message="  Market-data event processed.  ",
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        ),
        metadata=[
            ("  source  ", "  market-data-pipeline  "),
        ],
    )

    assert value.report_id == "pipeline-report-001"
    assert value.message == (
        "Market-data event processed."
    )
    assert value.warnings == (
        "warning one",
        "warning two",
    )
    assert value.metadata == (
        ("source", "market-data-pipeline"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_pipeline_report_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "report_id": "pipeline-report-001",
        "request": pipeline_request(),
        "result": MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
        ),
        "reported_at": NOW,
        "message": "Market-data event processed.",
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        MarketDataPipelineReport(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_pipeline_report_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "report_id": "pipeline-report-001",
        "request": pipeline_request(),
        "result": MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
        ),
        "reported_at": NOW,
        "message": "Market-data event processed.",
    }
    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        MarketDataPipelineReport(**arguments)


def test_pipeline_report_requires_request_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "request must be a "
            "MarketDataPipelineRequest"
        ),
    ):
        MarketDataPipelineReport(
            report_id="pipeline-report-001",
            request=object(),
            result=MarketDataPipelineResult(
                event_id="event-001",
                status=PipelineStatus.PROCESSING,
                decision=PipelineDecision.PROCEED,
                started_at=NOW,
                updated_at=NOW,
            ),
            reported_at=NOW,
            message="Market-data event processed.",
        )


def test_pipeline_report_requires_result_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "result must be a "
            "MarketDataPipelineResult"
        ),
    ):
        MarketDataPipelineReport(
            report_id="pipeline-report-001",
            request=pipeline_request(),
            result=object(),
            reported_at=NOW,
            message="Market-data event processed.",
        )


def test_pipeline_reported_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="reported_at must be a datetime",
    ):
        MarketDataPipelineReport(
            report_id="pipeline-report-001",
            request=pipeline_request(),
            result=MarketDataPipelineResult(
                event_id="event-001",
                status=PipelineStatus.PROCESSING,
                decision=PipelineDecision.PROCEED,
                started_at=NOW,
                updated_at=NOW,
            ),
            reported_at="2026-08-06",
            message="Market-data event processed.",
        )


def test_pipeline_reported_at_must_be_timezone_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="reported_at must be timezone-aware",
    ):
        pipeline_report(
            reported_at=datetime(
                2026,
                8,
                6,
                21,
                30,
            )
        )


def test_report_request_and_result_event_ids_must_match(
) -> None:
    result = MarketDataPipelineResult(
        event_id="different-event",
        status=PipelineStatus.PROCESSING,
        decision=PipelineDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result event_id values "
            "must match"
        ),
    ):
        pipeline_report(result=result)


def test_result_start_must_not_precede_request_receipt(
) -> None:
    result = MarketDataPipelineResult(
        event_id="event-001",
        status=PipelineStatus.PROCESSING,
        decision=PipelineDecision.PROCEED,
        started_at=NOW - timedelta(seconds=1),
        updated_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match=(
            "result started_at must not be earlier "
            "than request received_at"
        ),
    ):
        pipeline_report(result=result)


def test_reported_at_must_follow_result_update() -> None:
    result = MarketDataPipelineResult(
        event_id="event-001",
        status=PipelineStatus.PROCESSING,
        decision=PipelineDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW + timedelta(seconds=1),
    )

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier "
            "than result updated_at"
        ),
    ):
        pipeline_report(
            result=result,
            reported_at=NOW,
        )


def test_reported_at_must_follow_result_completion(
) -> None:
    checkpoint = successful_checkpoint(
        stage=PipelineStage.PUBLICATION,
        started_at=NOW,
        completed_at=NOW,
    )

    result = MarketDataPipelineResult(
        event_id="event-001",
        status=PipelineStatus.COMPLETED,
        decision=PipelineDecision.ACCEPT,
        started_at=NOW,
        updated_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
        checkpoints=(checkpoint,),
    )

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier "
            "than result completed_at"
        ),
    ):
        pipeline_report(
            result=result,
            reported_at=NOW,
        )


def test_pipeline_report_warnings_are_normalized(
) -> None:
    value = pipeline_report(
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        )
    )

    assert value.warnings == (
        "warning one",
        "warning two",
    )


def test_pipeline_report_warnings_reject_empty_values(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        pipeline_report(
            warnings=("valid", "   ")
        )


def test_pipeline_report_warnings_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        pipeline_report(
            warnings=("valid", 123)
        )


def test_pipeline_report_metadata_is_normalized(
) -> None:
    value = MarketDataPipelineReport(
        report_id="pipeline-report-001",
        request=pipeline_request(),
        result=MarketDataPipelineResult(
            event_id="event-001",
            status=PipelineStatus.PROCESSING,
            decision=PipelineDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
        ),
        reported_at=NOW,
        message="Market-data event processed.",
        metadata=[
            ("  source  ", "  pipeline  "),
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.metadata == (
        ("source", "pipeline"),
        ("environment", "paper"),
    )


def test_pipeline_report_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        MarketDataPipelineReport(
            report_id="pipeline-report-001",
            request=pipeline_request(),
            result=MarketDataPipelineResult(
                event_id="event-001",
                status=PipelineStatus.PROCESSING,
                decision=PipelineDecision.PROCEED,
                started_at=NOW,
                updated_at=NOW,
            ),
            reported_at=NOW,
            message="Market-data event processed.",
            metadata=(
                ("source", "pipeline"),
                ("source", "duplicate"),
            ),
        )


def test_pipeline_report_metadata_items_must_be_pairs(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        MarketDataPipelineReport(
            report_id="pipeline-report-001",
            request=pipeline_request(),
            result=MarketDataPipelineResult(
                event_id="event-001",
                status=PipelineStatus.PROCESSING,
                decision=PipelineDecision.PROCEED,
                started_at=NOW,
                updated_at=NOW,
            ),
            reported_at=NOW,
            message="Market-data event processed.",
            metadata=(
                ("source",),
            ),
        )


def test_pipeline_report_metadata_keys_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        MarketDataPipelineReport(
            report_id="pipeline-report-001",
            request=pipeline_request(),
            result=MarketDataPipelineResult(
                event_id="event-001",
                status=PipelineStatus.PROCESSING,
                decision=PipelineDecision.PROCEED,
                started_at=NOW,
                updated_at=NOW,
            ),
            reported_at=NOW,
            message="Market-data event processed.",
            metadata=(
                (123, "pipeline"),
            ),
        )


def test_pipeline_report_metadata_values_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        MarketDataPipelineReport(
            report_id="pipeline-report-001",
            request=pipeline_request(),
            result=MarketDataPipelineResult(
                event_id="event-001",
                status=PipelineStatus.PROCESSING,
                decision=PipelineDecision.PROCEED,
                started_at=NOW,
                updated_at=NOW,
            ),
            reported_at=NOW,
            message="Market-data event processed.",
            metadata=(
                ("source", 123),
            ),
        )


def test_pipeline_report_is_immutable() -> None:
    value = pipeline_report()

    with pytest.raises(FrozenInstanceError):
        value.report_id = "changed"