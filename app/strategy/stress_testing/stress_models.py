from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")
_ONE = Decimal("1")


class StressTestStatus(str, Enum):
    """Lifecycle status of a portfolio stress-test run."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StressScenarioType(str, Enum):
    """Supported categories of portfolio stress scenarios."""

    MARKET_CRASH = "MARKET_CRASH"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    LIQUIDITY_SHOCK = "LIQUIDITY_SHOCK"
    COMBINED_SHOCK = "COMBINED_SHOCK"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True, slots=True)
class StressScenario:
    """A deterministic scenario applied to portfolio equity."""

    scenario_id: str
    name: str
    scenario_type: StressScenarioType
    market_return_shock: Decimal = _ZERO
    volatility_multiplier: Decimal = _ONE
    liquidity_haircut: Decimal = _ZERO

    def __post_init__(self) -> None:
        normalized_id = self.scenario_id.strip()
        normalized_name = self.name.strip()

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
            StressScenarioType,
        ):
            raise TypeError(
                "scenario_type must be a StressScenarioType"
            )

        if not isinstance(
            self.market_return_shock,
            Decimal,
        ):
            raise TypeError(
                "market_return_shock must be a Decimal"
            )

        if self.market_return_shock < -_ONE:
            raise ValueError(
                "market_return_shock must not be less than -1"
            )

        if not isinstance(
            self.volatility_multiplier,
            Decimal,
        ):
            raise TypeError(
                "volatility_multiplier must be a Decimal"
            )

        if self.volatility_multiplier < _ZERO:
            raise ValueError(
                "volatility_multiplier must not be negative"
            )

        if not isinstance(
            self.liquidity_haircut,
            Decimal,
        ):
            raise TypeError(
                "liquidity_haircut must be a Decimal"
            )

        if not _ZERO <= self.liquidity_haircut <= _ONE:
            raise ValueError(
                "liquidity_haircut must be between 0 and 1"
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


@dataclass(frozen=True, slots=True)
class StressScenarioResult:
    """Portfolio outcome produced by one stress scenario."""

    scenario: StressScenario
    initial_equity: Decimal
    stressed_equity: Decimal
    loss_amount: Decimal
    loss_percent: Decimal
    breached_limit: bool = False
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        for field_name in (
            "initial_equity",
            "stressed_equity",
            "loss_amount",
            "loss_percent",
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

        if self.stressed_equity < _ZERO:
            raise ValueError(
                "stressed_equity must not be negative"
            )

        if self.loss_amount < _ZERO:
            raise ValueError(
                "loss_amount must not be negative"
            )

        if not _ZERO <= self.loss_percent <= _ONE:
            raise ValueError(
                "loss_percent must be between 0 and 1"
            )

        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )


@dataclass(frozen=True, slots=True)
class StressTestReport:
    """Aggregate result from all executed stress scenarios."""

    status: StressTestStatus
    results: tuple[StressScenarioResult, ...] = field(
        default_factory=tuple
    )
    worst_case_loss_percent: Decimal = _ZERO
    average_loss_percent: Decimal = _ZERO
    breach_count: int = 0
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.status,
            StressTestStatus,
        ):
            raise TypeError(
                "status must be a StressTestStatus"
            )

        for field_name in (
            "worst_case_loss_percent",
            "average_loss_percent",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

            if not _ZERO <= value <= _ONE:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        if self.breach_count < 0:
            raise ValueError(
                "breach_count must not be negative"
            )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if self.status is StressTestStatus.FAILED:
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
            "error",
            normalized_error,
        )