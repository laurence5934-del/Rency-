class RetryManager:
    def __init__(self,maximum_attempts=3): self.maximum_attempts=max(1,maximum_attempts)
    def execute(self,operation):
        err=None
        for _ in range(self.maximum_attempts):
            try:return operation()
            except Exception as e:err=e
        raise err
