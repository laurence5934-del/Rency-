from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence


class Recommendation(str, Enum):
    PROMOTE_TO_PAPER = "promote_to_paper"
    PROMOTE_TO_LIVE_REVIEW = "promote_to_live_review"
    NEEDS_MORE_DATA = "needs_more_data"
    NEEDS_OPTIMIZATION = "needs_optimization"
    RETIRE = "retire"


@dataclass(frozen=True)
class EvaluationWeights:
    performance: float = 0.40
    risk: float = 0.25
    consistency: float = 0.20
    confidence: float = 0.10
    operational: float = 0.05

    def __post_init__(self) -> None:
        values = tuple(asdict(self).values())
        if any(value < 0 for value in values):
            raise ValueError("weights cannot be negative")
        if abs(sum(values) - 1.0) > 1e-9:
            raise ValueError("weights must sum to 1.0")


@dataclass(frozen=True)
class StrategyEvidence:
    strategy_id: str
    strategy_version: str
    net_return_pct: float
    annualized_return_pct: float
    win_rate_pct: float
    profit_factor: float
    expectancy: float
    max_drawdown_pct: float
    annualized_volatility_pct: float
    monthly_returns_pct: Sequence[float] = field(default_factory=tuple)
    trade_count: int = 0
    profitable_period_ratio: float = 0.0
    execution_success_rate_pct: float = 100.0
    average_slippage_bps: float = 0.0
    order_failure_rate_pct: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.strategy_id.strip():
            raise ValueError("strategy_id is required")
        if not self.strategy_version.strip():
            raise ValueError("strategy_version is required")
        if self.trade_count < 0:
            raise ValueError("trade_count cannot be negative")


@dataclass(frozen=True)
class ScoreBreakdown:
    performance: float
    risk: float
    consistency: float
    confidence: float
    operational: float
    overall: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyEvaluation:
    evaluation_id: str
    strategy_id: str
    strategy_version: str
    scores: ScoreBreakdown
    recommendation: Recommendation
    reasons: tuple[str, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_summary: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        payload["recommendation"] = self.recommendation.value
        return payload
