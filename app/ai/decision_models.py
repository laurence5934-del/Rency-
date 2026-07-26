from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence
from uuid import UUID, uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_probability(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0")


def validate_non_negative(name: str, value: float) -> None:
    if value < 0.0:
        raise ValueError(f"{name} cannot be negative")


class DecisionSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"
    COVER = "COVER"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    EXIT = "EXIT"


class DecisionStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_VALIDATION = "PENDING_VALIDATION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"
    EXPIRED = "EXPIRED"
    SUBMITTED = "SUBMITTED"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class ConfidenceGrade(str, Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class EvidenceDirection(str, Enum):
    SUPPORTS = "SUPPORTS"
    OPPOSES = "OPPOSES"
    NEUTRAL = "NEUTRAL"


class EvidenceType(str, Enum):
    TECHNICAL = "TECHNICAL"
    FUNDAMENTAL = "FUNDAMENTAL"
    SENTIMENT = "SENTIMENT"
    MACRO = "MACRO"
    NEWS = "NEWS"
    OPTIONS_FLOW = "OPTIONS_FLOW"
    ORDER_FLOW = "ORDER_FLOW"
    MARKET_REGIME = "MARKET_REGIME"
    PORTFOLIO = "PORTFOLIO"
    RISK = "RISK"
    MODEL = "MODEL"
    STRATEGY = "STRATEGY"
    MANUAL = "MANUAL"
    OTHER = "OTHER"


class MarketRegime(str, Enum):
    UNKNOWN = "UNKNOWN"
    BULL_TREND = "BULL_TREND"
    BEAR_TREND = "BEAR_TREND"
    RANGE_BOUND = "RANGE_BOUND"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    TRANSITION = "TRANSITION"


class RiskLevel(str, Enum):
    MINIMAL = "MINIMAL"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class ExecutionUrgency(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    IMMEDIATE = "IMMEDIATE"


class DecisionSource(str, Enum):
    AI = "AI"
    STRATEGY = "STRATEGY"
    HYBRID = "HYBRID"
    HUMAN = "HUMAN"
    RECOVERY = "RECOVERY"


@dataclass(frozen=True, slots=True)
class DecisionEvidence:
    evidence_id: UUID
    evidence_type: EvidenceType
    source: str
    direction: EvidenceDirection
    title: str
    score: float
    confidence: float
    observed_at_utc: str
    expires_at_utc: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("evidence source cannot be empty")
        if not self.title.strip():
            raise ValueError("evidence title cannot be empty")
        if not -1.0 <= self.score <= 1.0:
            raise ValueError("evidence score must be between -1.0 and 1.0")
        validate_probability("confidence", self.confidence)

    @classmethod
    def create(
        cls,
        *,
        evidence_type: EvidenceType,
        source: str,
        direction: EvidenceDirection,
        title: str,
        score: float,
        confidence: float,
        observed_at_utc: str | None = None,
        expires_at_utc: str | None = None,
        details: Mapping[str, Any] | None = None,
        tags: Sequence[str] = (),
    ) -> "DecisionEvidence":
        return cls(
            evidence_id=uuid4(),
            evidence_type=evidence_type,
            source=source,
            direction=direction,
            title=title,
            score=score,
            confidence=confidence,
            observed_at_utc=observed_at_utc or utc_now(),
            expires_at_utc=expires_at_utc,
            details=dict(details or {}),
            tags=tuple(tags),
        )

    @property
    def weighted_score(self) -> float:
        direction = {
            EvidenceDirection.SUPPORTS: 1.0,
            EvidenceDirection.OPPOSES: -1.0,
            EvidenceDirection.NEUTRAL: 0.0,
        }[self.direction]
        return self.score * self.confidence * direction

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_id"] = str(self.evidence_id)
        data["evidence_type"] = self.evidence_type.value
        data["direction"] = self.direction.value
        return data


@dataclass(frozen=True, slots=True)
class DecisionConfidence:
    raw_score: float
    calibrated_score: float
    grade: ConfidenceGrade
    agreement_score: float
    evidence_quality_score: float
    model_reliability_score: float
    sample_size: int
    calibration_version: str
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "raw_score",
            "calibrated_score",
            "agreement_score",
            "evidence_quality_score",
            "model_reliability_score",
        ):
            validate_probability(name, getattr(self, name))
        if self.sample_size < 0:
            raise ValueError("sample_size cannot be negative")
        if not self.calibration_version.strip():
            raise ValueError("calibration_version cannot be empty")

    @classmethod
    def from_score(
        cls,
        score: float,
        *,
        agreement_score: float = 1.0,
        evidence_quality_score: float = 1.0,
        model_reliability_score: float = 1.0,
        sample_size: int = 0,
        calibration_version: str = "1.0",
        reasons: Sequence[str] = (),
    ) -> "DecisionConfidence":
        validate_probability("score", score)
        if score < 0.20:
            grade = ConfidenceGrade.VERY_LOW
        elif score < 0.40:
            grade = ConfidenceGrade.LOW
        elif score < 0.65:
            grade = ConfidenceGrade.MODERATE
        elif score < 0.85:
            grade = ConfidenceGrade.HIGH
        else:
            grade = ConfidenceGrade.VERY_HIGH
        return cls(
            raw_score=score,
            calibrated_score=score,
            grade=grade,
            agreement_score=agreement_score,
            evidence_quality_score=evidence_quality_score,
            model_reliability_score=model_reliability_score,
            sample_size=sample_size,
            calibration_version=calibration_version,
            reasons=tuple(reasons),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["grade"] = self.grade.value
        return data


@dataclass(frozen=True, slots=True)
class MarketContext:
    symbol: str
    asset_class: str
    venue: str | None
    regime: MarketRegime
    last_price: float | None
    bid_price: float | None
    ask_price: float | None
    volatility: float | None
    volume: float | None
    average_volume: float | None
    liquidity_score: float | None
    trend_score: float | None
    momentum_score: float | None
    observed_at_utc: str
    session: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        if not self.asset_class.strip():
            raise ValueError("asset_class cannot be empty")
        for name in ("last_price", "bid_price", "ask_price", "volatility", "volume", "average_volume"):
            value = getattr(self, name)
            if value is not None:
                validate_non_negative(name, value)
        for name in ("liquidity_score", "trend_score", "momentum_score"):
            value = getattr(self, name)
            if value is not None and not -1.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between -1.0 and 1.0")

    @property
    def spread(self) -> float | None:
        if self.bid_price is None or self.ask_price is None:
            return None
        return self.ask_price - self.bid_price

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["regime"] = self.regime.value
        return data


@dataclass(frozen=True, slots=True)
class PortfolioImpact:
    portfolio_id: str
    current_position_quantity: float
    proposed_position_quantity: float
    current_weight: float
    proposed_weight: float
    concentration_before: float
    concentration_after: float
    correlation_impact: float
    diversification_impact: float
    expected_portfolio_return_impact: float
    expected_portfolio_risk_impact: float
    buying_power_required: float
    buying_power_remaining: float
    constraint_violations: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.portfolio_id.strip():
            raise ValueError("portfolio_id cannot be empty")
        for name in ("current_weight", "proposed_weight", "concentration_before", "concentration_after"):
            validate_probability(name, getattr(self, name))
        for name in (
            "correlation_impact",
            "diversification_impact",
            "expected_portfolio_return_impact",
            "expected_portfolio_risk_impact",
        ):
            value = getattr(self, name)
            if not -1.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between -1.0 and 1.0")
        validate_non_negative("buying_power_required", self.buying_power_required)
        validate_non_negative("buying_power_remaining", self.buying_power_remaining)

    @property
    def acceptable(self) -> bool:
        return not self.constraint_violations

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    level: RiskLevel
    risk_score: float
    max_loss_amount: float | None
    max_loss_percent: float | None
    expected_drawdown_percent: float | None
    value_at_risk: float | None
    stop_loss_price: float | None
    take_profit_price: float | None
    reward_to_risk_ratio: float | None
    liquidity_risk: float
    volatility_risk: float
    concentration_risk: float
    correlation_risk: float
    model_risk: float
    approved: bool
    rejection_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_probability("risk_score", self.risk_score)
        for name in (
            "liquidity_risk",
            "volatility_risk",
            "concentration_risk",
            "correlation_risk",
            "model_risk",
        ):
            validate_probability(name, getattr(self, name))
        for name in (
            "max_loss_amount",
            "max_loss_percent",
            "expected_drawdown_percent",
            "value_at_risk",
            "stop_loss_price",
            "take_profit_price",
            "reward_to_risk_ratio",
        ):
            value = getattr(self, name)
            if value is not None:
                validate_non_negative(name, value)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["level"] = self.level.value
        return data


@dataclass(frozen=True, slots=True)
class ExecutionRecommendation:
    order_type: OrderType
    time_in_force: TimeInForce
    urgency: ExecutionUrgency
    quantity: float
    limit_price: float | None
    stop_price: float | None
    participation_rate: float | None
    allow_partial_fill: bool
    route_preference: str | None
    slippage_tolerance_bps: float
    expires_at_utc: str | None = None
    instructions: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.quantity <= 0.0:
            raise ValueError("quantity must be greater than zero")
        for name in ("limit_price", "stop_price", "slippage_tolerance_bps"):
            value = getattr(self, name)
            if value is not None:
                validate_non_negative(name, value)
        if self.participation_rate is not None:
            validate_probability("participation_rate", self.participation_rate)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["order_type"] = self.order_type.value
        data["time_in_force"] = self.time_in_force.value
        data["urgency"] = self.urgency.value
        return data


@dataclass(frozen=True, slots=True)
class AIContributor:
    contributor_id: str
    contributor_type: str
    version: str
    recommendation: DecisionSide
    confidence: float
    weight: float
    rationale: str
    latency_ms: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.contributor_id.strip():
            raise ValueError("contributor_id cannot be empty")
        if not self.contributor_type.strip():
            raise ValueError("contributor_type cannot be empty")
        if not self.version.strip():
            raise ValueError("version cannot be empty")
        validate_probability("confidence", self.confidence)
        validate_non_negative("weight", self.weight)
        if self.latency_ms is not None:
            validate_non_negative("latency_ms", self.latency_ms)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["recommendation"] = self.recommendation.value
        return data


@dataclass(frozen=True, slots=True)
class DecisionExplanation:
    summary: str
    primary_reasons: tuple[str, ...]
    supporting_reasons: tuple[str, ...]
    opposing_reasons: tuple[str, ...]
    risk_summary: str
    portfolio_summary: str
    execution_summary: str
    rejected_alternatives: tuple[str, ...] = ()
    disclosures: tuple[str, ...] = ()
    generated_by: str = "decision_explainer"
    explanation_version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise ValueError("summary cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TradeDecision:
    decision_id: UUID
    correlation_id: UUID
    decision_version: str
    created_at_utc: str
    expires_at_utc: str | None
    symbol: str
    asset_class: str
    side: DecisionSide
    status: DecisionStatus
    source: DecisionSource
    strategy_id: str | None
    portfolio_id: str | None
    requested_quantity: float
    approved_quantity: float
    expected_entry_price: float | None
    expected_return_percent: float | None
    expected_drawdown_percent: float | None
    expected_holding_seconds: float | None
    confidence: DecisionConfidence
    market_context: MarketContext
    portfolio_impact: PortfolioImpact | None
    risk_assessment: RiskAssessment
    execution_recommendation: ExecutionRecommendation | None
    explanation: DecisionExplanation
    supporting_evidence: tuple[DecisionEvidence, ...]
    rejected_evidence: tuple[DecisionEvidence, ...]
    contributors: tuple[AIContributor, ...]
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.decision_version.strip():
            raise ValueError("decision_version cannot be empty")
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        if not self.asset_class.strip():
            raise ValueError("asset_class cannot be empty")
        validate_non_negative("requested_quantity", self.requested_quantity)
        validate_non_negative("approved_quantity", self.approved_quantity)
        if self.approved_quantity > self.requested_quantity:
            raise ValueError("approved_quantity cannot exceed requested_quantity")
        if self.expected_entry_price is not None:
            validate_non_negative("expected_entry_price", self.expected_entry_price)
        if self.expected_drawdown_percent is not None:
            validate_non_negative("expected_drawdown_percent", self.expected_drawdown_percent)
        if self.expected_holding_seconds is not None:
            validate_non_negative("expected_holding_seconds", self.expected_holding_seconds)
        if self.market_context.symbol.upper() != self.symbol.upper():
            raise ValueError("market_context symbol must match decision symbol")
        if self.portfolio_impact is not None and self.portfolio_id is not None:
            if self.portfolio_impact.portfolio_id != self.portfolio_id:
                raise ValueError("portfolio IDs must match")
        if self.status == DecisionStatus.APPROVED:
            if not self.risk_assessment.approved:
                raise ValueError("approved decision requires approved risk assessment")
            if self.execution_recommendation is None and self.side != DecisionSide.HOLD:
                raise ValueError("approved actionable decision requires execution recommendation")
        if self.status == DecisionStatus.REJECTED and self.approved_quantity != 0.0:
            raise ValueError("rejected decision must approve zero quantity")

    @classmethod
    def create(
        cls,
        *,
        symbol: str,
        asset_class: str,
        side: DecisionSide,
        status: DecisionStatus,
        source: DecisionSource,
        requested_quantity: float,
        approved_quantity: float,
        confidence: DecisionConfidence,
        market_context: MarketContext,
        risk_assessment: RiskAssessment,
        explanation: DecisionExplanation,
        strategy_id: str | None = None,
        portfolio_id: str | None = None,
        portfolio_impact: PortfolioImpact | None = None,
        execution_recommendation: ExecutionRecommendation | None = None,
        supporting_evidence: Sequence[DecisionEvidence] = (),
        rejected_evidence: Sequence[DecisionEvidence] = (),
        contributors: Sequence[AIContributor] = (),
        expected_entry_price: float | None = None,
        expected_return_percent: float | None = None,
        expected_drawdown_percent: float | None = None,
        expected_holding_seconds: float | None = None,
        decision_version: str = "10.1.1",
        expires_at_utc: str | None = None,
        correlation_id: UUID | None = None,
        tags: Sequence[str] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> "TradeDecision":
        return cls(
            decision_id=uuid4(),
            correlation_id=correlation_id or uuid4(),
            decision_version=decision_version,
            created_at_utc=utc_now(),
            expires_at_utc=expires_at_utc,
            symbol=symbol,
            asset_class=asset_class,
            side=side,
            status=status,
            source=source,
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
            requested_quantity=requested_quantity,
            approved_quantity=approved_quantity,
            expected_entry_price=expected_entry_price,
            expected_return_percent=expected_return_percent,
            expected_drawdown_percent=expected_drawdown_percent,
            expected_holding_seconds=expected_holding_seconds,
            confidence=confidence,
            market_context=market_context,
            portfolio_impact=portfolio_impact,
            risk_assessment=risk_assessment,
            execution_recommendation=execution_recommendation,
            explanation=explanation,
            supporting_evidence=tuple(supporting_evidence),
            rejected_evidence=tuple(rejected_evidence),
            contributors=tuple(contributors),
            tags=tuple(tags),
            metadata=dict(metadata or {}),
        )

    @property
    def actionable(self) -> bool:
        return (
            self.status == DecisionStatus.APPROVED
            and self.side != DecisionSide.HOLD
            and self.approved_quantity > 0.0
            and self.risk_assessment.approved
        )

    @property
    def evidence_score(self) -> float:
        evidence = self.supporting_evidence + self.rejected_evidence
        if not evidence:
            return 0.0
        return sum(item.weighted_score for item in evidence) / len(evidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": str(self.decision_id),
            "correlation_id": str(self.correlation_id),
            "decision_version": self.decision_version,
            "created_at_utc": self.created_at_utc,
            "expires_at_utc": self.expires_at_utc,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "side": self.side.value,
            "status": self.status.value,
            "source": self.source.value,
            "strategy_id": self.strategy_id,
            "portfolio_id": self.portfolio_id,
            "requested_quantity": self.requested_quantity,
            "approved_quantity": self.approved_quantity,
            "expected_entry_price": self.expected_entry_price,
            "expected_return_percent": self.expected_return_percent,
            "expected_drawdown_percent": self.expected_drawdown_percent,
            "expected_holding_seconds": self.expected_holding_seconds,
            "confidence": self.confidence.to_dict(),
            "market_context": self.market_context.to_dict(),
            "portfolio_impact": self.portfolio_impact.to_dict() if self.portfolio_impact else None,
            "risk_assessment": self.risk_assessment.to_dict(),
            "execution_recommendation": (
                self.execution_recommendation.to_dict()
                if self.execution_recommendation else None
            ),
            "explanation": self.explanation.to_dict(),
            "supporting_evidence": [item.to_dict() for item in self.supporting_evidence],
            "rejected_evidence": [item.to_dict() for item in self.rejected_evidence],
            "contributors": [item.to_dict() for item in self.contributors],
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
            "actionable": self.actionable,
            "evidence_score": self.evidence_score,
        }
