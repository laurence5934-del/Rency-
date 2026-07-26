from __future__ import annotations

from .broker_models import BrokerOrderRequest, BrokerOrderResult
from .broker_registry import BrokerRegistry


class BrokerFailover:
    def __init__(self, registry: BrokerRegistry) -> None:
        self._registry = registry

    def execute(self, request: BrokerOrderRequest, broker_names: tuple[str, ...]) -> BrokerOrderResult:
        errors: list[str] = []
        for name in broker_names:
            try:
                broker = self._registry.get(name)
                return broker.submit_order(request)
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        raise RuntimeError("all brokers failed: " + " | ".join(errors))
