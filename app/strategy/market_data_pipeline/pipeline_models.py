from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TypeAlias

from app.strategy.market_data import (
    MarketBar,
    MarketDataHealthReport,
    MarketQuote,
    MarketSnapshot,
    MarketTrade,
)

class PipelineEventType(str, Enum):
    QUOTE = "QUOTE"
    TRADE = "TRADE"
    BAR = "BAR"
    SNAPSHOT = "SNAPSHOT"
    HEALTH = "HEALTH"


class PipelineStage(str, Enum):
    RECEIVED = "RECEIVED"
    VALIDATION = "VALIDATION"
    DEDUPLICATION = "DEDUPLICATION"
    ORDERING = "ORDERING"
    ROUTING = "ROUTING"
    PERSISTENCE = "PERSISTENCE"
    PUBLICATION = "PUBLICATION"


class PipelineStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    DROPPED = "DROPPED"
    FAILED = "FAILED"


class PipelineDecision(str, Enum):
    PROCEED = "PROCEED"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    DROP = "DROP"
    RETRY = "RETRY"
    NO_ACTION = "NO_ACTION"


MarketDataPayload: TypeAlias = (
    MarketQuote
    | MarketTrade
    | MarketBar
    | MarketSnapshot
    | MarketDataHealthReport
)


PIPELINE_STAGE_POSITIONS: dict[PipelineStage, int] = {
    PipelineStage.RECEIVED: 1,
    PipelineStage.VALIDATION: 2,
    PipelineStage.DEDUPLICATION: 3,
    PipelineStage.ORDERING: 4,
    PipelineStage.ROUTING: 5,
    PipelineStage.PERSISTENCE: 6,
    PipelineStage.PUBLICATION: 7,
}


TERMINAL_PIPELINE_STATUSES: frozenset[
    PipelineStatus
] = frozenset(
    {
        PipelineStatus.COMPLETED,
        PipelineStatus.REJECTED,
        PipelineStatus.DROPPED,
        PipelineStatus.FAILED,
    }
)


class PipelineModelSupport:
    @staticmethod
    def required_text(
        value: str,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return normalized

    @staticmethod
    def optional_text(
        value: str | None,
        field_name: str,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string or None"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return normalized

    @staticmethod
    def aware_datetime(
        value: datetime,
        field_name: str,
    ) -> datetime:
        if not isinstance(value, datetime):
            raise TypeError(
                f"{field_name} must be a datetime"
            )

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                f"{field_name} must be timezone-aware"
            )

        return value

    @staticmethod
    def normalize_metadata(
        values: (
            tuple[tuple[str, str], ...]
            | list[tuple[str, str]]
        ),
    ) -> tuple[tuple[str, str], ...]:
        if not isinstance(values, (tuple, list)):
            raise TypeError(
                "metadata must be a tuple or list"
            )

        normalized: list[tuple[str, str]] = []
        seen_keys: set[str] = set()

        for item in values:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
            ):
                raise TypeError(
                    "each metadata item must be "
                    "a two-item tuple"
                )

            raw_key, raw_value = item

            if not isinstance(raw_key, str):
                raise TypeError(
                    "metadata keys must be strings"
                )

            if not isinstance(raw_value, str):
                raise TypeError(
                    "metadata values must be strings"
                )

            key = raw_key.strip()
            value = raw_value.strip()

            if not key:
                raise ValueError(
                    "metadata keys must not be empty"
                )

            if key in seen_keys:
                raise ValueError(
                    "metadata keys must be unique"
                )

            seen_keys.add(key)
            normalized.append((key, value))

        return tuple(normalized)

    @staticmethod
    def normalize_warnings(
        values: tuple[str, ...] | list[str],
    ) -> tuple[str, ...]:
        if not isinstance(values, (tuple, list)):
            raise TypeError(
                "warnings must be a tuple or list"
            )

        normalized: list[str] = []
        seen: set[str] = set()

        for warning in values:
            if not isinstance(warning, str):
                raise TypeError(
                    "every warning must be a string"
                )

            value = warning.strip()

            if not value:
                raise ValueError(
                    "warnings must not contain "
                    "empty values"
                )

            if value not in seen:
                seen.add(value)
                normalized.append(value)

        return tuple(normalized)

    @staticmethod
    def payload_event_type(
        payload: MarketDataPayload,
    ) -> PipelineEventType:
        if isinstance(payload, MarketQuote):
            return PipelineEventType.QUOTE

        if isinstance(payload, MarketTrade):
            return PipelineEventType.TRADE

        if isinstance(payload, MarketBar):
            return PipelineEventType.BAR

        if isinstance(payload, MarketSnapshot):
            return PipelineEventType.SNAPSHOT

        if isinstance(
            payload,
            MarketDataHealthReport,
        ):
            return PipelineEventType.HEALTH

        raise TypeError(
            "payload must be a supported "
            "market-data model"
        )

    @staticmethod
    def payload_timestamp(
        payload: MarketDataPayload,
    ) -> datetime:
        if isinstance(
            payload,
            (
                MarketQuote,
                MarketTrade,
                MarketSnapshot,
            ),
        ):
            return payload.timestamp

        if isinstance(payload, MarketBar):
            return payload.end_time

        if isinstance(
            payload,
            MarketDataHealthReport,
        ):
            return payload.evaluated_at

        raise TypeError(
            "payload must be a supported "
            "market-data model"
        )

    @staticmethod
    def payload_symbol(
        payload: MarketDataPayload,
    ) -> str | None:
        if isinstance(
            payload,
            (
                MarketQuote,
                MarketTrade,
                MarketBar,
                MarketSnapshot,
            ),
        ):
            return payload.symbol

        if isinstance(
            payload,
            MarketDataHealthReport,
        ):
            return None

        raise TypeError(
            "payload must be a supported "
            "market-data model"
        )
@dataclass(frozen=True, slots=True)
class MarketDataPipelineRequest:
    event_id: str
    correlation_id: str
    source: str
    event_type: PipelineEventType
    payload: MarketDataPayload
    received_at: datetime
    sequence_number: int
    is_replay: bool = False
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        event_id = PipelineModelSupport.required_text(
            self.event_id,
            "event_id",
        )

        correlation_id = (
            PipelineModelSupport.required_text(
                self.correlation_id,
                "correlation_id",
            )
        )

        source = PipelineModelSupport.required_text(
            self.source,
            "source",
        )

        if not isinstance(
            self.event_type,
            PipelineEventType,
        ):
            raise TypeError(
                "event_type must be a PipelineEventType"
            )

        actual_event_type = (
            PipelineModelSupport.payload_event_type(
                self.payload
            )
        )

        if self.event_type is not actual_event_type:
            raise ValueError(
                "event_type must match the payload type"
            )

        PipelineModelSupport.aware_datetime(
            self.received_at,
            "received_at",
        )

        payload_timestamp = (
            PipelineModelSupport.payload_timestamp(
                self.payload
            )
        )

        if self.received_at < payload_timestamp:
            raise ValueError(
                "received_at must not be earlier "
                "than the payload timestamp"
            )

        if not isinstance(
            self.sequence_number,
            int,
        ):
            raise TypeError(
                "sequence_number must be an integer"
            )

        if isinstance(
            self.sequence_number,
            bool,
        ):
            raise TypeError(
                "sequence_number must be an integer"
            )

        if self.sequence_number < 0:
            raise ValueError(
                "sequence_number must not be negative"
            )

        if not isinstance(self.is_replay, bool):
            raise TypeError(
                "is_replay must be a bool"
            )

        metadata = (
            PipelineModelSupport.normalize_metadata(
                self.metadata
            )
        )

        object.__setattr__(
            self,
            "event_id",
            event_id,
        )

        object.__setattr__(
            self,
            "correlation_id",
            correlation_id,
        )

        object.__setattr__(
            self,
            "source",
            source,
        )

        object.__setattr__(
            self,
            "metadata",
            metadata,
        )

    @property
    def symbol(self) -> str | None:
        return PipelineModelSupport.payload_symbol(
            self.payload
        )

    @property
    def payload_timestamp(self) -> datetime:
        return PipelineModelSupport.payload_timestamp(
            self.payload
        )

    @property
    def is_health_event(self) -> bool:
        return (
            self.event_type
            is PipelineEventType.HEALTH
        )
@dataclass(frozen=True, slots=True)
class PipelineCheckpoint:
    checkpoint_id: str
    event_id: str
    stage: PipelineStage
    decision: PipelineDecision
    started_at: datetime
    completed_at: datetime | None
    successful: bool
    message: str
    reference_id: str | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        checkpoint_id = (
            PipelineModelSupport.required_text(
                self.checkpoint_id,
                "checkpoint_id",
            )
        )

        event_id = PipelineModelSupport.required_text(
            self.event_id,
            "event_id",
        )

        message = PipelineModelSupport.required_text(
            self.message,
            "message",
        )

        reference_id = (
            PipelineModelSupport.optional_text(
                self.reference_id,
                "reference_id",
            )
        )

        error = PipelineModelSupport.optional_text(
            self.error,
            "error",
        )

        if not isinstance(
            self.stage,
            PipelineStage,
        ):
            raise TypeError(
                "stage must be a PipelineStage"
            )

        if not isinstance(
            self.decision,
            PipelineDecision,
        ):
            raise TypeError(
                "decision must be a PipelineDecision"
            )

        if not isinstance(self.successful, bool):
            raise TypeError(
                "successful must be a bool"
            )

        PipelineModelSupport.aware_datetime(
            self.started_at,
            "started_at",
        )

        if self.completed_at is not None:
            PipelineModelSupport.aware_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.started_at:
                raise ValueError(
                    "completed_at must not be earlier "
                    "than started_at"
                )

        if self.successful:
            if error is not None:
                raise ValueError(
                    "successful checkpoints must not "
                    "include an error"
                )

            if self.decision in {
                PipelineDecision.REJECT,
                PipelineDecision.DROP,
                PipelineDecision.RETRY,
                PipelineDecision.NO_ACTION,
            }:
                raise ValueError(
                    "successful checkpoints require "
                    "a non-terminal decision"
                )
        else:
            if error is None:
                raise ValueError(
                    "unsuccessful checkpoints require "
                    "an error"
                )

            if self.decision in {
                PipelineDecision.PROCEED,
                PipelineDecision.ACCEPT,
            }:
                raise ValueError(
                    "unsuccessful checkpoints must not "
                    "use a successful decision"
                )

        warnings = (
            PipelineModelSupport.normalize_warnings(
                self.warnings
            )
        )

        metadata = (
            PipelineModelSupport.normalize_metadata(
                self.metadata
            )
        )

        object.__setattr__(
            self,
            "checkpoint_id",
            checkpoint_id,
        )

        object.__setattr__(
            self,
            "event_id",
            event_id,
        )

        object.__setattr__(
            self,
            "message",
            message,
        )

        object.__setattr__(
            self,
            "reference_id",
            reference_id,
        )

        object.__setattr__(
            self,
            "warnings",
            warnings,
        )

        object.__setattr__(
            self,
            "error",
            error,
        )

        object.__setattr__(
            self,
            "metadata",
            metadata,
        )

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    @property
    def stage_position(self) -> int:
        return PIPELINE_STAGE_POSITIONS[
            self.stage
        ]

@dataclass(frozen=True, slots=True)
class MarketDataPipelineResult:
    event_id: str
    status: PipelineStatus
    decision: PipelineDecision
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    checkpoints: tuple[PipelineCheckpoint, ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        event_id = PipelineModelSupport.required_text(
            self.event_id,
            "event_id",
        )

        if not isinstance(
            self.status,
            PipelineStatus,
        ):
            raise TypeError(
                "status must be a PipelineStatus"
            )

        if not isinstance(
            self.decision,
            PipelineDecision,
        ):
            raise TypeError(
                "decision must be a PipelineDecision"
            )

        PipelineModelSupport.aware_datetime(
            self.started_at,
            "started_at",
        )

        PipelineModelSupport.aware_datetime(
            self.updated_at,
            "updated_at",
        )

        if self.updated_at < self.started_at:
            raise ValueError(
                "updated_at must not be earlier "
                "than started_at"
            )

        if self.completed_at is not None:
            PipelineModelSupport.aware_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.updated_at:
                raise ValueError(
                    "completed_at must not be earlier "
                    "than updated_at"
                )

        if not isinstance(
            self.checkpoints,
            (tuple, list),
        ):
            raise TypeError(
                "checkpoints must be a tuple or list"
            )

        checkpoints = tuple(self.checkpoints)

        for checkpoint in checkpoints:
            if not isinstance(
                checkpoint,
                PipelineCheckpoint,
            ):
                raise TypeError(
                    "every checkpoint must be a "
                    "PipelineCheckpoint"
                )

            if checkpoint.event_id != event_id:
                raise ValueError(
                    "checkpoint event_id must match "
                    "result event_id"
                )

            if checkpoint.started_at < self.started_at:
                raise ValueError(
                    "checkpoint started_at must not be "
                    "earlier than result started_at"
                )

            checkpoint_end = (
                checkpoint.completed_at
                or checkpoint.started_at
            )

            if checkpoint_end > self.updated_at:
                raise ValueError(
                    "checkpoint time must not be later "
                    "than result updated_at"
                )

        checkpoint_ids = tuple(
            checkpoint.checkpoint_id
            for checkpoint in checkpoints
        )

        if len(checkpoint_ids) != len(
            set(checkpoint_ids)
        ):
            raise ValueError(
                "checkpoint IDs must be unique"
            )

        checkpoint_stages = tuple(
            checkpoint.stage
            for checkpoint in checkpoints
        )

        if len(checkpoint_stages) != len(
            set(checkpoint_stages)
        ):
            raise ValueError(
                "pipeline stages must be unique"
            )

        stage_positions = tuple(
            checkpoint.stage_position
            for checkpoint in checkpoints
        )

        if stage_positions != tuple(
            sorted(stage_positions)
        ):
            raise ValueError(
                "checkpoints must be ordered "
                "by pipeline stage"
            )

        warnings = (
            PipelineModelSupport.normalize_warnings(
                self.warnings
            )
        )

        error = PipelineModelSupport.optional_text(
            self.error,
            "error",
        )

        is_terminal = (
            self.status
            in TERMINAL_PIPELINE_STATUSES
        )

        if is_terminal:
            if self.completed_at is None:
                raise ValueError(
                    "terminal pipeline results require "
                    "completed_at"
                )
        elif self.completed_at is not None:
            raise ValueError(
                "non-terminal pipeline results must not "
                "include completed_at"
            )

        if self.status is PipelineStatus.PENDING:
            if self.decision is not (
                PipelineDecision.NO_ACTION
            ):
                raise ValueError(
                    "pending pipeline results require "
                    "NO_ACTION decision"
                )

            if checkpoints:
                raise ValueError(
                    "pending pipeline results must not "
                    "include checkpoints"
                )

        if self.status is PipelineStatus.PROCESSING:
            if self.decision is not (
                PipelineDecision.PROCEED
            ):
                raise ValueError(
                    "processing pipeline results require "
                    "PROCEED decision"
                )

        if self.status is PipelineStatus.COMPLETED:
            if self.decision is not (
                PipelineDecision.ACCEPT
            ):
                raise ValueError(
                    "completed pipeline results require "
                    "ACCEPT decision"
                )

            if not checkpoints:
                raise ValueError(
                    "completed pipeline results require "
                    "checkpoints"
                )

            if not all(
                checkpoint.successful
                for checkpoint in checkpoints
            ):
                raise ValueError(
                    "completed pipeline results require "
                    "successful checkpoints"
                )

            if (
                checkpoints[-1].stage
                is not PipelineStage.PUBLICATION
            ):
                raise ValueError(
                    "completed pipeline results must "
                    "reach the publication stage"
                )

        if self.status is PipelineStatus.REJECTED:
            if self.decision is not (
                PipelineDecision.REJECT
            ):
                raise ValueError(
                    "rejected pipeline results require "
                    "REJECT decision"
                )

            if not any(
                not checkpoint.successful
                for checkpoint in checkpoints
            ):
                raise ValueError(
                    "rejected pipeline results require "
                    "an unsuccessful checkpoint"
                )

        if self.status is PipelineStatus.DROPPED:
            if self.decision is not (
                PipelineDecision.DROP
            ):
                raise ValueError(
                    "dropped pipeline results require "
                    "DROP decision"
                )

            if not any(
                not checkpoint.successful
                for checkpoint in checkpoints
            ):
                raise ValueError(
                    "dropped pipeline results require "
                    "an unsuccessful checkpoint"
                )

        if self.status is PipelineStatus.FAILED:
            if self.decision not in {
                PipelineDecision.RETRY,
                PipelineDecision.NO_ACTION,
            }:
                raise ValueError(
                    "failed pipeline results require "
                    "RETRY or NO_ACTION decision"
                )

            if error is None:
                raise ValueError(
                    "failed pipeline results require "
                    "an error"
                )

            if not any(
                not checkpoint.successful
                for checkpoint in checkpoints
            ):
                raise ValueError(
                    "failed pipeline results require "
                    "an unsuccessful checkpoint"
                )

        if (
            self.status is not PipelineStatus.FAILED
            and error is not None
        ):
            raise ValueError(
                "only failed pipeline results may "
                "include an error"
            )

        object.__setattr__(
            self,
            "event_id",
            event_id,
        )

        object.__setattr__(
            self,
            "checkpoints",
            checkpoints,
        )

        object.__setattr__(
            self,
            "warnings",
            warnings,
        )

        object.__setattr__(
            self,
            "error",
            error,
        )

    @property
    def is_terminal(self) -> bool:
        return (
            self.status
            in TERMINAL_PIPELINE_STATUSES
        )

    @property
    def successful_checkpoint_count(self) -> int:
        return sum(
            1
            for checkpoint in self.checkpoints
            if checkpoint.successful
        )

    @property
    def failed_checkpoint(
        self,
    ) -> PipelineCheckpoint | None:
        for checkpoint in self.checkpoints:
            if not checkpoint.successful:
                return checkpoint

        return None

    @property
    def latest_checkpoint(
        self,
    ) -> PipelineCheckpoint | None:
        if not self.checkpoints:
            return None

        return self.checkpoints[-1]
@dataclass(frozen=True, slots=True)
class MarketDataPipelineReport:
    report_id: str
    request: MarketDataPipelineRequest
    result: MarketDataPipelineResult
    reported_at: datetime
    message: str
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        report_id = PipelineModelSupport.required_text(
            self.report_id,
            "report_id",
        )

        if not isinstance(
            self.request,
            MarketDataPipelineRequest,
        ):
            raise TypeError(
                "request must be a "
                "MarketDataPipelineRequest"
            )

        if not isinstance(
            self.result,
            MarketDataPipelineResult,
        ):
            raise TypeError(
                "result must be a "
                "MarketDataPipelineResult"
            )

        message = PipelineModelSupport.required_text(
            self.message,
            "message",
        )

        PipelineModelSupport.aware_datetime(
            self.reported_at,
            "reported_at",
        )

        if self.request.event_id != self.result.event_id:
            raise ValueError(
                "request and result event_id values "
                "must match"
            )

        if self.result.started_at < self.request.received_at:
            raise ValueError(
                "result started_at must not be earlier "
                "than request received_at"
            )

        if self.reported_at < self.result.updated_at:
            raise ValueError(
                "reported_at must not be earlier "
                "than result updated_at"
            )

        if (
            self.result.completed_at is not None
            and self.reported_at
            < self.result.completed_at
        ):
            raise ValueError(
                "reported_at must not be earlier "
                "than result completed_at"
            )

        warnings = (
            PipelineModelSupport.normalize_warnings(
                self.warnings
            )
        )

        metadata = (
            PipelineModelSupport.normalize_metadata(
                self.metadata
            )
        )

        object.__setattr__(
            self,
            "report_id",
            report_id,
        )

        object.__setattr__(
            self,
            "message",
            message,
        )

        object.__setattr__(
            self,
            "warnings",
            warnings,
        )

        object.__setattr__(
            self,
            "metadata",
            metadata,
        )

    @property
    def event_id(self) -> str:
        return self.request.event_id

    @property
    def event_type(self) -> PipelineEventType:
        return self.request.event_type

    @property
    def symbol(self) -> str | None:
        return self.request.symbol

    @property
    def status(self) -> PipelineStatus:
        return self.result.status

    @property
    def decision(self) -> PipelineDecision:
        return self.result.decision

    @property
    def is_terminal(self) -> bool:
        return self.result.is_terminal