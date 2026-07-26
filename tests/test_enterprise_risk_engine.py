from ai_trading_platform_v4_pro.ai_trading_platform_v4_pro.app.ai.risk_engine import *
def base(conf=.85,halt=False):
 return RiskEvaluationInput(PortfolioRiskContext(100000,50000,50000,50000,current_drawdown=.01,leverage=1.0,sector_exposure={'Technology':.1}),TradeRiskContext('NVDA','BUY',100,50,'Technology',conf,.8,estimated_volatility=.25,average_daily_volume=10000000),MarketRiskContext(17,halt,False,None,0,.95))
def test_valid_trade(): assert EnterpriseRiskEngine().evaluate(base()).decision in {RiskDecision.APPROVE,RiskDecision.REDUCE}
def test_halt_rejected(): assert EnterpriseRiskEngine().evaluate(base(halt=True)).decision==RiskDecision.REJECT
def test_low_confidence_rejected(): assert EnterpriseRiskEngine().evaluate(base(conf=.2)).decision==RiskDecision.REJECT
