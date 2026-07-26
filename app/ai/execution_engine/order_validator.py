class OrderValidator:
    def __init__(self,policy_engine): self._policy_engine=policy_engine
    def validate(self,request): return self._policy_engine.evaluate(request)
