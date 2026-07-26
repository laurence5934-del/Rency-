from __future__ import annotations

from ._scoring import linear_score
from .models import StrategyEvidence


class RiskScoreEngine:
    def calculate(self, evidence: StrategyEvidence) -> float:
        drawdown = linear_score(evidence.max_drawdown_pct, 40.0, 5.0)
        volatility = linear_score(evidence.annualized_volatility_pct, 60.0, 10.0)
        return round(0.65 * drawdown + 0.35 * volatility, 4)
