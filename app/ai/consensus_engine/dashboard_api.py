class ConsensusDashboardAPI:
    def __init__(self, engine): self.engine=engine
    def health(self): return self.engine.health()
    def metrics(self): return self.engine.metrics()
    def evaluate(self, symbol, votes): return self.engine.evaluate_votes(symbol,votes).to_dict()
