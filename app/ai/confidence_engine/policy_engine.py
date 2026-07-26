from __future__ import annotations

from dataclasses import dataclass

from .models import (
    ConfidenceBand,
    ConfidenceDecision,
    ConfidenceInput,
    ConfidencePolicySnapshot,
)


@dataclass(frozen=True, slots=True)
class ConfidencePolicy:
    trust_threshold: float = 0.72
    review_threshold: float = 0.52
    maximum_total_penalty: float = 0.45
    minimum_data_completeness: float = 0.60
    minimum_validation_quality: float = 0.60

    def __post_init__(self) -> None:
        if not 0.0 <= self.review_threshold <= self.trust_threshold <= 1.0:
            raise ValueError("invalid confidence thresholds")
        if not 0.0 <= self.maximum_total_penalty <= 1.0:
            raise ValueError("maximum_total_penalty must be between 0.0 and 1.0")

    def snapshot(self) -> ConfidencePolicySnapshot:
        return ConfidencePolicySnapshot(
            trust_threshold=self.trust_threshold,
            review_threshold=self.review_threshold,
            maximum_total_penalty=self.maximum_total_penalty,
            minimum_data_completeness=self.minimum_data_completeness,
            minimum_validation_quality=self.minimum_validation_quality,
        )


class ConfidencePolicyEngine:
    def __init__(self, policy: ConfidencePolicy | None = None) -> None:
        self.policy = policy or ConfidencePolicy()

    def band(self, score: float) -> ConfidenceBand:
        if score >= 0.90:
            return ConfidenceBand.VERY_HIGH
        if score >= 0.75:
            return ConfidenceBand.HIGH
        if score >= 0.55:
            return ConfidenceBand.MODERATE
        if score >= 0.35:
            return ConfidenceBand.LOW
        return ConfidenceBand.VERY_LOW

    def decide(
        self,
        score: float,
        source: ConfidenceInput,
        total_penalty: float,
    ) -> tuple[ConfidenceDecision, tuple[str, ...]]:
        reasons: list[str] = []

        if source.data_completeness < self.policy.minimum_data_completeness:
            reasons.append("INSUFFICIENT_DATA_COMPLETENESS")

        if source.validation_quality < self.policy.minimum_validation_quality:
            reasons.append("INSUFFICIENT_VALIDATION_QUALITY")

        if total_penalty > self.policy.maximum_total_penalty:
            reasons.append("EXCESSIVE_TOTAL_PENALTY")

        if reasons:
            return ConfidenceDecision.REJECT, tuple(reasons)

        if score >= self.policy.trust_threshold:
            return ConfidenceDecision.TRUST, ()

        if score >= self.policy.review_threshold:
            return ConfidenceDecision.REVIEW, ("CONFIDENCE_REQUIRES_REVIEW",)

        return ConfidenceDecision.REJECT, ("CONFIDENCE_BELOW_THRESHOLD",)
