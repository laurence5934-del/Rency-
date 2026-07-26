class RiskDashboardAPI:
    def __init__(self,engine): self._engine=engine
    def health(self): return self._engine.health()
    def metrics(self): return self._engine.metrics()
    def evaluate(self,source): return self._engine.evaluate(source).to_dict()
