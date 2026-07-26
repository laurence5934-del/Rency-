from abc import ABC,abstractmethod
from uuid import uuid4
from .models import BrokerAcknowledgement,Fill,OrderType
class BrokerAdapter(ABC):
    @abstractmethod
    def submit_order(self,order):...
    @abstractmethod
    def poll_fills(self,order):...
class SimulatedBrokerAdapter(BrokerAdapter):
    def __init__(self,default_price=100.0,partial_fill_ratio=1.0): self.default_price=default_price; self.partial_fill_ratio=partial_fill_ratio
    def submit_order(self,order): return BrokerAcknowledgement(True,f'SIM-{uuid4().hex[:16].upper()}','Simulated broker accepted order')
    def poll_fills(self,order):
        q=min(max(1,int(order.request.quantity*self.partial_fill_ratio)),order.remaining_quantity)
        if q<=0:return ()
        p=order.request.limit_price if order.request.order_type in {OrderType.LIMIT,OrderType.STOP_LIMIT} and order.request.limit_price is not None else self.default_price
        return (Fill.create(order.order_id,q,p),)
class OrderRouter:
    def __init__(self,adapter): self._adapter=adapter
    def route(self,order): return self._adapter.submit_order(order)
    def collect_fills(self,order): return self._adapter.poll_fills(order)
