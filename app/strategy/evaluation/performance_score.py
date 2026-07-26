from __future__ import annotations

from ._scoring import clamp, linear_score
from .models import StrategyEvidence


class PerformanceScoreEngine:
    def calculate(self, evidence: StrategyEvidence) -> float:
        return round(
            0.30 * linear_score(evidence.annualized_return_pct, -10.0, 25.0)
            + 0.20 * linear_score(evidence.net_return_pct, -10.0, 40.0)
            + 0.20 * linear_score(evidence.win_rate_pct, 30.0, 70.0)
            + 0.20 * linear_score(evidence.profit_factor, 0.7, 2.0)
            + 0.10 * linear_score(evidence.expectancy, -1.0, 2.0),
            4,
        )
