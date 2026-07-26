from __future__ import annotations

from ._scoring import linear_score
from .models import StrategyEvidence


class OperationalScoreEngine:
    def calculate(self, evidence: StrategyEvidence) -> float:
        success = linear_score(evidence.execution_success_rate_pct, 80.0, 100.0)
        slippage = linear_score(evidence.average_slippage_bps, 25.0, 0.0)
        failures = linear_score(evidence.order_failure_rate_pct, 10.0, 0.0)
        return round(0.60 * success + 0.25 * slippage + 0.15 * failures, 4)
