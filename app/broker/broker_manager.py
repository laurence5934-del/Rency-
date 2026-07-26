from __future__ import annotations

from .audit_log import BrokerAuditLog
from .broker_health import BrokerHealthMonitor
from .broker_models import BrokerOrderRequest, BrokerOrderResult
from .broker_registry import BrokerRegistry
from .broker_router import BrokerRouter
from .metrics import BrokerMetrics
from .rate_limiter import SlidingWindowRateLimiter


class EnterpriseBrokerManager:
    def __init__(
        self,
        registry: BrokerRegistry,
        *,
        default_broker: str = "SIMULATED",
        metrics: BrokerMetrics | None = None,
        audit_log: BrokerAuditLog | None = None,
        rate_limiter: SlidingWindowRateLimiter | None = None,
    ) -> None:
        self.registry = registry
        self.router = BrokerRouter(registry, default_broker)
        self.health_monitor = BrokerHealthMonitor(registry)
        self.metrics = metrics or BrokerMetrics()
        self.audit_log = audit_log or BrokerAuditLog()
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter()

    def submit(self, request: BrokerOrderRequest, broker_name: str | None = None) -> BrokerOrderResult:
        if not self.rate_limiter.acquire():
            self.metrics.increment("rate_limited")
            raise RuntimeError("broker request rate limit exceeded")
        self.metrics.increment("orders_submitted")
        result = self.router.route(request, broker_name)
        self.metrics.increment(f"status_{result.status.value.lower()}")
        self.audit_log.append(result)
        return result

    def health(self) -> dict[str, object]:
        snapshots = self.health_monitor.check_all()
        return {
            "status": "HEALTHY" if snapshots else "DEGRADED",
            "registered_brokers": self.registry.names(),
            "brokers": [
                {
                    "name": item.broker_name,
                    "status": item.status.value,
                    "environment": item.environment.value,
                    "latency_ms": item.latency_ms,
                    "message": item.message,
                }
                for item in snapshots
            ],
            "metrics": self.metrics.snapshot(),
        }
