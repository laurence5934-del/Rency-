class StopLossEngine:
    def calculate(self,t):
        d=max(.02,min(.15,t.estimated_volatility*.25))
        return round(t.price*(1-d if t.side.upper()=='BUY' else 1+d),4)
