from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .component_registry import ComponentRegistry
from .dependency_graph import DependencyGraph


@dataclass(frozen=True, slots=True)
class IntegrationValidationResult:
    valid: bool
    present: tuple[str, ...]
    missing: tuple[str, ...]
    dependency_valid: bool
    details: dict[str, Any]


class IntegrationValidator:
    DEFAULT_REQUIRED = (
        "recovery_coordinator",
        "circuit_breaker",
        "retry_engine",
        "failover_manager",
        "checkpoint_manager",
        "graceful_shutdown",
    )

    def __init__(
        self,
        registry: ComponentRegistry,
        dependency_graph: DependencyGraph,
    ) -> None:
        self.registry = registry
        self.dependency_graph = dependency_graph

    def validate(
        self,
        required_components: tuple[str, ...] | None = None,
    ) -> IntegrationValidationResult:
        required = required_components or self.DEFAULT_REQUIRED
        names = set(self.registry.names())
        present = tuple(name for name in required if name in names)
        missing = tuple(name for name in required if name not in names)
        dependency_report = self.dependency_graph.validate()

        return IntegrationValidationResult(
            valid=not missing and dependency_report.valid,
            present=present,
            missing=missing,
            dependency_valid=dependency_report.valid,
            details={
                "missing_dependencies": list(dependency_report.missing_dependencies),
                "cycles": [list(cycle) for cycle in dependency_report.cycles],
                "startup_order": list(dependency_report.startup_order),
                "shutdown_order": list(dependency_report.shutdown_order),
            },
        )
