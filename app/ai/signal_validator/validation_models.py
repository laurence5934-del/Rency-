from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence
from uuid import UUID, uuid4

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class ValidationDecision(str, Enum):
    ACCEPT="ACCEPT"; REVIEW="REVIEW"; REJECT="REJECT"; QUARANTINE="QUARANTINE"

class ValidationSeverity(str, Enum):
    INFO="INFO"; WARNING="WARNING"; ERROR="ERROR"; CRITICAL="CRITICAL"

class ValidationCheckType(str, Enum):
    FRESHNESS="FRESHNESS"; CONFIDENCE="CONFIDENCE"; DUPLICATE="DUPLICATE"
    CONFLICT="CONFLICT"; PORTFOLIO="PORTFOLIO"; RISK="RISK"; POLICY="POLICY"

class ValidationStatus(str, Enum):
    PASS="PASS"; WARN="WARN"; FAIL="FAIL"; ERROR="ERROR"

@dataclass(frozen=True, slots=True)
class PortfolioContext:
    gross_exposure: float=0.0
    net_exposure: float=0.0
    symbol_exposure: Mapping[str,float]=field(default_factory=dict)
    sector_exposure: Mapping[str,float]=field(default_factory=dict)
    available_buying_power: float=0.0
    def __post_init__(self):
        if self.gross_exposure < 0 or self.available_buying_power < 0:
            raise ValueError("portfolio values cannot be negative")

@dataclass(frozen=True, slots=True)
class RiskContext:
    portfolio_drawdown: float=0.0
    daily_loss: float=0.0
    volatility_index: float|None=None
    trading_halted: bool=False
    restricted_symbols: frozenset[str]=frozenset()
    def __post_init__(self):
        if self.portfolio_drawdown < 0 or self.daily_loss < 0:
            raise ValueError("risk values cannot be negative")

@dataclass(frozen=True, slots=True)
class ValidationContext:
    portfolio: PortfolioContext|None=None
    risk: RiskContext|None=None
    peer_signals: tuple[Any,...]=()
    metadata: Mapping[str,Any]=field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class ValidationCheckResult:
    check_type: ValidationCheckType
    status: ValidationStatus
    score: float
    severity: ValidationSeverity
    code: str
    message: str
    details: Mapping[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        if not 0 <= self.score <= 1: raise ValueError("score must be between 0 and 1")
    @property
    def passed(self): return self.status == ValidationStatus.PASS

@dataclass(frozen=True, slots=True)
class ValidationPolicySnapshot:
    minimum_accept_score: float
    minimum_review_score: float
    quarantine_on_critical: bool
    reject_on_error: bool
    check_weights: Mapping[str,float]

@dataclass(frozen=True, slots=True)
class SignalValidationReport:
    validation_id: UUID
    signal_id: UUID
    provider_id: str
    symbol: str
    started_at_utc: str
    completed_at_utc: str
    decision: ValidationDecision
    validation_score: float
    checks: tuple[ValidationCheckResult,...]
    policy: ValidationPolicySnapshot
    reasons: tuple[str,...]=()
    correlation_id: str|None=None
    @classmethod
    def create(cls, *, signal_id, provider_id, symbol, started_at_utc, decision,
               validation_score, checks:Sequence[ValidationCheckResult], policy,
               reasons=(), correlation_id=None):
        return cls(uuid4(), signal_id, provider_id, symbol, started_at_utc, utc_now(),
                   decision, validation_score, tuple(checks), policy, tuple(reasons),
                   correlation_id)
    @property
    def accepted(self): return self.decision == ValidationDecision.ACCEPT
    def to_dict(self):
        data=asdict(self); data["validation_id"]=str(self.validation_id)
        data["signal_id"]=str(self.signal_id); data["decision"]=self.decision.value
        return data

@dataclass(frozen=True, slots=True)
class BatchValidationResult:
    reports: tuple[SignalValidationReport,...]
    errors: tuple[str,...]=()
