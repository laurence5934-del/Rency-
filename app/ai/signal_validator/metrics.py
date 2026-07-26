from dataclasses import dataclass, asdict
from threading import RLock
@dataclass(slots=True)
class ValidationMetricsSnapshot:
    validation_cycles:int=0; signals_validated:int=0; signals_accepted:int=0
    signals_reviewed:int=0; signals_rejected:int=0; signals_quarantined:int=0
    validation_errors:int=0
class SignalValidationMetrics:
    def __init__(self): self._v=ValidationMetricsSnapshot(); self._lock=RLock()
    def increment(self,name,amount=1):
        with self._lock: setattr(self._v,name,getattr(self._v,name)+amount)
    def snapshot(self):
        with self._lock: return asdict(self._v)
