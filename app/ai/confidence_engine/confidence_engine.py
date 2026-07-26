from __future__ import annotations

from .metrics import ConfidenceMetrics
from .models import ConfidenceDecision, ConfidenceInput, ConfidenceReport
from .policy_engine import ConfidencePolicy, ConfidencePolicyEngine
from .scoring_engine import ConfidenceScoringEngine


class EnterpriseConfidenceEngine:
    def __init__(
        self,
        *,
        policy: ConfidencePolicy | None = None,
        scoring_engine: ConfidenceScoringEngine | None = None,
        metrics: ConfidenceMetrics | None = None,
    ) -> None:
        self._policy_engine = ConfidencePolicyEngine(policy)
        self._scoring_engine = scoring_engine or ConfidenceScoringEngine()
        self._metrics = metrics or ConfidenceMetrics()

    def evaluate(
        self,
        source: ConfidenceInput,
        *,
        correlation_id: str | None = None,
    ) -> ConfidenceReport:
        score, factors, penalties = self._scoring_engine.calculate(source)
        total_penalty = sum(penalties.values())
        decision, reasons = self._policy_engine.decide(
            score,
            source,
            total_penalty,
        )
        band = self._policy_engine.band(score)

        report = ConfidenceReport.create(
            symbol=source.symbol,
            score=score,
            band=band,
            decision=decision,
            factors=factors,
            penalties=penalties,
            reasons=reasons,
            policy=self._policy_engine.policy.snapshot(),
            correlation_id=correlation_id,
        )

        self._metrics.increment("evaluations")
        self._metrics.increment(
            {
                ConfidenceDecision.TRUST: "trusted",
                ConfidenceDecision.REVIEW: "reviewed",
                ConfidenceDecision.REJECT: "rejected",
            }[decision]
        )
        return report

    def metrics(self) -> dict[str, int]:
        return self._metrics.snapshot()

    def health(self) -> dict[str, object]:
        return {
            "status": "HEALTHY",
            "metrics": self.metrics(),
            "policy": self._policy_engine.policy.snapshot(),
        }
