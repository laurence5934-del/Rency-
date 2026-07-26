from datetime import datetime,timezone
from threading import RLock
from .models import Order
from .state_machine import ExecutionStateMachine
class OrderManager:
    def __init__(self): self._sm=ExecutionStateMachine(); self._orders={}; self._lock=RLock()
    def create(self,request):
        o=Order.create(request)
        with self._lock:self._orders[o.order_id]=o
        return o
    def transition(self,o,target):
        with self._lock:o.status=self._sm.transition(o.status,target); o.updated_at_utc=datetime.now(timezone.utc).isoformat(); return o
    def recent(self,limit=50):
        with self._lock:return tuple(list(self._orders.values())[-limit:])
