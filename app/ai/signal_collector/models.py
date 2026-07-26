from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import UUID, uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SignalType(str, Enum):
    TECHNICAL = "TECHNICAL"
    FUNDAMENTAL = "FUNDAMENTAL"
    SENTIMENT = "SENTIMENT"
    NEWS = "NEWS"
    MACRO = "MACRO"
    ORDER_FLOW = "ORDER_FLOW"
    OPTIONS_FLOW = "OPTIONS_FLOW"
    MARKET_REGIME = "MARKET_REGIME"
    PORTFOLIO = "PORTFOLIO"
    RISK = "RISK"
    MODEL = "MODEL"
    STRATEGY = "STRATEGY"
    MANUAL = "MANUAL"
    OTHER = "OTHER"


class SignalDirection(str, Enum):
    STRONGLY_BEARISH = "STRONGLY_BEARISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    BULLISH = "BULLISH"
    STRONGLY_BULLISH = "STRONGLY_BULLISH"


class SignalPriority(int, Enum):
    LOW = 10
    NORMAL = 20
    HIGH = 30
    CRITICAL = 40


class SignalStatus(str, Enum):
    RECEIVED = "RECEIVED"
    NORMALIZED = "NORMALIZED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"
    EXPIRED = "EXPIRED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class RawSignal:
    provider_id: str
    signal_type: SignalType
    symbol: str
    value: float
    confidence: float
    observed_at_utc: str
    direction: SignalDirection = SignalDirection.NEUTRAL
    priority: SignalPriority = SignalPriority.NORMAL
    expires_at_utc: str | None = None
    source_event_id: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id cannot be empty")
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        if not -1.0 <= self.value <= 1.0:
            raise ValueError("value must be between -1.0 and 1.0")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class NormalizedSignal:
    signal_id: UUID
    fingerprint: str
    provider_id: str
    signal_type: SignalType
    symbol: str
    value: float
    confidence: float
    direction: SignalDirection
    priority: SignalPriority
    quality_score: float
    observed_at_utc: str
    received_at_utc: str
    expires_at_utc: str | None
    source_event_id: str | None
    status: SignalStatus
    payload: Mapping[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.fingerprint.strip():
            raise ValueError("fingerprint cannot be empty")
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError("quality_score must be between 0.0 and 1.0")

    @classmethod
    def create(
        cls,
        *,
        fingerprint: str,
        raw: RawSignal,
        quality_score: float,
        status: SignalStatus = SignalStatus.NORMALIZED,
    ) -> "NormalizedSignal":
        return cls(
            signal_id=uuid4(),
            fingerprint=fingerprint,
            provider_id=raw.provider_id,
            signal_type=raw.signal_type,
            symbol=raw.symbol.upper().strip(),
            value=raw.value,
            confidence=raw.confidence,
            direction=raw.direction,
            priority=raw.priority,
            quality_score=quality_score,
            observed_at_utc=raw.observed_at_utc,
            received_at_utc=utc_now(),
            expires_at_utc=raw.expires_at_utc,
            source_event_id=raw.source_event_id,
            status=status,
            payload=dict(raw.payload),
            tags=tuple(raw.tags),
        )

    @property
    def weighted_score(self) -> float:
        return self.value * self.confidence * self.quality_score

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["signal_id"] = str(self.signal_id)
        data["signal_type"] = self.signal_type.value
        data["direction"] = self.direction.value
        data["priority"] = self.priority.value
        data["status"] = self.status.value
        data["weighted_score"] = self.weighted_score
        return data


@dataclass(frozen=True, slots=True)
class CollectionResult:
    accepted: tuple[NormalizedSignal, ...] = ()
    rejected: tuple[NormalizedSignal, ...] = ()
    duplicates: tuple[NormalizedSignal, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def total(self) -> int:
        return len(self.accepted) + len(self.rejected) + len(self.duplicates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": [item.to_dict() for item in self.accepted],
            "rejected": [item.to_dict() for item in self.rejected],
            "duplicates": [item.to_dict() for item in self.duplicates],
            "errors": list(self.errors),
            "total": self.total,
        }
