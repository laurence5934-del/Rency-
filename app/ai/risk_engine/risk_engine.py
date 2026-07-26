from .models import RiskFactor,RiskReport,RiskDecision
from .policy_engine import RiskPolicyEngine
from .position_sizer import PositionSizer
from .stop_loss import StopLossEngine
from .take_profit import TakeProfitEngine
from .var_engine import ValueAtRiskEngine
from .cvar_engine import ConditionalValueAtRiskEngine
from .metrics import RiskMetrics
class EnterpriseRiskEngine:
    def __init__(self,policy=None,metrics=None):
        self._pe=RiskPolicyEngine(policy); self._m=metrics or RiskMetrics(); self._s=PositionSizer(); self._sl=StopLossEngine(); self._tp=TakeProfitEngine(); self._var=ValueAtRiskEngine(); self._cvar=ConditionalValueAtRiskEngine()
    def _factors(self,src):
        p,t,m=src.portfolio,src.trade,src.market; pol=self._pe.policy
        pos=(t.price*t.requested_quantity)/p.portfolio_value
        sector=p.sector_exposure.get(t.sector,0)+(t.price*t.requested_quantity)/p.portfolio_value
        return (
            RiskFactor('drawdown',min(1,p.current_drawdown/max(pol.max_drawdown_pct,1e-9)),.16,'Drawdown utilization'),
            RiskFactor('leverage',min(1,p.leverage/max(pol.max_leverage,1e-9)),.12,'Leverage utilization'),
            RiskFactor('position_concentration',min(1,pos/max(pol.max_position_pct,1e-9)),.14,'Position concentration'),
            RiskFactor('sector_exposure',min(1,sector/max(pol.max_sector_exposure_pct,1e-9)),.10,'Projected sector exposure'),
            RiskFactor('market_volatility',min(1,m.market_volatility_index/40),.12,'Market volatility regime'),
            RiskFactor('liquidity_risk',1-m.liquidity_score,.10,'Inverse liquidity score'),
            RiskFactor('gap_risk',m.gap_risk_score,.08,'Gap risk'),
            RiskFactor('instrument_volatility',min(1,t.estimated_volatility/.80),.08,'Instrument volatility'),
            RiskFactor('confidence_risk',1-t.confidence_score,.05,'Inverse confidence'),
            RiskFactor('consensus_risk',1-t.consensus_score,.05,'Inverse consensus'),
        )
    def evaluate(self,source,correlation_id=None):
        factors=self._factors(source); tw=sum(x.weight for x in factors); score=sum(x.score*x.weight for x in factors)/tw if tw else 0
        maxq=self._s.maximum_quantity(source,self._pe.policy); decision,violations,warnings=self._pe.evaluate(source,score,maxq)
        approved=source.trade.requested_quantity if decision==RiskDecision.APPROVE else maxq if decision==RiskDecision.REDUCE else 0
        stop=self._sl.calculate(source.trade); target,rr=self._tp.calculate(source.trade,stop); posval=source.trade.price*max(approved,maxq)
        report=RiskReport.create(symbol=source.trade.symbol,score=score,level=self._pe.level(score),decision=decision,approved_quantity=approved,maximum_allowed_quantity=maxq,suggested_stop_loss=stop,suggested_take_profit=target,risk_reward_ratio=rr,value_at_risk=self._var.calculate(source.historical_returns,posval),conditional_value_at_risk=self._cvar.calculate(source.historical_returns,posval),factors=factors,violations=violations,warnings=warnings,policy=self._pe.policy.snapshot(),correlation_id=correlation_id)
        self._m.increment('evaluations'); self._m.increment({RiskDecision.APPROVE:'approved',RiskDecision.REDUCE:'reduced',RiskDecision.REVIEW:'reviewed',RiskDecision.REJECT:'rejected'}[decision]); return report
    def metrics(self): return self._m.snapshot()
    def health(self): return {'status':'HEALTHY','metrics':self.metrics(),'policy':self._pe.policy.snapshot()}
