from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Any, Protocol

from .models import StrategyDefinition


class ExecutableStrategy(Protocol):
    definition: StrategyDefinition

    def evaluate(self, market_context: dict[str, Any]) -> Any: ...


StrategyBuilder = Callable[[StrategyDefinition], ExecutableStrategy]


class StrategyFactory:
    def __init__(self) -> None:
        self._builders: dict[str, StrategyBuilder] = {}
        self._lock = RLock()

    def register_builder(self, category: str, builder: StrategyBuilder, *, replace: bool = False) -> None:
        key = category.strip().lower()
        if not key:
            raise ValueError("category is required")
        with self._lock:
            if key in self._builders and not replace:
                raise ValueError(f"builder already exists for category: {key}")
            self._builders[key] = builder

    def create(self, definition: StrategyDefinition) -> ExecutableStrategy:
        with self._lock:
            builder = self._builders.get(definition.category)
        if builder is None:
            raise KeyError(f"no builder for category: {definition.category}")
        return builder(definition)
