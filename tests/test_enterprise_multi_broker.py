from app.broker import (
    BrokerOrderRequest,
    BrokerOrderSide,
    BrokerOrderStatus,
    BrokerRegistry,
    EnterpriseBrokerManager,
    SimulatedBroker,
)


def test_partial_fill():
    registry = BrokerRegistry()
    registry.register(SimulatedBroker(fill_ratio=0.5))
    manager = EnterpriseBrokerManager(registry)
    result = manager.submit(BrokerOrderRequest("NVDA", BrokerOrderSide.BUY, 20))
    assert result.status == BrokerOrderStatus.PARTIALLY_FILLED
    assert result.filled_quantity == 10
