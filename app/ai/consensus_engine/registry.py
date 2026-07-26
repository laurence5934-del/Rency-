from dataclasses import dataclass
from threading import RLock
from typing import Protocol
from .models import ContributorVote

class ConsensusContributor(Protocol):
    contributor_id:str
    def vote(self, symbol:str, context:object|None=None)->ContributorVote: ...

@dataclass(frozen=True, slots=True)
class RegistryEntry:
    contributor_id:str
    contributor:ConsensusContributor
    enabled:bool=True

class ContributorRegistry:
    def __init__(self): self._entries={}; self._lock=RLock()
    def register(self, contributor, enabled=True):
        cid=contributor.contributor_id.strip()
        if not cid: raise ValueError("contributor_id cannot be empty")
        with self._lock:
            if cid in self._entries: raise ValueError(f"already registered: {cid}")
            self._entries[cid]=RegistryEntry(cid,contributor,enabled)
    def unregister(self, contributor_id):
        with self._lock: return self._entries.pop(contributor_id,None) is not None
    def enabled(self):
        with self._lock: return tuple(e.contributor for e in self._entries.values() if e.enabled)
    def health(self):
        with self._lock:
            return {"registered":len(self._entries),
                    "enabled":sum(e.enabled for e in self._entries.values()),
                    "contributors":tuple(sorted(self._entries))}
