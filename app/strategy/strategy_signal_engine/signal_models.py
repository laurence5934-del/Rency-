from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TypeAlias
from dataclasses import dataclass, field


class SignalType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    SCALE_IN = "SCALE_IN"
    SCALE_OUT = "SCALE_OUT"
    HEDGE = "HEDGE"
    REBALANCE = "REBALANCE"
    HOLD = "HOLD"


class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class SignalStrength(str, Enum):
    VERY_WEAK = "VERY_WEAK"
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"


class SignalStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class SignalDecision(str, Enum):
    PROCEED = "PROCEED"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    HOLD = "HOLD"
    CANCEL = "CANCEL"
    RETRY = "RETRY"
    NO_ACTION = "NO_ACTION"


class SignalStage(str, Enum):
    RECEIVED = "RECEIVED"
    VALIDATION = "VALIDATION"
    MARKET_CONTEXT = "MARKET_CONTEXT"
    STRATEGY_EVALUATION = "STRATEGY_EVALUATION"
    CONFIDENCE = "CONFIDENCE"
    RISK_PRECHECK = "RISK_PRECHECK"
    FINALIZATION = "FINALIZATION"


SIGNAL_STAGE_POSITIONS: dict[
    SignalStage,
    int,
] = {
    SignalStage.RECEIVED: 1,
    SignalStage.VALIDATION: 2,
    SignalStage.MARKET_CONTEXT: 3,
    SignalStage.STRATEGY_EVALUATION: 4,
    SignalStage.CONFIDENCE: 5,
    SignalStage.RISK_PRECHECK: 6,
    SignalStage.FINALIZATION: 7,
}


TERMINAL_SIGNAL_STATUSES: frozenset[
    SignalStatus
] = frozenset(
    {
        SignalStatus.ACCEPTED,
        SignalStatus.REJECTED,
        SignalStatus.EXPIRED,
        SignalStatus.CANCELLED,
        SignalStatus.FAILED,
    }
)


Metadata: TypeAlias = tuple[
    tuple[str, str],
    ...,
]


class SignalModelSupport:
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
        if not isinstance(
            values,
            (tuple, list),
        ):
            raise TypeError(
                "metadata must be a tuple or list"
            )

        normalized: list[
            tuple[str, str]
        ] = []

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
            normalized.append(
                (key, value)
            )

        return tuple(normalized)

    @staticmethod
    def normalize_warnings(
        values: tuple[str, ...] | list[str],
    ) -> tuple[str, ...]:
        if not isinstance(
            values,
            (tuple, list),
        ):
            raise TypeError(
                "warnings must be a tuple or list"
            )

        normalized: list[str] = []
        seen: set[str] = set()

        for warning in values:
            if not isinstance(
                warning,
                str,
            ):
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
    def confidence_value(
        value: int,
        field_name: str = "confidence",
    ) -> int:
        if not isinstance(value, int):
            raise TypeError(
                f"{field_name} must be an integer"
            )

        if isinstance(value, bool):
            raise TypeError(
                f"{field_name} must be an integer"
            )

        if value < 0 or value > 100:
            raise ValueError(
                f"{field_name} must be between 0 and 100"
            )

        return value

    @staticmethod
    def non_negative_integer(
        value: int,
        field_name: str,
    ) -> int:
        if not isinstance(value, int):
            raise TypeError(
                f"{field_name} must be an integer"
            )

        if isinstance(value, bool):
            raise TypeError(
                f"{field_name} must be an integer"
            )

        if value < 0:
            raise ValueError(
                f"{field_name} must not be negative"
            )

        return value
@dataclass(frozen=True, slots=True)
class StrategySignalRequest:
    request_id: str
    correlation_id: str
    strategy_id: str
    portfolio_id: str
    symbol: str
    signal_type: SignalType
    direction: SignalDirection
    strength: SignalStrength
    confidence: int
    market_data_correlation_id: str
    created_at: datetime
    sequence_number: int
    requested_by: str
    is_replay: bool = False
    metadata: Metadata = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        request_id = SignalModelSupport.required_text(
            self.request_id,
            "request_id",
        )

        correlation_id = SignalModelSupport.required_text(
            self.correlation_id,
            "correlation_id",
        )

        strategy_id = SignalModelSupport.required_text(
            self.strategy_id,
            "strategy_id",
        )

        portfolio_id = SignalModelSupport.required_text(
            self.portfolio_id,
            "portfolio_id",
        )

        symbol = SignalModelSupport.required_text(
            self.symbol,
            "symbol",
        ).upper()

        market_data_correlation_id = (
            SignalModelSupport.required_text(
                self.market_data_correlation_id,
                "market_data_correlation_id",
            )
        )

        requested_by = SignalModelSupport.required_text(
            self.requested_by,
            "requested_by",
        )

        if not isinstance(
            self.signal_type,
            SignalType,
        ):
            raise TypeError(
                "signal_type must be a SignalType"
            )

        if not isinstance(
            self.direction,
            SignalDirection,
        ):
            raise TypeError(
                "direction must be a SignalDirection"
            )

        if not isinstance(
            self.strength,
            SignalStrength,
        ):
            raise TypeError(
                "strength must be a SignalStrength"
            )

        confidence = (
            SignalModelSupport.confidence_value(
                self.confidence
            )
        )

        SignalModelSupport.aware_datetime(
            self.created_at,
            "created_at",
        )

        sequence_number = (
            SignalModelSupport.non_negative_integer(
                self.sequence_number,
                "sequence_number",
            )
        )

        if not isinstance(
            self.is_replay,
            bool,
        ):
            raise TypeError(
                "is_replay must be a bool"
            )

        if (
            self.signal_type is SignalType.HOLD
            and self.direction is not SignalDirection.FLAT
        ):
            raise ValueError(
                "HOLD signals require FLAT direction"
            )

        if (
            self.signal_type is SignalType.ENTRY
            and self.direction is SignalDirection.FLAT
        ):
            raise ValueError(
                "ENTRY signals require LONG or SHORT direction"
            )

        if (
            self.signal_type
            in {
                SignalType.SCALE_IN,
                SignalType.SCALE_OUT,
                SignalType.HEDGE,
            }
            and self.direction is SignalDirection.FLAT
        ):
            raise ValueError(
                f"{self.signal_type.value} signals require "
                "LONG or SHORT direction"
            )

        metadata = SignalModelSupport.normalize_metadata(
            self.metadata
        )

        object.__setattr__(
            self,
            "request_id",
            request_id,
        )

        object.__setattr__(
            self,
            "correlation_id",
            correlation_id,
        )

        object.__setattr__(
            self,
            "strategy_id",
            strategy_id,
        )

        object.__setattr__(
            self,
            "portfolio_id",
            portfolio_id,
        )

        object.__setattr__(
            self,
            "symbol",
            symbol,
        )

        object.__setattr__(
            self,
            "confidence",
            confidence,
        )

        object.__setattr__(
            self,
            "market_data_correlation_id",
            market_data_correlation_id,
        )

        object.__setattr__(
            self,
            "sequence_number",
            sequence_number,
        )

        object.__setattr__(
            self,
            "requested_by",
            requested_by,
        )

        object.__setattr__(
            self,
            "metadata",
            metadata,
        )

    @property
    def is_actionable(self) -> bool:
        return (
            self.signal_type is not SignalType.HOLD
            and self.direction is not SignalDirection.FLAT
        )

    @property
    def is_entry_signal(self) -> bool:
        return self.signal_type is SignalType.ENTRY

    @property
    def is_exit_signal(self) -> bool:
        return self.signal_type is SignalType.EXIT

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 80
@dataclass(frozen=True, slots=True)
class StrategySignal:
    signal_id: str
    request_id: str
    correlation_id: str
    strategy_id: str
    portfolio_id: str
    symbol: str
    signal_type: SignalType
    direction: SignalDirection
    strength: SignalStrength
    confidence: int
    generated_at: datetime
    expires_at: datetime | None
    rationale: str
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    metadata: Metadata = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        signal_id = SignalModelSupport.required_text(
            self.signal_id,
            "signal_id",
        )

        request_id = SignalModelSupport.required_text(
            self.request_id,
            "request_id",
        )

        correlation_id = SignalModelSupport.required_text(
            self.correlation_id,
            "correlation_id",
        )

        strategy_id = SignalModelSupport.required_text(
            self.strategy_id,
            "strategy_id",
        )

        portfolio_id = SignalModelSupport.required_text(
            self.portfolio_id,
            "portfolio_id",
        )

        symbol = SignalModelSupport.required_text(
            self.symbol,
            "symbol",
        ).upper()

        rationale = SignalModelSupport.required_text(
            self.rationale,
            "rationale",
        )

        if not isinstance(
            self.signal_type,
            SignalType,
        ):
            raise TypeError(
                "signal_type must be a SignalType"
            )

        if not isinstance(
            self.direction,
            SignalDirection,
        ):
            raise TypeError(
                "direction must be a SignalDirection"
            )

        if not isinstance(
            self.strength,
            SignalStrength,
        ):
            raise TypeError(
                "strength must be a SignalStrength"
            )

        confidence = (
            SignalModelSupport.confidence_value(
                self.confidence
            )
        )

        SignalModelSupport.aware_datetime(
            self.generated_at,
            "generated_at",
        )

        if self.expires_at is not None:
            SignalModelSupport.aware_datetime(
                self.expires_at,
                "expires_at",
            )

            if self.expires_at < self.generated_at:
                raise ValueError(
                    "expires_at must not be earlier "
                    "than generated_at"
                )

        if (
            self.signal_type is SignalType.HOLD
            and self.direction is not SignalDirection.FLAT
        ):
            raise ValueError(
                "HOLD signals require FLAT direction"
            )

        if (
            self.signal_type is SignalType.ENTRY
            and self.direction is SignalDirection.FLAT
        ):
            raise ValueError(
                "ENTRY signals require LONG or SHORT direction"
            )

        if (
            self.signal_type
            in {
                SignalType.SCALE_IN,
                SignalType.SCALE_OUT,
                SignalType.HEDGE,
            }
            and self.direction is SignalDirection.FLAT
        ):
            raise ValueError(
                f"{self.signal_type.value} signals require "
                "LONG or SHORT direction"
            )

        warnings = (
            SignalModelSupport.normalize_warnings(
                self.warnings
            )
        )

        metadata = (
            SignalModelSupport.normalize_metadata(
                self.metadata
            )
        )

        object.__setattr__(
            self,
            "signal_id",
            signal_id,
        )

        object.__setattr__(
            self,
            "request_id",
            request_id,
        )

        object.__setattr__(
            self,
            "correlation_id",
            correlation_id,
        )

        object.__setattr__(
            self,
            "strategy_id",
            strategy_id,
        )

        object.__setattr__(
            self,
            "portfolio_id",
            portfolio_id,
        )

        object.__setattr__(
            self,
            "symbol",
            symbol,
        )

        object.__setattr__(
            self,
            "confidence",
            confidence,
        )

        object.__setattr__(
            self,
            "rationale",
            rationale,
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
    def is_actionable(self) -> bool:
        return (
            self.signal_type is not SignalType.HOLD
            and self.direction is not SignalDirection.FLAT
        )

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 80

    @property
    def has_expiration(self) -> bool:
        return self.expires_at is not None

    def is_expired_at(
        self,
        value: datetime,
    ) -> bool:
        SignalModelSupport.aware_datetime(
            value,
            "value",
        )

        if self.expires_at is None:
            return False

        return value > self.expires_at
@dataclass(frozen=True, slots=True)
class StrategySignalResult:
    request_id: str
    correlation_id: str
    status: SignalStatus
    decision: SignalDecision
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    signal: StrategySignal | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None
    metadata: Metadata = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        request_id = SignalModelSupport.required_text(
            self.request_id,
            "request_id",
        )

        correlation_id = SignalModelSupport.required_text(
            self.correlation_id,
            "correlation_id",
        )

        if not isinstance(
            self.status,
            SignalStatus,
        ):
            raise TypeError(
                "status must be a SignalStatus"
            )

        if not isinstance(
            self.decision,
            SignalDecision,
        ):
            raise TypeError(
                "decision must be a SignalDecision"
            )

        SignalModelSupport.aware_datetime(
            self.started_at,
            "started_at",
        )

        SignalModelSupport.aware_datetime(
            self.updated_at,
            "updated_at",
        )

        if self.updated_at < self.started_at:
            raise ValueError(
                "updated_at must not be earlier "
                "than started_at"
            )

        if self.completed_at is not None:
            SignalModelSupport.aware_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.updated_at:
                raise ValueError(
                    "completed_at must not be earlier "
                    "than updated_at"
                )

        if (
            self.signal is not None
            and not isinstance(
                self.signal,
                StrategySignal,
            )
        ):
            raise TypeError(
                "signal must be a StrategySignal or None"
            )

        if self.signal is not None:
            if self.signal.request_id != request_id:
                raise ValueError(
                    "signal request_id must match "
                    "result request_id"
                )

            if self.signal.correlation_id != correlation_id:
                raise ValueError(
                    "signal correlation_id must match "
                    "result correlation_id"
                )

            if self.signal.generated_at < self.started_at:
                raise ValueError(
                    "signal generated_at must not be earlier "
                    "than result started_at"
                )

            if self.signal.generated_at > self.updated_at:
                raise ValueError(
                    "signal generated_at must not be later "
                    "than result updated_at"
                )

        warnings = (
            SignalModelSupport.normalize_warnings(
                self.warnings
            )
        )

        error = SignalModelSupport.optional_text(
            self.error,
            "error",
        )

        metadata = (
            SignalModelSupport.normalize_metadata(
                self.metadata
            )
        )

        is_terminal = (
            self.status
            in TERMINAL_SIGNAL_STATUSES
        )

        if is_terminal:
            if self.completed_at is None:
                raise ValueError(
                    "terminal signal results require "
                    "completed_at"
                )
        elif self.completed_at is not None:
            raise ValueError(
                "non-terminal signal results must not "
                "include completed_at"
            )

        if self.status is SignalStatus.PENDING:
            if self.decision is not SignalDecision.NO_ACTION:
                raise ValueError(
                    "pending signal results require "
                    "NO_ACTION decision"
                )

            if self.signal is not None:
                raise ValueError(
                    "pending signal results must not "
                    "include a signal"
                )

        if self.status is SignalStatus.ACTIVE:
            if self.decision is not SignalDecision.PROCEED:
                raise ValueError(
                    "active signal results require "
                    "PROCEED decision"
                )

        if self.status is SignalStatus.ACCEPTED:
            if self.decision is not SignalDecision.ACCEPT:
                raise ValueError(
                    "accepted signal results require "
                    "ACCEPT decision"
                )

            if self.signal is None:
                raise ValueError(
                    "accepted signal results require "
                    "a signal"
                )

        if self.status is SignalStatus.REJECTED:
            if self.decision is not SignalDecision.REJECT:
                raise ValueError(
                    "rejected signal results require "
                    "REJECT decision"
                )

        if self.status is SignalStatus.EXPIRED:
            if self.decision is not SignalDecision.NO_ACTION:
                raise ValueError(
                    "expired signal results require "
                    "NO_ACTION decision"
                )

            if self.signal is None:
                raise ValueError(
                    "expired signal results require "
                    "a signal"
                )

        if self.status is SignalStatus.CANCELLED:
            if self.decision is not SignalDecision.CANCEL:
                raise ValueError(
                    "cancelled signal results require "
                    "CANCEL decision"
                )

        if self.status is SignalStatus.FAILED:
            if self.decision not in {
                SignalDecision.RETRY,
                SignalDecision.NO_ACTION,
            }:
                raise ValueError(
                    "failed signal results require "
                    "RETRY or NO_ACTION decision"
                )

            if error is None:
                raise ValueError(
                    "failed signal results require "
                    "an error"
                )

        if (
            self.status is not SignalStatus.FAILED
            and error is not None
        ):
            raise ValueError(
                "only failed signal results may "
                "include an error"
            )

        object.__setattr__(
            self,
            "request_id",
            request_id,
        )

        object.__setattr__(
            self,
            "correlation_id",
            correlation_id,
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
    def is_terminal(self) -> bool:
        return (
            self.status
            in TERMINAL_SIGNAL_STATUSES
        )

    @property
    def is_successful(self) -> bool:
        return self.status is SignalStatus.ACCEPTED

    @property
    def has_signal(self) -> bool:
        return self.signal is not None
@dataclass(frozen=True, slots=True)
class StrategySignalReport:
    report_id: str
    request: StrategySignalRequest
    result: StrategySignalResult
    reported_at: datetime
    message: str
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    metadata: Metadata = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        report_id = SignalModelSupport.required_text(
            self.report_id,
            "report_id",
        )

        if not isinstance(
            self.request,
            StrategySignalRequest,
        ):
            raise TypeError(
                "request must be a StrategySignalRequest"
            )

        if not isinstance(
            self.result,
            StrategySignalResult,
        ):
            raise TypeError(
                "result must be a StrategySignalResult"
            )

        message = SignalModelSupport.required_text(
            self.message,
            "message",
        )

        SignalModelSupport.aware_datetime(
            self.reported_at,
            "reported_at",
        )

        if self.request.request_id != self.result.request_id:
            raise ValueError(
                "request and result request_id values "
                "must match"
            )

        if (
            self.request.correlation_id
            != self.result.correlation_id
        ):
            raise ValueError(
                "request and result correlation_id values "
                "must match"
            )

        if self.result.started_at < self.request.created_at:
            raise ValueError(
                "result started_at must not be earlier "
                "than request created_at"
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

        if self.result.signal is not None:
            signal = self.result.signal

            if signal.strategy_id != self.request.strategy_id:
                raise ValueError(
                    "signal strategy_id must match request"
                )

            if signal.portfolio_id != self.request.portfolio_id:
                raise ValueError(
                    "signal portfolio_id must match request"
                )

            if signal.symbol != self.request.symbol:
                raise ValueError(
                    "signal symbol must match request"
                )

            if signal.signal_type is not self.request.signal_type:
                raise ValueError(
                    "signal signal_type must match request"
                )

            if signal.direction is not self.request.direction:
                raise ValueError(
                    "signal direction must match request"
                )

        warnings = SignalModelSupport.normalize_warnings(
            self.warnings
        )

        metadata = SignalModelSupport.normalize_metadata(
            self.metadata
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
    def request_id(self) -> str:
        return self.request.request_id

    @property
    def correlation_id(self) -> str:
        return self.request.correlation_id

    @property
    def strategy_id(self) -> str:
        return self.request.strategy_id

    @property
    def portfolio_id(self) -> str:
        return self.request.portfolio_id

    @property
    def symbol(self) -> str:
        return self.request.symbol

    @property
    def status(self) -> SignalStatus:
        return self.result.status

    @property
    def decision(self) -> SignalDecision:
        return self.result.decision

    @property
    def signal(self) -> StrategySignal | None:
        return self.result.signal

    @property
    def is_terminal(self) -> bool:
        return self.result.is_terminal