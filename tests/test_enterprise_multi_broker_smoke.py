from app.broker import (
    BrokerOrderRequest,
    BrokerOrderSide,
    BrokerOrderStatus,
    BrokerRegistry,
    EnterpriseBrokerManager,
    PaperBroker,
    SimulatedBroker,
)

registry = BrokerRegistry()
registry.register(SimulatedBroker(default_price=125.50))
registry.register(PaperBroker(default_price=126.00))
manager = EnterpriseBrokerManager(registry)

request = BrokerOrderRequest(
    symbol="PLTR",
    side=BrokerOrderSide.BUY,
    quantity=10,
    client_order_id="smoke-001",
    correlation_id="correlation-001",
)

result = manager.submit(request)
assert result.status == BrokerOrderStatus.FILLED
assert result.broker_name == "SIMULATED"
assert result.filled_quantity == 10
assert result.average_fill_price == 125.50
assert set(registry.names()) == {"PAPER", "SIMULATED"}
assert manager.health()["status"] == "HEALTHY"
assert manager.metrics.snapshot()["orders_submitted"] == 1
