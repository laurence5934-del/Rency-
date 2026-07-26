from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from numbers import Real
from typing import Any, Iterable, Mapping, Sequence


class StrategyCategory(str, Enum):
    TREND = "TREND"
    MOMENTUM = "MOMENTUM"
    BREAKOUT = "BREAKOUT"
    MEAN_REVERSION = "MEAN_REVERSION"
    DEFENSIVE = "DEFENSIVE"
    VOLATILITY = "VOLATILITY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class StrategyProfile:
    """Describes one selectable trading strategy."""

    name: str
    category: StrategyCategory | str
    enabled: bool = True
    minimum_score: float = 0.0
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("name must be a string")

        name = self.name.strip()
        if not name:
            raise ValueError("name cannot be empty")

        category = self.category
        if isinstance(category, str):
            try:
                category = StrategyCategory(category.strip().upper())
            except ValueError as exc:
                raise ValueError(
                    f"unknown strategy category: {category}"
                ) from exc
        elif not isinstance(category, StrategyCategory):
            raise TypeError(
                "category must be StrategyCategory or string"
            )

        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a boolean")

        if (
            not isinstance(self.minimum_score, Real)
            or isinstance(self.minimum_score, bool)
        ):
            raise TypeError("minimum_score must be numeric")

        minimum_score = float(self.minimum_score)
        if not isfinite(minimum_score):
            raise ValueError("minimum_score must be finite")
        if not 0.0 <= minimum_score <= 1.0:
            raise ValueError("minimum_score must be between 0 and 1")

        metadata = {} if self.metadata is None else self.metadata
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping or None")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "minimum_score", minimum_score)
        object.__setattr__(self, "metadata", dict(metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "enabled": self.enabled,
            "minimum_score": self.minimum_score,
            "metadata": dict(self.metadata or {}),
        }


@dataclass(frozen=True, slots=True)
class StrategyMetrics:
    """Normalized strategy inputs used for selection."""

    historical_performance: float
    recent_performance: float
    confidence: float
    risk_score: float
    allocation_weight: float = 1.0

    def __post_init__(self) -> None:
        for name, value in (
            ("historical_performance", self.historical_performance),
            ("recent_performance", self.recent_performance),
            ("confidence", self.confidence),
            ("risk_score", self.risk_score),
            ("allocation_weight", self.allocation_weight),
        ):
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{name} must be numeric")

            numeric = float(value)
            if not isfinite(numeric):
                raise ValueError(f"{name} must be finite")
            if not 0.0 <= numeric <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")

            object.__setattr__(self, name, numeric)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "StrategyMetrics":
        if not isinstance(data, Mapping):
            raise TypeError("data must be a mapping")
        return cls(
            historical_performance=data["historical_performance"],
            recent_performance=data["recent_performance"],
            confidence=data["confidence"],
            risk_score=data["risk_score"],
            allocation_weight=data.get("allocation_weight", 1.0),
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "historical_performance": self.historical_performance,
            "recent_performance": self.recent_performance,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "allocation_weight": self.allocation_weight,
        }


@dataclass(frozen=True, slots=True)
class StrategySelection:
    """One ranked strategy selection result."""

    rank: int
    strategy_name: str
    category: StrategyCategory
    score: float
    normalized_weight: float
    compatible_score: float
    selected: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.rank, int) or isinstance(self.rank, bool):
            raise TypeError("rank must be an integer")
        if self.rank < 1:
            raise ValueError("rank must be at least 1")

        if not isinstance(self.strategy_name, str):
            raise TypeError("strategy_name must be a string")
        if not self.strategy_name.strip():
            raise ValueError("strategy_name cannot be empty")

        if not isinstance(self.category, StrategyCategory):
            raise TypeError("category must be a StrategyCategory")

        for name, value in (
            ("score", self.score),
            ("normalized_weight", self.normalized_weight),
            ("compatible_score", self.compatible_score),
        ):
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{name} must be numeric")
            numeric = float(value)
            if not isfinite(numeric):
                raise ValueError(f"{name} must be finite")
            if not 0.0 <= numeric <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
            object.__setattr__(self, name, numeric)

        if not isinstance(self.selected, bool):
            raise TypeError("selected must be a boolean")

        if not isinstance(self.reasons, tuple):
            object.__setattr__(self, "reasons", tuple(self.reasons))
        if any(not isinstance(reason, str) for reason in self.reasons):
            raise TypeError("all reasons must be strings")

        object.__setattr__(
            self,
            "strategy_name",
            self.strategy_name.strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "strategy_name": self.strategy_name,
            "category": self.category.value,
            "score": self.score,
            "normalized_weight": self.normalized_weight,
            "compatible_score": self.compatible_score,
            "selected": self.selected,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class StrategySelectionReport:
    """Complete strategy ranking and selected ensemble."""

    regime: str
    selections: tuple[StrategySelection, ...]
    selected_count: int
    top_strategy: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.regime, str):
            raise TypeError("regime must be a string")
        if not self.regime.strip():
            raise ValueError("regime cannot be empty")

        if not isinstance(self.selections, tuple):
            object.__setattr__(
                self,
                "selections",
                tuple(self.selections),
            )
        if any(
            not isinstance(item, StrategySelection)
            for item in self.selections
        ):
            raise TypeError(
                "all selections must be StrategySelection instances"
            )

        if (
            not isinstance(self.selected_count, int)
            or isinstance(self.selected_count, bool)
        ):
            raise TypeError("selected_count must be an integer")
        if self.selected_count < 0:
            raise ValueError("selected_count cannot be negative")

        if self.top_strategy is not None and not isinstance(
            self.top_strategy,
            str,
        ):
            raise TypeError("top_strategy must be a string or None")

        object.__setattr__(self, "regime", self.regime.strip().upper())

    @property
    def selected(self) -> tuple[StrategySelection, ...]:
        return tuple(item for item in self.selections if item.selected)

    def ensemble_weights(self) -> dict[str, float]:
        return {
            item.strategy_name: item.normalized_weight
            for item in self.selected
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime": self.regime,
            "selected_count": self.selected_count,
            "top_strategy": self.top_strategy,
            "selections": [
                item.to_dict() for item in self.selections
            ],
            "ensemble_weights": self.ensemble_weights(),
        }


class AIStrategySelector:
    """
    Rank and select strategies using market compatibility and performance.

    Version 9.8.0.3 combines:
    - historical performance
    - recent performance
    - market-regime compatibility
    - strategy confidence
    - risk quality
    - adaptive allocation weight
    """

    DEFAULT_COMPONENT_WEIGHTS = {
        "historical_performance": 0.25,
        "recent_performance": 0.20,
        "regime_compatibility": 0.25,
        "confidence": 0.15,
        "risk_score": 0.10,
        "allocation_weight": 0.05,
    }

    DEFAULT_COMPATIBILITY = {
        "STRONG_BULL": {
            StrategyCategory.BREAKOUT: 1.00,
            StrategyCategory.TREND: 0.95,
            StrategyCategory.MOMENTUM: 0.90,
            StrategyCategory.MEAN_REVERSION: 0.45,
            StrategyCategory.DEFENSIVE: 0.35,
            StrategyCategory.VOLATILITY: 0.60,
            StrategyCategory.UNKNOWN: 0.50,
        },
        "BULL": {
            StrategyCategory.BREAKOUT: 0.90,
            StrategyCategory.TREND: 0.95,
            StrategyCategory.MOMENTUM: 0.90,
            StrategyCategory.MEAN_REVERSION: 0.60,
            StrategyCategory.DEFENSIVE: 0.45,
            StrategyCategory.VOLATILITY: 0.60,
            StrategyCategory.UNKNOWN: 0.50,
        },
        "SIDEWAYS": {
            StrategyCategory.BREAKOUT: 0.45,
            StrategyCategory.TREND: 0.40,
            StrategyCategory.MOMENTUM: 0.50,
            StrategyCategory.MEAN_REVERSION: 1.00,
            StrategyCategory.DEFENSIVE: 0.70,
            StrategyCategory.VOLATILITY: 0.75,
            StrategyCategory.UNKNOWN: 0.50,
        },
        "BEAR": {
            StrategyCategory.BREAKOUT: 0.55,
            StrategyCategory.TREND: 0.75,
            StrategyCategory.MOMENTUM: 0.70,
            StrategyCategory.MEAN_REVERSION: 0.55,
            StrategyCategory.DEFENSIVE: 0.95,
            StrategyCategory.VOLATILITY: 0.80,
            StrategyCategory.UNKNOWN: 0.50,
        },
        "STRONG_BEAR": {
            StrategyCategory.BREAKOUT: 0.45,
            StrategyCategory.TREND: 0.70,
            StrategyCategory.MOMENTUM: 0.60,
            StrategyCategory.MEAN_REVERSION: 0.40,
            StrategyCategory.DEFENSIVE: 1.00,
            StrategyCategory.VOLATILITY: 0.90,
            StrategyCategory.UNKNOWN: 0.45,
        },
        "UNKNOWN": {
            category: 0.50 for category in StrategyCategory
        },
    }

    def __init__(
        self,
        *,
        component_weights: Mapping[str, Real] | None = None,
        top_n: int = 3,
        selection_threshold: float = 0.55,
        minimum_selected: int = 1,
    ) -> None:
        weights = dict(
            component_weights or self.DEFAULT_COMPONENT_WEIGHTS
        )

        expected = set(self.DEFAULT_COMPONENT_WEIGHTS)
        if set(weights) != expected:
            missing = expected - set(weights)
            extra = set(weights) - expected
            details: list[str] = []
            if missing:
                details.append(
                    "missing=" + ",".join(sorted(missing))
                )
            if extra:
                details.append(
                    "extra=" + ",".join(sorted(extra))
                )
            raise ValueError(
                "component_weights keys are invalid: "
                + "; ".join(details)
            )

        normalized_weights: dict[str, float] = {}
        total = 0.0
        for name, value in weights.items():
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(
                    f"component weight {name} must be numeric"
                )
            numeric = float(value)
            if not isfinite(numeric):
                raise ValueError(
                    f"component weight {name} must be finite"
                )
            if numeric < 0.0:
                raise ValueError(
                    f"component weight {name} cannot be negative"
                )
            normalized_weights[name] = numeric
            total += numeric

        if total <= 0.0:
            raise ValueError(
                "component weights must have a positive total"
            )

        self.component_weights = {
            name: value / total
            for name, value in normalized_weights.items()
        }

        if not isinstance(top_n, int) or isinstance(top_n, bool):
            raise TypeError("top_n must be an integer")
        if top_n < 1:
            raise ValueError("top_n must be at least 1")

        if (
            not isinstance(selection_threshold, Real)
            or isinstance(selection_threshold, bool)
        ):
            raise TypeError("selection_threshold must be numeric")
        threshold = float(selection_threshold)
        if not isfinite(threshold):
            raise ValueError("selection_threshold must be finite")
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                "selection_threshold must be between 0 and 1"
            )

        if (
            not isinstance(minimum_selected, int)
            or isinstance(minimum_selected, bool)
        ):
            raise TypeError("minimum_selected must be an integer")
        if minimum_selected < 0:
            raise ValueError("minimum_selected cannot be negative")
        if minimum_selected > top_n:
            raise ValueError(
                "minimum_selected cannot exceed top_n"
            )

        self.top_n = top_n
        self.selection_threshold = threshold
        self.minimum_selected = minimum_selected
        self._last_report: StrategySelectionReport | None = None

    @property
    def last_report(self) -> StrategySelectionReport | None:
        return self._last_report

    @staticmethod
    def _normalize_regime(regime: Any) -> str:
        if hasattr(regime, "trend"):
            regime = getattr(regime, "trend")
        if hasattr(regime, "value"):
            regime = getattr(regime, "value")
        if not isinstance(regime, str):
            raise TypeError(
                "regime must be a string, enum, or object with trend"
            )

        normalized = regime.strip().upper().replace(" ", "_")
        return normalized if normalized else "UNKNOWN"

    @classmethod
    def compatibility_score(
        cls,
        regime: Any,
        category: StrategyCategory,
    ) -> float:
        if not isinstance(category, StrategyCategory):
            raise TypeError(
                "category must be a StrategyCategory"
            )

        normalized_regime = cls._normalize_regime(regime)
        matrix = cls.DEFAULT_COMPATIBILITY.get(
            normalized_regime,
            cls.DEFAULT_COMPATIBILITY["UNKNOWN"],
        )
        return float(matrix.get(category, 0.50))

    def _composite_score(
        self,
        metrics: StrategyMetrics,
        compatibility: float,
    ) -> float:
        values = {
            "historical_performance": (
                metrics.historical_performance
            ),
            "recent_performance": metrics.recent_performance,
            "regime_compatibility": compatibility,
            "confidence": metrics.confidence,
            "risk_score": metrics.risk_score,
            "allocation_weight": metrics.allocation_weight,
        }

        score = sum(
            values[name] * self.component_weights[name]
            for name in self.component_weights
        )
        return min(1.0, max(0.0, score))

    @staticmethod
    def _coerce_profiles(
        profiles: Iterable[StrategyProfile],
    ) -> list[StrategyProfile]:
        if isinstance(profiles, (str, bytes)):
            raise TypeError(
                "profiles must be an iterable of StrategyProfile"
            )
        result = list(profiles)
        if any(
            not isinstance(profile, StrategyProfile)
            for profile in result
        ):
            raise TypeError(
                "all profiles must be StrategyProfile instances"
            )

        names = [profile.name for profile in result]
        if len(set(names)) != len(names):
            raise ValueError("strategy profile names must be unique")
        return result

    @staticmethod
    def _coerce_metrics(
        metrics: Mapping[
            str,
            StrategyMetrics | Mapping[str, Any],
        ],
    ) -> dict[str, StrategyMetrics]:
        if not isinstance(metrics, Mapping):
            raise TypeError("metrics must be a mapping")

        result: dict[str, StrategyMetrics] = {}
        for name, value in metrics.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError(
                    "metric strategy names must be non-empty strings"
                )
            if isinstance(value, StrategyMetrics):
                result[name.strip()] = value
            elif isinstance(value, Mapping):
                result[name.strip()] = StrategyMetrics.from_mapping(
                    value
                )
            else:
                raise TypeError(
                    "metric values must be StrategyMetrics or mappings"
                )
        return result

    def select(
        self,
        regime: Any,
        profiles: Iterable[StrategyProfile],
        metrics: Mapping[
            str,
            StrategyMetrics | Mapping[str, Any],
        ],
    ) -> StrategySelectionReport:
        normalized_regime = self._normalize_regime(regime)
        profile_list = self._coerce_profiles(profiles)
        metric_map = self._coerce_metrics(metrics)

        scored: list[dict[str, Any]] = []

        for profile in profile_list:
            if not profile.enabled:
                continue
            if profile.name not in metric_map:
                raise KeyError(
                    f"missing metrics for strategy: {profile.name}"
                )

            strategy_metrics = metric_map[profile.name]
            compatibility = self.compatibility_score(
                normalized_regime,
                profile.category,
            )
            score = self._composite_score(
                strategy_metrics,
                compatibility,
            )

            reasons = (
                f"Regime compatibility: {compatibility:.3f}",
                (
                    "Historical performance: "
                    f"{strategy_metrics.historical_performance:.3f}"
                ),
                (
                    "Recent performance: "
                    f"{strategy_metrics.recent_performance:.3f}"
                ),
                f"Confidence: {strategy_metrics.confidence:.3f}",
                f"Risk quality: {strategy_metrics.risk_score:.3f}",
                (
                    "Allocator weight: "
                    f"{strategy_metrics.allocation_weight:.3f}"
                ),
            )

            scored.append(
                {
                    "profile": profile,
                    "score": score,
                    "compatibility": compatibility,
                    "reasons": reasons,
                }
            )

        scored.sort(
            key=lambda item: (
                -item["score"],
                item["profile"].name.lower(),
            )
        )

        selected_indexes = {
            index
            for index, item in enumerate(scored[: self.top_n])
            if item["score"]
            >= max(
                self.selection_threshold,
                item["profile"].minimum_score,
            )
        }

        needed = min(self.minimum_selected, len(scored), self.top_n)
        for index in range(needed):
            selected_indexes.add(index)

        selected_score_total = sum(
            scored[index]["score"] for index in selected_indexes
        )

        selections: list[StrategySelection] = []
        for index, item in enumerate(scored):
            is_selected = index in selected_indexes

            if is_selected and selected_score_total > 0.0:
                normalized_weight = (
                    item["score"] / selected_score_total
                )
            elif is_selected and selected_indexes:
                normalized_weight = 1.0 / len(selected_indexes)
            else:
                normalized_weight = 0.0

            selections.append(
                StrategySelection(
                    rank=index + 1,
                    strategy_name=item["profile"].name,
                    category=item["profile"].category,
                    score=round(item["score"], 12),
                    normalized_weight=round(
                        normalized_weight,
                        12,
                    ),
                    compatible_score=item["compatibility"],
                    selected=is_selected,
                    reasons=item["reasons"],
                )
            )

        selected_count = len(selected_indexes)
        top_strategy = (
            selections[0].strategy_name if selections else None
        )

        report = StrategySelectionReport(
            regime=normalized_regime,
            selections=tuple(selections),
            selected_count=selected_count,
            top_strategy=top_strategy,
        )
        self._last_report = report
        return report

    def select_from_mappings(
        self,
        regime: Any,
        profile_data: Sequence[Mapping[str, Any]],
        metrics: Mapping[str, Mapping[str, Any]],
    ) -> StrategySelectionReport:
        if isinstance(profile_data, (str, bytes)):
            raise TypeError(
                "profile_data must be a sequence of mappings"
            )

        profiles = [
            StrategyProfile(
                name=item["name"],
                category=item["category"],
                enabled=item.get("enabled", True),
                minimum_score=item.get("minimum_score", 0.0),
                metadata=item.get("metadata"),
            )
            for item in profile_data
        ]

        return self.select(regime, profiles, metrics)

    def reset(self) -> None:
        self._last_report = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_weights": dict(self.component_weights),
            "top_n": self.top_n,
            "selection_threshold": self.selection_threshold,
            "minimum_selected": self.minimum_selected,
            "last_report": (
                self._last_report.to_dict()
                if self._last_report is not None
                else None
            ),
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"top_n={self.top_n}, "
            f"selection_threshold={self.selection_threshold}, "
            f"minimum_selected={self.minimum_selected})"
        )
