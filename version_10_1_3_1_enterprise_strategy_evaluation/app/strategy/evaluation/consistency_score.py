from __future__ import annotations

from statistics import pstdev

from ._scoring import clamp, linear_score
from .models import StrategyEvidence


class ConsistencyScoreEngine:
    def calculate(self, evidence: StrategyEvidence) -> float:
        returns = tuple(float(x) for x in evidence.monthly_returns_pct)
        if not returns:
            return round(clamp(evidence.profitable_period_ratio * 100.0), 4)
        profitable_ratio = sum(1 for value in returns if value > 0) / len(returns)
        dispersion = pstdev(returns) if len(returns) > 1 else 0.0
        stability = linear_score(dispersion, 20.0, 2.0)
        return round(0.70 * profitable_ratio * 100.0 + 0.30 * stability, 4)
