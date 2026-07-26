from dataclasses import dataclass
from .models import OrderType
@dataclass(frozen=True,slots=True)
class ExecutionPolicy:
    maximum_order_quantity:int=10000; minimum_order_quantity:int=1; allow_market_orders:bool=True; require_idempotency_key:bool=True; maximum_retry_attempts:int=3
class ExecutionPolicyEngine:
    def __init__(self,policy=None): self.policy=policy or ExecutionPolicy()
    def evaluate(self,request):
        r=[]
        if request.quantity<self.policy.minimum_order_quantity:r.append('ORDER_QUANTITY_BELOW_MINIMUM')
        if request.quantity>self.policy.maximum_order_quantity:r.append('ORDER_QUANTITY_ABOVE_MAXIMUM')
        if request.order_type==OrderType.MARKET and not self.policy.allow_market_orders:r.append('MARKET_ORDERS_DISABLED')
        if self.policy.require_idempotency_key and not request.idempotency_key:r.append('IDEMPOTENCY_KEY_REQUIRED')
        if request.order_type in {OrderType.LIMIT,OrderType.STOP_LIMIT} and request.limit_price is None:r.append('LIMIT_PRICE_REQUIRED')
        if request.order_type in {OrderType.STOP,OrderType.STOP_LIMIT} and request.stop_price is None:r.append('STOP_PRICE_REQUIRED')
        if request.order_type==OrderType.TRAILING_STOP and request.trailing_percent is None:r.append('TRAILING_PERCENT_REQUIRED')
        return (not r,tuple(r))
