from __future__ import annotations

from threading import RLock
from uuid import uuid4

from .audit_log import EvaluationAuditLog
from .confidence_score import ConfidenceScoreEngine
from .consistency_score import ConsistencyScoreEngine
from .metrics import EvaluationMetrics
from .models import EvaluationWeights, ScoreBreakdown, StrategyEvaluation, StrategyEvidence
from .operational_score import OperationalScoreEngine
from .performance_score import PerformanceScoreEngine
from .recommendation_engine import RecommendationEngine
from .risk_score import RiskScoreEngine


class StrategyEvaluationEngine:
    def __init__(self, weights: EvaluationWeights | None = None) -> None:
        self.weights = weights or EvaluationWeights()
        self.performance = PerformanceScoreEngine()
        self.risk = RiskScoreEngine()
        self.consistency = ConsistencyScoreEngine()
        self.confidence = ConfidenceScoreEngine()
        self.operational = OperationalScoreEngine()
        self.recommendations = RecommendationEngine()
        self.metrics = EvaluationMetrics()
        self.audit_log = EvaluationAuditLog()
        self._evaluations: dict[str, StrategyEvaluation] = {}
        self._lock = RLock()

    def evaluate(self, evidence: StrategyEvidence) -> StrategyEvaluation:
        p = self.performance.calculate(evidence)
        r = self.risk.calculate(evidence)
        c = self.consistency.calculate(evidence)
        cf = self.confidence.calculate(evidence)
        o = self.operational.calculate(evidence)
        overall = round(
            p * self.weights.performance
            + r * self.weights.risk
            + c * self.weights.consistency
            + cf * self.weights.confidence
            + o * self.weights.operational,
            4,
        )
        scores = ScoreBreakdown(p, r, c, cf, o, overall)
        recommendation, reasons = self.recommendations.recommend(scores, evidence)
        result = StrategyEvaluation(
            evaluation_id=str(uuid4()),
            strategy_id=evidence.strategy_id,
            strategy_version=evidence.strategy_version,
            scores=scores,
            recommendation=recommendation,
            reasons=reasons,
            evidence_summary={
                "trade_count": evidence.trade_count,
                "max_drawdown_pct": evidence.max_drawdown_pct,
                "annualized_return_pct": evidence.annualized_return_pct,
            },
        )
        key = f"{evidence.strategy_id}:{evidence.strategy_version}"
        with self._lock:
            self._evaluations[key] = result
        self.metrics.increment("evaluations_total")
        self.metrics.increment(f"recommendation_{recommendation.value}")
        self.audit_log.record("strategy_evaluated", key, overall_score=overall, recommendation=recommendation.value)
        return result

    def get(self, strategy_id: str, strategy_version: str) -> StrategyEvaluation | None:
        with self._lock:
            return self._evaluations.get(f"{strategy_id}:{strategy_version}")

    def list_evaluations(self) -> tuple[StrategyEvaluation, ...]:
        with self._lock:
            return tuple(self._evaluations.values())
