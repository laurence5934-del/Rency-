from dataclasses import dataclass
from .models import RiskDecision, RiskLevel, RiskPolicySnapshot
@dataclass(frozen=True, slots=True)
class RiskPolicy:
    max_position_pct: float=.10; max_sector_exposure_pct: float=.30; max_leverage: float=1.5
    max_daily_loss_pct: float=.03; max_weekly_loss_pct: float=.06; max_monthly_loss_pct: float=.10
    max_drawdown_pct: float=.15; max_order_adv_pct: float=.02; minimum_confidence: float=.60; minimum_consensus: float=.55
    review_score_threshold: float=.50; reject_score_threshold: float=.75
    def snapshot(self): return RiskPolicySnapshot(self.max_position_pct,self.max_sector_exposure_pct,self.max_leverage,self.max_daily_loss_pct,self.max_weekly_loss_pct,self.max_monthly_loss_pct,self.max_drawdown_pct,self.max_order_adv_pct,self.minimum_confidence,self.minimum_consensus)
class RiskPolicyEngine:
    def __init__(self,policy=None): self.policy=policy or RiskPolicy()
    def level(self,s): return RiskLevel.CRITICAL if s>=.75 else RiskLevel.HIGH if s>=.50 else RiskLevel.MODERATE if s>=.25 else RiskLevel.LOW
    def evaluate(self,source,score,max_qty):
        p,t,m=source.portfolio,source.trade,source.market; v=[]; w=[]; pol=self.policy
        if m.trading_halted: v.append('TRADING_HALTED')
        if m.circuit_breaker_active: v.append('CIRCUIT_BREAKER_ACTIVE')
        if p.leverage>pol.max_leverage: v.append('MAXIMUM_LEVERAGE_EXCEEDED')
        if p.current_drawdown>=pol.max_drawdown_pct: v.append('MAXIMUM_DRAWDOWN_REACHED')
        if p.daily_pnl<=-(p.portfolio_value*pol.max_daily_loss_pct): v.append('DAILY_LOSS_LIMIT_REACHED')
        if p.weekly_pnl<=-(p.portfolio_value*pol.max_weekly_loss_pct): v.append('WEEKLY_LOSS_LIMIT_REACHED')
        if p.monthly_pnl<=-(p.portfolio_value*pol.max_monthly_loss_pct): v.append('MONTHLY_LOSS_LIMIT_REACHED')
        if t.confidence_score<pol.minimum_confidence: v.append('CONFIDENCE_BELOW_MINIMUM')
        if t.consensus_score<pol.minimum_consensus: v.append('CONSENSUS_BELOW_MINIMUM')
        if max_qty<=0: v.append('NO_RISK_CAPACITY_AVAILABLE')
        if m.earnings_event_within_days is not None and m.earnings_event_within_days<=2: w.append('NEAR_TERM_EARNINGS_EVENT')
        if m.liquidity_score<.5: w.append('LOW_LIQUIDITY')
        if m.gap_risk_score>=.7: w.append('HIGH_GAP_RISK')
        if m.market_volatility_index>=30: w.append('HIGH_MARKET_VOLATILITY')
        if v or score>=pol.reject_score_threshold: return RiskDecision.REJECT,tuple(v),tuple(w)
        if score>=pol.review_score_threshold: return RiskDecision.REVIEW,(),tuple(w)
        if max_qty<t.requested_quantity: return RiskDecision.REDUCE,(),tuple(w)
        return RiskDecision.APPROVE,(),tuple(w)
