from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TypeAlias



class AllocationAction(str, Enum):
    OPEN = "OPEN"
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    CLOSE = "CLOSE"
    HOLD = "HOLD"
    REBALANCE = "REBALANCE"


class AllocationDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class AllocationStrength(str, Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class AllocationStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class AllocationDecision(str, Enum):
    PROCEED = "PROCEED"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    HOLD = "HOLD"
    CANCEL = "CANCEL"
    RETRY = "RETRY"
    NO_ACTION = "NO_ACTION"


class AllocationStage(str, Enum):
    RECEIVED = "RECEIVED"
    VALIDATION = "VALIDATION"
    PORTFOLIO_CONTEXT = "PORTFOLIO_CONTEXT"
    SIGNAL_CONTEXT = "SIGNAL_CONTEXT"
    EXPOSURE_ANALYSIS = "EXPOSURE_ANALYSIS"
    SIZING = "SIZING"
    FINALIZATION = "FINALIZATION"


ALLOCATION_STAGE_POSITIONS: dict[
    AllocationStage,
    int,
] = {
    AllocationStage.RECEIVED: 1,
    AllocationStage.VALIDATION: 2,
    AllocationStage.PORTFOLIO_CONTEXT: 3,
    AllocationStage.SIGNAL_CONTEXT: 4,
    AllocationStage.EXPOSURE_ANALYSIS: 5,
    AllocationStage.SIZING: 6,
    AllocationStage.FINALIZATION: 7,
}


TERMINAL_ALLOCATION_STATUSES: frozenset[
    AllocationStatus
] = frozenset(
    {
        AllocationStatus.APPROVED,
        AllocationStatus.REJECTED,
        AllocationStatus.CANCELLED,
        AllocationStatus.FAILED,
    }
)


Metadata: TypeAlias = tuple[
    tuple[str, str],
    ...,
]


class AllocationModelSupport:
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
    def percentage(
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

    @staticmethod
    def positive_integer(
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

        if value <= 0:
            raise ValueError(
                f"{field_name} must be positive"
            )

        return value

@dataclass(frozen=True, slots=True)
class PortfolioAllocationRequest:
    request_id: str
    correlation_id: str
    strategy_id: str
    portfolio_id: str
    signal_id: str
    symbol: str
    action: AllocationAction
    direction: AllocationDirection
    strength: AllocationStrength
    target_allocation_percent: int
    confidence: int
    created_at: datetime
    sequence_number: int
    requested_by: str
    is_replay: bool = False
    metadata: Metadata = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        request_id = AllocationModelSupport.required_text(
            self.request_id,
            "request_id",
        )

        correlation_id = AllocationModelSupport.required_text(
            self.correlation_id,
            "correlation_id",
        )

        strategy_id = AllocationModelSupport.required_text(
            self.strategy_id,
            "strategy_id",
        )

        portfolio_id = AllocationModelSupport.required_text(
            self.portfolio_id,
            "portfolio_id",
        )

        signal_id = AllocationModelSupport.required_text(
            self.signal_id,
            "signal_id",
        )

        symbol = AllocationModelSupport.required_text(
            self.symbol,
            "symbol",
        ).upper()

        requested_by = AllocationModelSupport.required_text(
            self.requested_by,
            "requested_by",
        )

        if not isinstance(
            self.action,
            AllocationAction,
        ):
            raise TypeError(
                "action must be an AllocationAction"
            )

        if not isinstance(
            self.direction,
            AllocationDirection,
        ):
            raise TypeError(
                "direction must be an AllocationDirection"
            )

        if not isinstance(
            self.strength,
            AllocationStrength,
        ):
            raise TypeError(
                "strength must be an AllocationStrength"
            )

        target_allocation_percent = (
            AllocationModelSupport.percentage(
                self.target_allocation_percent,
                "target_allocation_percent",
            )
        )

        confidence = AllocationModelSupport.percentage(
            self.confidence,
            "confidence",
        )

        AllocationModelSupport.aware_datetime(
            self.created_at,
            "created_at",
        )

        sequence_number = (
            AllocationModelSupport.non_negative_integer(
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
            self.action is AllocationAction.HOLD
            and self.direction is not AllocationDirection.FLAT
        ):
            raise ValueError(
                "HOLD allocations require FLAT direction"
            )

        if (
            self.action is AllocationAction.CLOSE
            and target_allocation_percent != 0
        ):
            raise ValueError(
                "CLOSE allocations require "
                "target_allocation_percent of 0"
            )

        if (
            self.action is AllocationAction.OPEN
            and self.direction is AllocationDirection.FLAT
        ):
            raise ValueError(
                "OPEN allocations require LONG or SHORT direction"
            )

        if (
            self.action
            in {
                AllocationAction.INCREASE,
                AllocationAction.DECREASE,
                AllocationAction.REBALANCE,
            }
            and self.direction is AllocationDirection.FLAT
        ):
            raise ValueError(
                f"{self.action.value} allocations require "
                "LONG or SHORT direction"
            )

        if (
            self.action is AllocationAction.HOLD
            and target_allocation_percent != 0
        ):
            raise ValueError(
                "HOLD allocations require "
                "target_allocation_percent of 0"
            )

        metadata = (
            AllocationModelSupport.normalize_metadata(
                self.metadata
            )
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
            "signal_id",
            signal_id,
        )

        object.__setattr__(
            self,
            "symbol",
            symbol,
        )

        object.__setattr__(
            self,
            "target_allocation_percent",
            target_allocation_percent,
        )

        object.__setattr__(
            self,
            "confidence",
            confidence,
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
            self.action is not AllocationAction.HOLD
            and self.direction is not AllocationDirection.FLAT
        )

    @property
    def is_opening(self) -> bool:
        return self.action is AllocationAction.OPEN

    @property
    def is_closing(self) -> bool:
        return self.action is AllocationAction.CLOSE

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 80
@dataclass(frozen=True, slots=True)
class PortfolioAllocation:
    allocation_id: str
    request_id: str
    correlation_id: str
    strategy_id: str
    portfolio_id: str
    signal_id: str
    symbol: str
    action: AllocationAction
    direction: AllocationDirection
    strength: AllocationStrength
    target_allocation_percent: int
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
        allocation_id = (
            AllocationModelSupport.required_text(
                self.allocation_id,
                "allocation_id",
            )
        )

        request_id = (
            AllocationModelSupport.required_text(
                self.request_id,
                "request_id",
            )
        )

        correlation_id = (
            AllocationModelSupport.required_text(
                self.correlation_id,
                "correlation_id",
            )
        )

        strategy_id = (
            AllocationModelSupport.required_text(
                self.strategy_id,
                "strategy_id",
            )
        )

        portfolio_id = (
            AllocationModelSupport.required_text(
                self.portfolio_id,
                "portfolio_id",
            )
        )

        signal_id = (
            AllocationModelSupport.required_text(
                self.signal_id,
                "signal_id",
            )
        )

        symbol = (
            AllocationModelSupport.required_text(
                self.symbol,
                "symbol",
            ).upper()
        )

        rationale = (
            AllocationModelSupport.required_text(
                self.rationale,
                "rationale",
            )
        )

        if not isinstance(
            self.action,
            AllocationAction,
        ):
            raise TypeError(
                "action must be an AllocationAction"
            )

        if not isinstance(
            self.direction,
            AllocationDirection,
        ):
            raise TypeError(
                "direction must be an AllocationDirection"
            )

        if not isinstance(
            self.strength,
            AllocationStrength,
        ):
            raise TypeError(
                "strength must be an AllocationStrength"
            )

        target_allocation_percent = (
            AllocationModelSupport.percentage(
                self.target_allocation_percent,
                "target_allocation_percent",
            )
        )

        confidence = (
            AllocationModelSupport.percentage(
                self.confidence,
                "confidence",
            )
        )

        AllocationModelSupport.aware_datetime(
            self.generated_at,
            "generated_at",
        )

        if self.expires_at is not None:
            AllocationModelSupport.aware_datetime(
                self.expires_at,
                "expires_at",
            )

            if self.expires_at < self.generated_at:
                raise ValueError(
                    "expires_at must not be earlier "
                    "than generated_at"
                )

        if (
            self.action is AllocationAction.HOLD
            and self.direction
            is not AllocationDirection.FLAT
        ):
            raise ValueError(
                "HOLD allocations require FLAT direction"
            )

        if (
            self.action is AllocationAction.CLOSE
            and target_allocation_percent != 0
        ):
            raise ValueError(
                "CLOSE allocations require "
                "target_allocation_percent of 0"
            )

        if (
            self.action is AllocationAction.OPEN
            and self.direction
            is AllocationDirection.FLAT
        ):
            raise ValueError(
                "OPEN allocations require "
                "LONG or SHORT direction"
            )

        if (
            self.action
            in {
                AllocationAction.INCREASE,
                AllocationAction.DECREASE,
                AllocationAction.REBALANCE,
            }
            and self.direction
            is AllocationDirection.FLAT
        ):
            raise ValueError(
                f"{self.action.value} allocations require "
                "LONG or SHORT direction"
            )

        if (
            self.action is AllocationAction.HOLD
            and target_allocation_percent != 0
        ):
            raise ValueError(
                "HOLD allocations require "
                "target_allocation_percent of 0"
            )

        warnings = (
            AllocationModelSupport.normalize_warnings(
                self.warnings
            )
        )

        metadata = (
            AllocationModelSupport.normalize_metadata(
                self.metadata
            )
        )

        object.__setattr__(
            self,
            "allocation_id",
            allocation_id,
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
            "signal_id",
            signal_id,
        )

        object.__setattr__(
            self,
            "symbol",
            symbol,
        )

        object.__setattr__(
            self,
            "target_allocation_percent",
            target_allocation_percent,
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
            self.action is not AllocationAction.HOLD
            and self.direction
            is not AllocationDirection.FLAT
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
        AllocationModelSupport.aware_datetime(
            value,
            "value",
        )

        if self.expires_at is None:
            return False

        return value > self.expires_at
@dataclass(frozen=True, slots=True)
class PortfolioAllocationResult:
    request_id: str
    correlation_id: str
    status: AllocationStatus
    decision: AllocationDecision
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    allocation: PortfolioAllocation | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None
    metadata: Metadata = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        request_id = AllocationModelSupport.required_text(
            self.request_id,
            "request_id",
        )

        correlation_id = AllocationModelSupport.required_text(
            self.correlation_id,
            "correlation_id",
        )

        if not isinstance(
            self.status,
            AllocationStatus,
        ):
            raise TypeError(
                "status must be an AllocationStatus"
            )

        if not isinstance(
            self.decision,
            AllocationDecision,
        ):
            raise TypeError(
                "decision must be an AllocationDecision"
            )

        AllocationModelSupport.aware_datetime(
            self.started_at,
            "started_at",
        )

        AllocationModelSupport.aware_datetime(
            self.updated_at,
            "updated_at",
        )

        if self.updated_at < self.started_at:
            raise ValueError(
                "updated_at must not be earlier "
                "than started_at"
            )

        if self.completed_at is not None:
            AllocationModelSupport.aware_datetime(
                self.completed_at,
                "completed_at",
            )

            if self.completed_at < self.updated_at:
                raise ValueError(
                    "completed_at must not be earlier "
                    "than updated_at"
                )

        if (
            self.allocation is not None
            and not isinstance(
                self.allocation,
                PortfolioAllocation,
            )
        ):
            raise TypeError(
                "allocation must be a "
                "PortfolioAllocation or None"
            )

        if self.allocation is not None:
            if (
                self.allocation.request_id
                != request_id
            ):
                raise ValueError(
                    "allocation request_id must match "
                    "result request_id"
                )

            if (
                self.allocation.correlation_id
                != correlation_id
            ):
                raise ValueError(
                    "allocation correlation_id must match "
                    "result correlation_id"
                )

            if (
                self.allocation.generated_at
                < self.started_at
            ):
                raise ValueError(
                    "allocation generated_at must not be "
                    "earlier than result started_at"
                )

            if (
                self.allocation.generated_at
                > self.updated_at
            ):
                raise ValueError(
                    "allocation generated_at must not be "
                    "later than result updated_at"
                )

        warnings = (
            AllocationModelSupport.normalize_warnings(
                self.warnings
            )
        )

        error = AllocationModelSupport.optional_text(
            self.error,
            "error",
        )

        metadata = (
            AllocationModelSupport.normalize_metadata(
                self.metadata
            )
        )

        is_terminal = (
            self.status
            in TERMINAL_ALLOCATION_STATUSES
        )

        if is_terminal:
            if self.completed_at is None:
                raise ValueError(
                    "terminal allocation results require "
                    "completed_at"
                )
        elif self.completed_at is not None:
            raise ValueError(
                "non-terminal allocation results must not "
                "include completed_at"
            )

        if self.status is AllocationStatus.PENDING:
            if (
                self.decision
                is not AllocationDecision.NO_ACTION
            ):
                raise ValueError(
                    "pending allocation results require "
                    "NO_ACTION decision"
                )

            if self.allocation is not None:
                raise ValueError(
                    "pending allocation results must not "
                    "include an allocation"
                )

        if self.status is AllocationStatus.ACTIVE:
            if (
                self.decision
                is not AllocationDecision.PROCEED
            ):
                raise ValueError(
                    "active allocation results require "
                    "PROCEED decision"
                )

        if self.status is AllocationStatus.APPROVED:
            if (
                self.decision
                is not AllocationDecision.APPROVE
            ):
                raise ValueError(
                    "approved allocation results require "
                    "APPROVE decision"
                )

            if self.allocation is None:
                raise ValueError(
                    "approved allocation results require "
                    "an allocation"
                )

        if self.status is AllocationStatus.REJECTED:
            if (
                self.decision
                is not AllocationDecision.REJECT
            ):
                raise ValueError(
                    "rejected allocation results require "
                    "REJECT decision"
                )

        if self.status is AllocationStatus.CANCELLED:
            if (
                self.decision
                is not AllocationDecision.CANCEL
            ):
                raise ValueError(
                    "cancelled allocation results require "
                    "CANCEL decision"
                )

        if self.status is AllocationStatus.FAILED:
            if self.decision not in {
                AllocationDecision.RETRY,
                AllocationDecision.NO_ACTION,
            }:
                raise ValueError(
                    "failed allocation results require "
                    "RETRY or NO_ACTION decision"
                )

            if error is None:
                raise ValueError(
                    "failed allocation results require "
                    "an error"
                )

        if (
            self.status is not AllocationStatus.FAILED
            and error is not None
        ):
            raise ValueError(
                "only failed allocation results may "
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
            in TERMINAL_ALLOCATION_STATUSES
        )

    @property
    def is_successful(self) -> bool:
        return (
            self.status
            is AllocationStatus.APPROVED
        )

    @property
    def has_allocation(self) -> bool:
        return self.allocation is not None
@dataclass(frozen=True, slots=True)
class PortfolioAllocationReport:
    report_id: str
    request: PortfolioAllocationRequest
    result: PortfolioAllocationResult
    reported_at: datetime
    message: str
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    metadata: Metadata = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        report_id = AllocationModelSupport.required_text(
            self.report_id,
            "report_id",
        )

        if not isinstance(
            self.request,
            PortfolioAllocationRequest,
        ):
            raise TypeError(
                "request must be a "
                "PortfolioAllocationRequest"
            )

        if not isinstance(
            self.result,
            PortfolioAllocationResult,
        ):
            raise TypeError(
                "result must be a "
                "PortfolioAllocationResult"
            )

        message = AllocationModelSupport.required_text(
            self.message,
            "message",
        )

        AllocationModelSupport.aware_datetime(
            self.reported_at,
            "reported_at",
        )

        if (
            self.request.request_id
            != self.result.request_id
        ):
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

        if (
            self.result.started_at
            < self.request.created_at
        ):
            raise ValueError(
                "result started_at must not be earlier "
                "than request created_at"
            )

        if (
            self.reported_at
            < self.result.updated_at
        ):
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

        if self.result.allocation is not None:
            allocation = self.result.allocation

            if (
                allocation.strategy_id
                != self.request.strategy_id
            ):
                raise ValueError(
                    "allocation strategy_id must match request"
                )

            if (
                allocation.portfolio_id
                != self.request.portfolio_id
            ):
                raise ValueError(
                    "allocation portfolio_id must match request"
                )

            if (
                allocation.signal_id
                != self.request.signal_id
            ):
                raise ValueError(
                    "allocation signal_id must match request"
                )

            if (
                allocation.symbol
                != self.request.symbol
            ):
                raise ValueError(
                    "allocation symbol must match request"
                )

            if (
                allocation.action
                is not self.request.action
            ):
                raise ValueError(
                    "allocation action must match request"
                )

            if (
                allocation.direction
                is not self.request.direction
            ):
                raise ValueError(
                    "allocation direction must match request"
                )

        warnings = (
            AllocationModelSupport.normalize_warnings(
                self.warnings
            )
        )

        metadata = (
            AllocationModelSupport.normalize_metadata(
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
    def signal_id(self) -> str:
        return self.request.signal_id

    @property
    def symbol(self) -> str:
        return self.request.symbol

    @property
    def status(self) -> AllocationStatus:
        return self.result.status

    @property
    def decision(self) -> AllocationDecision:
        return self.result.decision

    @property
    def allocation(
        self,
    ) -> PortfolioAllocation | None:
        return self.result.allocation

    @property
    def is_terminal(self) -> bool:
        return self.result.is_terminal