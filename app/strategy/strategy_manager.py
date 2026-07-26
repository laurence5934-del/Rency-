from __future__ import annotations

from .models import StrategyDefinition, StrategyStatus, StrategyVersion
from .strategy_factory import ExecutableStrategy, StrategyFactory
from .strategy_registry import StrategyRegistry


class StrategyManager:
    """Application service combining registry and executable factory."""

    def __init__(self, registry: StrategyRegistry | None = None, factory: StrategyFactory | None = None) -> None:
        self.registry = registry or StrategyRegistry()
        self.factory = factory or StrategyFactory()

    def onboard(self, definition: StrategyDefinition) -> StrategyDefinition:
        return self.registry.register(definition)

    def certify(self, strategy_id: str, version: StrategyVersion | str) -> StrategyDefinition:
        return self.registry.set_status(strategy_id, version, StrategyStatus.CERTIFIED)

    def instantiate(self, strategy_id: str, version: StrategyVersion | str | None = None,
                    *, require_certified: bool = True) -> ExecutableStrategy:
        definition = self.registry.get(strategy_id, version)
        if require_certified and definition.status != StrategyStatus.CERTIFIED:
            raise PermissionError(f"strategy is not certified: {definition.key}")
        return self.factory.create(definition)
