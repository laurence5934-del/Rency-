from .audit_log import ExecutionAuditLog
from .fill_manager import FillManager
from .metrics import ExecutionMetrics
from .models import ExecutionResult,ExecutionStatus,OrderStatus
from .order_manager import OrderManager
from .order_router import OrderRouter,SimulatedBrokerAdapter
from .order_validator import OrderValidator
from .policy_engine import ExecutionPolicyEngine
from .reconciliation import ExecutionReconciler
from .retry_manager import RetryManager
class EnterpriseExecutionEngine:
    def __init__(self,policy=None,router=None):
        self._pe=ExecutionPolicyEngine(policy); self._validator=OrderValidator(self._pe); self._orders=OrderManager(); self._fills=FillManager(); self._router=router or OrderRouter(SimulatedBrokerAdapter()); self._retry=RetryManager(self._pe.policy.maximum_retry_attempts); self._recon=ExecutionReconciler(); self._metrics=ExecutionMetrics(); self._audit=ExecutionAuditLog(); self._idem={}
    def execute(self,request):
        if request.idempotency_key and request.idempotency_key in self._idem:return self._idem[request.idempotency_key]
        o=self._orders.create(request); valid,reasons=self._validator.validate(request)
        if not valid:
            self._orders.transition(o,OrderStatus.REJECTED); o.failure_reason=','.join(reasons); return self._finalize(request,ExecutionResult.create(ExecutionStatus.REJECTED,o,(),o.failure_reason))
        for s in (OrderStatus.VALIDATED,OrderStatus.ROUTED,OrderStatus.SUBMITTED): self._orders.transition(o,s)
        try: ack=self._retry.execute(lambda:self._router.route(o))
        except Exception as e:
            self._orders.transition(o,OrderStatus.FAILED); return self._finalize(request,ExecutionResult.create(ExecutionStatus.FAILED,o,(),str(e)))
        if not ack.accepted:
            self._orders.transition(o,OrderStatus.REJECTED); return self._finalize(request,ExecutionResult.create(ExecutionStatus.REJECTED,o,(),ack.message))
        o.broker_order_id=ack.broker_order_id; self._orders.transition(o,OrderStatus.ACKNOWLEDGED)
        fills=self._retry.execute(lambda:self._router.collect_fills(o)); self._fills.apply(o,fills)
        if o.filled_quantity==o.request.quantity: self._orders.transition(o,OrderStatus.FILLED); status=ExecutionStatus.SUCCESS; msg='Order fully filled'
        elif o.filled_quantity>0: self._orders.transition(o,OrderStatus.PARTIALLY_FILLED); status=ExecutionStatus.PARTIAL; msg='Order partially filled'
        else: self._orders.transition(o,OrderStatus.FAILED); status=ExecutionStatus.FAILED; msg='No fills received'
        ok,issues=self._recon.reconcile(o)
        if not ok: status=ExecutionStatus.FAILED; msg='Reconciliation failed: '+','.join(issues)
        return self._finalize(request,ExecutionResult.create(status,o,self._fills.for_order(o.order_id),msg))
    def _finalize(self,request,result):
        self._audit.append(result); self._metrics.increment('total'); self._metrics.increment(result.status.value.lower()); self._metrics.increment('fills',len(result.fills)); self._metrics.increment('filled_quantity',sum(f.quantity for f in result.fills))
        if request.idempotency_key:self._idem[request.idempotency_key]=result
        return result
    def metrics(self): return self._metrics.snapshot()
    def recent_executions(self,limit=50): return self._audit.recent(limit)
    def recent_orders(self,limit=50): return self._orders.recent(limit)
    def health(self): return {'status':'HEALTHY','mode':'SIMULATED','metrics':self.metrics(),'audit_entries':self._audit.count()}
