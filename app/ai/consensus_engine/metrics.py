from dataclasses import dataclass, asdict
from threading import RLock
@dataclass(slots=True)
class ConsensusMetricsSnapshot:
    consensus_cycles:int=0; votes_processed:int=0; decisions_approved:int=0
    decisions_reviewed:int=0; decisions_rejected:int=0; decisions_abstained:int=0
    contributor_errors:int=0
class ConsensusMetrics:
    def __init__(self): self._v=ConsensusMetricsSnapshot(); self._lock=RLock()
    def increment(self,name,amount=1):
        with self._lock: setattr(self._v,name,getattr(self._v,name)+amount)
    def snapshot(self):
        with self._lock: return asdict(self._v)
