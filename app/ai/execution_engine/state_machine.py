from .models import OrderStatus
class ExecutionStateMachine:
    _allowed={OrderStatus.CREATED:{OrderStatus.VALIDATED,OrderStatus.REJECTED},OrderStatus.VALIDATED:{OrderStatus.ROUTED,OrderStatus.REJECTED},OrderStatus.ROUTED:{OrderStatus.SUBMITTED,OrderStatus.FAILED},OrderStatus.SUBMITTED:{OrderStatus.ACKNOWLEDGED,OrderStatus.REJECTED,OrderStatus.FAILED},OrderStatus.ACKNOWLEDGED:{OrderStatus.PARTIALLY_FILLED,OrderStatus.FILLED,OrderStatus.CANCELLED,OrderStatus.FAILED},OrderStatus.PARTIALLY_FILLED:{OrderStatus.PARTIALLY_FILLED,OrderStatus.FILLED,OrderStatus.CANCELLED,OrderStatus.FAILED},OrderStatus.FILLED:set(),OrderStatus.CANCELLED:set(),OrderStatus.REJECTED:set(),OrderStatus.FAILED:set()}
    def transition(self,current,target):
        if target not in self._allowed[current]: raise ValueError(f'invalid order transition: {current.value} -> {target.value}')
        return target
