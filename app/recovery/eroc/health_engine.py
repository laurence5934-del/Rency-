from __future__ import annotations

import time
from typing import Any, Mapping

from .component_registry import ComponentRegistry, RegisteredComponent
from .models import (
    ComponentCriticality,
    ComponentHealth,
    ComponentState,
    HealthSnapshot,
    utc_now,
)


class HealthEngine:
    def __init__(self, registry: ComponentRegistry) -> None:
        self.registry = registry

    def evaluate(self) -> HealthSnapshot:
        results = tuple(self._check(component) for component in self.registry.all())
        blockers: list[str] = []
        warnings: list[str] = []
        weighted_score = 0.0
        total_weight = 0.0

        for component, health in zip(self.registry.all(), results):
            weight = {
                ComponentCriticality.OPTIONAL: 1.0,
                ComponentCriticality.IMPORTANT: 2.0,
                ComponentCriticality.CRITICAL: 4.0,
            }[component.criticality]
            total_weight += weight
            weighted_score += health.score * weight

            if component.criticality == ComponentCriticality.CRITICAL and not health.ready:
                blockers.append(component.name)
            elif not health.healthy:
                warnings.append(component.name)

        score = weighted_score / total_weight if total_weight else 100.0
        return HealthSnapshot(
            created_at_utc=utc_now(),
            healthy=all(item.healthy for item in results) if results else True,
            ready=not blockers,
            score=round(score, 2),
            components=results,
            blockers=tuple(blockers),
            warnings=tuple(warnings),
        )

    def _check(self, component: RegisteredComponent) -> ComponentHealth:
        started = time.monotonic()
        try:
            raw = component.health_check()
            latency_ms = (time.monotonic() - started) * 1000.0
            return self._normalize(component.name, raw, latency_ms)
        except Exception as exc:
            return ComponentHealth(
                name=component.name,
                state=ComponentState.FAILED,
                healthy=False,
                ready=False,
                score=0.0,
                checked_at_utc=utc_now(),
                latency_ms=(time.monotonic() - started) * 1000.0,
                message=f"{type(exc).__name__}: {exc}",
            )

    @staticmethod
    def _normalize(name: str, raw: Any, latency_ms: float) -> ComponentHealth:
        if isinstance(raw, bool):
            healthy = raw
            ready = raw
            state = ComponentState.READY if raw else ComponentState.FAILED
            score = 100.0 if raw else 0.0
            message = ""
            details: Mapping[str, Any] = {}
        elif isinstance(raw, Mapping):
            healthy = bool(raw.get("healthy", True))
            ready = bool(raw.get("ready", healthy))
            state_value = raw.get("state")
            state = ComponentState(str(state_value)) if state_value else (
                ComponentState.READY if ready else ComponentState.DEGRADED if healthy else ComponentState.FAILED
            )
            score = float(raw.get("score", 100.0 if healthy else 0.0))
            message = str(raw.get("message", ""))
            details = dict(raw)
        else:
            healthy = True
            ready = True
            state = ComponentState.READY
            score = 100.0
            message = str(raw) if raw is not None else ""
            details = {}

        return ComponentHealth(
            name=name,
            state=state,
            healthy=healthy,
            ready=ready,
            score=max(0.0, min(100.0, score)),
            checked_at_utc=utc_now(),
            latency_ms=latency_ms,
            message=message,
            details=details,
        )
