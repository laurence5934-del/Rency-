from __future__ import annotations

from ._scoring import clamp, linear_score
from .models import StrategyEvidence


class ConfidenceScoreEngine:
    def calculate(self, evidence: StrategyEvidence) -> float:
        sample = linear_score(float(evidence.trade_count), 10.0, 200.0)
        periods = linear_score(float(len(tuple(evidence.monthly_returns_pct))), 2.0, 24.0)
        persistence = clamp(evidence.profitable_period_ratio * 100.0)
        return round(0.50 * sample + 0.25 * periods + 0.25 * persistence, 4)
