import math
class PositionSizer:
    def maximum_quantity(self,source,policy):
        p,t=source.portfolio,source.trade
        budget=min(p.portfolio_value*policy.max_position_pct,p.cash_available)
        budget*=max(0,min(1,t.confidence_score))*max(.10,1-min(.90,t.estimated_volatility))
        q=math.floor(budget/t.price)
        if t.average_daily_volume>0: q=min(q,math.floor(t.average_daily_volume*policy.max_order_adv_pct))
        return max(0,q)
