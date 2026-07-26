class SignalValidatorDashboardAPI:
    def __init__(self, validator): self.validator=validator
    def health(self): return self.validator.health()
    def metrics(self): return self.validator.metrics()
    def quarantine(self, limit=100): return [r.to_dict() for r in self.validator.quarantine(limit)]
