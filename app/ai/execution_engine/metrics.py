class ExecutionMetrics:
    def __init__(self): self._v={'total':0,'success':0,'partial':0,'rejected':0,'failed':0,'deferred':0,'fills':0,'filled_quantity':0}
    def increment(self,name,amount=1):
        if name in self._v:self._v[name]+=amount
    def snapshot(self): return dict(self._v)
