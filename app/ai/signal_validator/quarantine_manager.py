from collections import deque
from threading import RLock
class QuarantineManager:
    def __init__(self, capacity=10000):
        self._items=deque(maxlen=capacity); self._lock=RLock()
    def add(self, report):
        with self._lock: self._items.append(report)
    def list(self, limit=100):
        with self._lock: return tuple(list(self._items)[-limit:])
    def size(self):
        with self._lock: return len(self._items)
