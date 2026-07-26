from __future__ import annotations

from dataclasses import replace

from .models import StrategyDefinition, StrategyVersion, utc_now


class StrategyVersioning:
    @staticmethod
    def next_patch(strategy: StrategyDefinition, **changes: object) -> StrategyDefinition:
        version = StrategyVersion(strategy.version.major, strategy.version.minor, strategy.version.patch + 1)
        return replace(strategy, version=version, updated_at=utc_now(), **changes)

    @staticmethod
    def next_minor(strategy: StrategyDefinition, **changes: object) -> StrategyDefinition:
        version = StrategyVersion(strategy.version.major, strategy.version.minor + 1, 0)
        return replace(strategy, version=version, updated_at=utc_now(), **changes)

    @staticmethod
    def next_major(strategy: StrategyDefinition, **changes: object) -> StrategyDefinition:
        version = StrategyVersion(strategy.version.major + 1, 0, 0)
        return replace(strategy, version=version, updated_at=utc_now(), **changes)
