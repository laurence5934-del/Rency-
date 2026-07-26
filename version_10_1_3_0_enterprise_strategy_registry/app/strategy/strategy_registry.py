from __future__ import annotations

from threading import RLock
from typing import Iterable

from .audit_log import StrategyAuditLog
from .metrics import StrategyMetrics
from .models import StrategyDefinition, StrategyStatus, StrategyVersion
from .strategy_validator import StrategyValidator


class StrategyNotFoundError(KeyError):
    pass


class StrategyConflictError(ValueError):
    pass


class StrategyRegistry:
    """Thread-safe source of truth for immutable strategy definitions."""

    def __init__(self, validator: StrategyValidator | None = None, audit_log: StrategyAuditLog | None = None,
                 metrics: StrategyMetrics | None = None) -> None:
        self._validator = validator or StrategyValidator()
        self._audit = audit_log or StrategyAuditLog()
        self._metrics = metrics or StrategyMetrics()
        self._items: dict[str, dict[StrategyVersion, StrategyDefinition]] = {}
        self._lock = RLock()

    @property
    def audit_log(self) -> StrategyAuditLog:
        return self._audit

    @property
    def metrics(self) -> StrategyMetrics:
        return self._metrics

    def register(self, strategy: StrategyDefinition, *, replace: bool = False) -> StrategyDefinition:
        self._validator.validate(strategy).require_valid()
        with self._lock:
            versions = self._items.setdefault(strategy.strategy_id, {})
            if strategy.version in versions and not replace:
                self._metrics.increment("registration_conflicts")
                raise StrategyConflictError(f"strategy already registered: {strategy.key}")
            versions[strategy.version] = strategy
            self._metrics.increment("registrations")
            self._audit.record("strategy.registered", strategy.key, {"replace": replace})
            return strategy

    def get(self, strategy_id: str, version: StrategyVersion | str | None = None) -> StrategyDefinition:
        with self._lock:
            versions = self._items.get(strategy_id)
            if not versions:
                raise StrategyNotFoundError(strategy_id)
            selected = max(versions) if version is None else (StrategyVersion.parse(version) if isinstance(version, str) else version)
            try:
                return versions[selected]
            except KeyError as exc:
                raise StrategyNotFoundError(f"{strategy_id}@{selected}") from exc

    def list(self, *, status: StrategyStatus | None = None, category: str | None = None,
             latest_only: bool = True) -> tuple[StrategyDefinition, ...]:
        with self._lock:
            values = [max(v.values(), key=lambda s: s.version) for v in self._items.values()] if latest_only else [s for v in self._items.values() for s in v.values()]
        if status is not None:
            values = [s for s in values if s.status == status]
        if category is not None:
            values = [s for s in values if s.category == category.strip().lower()]
        return tuple(sorted(values, key=lambda s: (s.strategy_id, s.version)))

    def set_status(self, strategy_id: str, version: StrategyVersion | str, status: StrategyStatus) -> StrategyDefinition:
        current = self.get(strategy_id, version)
        updated = current.with_status(status)
        with self._lock:
            self._items[strategy_id][updated.version] = updated
        self._metrics.increment(f"status.{status.value}")
        self._audit.record("strategy.status_changed", updated.key, {"status": status.value})
        return updated

    def remove(self, strategy_id: str, version: StrategyVersion | str) -> StrategyDefinition:
        target = self.get(strategy_id, version)
        with self._lock:
            del self._items[strategy_id][target.version]
            if not self._items[strategy_id]:
                del self._items[strategy_id]
        self._metrics.increment("removals")
        self._audit.record("strategy.removed", target.key, {})
        return target

    def snapshot(self) -> dict[str, object]:
        strategies = self.list(latest_only=False)
        return {
            "strategy_count": len({s.strategy_id for s in strategies}),
            "version_count": len(strategies),
            "certified_count": sum(s.status == StrategyStatus.CERTIFIED for s in strategies),
            "strategies": tuple(s.key for s in strategies),
        }
