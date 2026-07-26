from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable, Mapping

from .models import ComponentCriticality


@dataclass(slots=True)
class RegisteredComponent:
    name: str
    version: str
    criticality: ComponentCriticality
    health_check: Callable[[], Any]
    dependencies: tuple[str, ...] = ()
    recovery_handler: Callable[[str, Mapping[str, Any]], Any] | None = None
    metrics_provider: Callable[[], Mapping[str, Any]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    registered_monotonic: float = field(default_factory=time.monotonic)


class ComponentRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._components: dict[str, RegisteredComponent] = {}

    def register(self, component: RegisteredComponent) -> None:
        if not component.name.strip():
            raise ValueError("component name cannot be empty")
        with self._lock:
            if component.name in self._components:
                raise KeyError(f"component already registered: {component.name}")
            self._components[component.name] = component

    def unregister(self, name: str) -> bool:
        with self._lock:
            return self._components.pop(name, None) is not None

    def get(self, name: str) -> RegisteredComponent:
        with self._lock:
            component = self._components.get(name)
            if component is None:
                raise KeyError(f"unknown component: {name}")
            return component

    def try_get(self, name: str) -> RegisteredComponent | None:
        with self._lock:
            return self._components.get(name)

    def all(self) -> tuple[RegisteredComponent, ...]:
        with self._lock:
            return tuple(sorted(self._components.values(), key=lambda item: item.name))

    def names(self) -> tuple[str, ...]:
        return tuple(component.name for component in self.all())

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "name": item.name,
                "version": item.version,
                "criticality": item.criticality.value,
                "dependencies": list(item.dependencies),
                "metadata": dict(item.metadata),
            }
            for item in self.all()
        ]
