from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")
_ONE = Decimal("1")


class ScenarioAnalysisStatus(str, Enum):
    """Lifecycle status for portfolio scenario analysis."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ScenarioType(str, Enum):
    """Supported economic and market scenario categories."""

    BULL_MARKET = "BULL_MARKET"
    BEAR_MARKET = "BEAR_MARKET"
    SIDEWAYS_MARKET = "SIDEWAYS_MARKET"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    INFLATION_SHOCK = "INFLATION_SHOCK"
    DEFLATION_SHOCK = "DEFLATION_SHOCK"
    RISING_RATES = "RISING_RATES"
    FALLING_RATES = "FALLING_RATES"
    LIQUIDITY_CRISIS = "LIQUIDITY_CRISIS"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    """One deterministic portfolio-analysis scenario."""

    scenario_id: str
    name: str
    scenario_type: ScenarioType
    expected_return: Decimal
    expected_volatility: Decimal
    probability_weight: Decimal
    description: str = ""

    def __post_init__(self) -> None:
        normalized_id = self.scenario_id.strip()
        normalized_name = self.name.strip()
        normalized_description = self.description.strip()

        if not normalized_id:
            raise ValueError(
                "scenario_id must not be empty"
            )

        if not normalized_name:
            raise ValueError(
                "name must not be empty"
            )

        if not isinstance(
            self.scenario_type,
            ScenarioType,
        ):
            raise TypeError(
                "scenario_type must be a ScenarioType"
            )

        for field_name in (
            "expected_return",
            "expected_volatility",
            "probability_weight",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if self.expected_return < -_ONE:
            raise ValueError(
                "expected_return must not be less than -1"
            )

        if self.expected_volatility < _ZERO:
            raise ValueError(
                "expected_volatility must not be negative"
            )

        if not _ZERO <= self.probability_weight <= _ONE:
            raise ValueError(
                "probability_weight must be between 0 and 1"
            )

        object.__setattr__(
            self,
            "scenario_id",
            normalized_id,
        )
        object.__setattr__(
            self,
            "name",
            normalized_name,
        )
        object.__setattr__(
            self,
            "description",
            normalized_description,
        )


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """Projected portfolio outcome under one scenario."""

    scenario: ScenarioDefinition
    initial_equity: Decimal
    projected_equity: Decimal
    projected_return: Decimal
    projected_drawdown: Decimal
    risk_score: Decimal
    passed: bool
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        for field_name in (
            "initial_equity",
            "projected_equity",
            "projected_return",
            "projected_drawdown",
            "risk_score",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if self.initial_equity <= _ZERO:
            raise ValueError(
                "initial_equity must be greater than zero"
            )

        if self.projected_equity < _ZERO:
            raise ValueError(
                "projected_equity must not be negative"
            )

        if self.projected_return < -_ONE:
            raise ValueError(
                "projected_return must not be less than -1"
            )

        if not _ZERO <= self.projected_drawdown <= _ONE:
            raise ValueError(
                "projected_drawdown must be between 0 and 1"
            )

        if not _ZERO <= self.risk_score <= _ONE:
            raise ValueError(
                "risk_score must be between 0 and 1"
            )

        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )


@dataclass(frozen=True, slots=True)
class PortfolioScenarioReport:
    """Aggregate report across all portfolio scenarios."""

    status: ScenarioAnalysisStatus
    results: tuple[ScenarioResult, ...] = field(
        default_factory=tuple
    )
    weighted_return: Decimal = _ZERO
    weighted_drawdown: Decimal = _ZERO
    weighted_risk_score: Decimal = _ZERO
    best_scenario_id: str | None = None
    worst_scenario_id: str | None = None
    recommendation: str = ""
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.status,
            ScenarioAnalysisStatus,
        ):
            raise TypeError(
                "status must be a ScenarioAnalysisStatus"
            )

        for field_name in (
            "weighted_return",
            "weighted_drawdown",
            "weighted_risk_score",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if self.weighted_return < -_ONE:
            raise ValueError(
                "weighted_return must not be less than -1"
            )

        if not _ZERO <= self.weighted_drawdown <= _ONE:
            raise ValueError(
                "weighted_drawdown must be between 0 and 1"
            )

        if not _ZERO <= self.weighted_risk_score <= _ONE:
            raise ValueError(
                "weighted_risk_score must be between 0 and 1"
            )

        normalized_best = (
            self.best_scenario_id.strip()
            if self.best_scenario_id is not None
            else None
        )
        normalized_worst = (
            self.worst_scenario_id.strip()
            if self.worst_scenario_id is not None
            else None
        )
        normalized_recommendation = (
            self.recommendation.strip()
        )
        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if self.status is ScenarioAnalysisStatus.FAILED:
            if not normalized_error:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error:
            raise ValueError(
                "only failed reports may include an error"
            )

        object.__setattr__(
            self,
            "results",
            tuple(self.results),
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )
        object.__setattr__(
            self,
            "best_scenario_id",
            normalized_best,
        )
        object.__setattr__(
            self,
            "worst_scenario_id",
            normalized_worst,
        )
        object.__setattr__(
            self,
            "recommendation",
            normalized_recommendation,
        )
        object.__setattr__(
            self,
            "error",
            normalized_error,
        )