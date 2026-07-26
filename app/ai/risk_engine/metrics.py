from threading import RLock
class RiskMetrics:
    def __init__(self): self._d={'evaluations':0,'approved':0,'reduced':0,'reviewed':0,'rejected':0}; self._lock=RLock()
    def increment(self,k):
        with self._lock: self._d[k]+=1
    def snapshot(self):
        with self._lock: return dict(self._d)
