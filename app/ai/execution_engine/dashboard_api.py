class ExecutionDashboardAPI:
    def __init__(self,engine): self._engine=engine
    def health(self): return self._engine.health()
    def metrics(self): return self._engine.metrics()
    def recent_executions(self,limit=50): return [x.to_dict() for x in self._engine.recent_executions(limit)]
    def recent_orders(self,limit=50): return [x.to_dict() for x in self._engine.recent_orders(limit)]
    def execute(self,request): return self._engine.execute(request).to_dict()
