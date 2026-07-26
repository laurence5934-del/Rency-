from __future__ import annotations

from .dependency_graph import DependencyGraph
from .health_engine import HealthEngine
from .models import DiagnosticFinding, IncidentSeverity


class DiagnosticsEngine:
    def __init__(
        self,
        dependency_graph: DependencyGraph,
        health_engine: HealthEngine,
    ) -> None:
        self.dependency_graph = dependency_graph
        self.health_engine = health_engine

    def run(self) -> tuple[DiagnosticFinding, ...]:
        findings: list[DiagnosticFinding] = []
        dependency_report = self.dependency_graph.validate()

        for item in dependency_report.missing_dependencies:
            findings.append(DiagnosticFinding(
                code="MISSING_DEPENDENCY",
                severity=IncidentSeverity.CRITICAL,
                component=item.split("->", 1)[0],
                message=f"Missing dependency: {item}",
                remediation="Register the dependency before enabling live trading.",
            ))

        for cycle in dependency_report.cycles:
            findings.append(DiagnosticFinding(
                code="DEPENDENCY_CYCLE",
                severity=IncidentSeverity.CRITICAL,
                component=cycle[0] if cycle else None,
                message="Dependency cycle detected: " + " -> ".join(cycle),
                remediation="Break the cycle by introducing a stable interface boundary.",
            ))

        health = self.health_engine.evaluate()
        for component in health.components:
            if not component.healthy:
                findings.append(DiagnosticFinding(
                    code="COMPONENT_UNHEALTHY",
                    severity=IncidentSeverity.ERROR,
                    component=component.name,
                    message=component.message or "Component health check failed.",
                    remediation="Inspect component logs, dependencies, and recovery status.",
                    details=component.details,
                ))
            elif not component.ready:
                findings.append(DiagnosticFinding(
                    code="COMPONENT_NOT_READY",
                    severity=IncidentSeverity.WARNING,
                    component=component.name,
                    message=component.message or "Component is not ready.",
                ))

        return tuple(findings)
