from collections import deque
class ExecutionAuditLog:
    def __init__(self,max_entries=1000): self._entries=deque(maxlen=max_entries)
    def append(self,result): self._entries.append(result)
    def recent(self,limit=50): return tuple(list(self._entries)[-limit:])
    def count(self): return len(self._entries)
