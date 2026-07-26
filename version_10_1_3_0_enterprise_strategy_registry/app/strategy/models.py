from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrategyStatus(str, Enum):
    DRAFT = "draft"
    TESTING = "testing"
    CERTIFIED = "certified"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class RiskProfile(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass(frozen=True, order=True)
class StrategyVersion:
    major: int
    minor: int = 0
    patch: int = 0

    def __post_init__(self) -> None:
        if min(self.major, self.minor, self.patch) < 0:
            raise ValueError("version components must be non-negative")

    @classmethod
    def parse(cls, value: str) -> "StrategyVersion":
        parts = value.strip().removeprefix("v").split(".")
        if not 1 <= len(parts) <= 3:
            raise ValueError(f"invalid semantic version: {value}")
        try:
            numbers = [int(part) for part in parts]
        except ValueError as exc:
            raise ValueError(f"invalid semantic version: {value}") from exc
        numbers += [0] * (3 - len(numbers))
        return cls(*numbers)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class StrategyDefinition:
    strategy_id: str
    name: str
    version: StrategyVersion
    description: str
    author: str
    category: str
    risk_profile: RiskProfile
    supported_assets: tuple[str, ...]
    supported_timeframes: tuple[str, ...]
    parameters: Mapping[str, Any] = field(default_factory=dict)
    dependencies: tuple[str, ...] = ()
    entry_rules: tuple[str, ...] = ()
    exit_rules: tuple[str, ...] = ()
    position_sizing_rule: str = "fixed_fractional"
    status: StrategyStatus = StrategyStatus.DRAFT
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategy_id", self.strategy_id.strip())
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "category", self.category.strip().lower())
        object.__setattr__(self, "supported_assets", tuple(dict.fromkeys(a.upper() for a in self.supported_assets)))
        object.__setattr__(self, "supported_timeframes", tuple(dict.fromkeys(t.lower() for t in self.supported_timeframes)))
        object.__setattr__(self, "dependencies", tuple(dict.fromkeys(self.dependencies)))
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def key(self) -> str:
        return f"{self.strategy_id}@{self.version}"

    def with_status(self, status: StrategyStatus) -> "StrategyDefinition":
        return replace(self, status=status, updated_at=utc_now())


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str
    code: str = "invalid"


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...] = ()

    def require_valid(self) -> None:
        if not self.valid:
            details = "; ".join(f"{i.field}: {i.message}" for i in self.issues)
            raise ValueError(details)
