from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import UUID, uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    SCALE_IN = "SCALE_IN"
    SCALE_OUT = "SCALE_OUT"
    CLOSE_POSITION = "CLOSE_POSITION"
    CANCEL = "CANCEL"
    DEFER = "DEFER"
    ESCALATE_REVIEW = "ESCALATE_REVIEW"


class DecisionStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class DecisionPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class StrategyDecisionContext:
    strategy_name: str
    desired_action: DecisionAction
    signal_strength: float
    expected_return_pct: float = 0.0
    time_horizon: str = "UNKNOWN"
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.strategy_name.strip():
            raise ValueError("strategy_name cannot be empty")
        if not 0.0 <= self.signal_strength <= 1.0:
            raise ValueError("signal_strength must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class RiskDecisionContext:
    decision: str
    risk_score: float
    approved_quantity: int
    maximum_allowed_quantity: int
    violations: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.risk_score <= 1.0:
            raise ValueError("risk_score must be between 0.0 and 1.0")
        if self.approved_quantity < 0 or self.maximum_allowed_quantity < 0:
            raise ValueError("quantities cannot be negative")


@dataclass(frozen=True, slots=True)
class PortfolioDecisionContext:
    portfolio_value: float
    cash_available: float
    gross_exposure: float
    net_exposure: float
    open_positions: int = 0

    def __post_init__(self) -> None:
        if self.portfolio_value <= 0.0:
            raise ValueError("portfolio_value must be positive")
        if self.cash_available < 0.0:
            raise ValueError("cash_available cannot be negative")
        if self.open_positions < 0:
            raise ValueError("open_positions cannot be negative")


@dataclass(frozen=True, slots=True)
class PositionDecisionContext:
    current_quantity: int = 0
    average_price: float = 0.0
    unrealized_pnl_pct: float = 0.0
    has_open_position: bool = False

    def __post_init__(self) -> None:
        if self.current_quantity < 0:
            raise ValueError("current_quantity cannot be negative")
        if self.average_price < 0.0:
            raise ValueError("average_price cannot be negative")


@dataclass(frozen=True, slots=True)
class MarketDecisionContext:
    market_open: bool = True
    trading_halted: bool = False
    volatility_regime: str = "NORMAL"
    liquidity_score: float = 1.0
    market_trend: str = "NEUTRAL"

    def __post_init__(self) -> None:
        if not 0.0 <= self.liquidity_score <= 1.0:
            raise ValueError("liquidity_score must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class DecisionContext:
    symbol: str
    side: str
    requested_quantity: int
    consensus_score: float
    confidence_score: float
    validation_score: float
    strategy: StrategyDecisionContext
    risk: RiskDecisionContext
    portfolio: PortfolioDecisionContext
    position: PositionDecisionContext
    market: MarketDecisionContext
    priority: DecisionPriority = DecisionPriority.NORMAL
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        if self.side.upper() not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if self.requested_quantity <= 0:
            raise ValueError("requested_quantity must be positive")
        for field_name in ("consensus_score", "confidence_score", "validation_score"):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0")


DecisionInput = DecisionContext


@dataclass(frozen=True, slots=True)
class DecisionEvidence:
    source: str
    key: str
    value: Any
    weight: float
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("evidence source cannot be empty")
        if not self.key.strip():
            raise ValueError("evidence key cannot be empty")
        if self.weight < 0.0:
            raise ValueError("evidence weight cannot be negative")


@dataclass(frozen=True, slots=True)
class DecisionRuleResult:
    rule_name: str
    passed: bool
    action: DecisionAction
    severity: DecisionPriority
    score: float
    rationale: str

    def __post_init__(self) -> None:
        if not self.rule_name.strip():
            raise ValueError("rule_name cannot be empty")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("rule score must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class DecisionReport:
    decision_id: UUID
    created_at_utc: str
    symbol: str
    action: DecisionAction
    status: DecisionStatus
    requested_quantity: int
    approved_quantity: int
    decision_score: float
    priority: DecisionPriority
    reasons: tuple[str, ...]
    rule_results: tuple[DecisionRuleResult, ...]
    evidence: tuple[DecisionEvidence, ...]
    explanation: str
    correlation_id: str | None = None

    @classmethod
    def create(cls, **kwargs: Any) -> "DecisionReport":
        return cls(
            decision_id=uuid4(),
            created_at_utc=utc_now(),
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["decision_id"] = str(self.decision_id)
        result["action"] = self.action.value
        result["status"] = self.status.value
        result["priority"] = self.priority.value
        return result
