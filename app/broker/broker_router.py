from __future__ import annotations

from .broker_models import BrokerOrderRequest, BrokerOrderResult, BrokerStatus
from .broker_registry import BrokerRegistry


class BrokerRouter:
    def __init__(self, registry: BrokerRegistry, default_broker: str = "SIMULATED") -> None:
        self._registry = registry
        self._default_broker = default_broker

    def route(self, request: BrokerOrderRequest, broker_name: str | None = None) -> BrokerOrderResult:
        broker = self._registry.get(broker_name or self._default_broker)
        health = broker.health()
        if health.status not in {BrokerStatus.HEALTHY, BrokerStatus.DEGRADED}:
            raise RuntimeError(f"broker unavailable: {broker.name}")
        return broker.submit_order(request)
