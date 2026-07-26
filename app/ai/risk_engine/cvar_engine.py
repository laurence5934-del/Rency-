class ConditionalValueAtRiskEngine:
    def calculate(self,returns,position_value,percentile=.05):
        if position_value<=0 or not returns: return 0.0
        r=sorted(returns); n=max(1,int(len(r)*percentile)); return round(position_value*max(0,-sum(r[:n])/n),4)
