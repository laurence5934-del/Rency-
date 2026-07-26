from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import UUID, uuid4

class RiskLevel(str, Enum): LOW="LOW"; MODERATE="MODERATE"; HIGH="HIGH"; CRITICAL="CRITICAL"
class RiskDecision(str, Enum): APPROVE="APPROVE"; REDUCE="REDUCE"; REVIEW="REVIEW"; REJECT="REJECT"

@dataclass(frozen=True, slots=True)
class PortfolioRiskContext:
    portfolio_value: float
    cash_available: float
    current_gross_exposure: float
    current_net_exposure: float
    daily_pnl: float=0.0
    weekly_pnl: float=0.0
    monthly_pnl: float=0.0
    current_drawdown: float=0.0
    leverage: float=1.0
    sector_exposure: Mapping[str,float]=field(default_factory=dict)
    def __post_init__(self):
        if self.portfolio_value<=0: raise ValueError('portfolio_value must be positive')
        if self.cash_available<0: raise ValueError('cash_available cannot be negative')
        if not 0<=self.current_drawdown<=1: raise ValueError('current_drawdown must be between 0 and 1')

@dataclass(frozen=True, slots=True)
class TradeRiskContext:
    symbol: str; side: str; price: float; requested_quantity: int
    sector: str='UNKNOWN'; confidence_score: float=0.0; consensus_score: float=0.0
    expected_return_pct: float=0.0; estimated_volatility: float=0.0; average_daily_volume: float=0.0
    def __post_init__(self):
        if not self.symbol.strip(): raise ValueError('symbol cannot be empty')
        if self.side.upper() not in {'BUY','SELL'}: raise ValueError('side must be BUY or SELL')
        if self.price<=0 or self.requested_quantity<=0: raise ValueError('price and requested_quantity must be positive')
        for n in ('confidence_score','consensus_score'):
            if not 0<=getattr(self,n)<=1: raise ValueError(f'{n} must be between 0 and 1')

@dataclass(frozen=True, slots=True)
class MarketRiskContext:
    market_volatility_index: float=0.0; trading_halted: bool=False; circuit_breaker_active: bool=False
    earnings_event_within_days: int|None=None; gap_risk_score: float=0.0; liquidity_score: float=1.0
    def __post_init__(self):
        if not 0<=self.gap_risk_score<=1 or not 0<=self.liquidity_score<=1: raise ValueError('risk scores must be between 0 and 1')

@dataclass(frozen=True, slots=True)
class RiskEvaluationInput:
    portfolio: PortfolioRiskContext; trade: TradeRiskContext; market: MarketRiskContext
    historical_returns: tuple[float,...]=(); metadata: Mapping[str,Any]=field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class RiskFactor:
    name: str; score: float; weight: float; rationale: str

@dataclass(frozen=True, slots=True)
class RiskPolicySnapshot:
    max_position_pct: float; max_sector_exposure_pct: float; max_leverage: float
    max_daily_loss_pct: float; max_weekly_loss_pct: float; max_monthly_loss_pct: float
    max_drawdown_pct: float; max_order_adv_pct: float; minimum_confidence: float; minimum_consensus: float

@dataclass(frozen=True, slots=True)
class RiskReport:
    risk_id: UUID; created_at_utc: str; symbol: str; score: float; level: RiskLevel; decision: RiskDecision
    approved_quantity: int; maximum_allowed_quantity: int; suggested_stop_loss: float; suggested_take_profit: float
    risk_reward_ratio: float; value_at_risk: float; conditional_value_at_risk: float
    factors: tuple[RiskFactor,...]; violations: tuple[str,...]; warnings: tuple[str,...]
    policy: RiskPolicySnapshot; correlation_id: str|None=None
    @classmethod
    def create(cls, **kwargs): return cls(risk_id=uuid4(), created_at_utc=datetime.now(timezone.utc).isoformat(), **kwargs)
    def to_dict(self):
        d=asdict(self); d['risk_id']=str(self.risk_id); d['level']=self.level.value; d['decision']=self.decision.value; return d
