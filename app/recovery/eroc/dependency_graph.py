from __future__ import annotations

from dataclasses import dataclass

from .component_registry import ComponentRegistry


@dataclass(frozen=True, slots=True)
class DependencyValidationReport:
    valid: bool
    missing_dependencies: tuple[str, ...]
    cycles: tuple[tuple[str, ...], ...]
    startup_order: tuple[str, ...]
    shutdown_order: tuple[str, ...]
    orphan_components: tuple[str, ...]


class DependencyGraph:
    def __init__(self, registry: ComponentRegistry) -> None:
        self.registry = registry

    def validate(self) -> DependencyValidationReport:
        components = {item.name: item for item in self.registry.all()}
        missing: list[str] = []

        for item in components.values():
            for dependency in item.dependencies:
                if dependency not in components:
                    missing.append(f"{item.name}->{dependency}")

        cycles = self._find_cycles(components)
        startup_order = self._topological_order(components) if not cycles else ()
        depended_on = {
            dependency
            for item in components.values()
            for dependency in item.dependencies
            if dependency in components
        }
        orphans = tuple(sorted(name for name in components if name not in depended_on and not components[name].dependencies))

        return DependencyValidationReport(
            valid=not missing and not cycles,
            missing_dependencies=tuple(sorted(set(missing))),
            cycles=tuple(cycles),
            startup_order=tuple(startup_order),
            shutdown_order=tuple(reversed(startup_order)),
            orphan_components=orphans,
        )

    @staticmethod
    def _topological_order(components: dict[str, object]) -> list[str]:
        indegree = {name: 0 for name in components}
        dependents: dict[str, list[str]] = {name: [] for name in components}

        for name, item in components.items():
            for dependency in item.dependencies:
                if dependency in components:
                    indegree[name] += 1
                    dependents[dependency].append(name)

        queue = sorted(name for name, degree in indegree.items() if degree == 0)
        order: list[str] = []

        while queue:
            current = queue.pop(0)
            order.append(current)
            for dependent in sorted(dependents[current]):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    queue.append(dependent)
                    queue.sort()
        return order

    @staticmethod
    def _find_cycles(components: dict[str, object]) -> list[tuple[str, ...]]:
        visiting: set[str] = set()
        visited: set[str] = set()
        stack: list[str] = []
        cycles: list[tuple[str, ...]] = []

        def visit(name: str) -> None:
            if name in visiting:
                index = stack.index(name)
                cycle = tuple(stack[index:] + [name])
                if cycle not in cycles:
                    cycles.append(cycle)
                return
            if name in visited:
                return
            visiting.add(name)
            stack.append(name)
            for dependency in components[name].dependencies:
                if dependency in components:
                    visit(dependency)
            stack.pop()
            visiting.remove(name)
            visited.add(name)

        for name in sorted(components):
            visit(name)
        return cycles
