from __future__ import annotations

from .models import Recommendation, ScoreBreakdown, StrategyEvidence


class RecommendationEngine:
    def recommend(self, scores: ScoreBreakdown, evidence: StrategyEvidence) -> tuple[Recommendation, tuple[str, ...]]:
        reasons: list[str] = []
        if evidence.trade_count < 30:
            reasons.append("Insufficient trade sample; collect at least 30 trades.")
            return Recommendation.NEEDS_MORE_DATA, tuple(reasons)
        if scores.risk < 35 or evidence.max_drawdown_pct >= 40:
            reasons.append("Risk profile exceeds promotion thresholds.")
            return Recommendation.RETIRE, tuple(reasons)
        if scores.overall >= 85 and scores.risk >= 65 and scores.operational >= 75:
            reasons.append("High overall, risk, and operational scores support live review.")
            return Recommendation.PROMOTE_TO_LIVE_REVIEW, tuple(reasons)
        if scores.overall >= 70 and scores.risk >= 55:
            reasons.append("Evaluation meets paper-trading promotion thresholds.")
            return Recommendation.PROMOTE_TO_PAPER, tuple(reasons)
        reasons.append("Strategy requires parameter or rule optimization before promotion.")
        return Recommendation.NEEDS_OPTIMIZATION, tuple(reasons)
