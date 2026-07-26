from __future__ import annotations

from collections.abc import Iterable

from .models import StrategyDefinition


class DependencyResolutionError(ValueError):
    pass


class DependencyResolver:
    """Validates dependency presence and returns a topological order."""

    def resolve(self, strategies: Iterable[StrategyDefinition]) -> tuple[StrategyDefinition, ...]:
        by_id = {strategy.strategy_id: strategy for strategy in strategies}
        ordered: list[StrategyDefinition] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(strategy_id: str) -> None:
            if strategy_id in visited:
                return
            if strategy_id in visiting:
                raise DependencyResolutionError(f"dependency cycle detected at {strategy_id}")
            if strategy_id not in by_id:
                raise DependencyResolutionError(f"missing dependency: {strategy_id}")
            visiting.add(strategy_id)
            for dependency in by_id[strategy_id].dependencies:
                visit(dependency)
            visiting.remove(strategy_id)
            visited.add(strategy_id)
            ordered.append(by_id[strategy_id])

        for key in sorted(by_id):
            visit(key)
        return tuple(ordered)
