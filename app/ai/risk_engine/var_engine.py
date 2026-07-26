from statistics import mean,pstdev
class ValueAtRiskEngine:
    def calculate(self,returns,position_value,z=1.645):
        if position_value<=0 or len(returns)<2: return 0.0
        return round(position_value*max(0,z*pstdev(returns)-mean(returns)),4)
