from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Event, RLock, Thread
from typing import Any, Callable, Mapping

from .component_registry import ComponentRegistry, RegisteredComponent
from .dashboard_api import RecoveryDashboardAPI
from .dependency_graph import DependencyGraph
from .diagnostics_engine import DiagnosticsEngine
from .health_engine import HealthEngine
from .incident_manager import IncidentManager
from .integration_validator import IntegrationValidator
from .metrics_engine import RecoveryMetricsEngine
from .models import (
    ComponentCriticality,
    HealthSnapshot,
    IncidentSeverity,
    ReadinessReport,
    RecoveryAction,
    RecoveryPolicy,
)
from .policy_engine import RecoveryPolicyEngine
from .readiness_validator import ReadinessValidator
from .timeline import RecoveryTimeline


@dataclass(frozen=True, slots=True)
class RecoveryOperatingCenterConfig:
    health_interval_seconds: float = 30.0
    timeline_capacity: int = 5000
    auto_open_health_incidents: bool = True
    publish_events: bool = True

    def __post_init__(self) -> None:
        if self.health_interval_seconds <= 0:
            raise ValueError("health_interval_seconds must be positive")
        if self.timeline_capacity < 1:
            raise ValueError("timeline_capacity must be positive")


class EnterpriseRecoveryOperatingCenter:
    """
    Version 10.0.8.7 - Enterprise Recovery Operating Center.

    Integrates component registration, dependency validation, health aggregation,
    trading readiness, policy execution, incident management, diagnostics,
    recovery metrics, timeline auditing, dashboard access, and continuous
    validation for the complete Version 10.0.8 recovery framework.
    """

    def __init__(
        self,
        *,
        config: RecoveryOperatingCenterConfig | None = None,
        event_publisher: Any | None = None,
    ) -> None:
        self.config = config or RecoveryOperatingCenterConfig()
        self.event_publisher = event_publisher

        self.registry = ComponentRegistry()
        self.dependency_graph = DependencyGraph(self.registry)
        self.health_engine = HealthEngine(self.registry)
        self.readiness_validator = ReadinessValidator(self.health_engine)
        self.timeline = RecoveryTimeline(self.config.timeline_capacity)
        self.incidents = IncidentManager(self.timeline)
        self.policies = RecoveryPolicyEngine()
        self.metrics = RecoveryMetricsEngine()
        self.diagnostics = DiagnosticsEngine(
            self.dependency_graph,
            self.health_engine,
        )
        self.integration = IntegrationValidator(
            self.registry,
            self.dependency_graph,
        )
        self.dashboard = RecoveryDashboardAPI(self)

        self._lock = RLock()
        self._stop_event = Event()
        self._monitor_thread: Thread | None = None
        self._last_health: HealthSnapshot | None = None

        self._install_default_policies()

    def register_component(
        self,
        *,
        name: str,
        version: str,
        criticality: ComponentCriticality,
        health_check: Callable[[], Any],
        dependencies: tuple[str, ...] = (),
        recovery_handler: Callable[[str, Mapping[str, Any]], Any] | None = None,
        metrics_provider: Callable[[], Mapping[str, Any]] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self.registry.register(
            RegisteredComponent(
                name=name,
                version=version,
                criticality=criticality,
                health_check=health_check,
                dependencies=dependencies,
                recovery_handler=recovery_handler,
                metrics_provider=metrics_provider,
                metadata=dict(metadata or {}),
            )
        )
        self.timeline.record(
            "component.registered",
            f"Registered component {name}",
            component=name,
            payload={"version": version, "criticality": criticality.value},
        )

    def wire_recovery_components(
        self,
        *,
        recovery_coordinator: Any,
        circuit_breaker: Any,
        retry_engine: Any,
        failover_manager: Any,
        checkpoint_manager: Any,
        graceful_shutdown: Any,
    ) -> None:
        components = {
            "recovery_coordinator": recovery_coordinator,
            "circuit_breaker": circuit_breaker,
            "retry_engine": retry_engine,
            "failover_manager": failover_manager,
            "checkpoint_manager": checkpoint_manager,
            "graceful_shutdown": graceful_shutdown,
        }

        dependencies = {
            "recovery_coordinator": (
                "circuit_breaker",
                "retry_engine",
                "failover_manager",
                "checkpoint_manager",
                "graceful_shutdown",
            ),
            "circuit_breaker": (),
            "retry_engine": ("circuit_breaker",),
            "failover_manager": ("retry_engine", "circuit_breaker"),
            "checkpoint_manager": (),
            "graceful_shutdown": ("checkpoint_manager",),
        }

        for name, component in components.items():
            self.register_component(
                name=name,
                version=str(getattr(component, "version", "10.0.8")),
                criticality=ComponentCriticality.CRITICAL,
                health_check=self._health_adapter(component),
                dependencies=dependencies[name],
                recovery_handler=self._recovery_adapter(component),
                metrics_provider=self._metrics_adapter(component),
            )

        self._register_action_handlers(components)

    def validate_platform(self) -> dict[str, Any]:
        dependency = self.dependency_graph.validate()
        integration = self.integration.validate()
        health = self.health()
        readiness = self.readiness()
        diagnostics = self.diagnostics.run()

        return {
            "valid": (
                dependency.valid
                and integration.valid
                and health.healthy
                and readiness.trading_allowed
            ),
            "dependency": {
                "valid": dependency.valid,
                "missing_dependencies": list(dependency.missing_dependencies),
                "cycles": [list(item) for item in dependency.cycles],
                "startup_order": list(dependency.startup_order),
                "shutdown_order": list(dependency.shutdown_order),
            },
            "integration": {
                "valid": integration.valid,
                "present": list(integration.present),
                "missing": list(integration.missing),
                "details": integration.details,
            },
            "health": health.to_dict(),
            "readiness": readiness.to_dict(),
            "diagnostics": [item.to_dict() for item in diagnostics],
        }

    def health(self) -> HealthSnapshot:
        snapshot = self.health_engine.evaluate()
        with self._lock:
            self._last_health = snapshot
        return snapshot

    def readiness(self) -> ReadinessReport:
        return self.readiness_validator.validate()

    def recover(
        self,
        failure_type: str,
        *,
        component: str | None = None,
        context: Mapping[str, Any] | None = None,
        severity: IncidentSeverity = IncidentSeverity.ERROR,
    ) -> dict[str, Any]:
        started = time.monotonic()
        incident = self.incidents.open(
            title=f"Recovery required: {failure_type}",
            severity=severity,
            component=component,
            metadata=context,
        )
        self.metrics.increment("recoveries_attempted")
        self.metrics.record_failure()

        self._publish(
            "eroc.recovery_started",
            {
                "incident_id": incident.incident_id,
                "failure_type": failure_type,
                "component": component,
            },
        )

        results = self.policies.execute(
            failure_type,
            context={
                **dict(context or {}),
                "component": component,
                "incident_id": incident.incident_id,
            },
        )

        for result in results:
            self.incidents.add_action(
                incident.incident_id,
                f"{result['action']}: {'success' if result['success'] else 'failure'}",
            )

        succeeded = bool(results) and all(item["success"] for item in results)
        if succeeded:
            self.incidents.resolve(
                incident.incident_id,
                root_cause=str((context or {}).get("root_cause", "unspecified")),
            )
            self.metrics.increment("recoveries_succeeded")
        else:
            self.metrics.increment("recoveries_failed")

        duration = time.monotonic() - started
        self.metrics.observe("recovery_duration", duration)

        outcome = {
            "incident_id": incident.incident_id,
            "failure_type": failure_type,
            "component": component,
            "succeeded": succeeded,
            "duration_seconds": duration,
            "actions": results,
        }
        self._publish("eroc.recovery_completed", outcome)
        return outcome

    def start_monitoring(self) -> None:
        with self._lock:
            if self._monitor_thread is not None and self._monitor_thread.is_alive():
                return
            self._stop_event.clear()
            self._monitor_thread = Thread(
                target=self._monitor_loop,
                name="eroc-health-monitor",
                daemon=True,
            )
            self._monitor_thread.start()

    def stop_monitoring(self, timeout_seconds: float = 5.0) -> None:
        self._stop_event.set()
        thread = self._monitor_thread
        if thread is not None:
            thread.join(timeout_seconds)

    def _monitor_loop(self) -> None:
        while not self._stop_event.wait(self.config.health_interval_seconds):
            snapshot = self.health()
            self.timeline.record(
                "health.snapshot",
                "Platform health evaluated",
                payload={
                    "healthy": snapshot.healthy,
                    "ready": snapshot.ready,
                    "score": snapshot.score,
                },
            )
            if self.config.auto_open_health_incidents:
                self._open_health_incidents(snapshot)

    def _open_health_incidents(self, snapshot: HealthSnapshot) -> None:
        active_components = {
            item.component
            for item in self.incidents.active()
            if item.component is not None
        }
        for health in snapshot.components:
            if not health.healthy and health.name not in active_components:
                self.incidents.open(
                    title=f"Component unhealthy: {health.name}",
                    severity=IncidentSeverity.CRITICAL if not health.ready else IncidentSeverity.ERROR,
                    component=health.name,
                    metadata=health.to_dict(),
                )

    def _install_default_policies(self) -> None:
        defaults = (
            RecoveryPolicy(
                name="broker-failure-policy",
                failure_type="broker_failure",
                actions=(
                    RecoveryAction.RETRY,
                    RecoveryAction.OPEN_CIRCUIT,
                    RecoveryAction.FAILOVER,
                    RecoveryAction.CHECKPOINT,
                ),
            ),
            RecoveryPolicy(
                name="market-data-failure-policy",
                failure_type="market_data_failure",
                actions=(
                    RecoveryAction.RETRY,
                    RecoveryAction.FAILOVER,
                    RecoveryAction.PAUSE_TRADING,
                ),
            ),
            RecoveryPolicy(
                name="critical-platform-failure-policy",
                failure_type="critical_platform_failure",
                actions=(
                    RecoveryAction.CHECKPOINT,
                    RecoveryAction.PAUSE_TRADING,
                    RecoveryAction.SHUTDOWN,
                ),
            ),
        )
        for policy in defaults:
            self.policies.register_policy(policy)

    def _register_action_handlers(self, components: Mapping[str, Any]) -> None:
        self.policies.register_action_handler(
            RecoveryAction.RETRY,
            lambda failure_type, context: self._invoke_first(
                components["retry_engine"],
                ("execute", "run", "retry"),
                failure_type,
                context,
            ),
        )
        self.policies.register_action_handler(
            RecoveryAction.OPEN_CIRCUIT,
            lambda failure_type, context: self._invoke_first(
                components["circuit_breaker"],
                ("open", "trip", "record_failure"),
                failure_type,
                context,
            ),
        )
        self.policies.register_action_handler(
            RecoveryAction.FAILOVER,
            lambda failure_type, context: self._invoke_first(
                components["failover_manager"],
                ("failover", "trigger_failover", "switch_provider"),
                failure_type,
                context,
            ),
        )
        self.policies.register_action_handler(
            RecoveryAction.CHECKPOINT,
            lambda failure_type, context: self._invoke_first(
                components["checkpoint_manager"],
                ("create_checkpoint",),
                metadata={
                    "failure_type": failure_type,
                    **dict(context),
                },
            ),
        )
        self.policies.register_action_handler(
            RecoveryAction.RESTORE,
            lambda failure_type, context: self._invoke_first(
                components["checkpoint_manager"],
                ("restore_checkpoint",),
                context.get("checkpoint_id"),
            ),
        )
        self.policies.register_action_handler(
            RecoveryAction.SHUTDOWN,
            lambda failure_type, context: self._invoke_first(
                components["graceful_shutdown"],
                ("execute_shutdown", "request_shutdown"),
                reason=f"EROC recovery escalation: {failure_type}",
                metadata=context,
            ),
        )
        self.policies.register_action_handler(
            RecoveryAction.PAUSE_TRADING,
            lambda failure_type, context: {
                "paused": True,
                "reason": failure_type,
                "context": dict(context),
            },
        )

    @staticmethod
    def _invoke_first(target: Any, method_names: tuple[str, ...], *args: Any, **kwargs: Any) -> Any:
        for name in method_names:
            method = getattr(target, name, None)
            if callable(method):
                try:
                    return method(*args, **kwargs)
                except TypeError:
                    return method()
        raise AttributeError(
            f"{type(target).__name__} does not expose any supported method: {method_names}"
        )

    @staticmethod
    def _health_adapter(component: Any) -> Callable[[], Any]:
        for name in ("health_check", "health", "status"):
            candidate = getattr(component, name, None)
            if callable(candidate):
                return candidate
        return lambda: {"healthy": True, "ready": True, "message": "No explicit health check"}

    @staticmethod
    def _recovery_adapter(component: Any) -> Callable[[str, Mapping[str, Any]], Any] | None:
        for name in ("recover", "execute_recovery", "handle_failure"):
            candidate = getattr(component, name, None)
            if callable(candidate):
                return lambda failure_type, context, method=candidate: method(
                    failure_type=failure_type,
                    context=context,
                )
        return None

    @staticmethod
    def _metrics_adapter(component: Any) -> Callable[[], Mapping[str, Any]] | None:
        candidate = getattr(component, "metrics", None)
        return candidate if callable(candidate) else None

    def _publish(self, event_type: str, payload: Any) -> None:
        self.timeline.record(
            event_type,
            event_type,
            payload=payload if isinstance(payload, Mapping) else {"value": payload},
        )
        if self.config.publish_events and self.event_publisher is not None:
            self.event_publisher.publish_event(
                event_type,
                payload,
                source="enterprise_recovery_operating_center",
            )
