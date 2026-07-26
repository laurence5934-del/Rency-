from threading import RLock
class FillManager:
    def __init__(self): self._fills={}; self._lock=RLock()
    def apply(self,order,fills):
        with self._lock:
            lst=self._fills.setdefault(order.order_id,[]); total=order.filled_quantity; value=order.average_fill_price*total
            for f in fills:
                if order.filled_quantity+f.quantity>order.request.quantity: raise ValueError('fill exceeds remaining order quantity')
                lst.append(f); order.filled_quantity+=f.quantity; value+=f.quantity*f.price
            if order.filled_quantity: order.average_fill_price=value/order.filled_quantity
    def for_order(self,order_id):
        with self._lock:return tuple(self._fills.get(order_id,()))
