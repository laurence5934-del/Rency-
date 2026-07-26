class TakeProfitEngine:
    def calculate(self,t,stop,target_rr=2.0):
        risk=abs(t.price-stop)
        if risk<=0: return t.price,0.0
        target=t.price+risk*target_rr if t.side.upper()=='BUY' else t.price-risk*target_rr
        return round(target,4),round(abs(target-t.price)/risk,4)
