from __future__ import annotations

from .broker_models import BrokerHealthSnapshot, BrokerStatus
from .broker_registry import BrokerRegistry


class BrokerHealthMonitor:
    def __init__(self, registry: BrokerRegistry) -> None:
        self._registry = registry

    def check_all(self) -> tuple[BrokerHealthSnapshot, ...]:
        snapshots: list[BrokerHealthSnapshot] = []
        for broker in self._registry.all():
            try:
                snapshots.append(broker.health())
            except Exception as exc:
                snapshots.append(
                    BrokerHealthSnapshot(
                        broker_name=broker.name,
                        status=BrokerStatus.UNAVAILABLE,
                        environment=broker.environment,
                        latency_ms=0.0,
                        message=str(exc),
                    )
                )
        return tuple(snapshots)
