from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import UUID, uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConfidenceBand(str, Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class ConfidenceDecision(str, Enum):
    TRUST = "TRUST"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class ConfidenceFactor:
    name: str
    score: float
    weight: float
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("factor name cannot be empty")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("factor score must be between 0.0 and 1.0")
        if self.weight < 0.0:
            raise ValueError("factor weight cannot be negative")


@dataclass(frozen=True, slots=True)
class ConfidenceInput:
    symbol: str
    consensus_score: float
    agreement_ratio: float
    contributor_reputation: float
    validation_quality: float
    data_completeness: float
    freshness_score: float
    stability_score: float
    volatility_penalty: float = 0.0
    uncertainty_penalty: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        for name in (
            "consensus_score",
            "agreement_ratio",
            "contributor_reputation",
            "validation_quality",
            "data_completeness",
            "freshness_score",
            "stability_score",
            "volatility_penalty",
            "uncertainty_penalty",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class ConfidencePolicySnapshot:
    trust_threshold: float
    review_threshold: float
    maximum_total_penalty: float
    minimum_data_completeness: float
    minimum_validation_quality: float


@dataclass(frozen=True, slots=True)
class ConfidenceReport:
    confidence_id: UUID
    symbol: str
    created_at_utc: str
    score: float
    band: ConfidenceBand
    decision: ConfidenceDecision
    factors: tuple[ConfidenceFactor, ...]
    penalties: Mapping[str, float]
    reasons: tuple[str, ...]
    policy: ConfidencePolicySnapshot
    correlation_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        symbol: str,
        score: float,
        band: ConfidenceBand,
        decision: ConfidenceDecision,
        factors: tuple[ConfidenceFactor, ...],
        penalties: Mapping[str, float],
        reasons: tuple[str, ...],
        policy: ConfidencePolicySnapshot,
        correlation_id: str | None = None,
    ) -> "ConfidenceReport":
        return cls(
            confidence_id=uuid4(),
            symbol=symbol,
            created_at_utc=utc_now(),
            score=score,
            band=band,
            decision=decision,
            factors=factors,
            penalties=dict(penalties),
            reasons=reasons,
            policy=policy,
            correlation_id=correlation_id,
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["confidence_id"] = str(self.confidence_id)
        result["band"] = self.band.value
        result["decision"] = self.decision.value
        return result
