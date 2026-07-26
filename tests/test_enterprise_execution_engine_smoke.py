from app.ai.execution_engine import EnterpriseExecutionEngine,ExecutionRequest,ExecutionStatus,OrderSide,OrderStatus
engine=EnterpriseExecutionEngine()
req=ExecutionRequest(symbol='PLTR',side=OrderSide.BUY,quantity=100,idempotency_key='execution-smoke-001')
res=engine.execute(req)
assert res.status==ExecutionStatus.SUCCESS
assert res.order.status==OrderStatus.FILLED
assert res.order.filled_quantity==100
assert engine.metrics()['total']==1
assert engine.health()['mode']=='SIMULATED'
assert engine.execute(req).execution_id==res.execution_id
assert engine.metrics()['total']==1
