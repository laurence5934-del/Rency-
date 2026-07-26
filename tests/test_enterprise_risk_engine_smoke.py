from ai_trading_platform_v4_pro.ai_trading_platform_v4_pro.app.ai.risk_engine import EnterpriseRiskEngine, PortfolioRiskContext, TradeRiskContext, MarketRiskContext, RiskEvaluationInput, RiskDecision
source=RiskEvaluationInput(
 portfolio=PortfolioRiskContext(100000,40000,60000,60000,daily_pnl=500,weekly_pnl=1200,monthly_pnl=3000,current_drawdown=.02,leverage=1.0,sector_exposure={'Technology':.12}),
 trade=TradeRiskContext('PLTR','BUY',25,100,'Technology',.84,.79,.12,.28,20000000),
 market=MarketRiskContext(18,False,False,10,.20,.95),
 historical_returns=(.010,-.008,.006,-.004,.012,-.015,.004,.008,-.006,.009))
engine=EnterpriseRiskEngine(); report=engine.evaluate(source)
assert report.decision in {RiskDecision.APPROVE,RiskDecision.REDUCE}
assert report.maximum_allowed_quantity>0
assert report.suggested_stop_loss<source.trade.price
assert report.suggested_take_profit>source.trade.price
assert report.risk_reward_ratio>=2.0
assert engine.metrics()['evaluations']==1
