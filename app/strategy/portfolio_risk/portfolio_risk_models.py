from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")
_ONE = Decimal("1")


class PortfolioRiskStatus(str, Enum):
    """Lifecycle status of a portfolio-risk assessment."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PortfolioRiskDecision(str, Enum):
    """Final portfolio-level risk decision."""

    APPROVE = "APPROVE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECT = "REJECT"


class ExposureType(str, Enum):
    """Supported portfolio exposure classifications."""

    POSITION = "POSITION"
    SECTOR = "SECTOR"
    INDUSTRY = "INDUSTRY"
    ASSET_CLASS = "ASSET_CLASS"
    GEOGRAPHY = "GEOGRAPHY"
    STRATEGY = "STRATEGY"
    CUSTOM = "CUSTOM"


class RiskLimitType(str, Enum):
    """Supported portfolio risk-limit categories."""

    POSITION_EXPOSURE = "POSITION_EXPOSURE"
    SECTOR_EXPOSURE = "SECTOR_EXPOSURE"
    GROSS_EXPOSURE = "GROSS_EXPOSURE"
    NET_EXPOSURE = "NET_EXPOSURE"
    LEVERAGE = "LEVERAGE"
    CONCENTRATION = "CONCENTRATION"
    VOLATILITY = "VOLATILITY"
    DRAWDOWN = "DRAWDOWN"
    VALUE_AT_RISK = "VALUE_AT_RISK"
    EXPECTED_SHORTFALL = "EXPECTED_SHORTFALL"
    RISK_BUDGET = "RISK_BUDGET"
    LIQUIDITY = "LIQUIDITY"
    CUSTOM = "CUSTOM"


class RiskLimitSeverity(str, Enum):
    """Severity assigned to a breached risk limit."""

    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class PortfolioExposure:
    """One immutable portfolio exposure measurement."""

    exposure_id: str
    name: str
    exposure_type: ExposureType
    market_value: Decimal
    exposure_ratio: Decimal
    risk_contribution: Decimal = _ZERO
    liquid: bool = True
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_exposure_id = self.exposure_id.strip()
        normalized_name = self.name.strip()

        if not normalized_exposure_id:
            raise ValueError(
                "exposure_id must not be empty"
            )

        if not normalized_name:
            raise ValueError(
                "name must not be empty"
            )

        if not isinstance(
            self.exposure_type,
            ExposureType,
        ):
            raise TypeError(
                "exposure_type must be an ExposureType"
            )

        for field_name in (
            "market_value",
            "exposure_ratio",
            "risk_contribution",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if self.market_value < _ZERO:
            raise ValueError(
                "market_value must not be negative"
            )

        if not _ZERO <= self.exposure_ratio <= _ONE:
            raise ValueError(
                "exposure_ratio must be between 0 and 1"
            )

        if not _ZERO <= self.risk_contribution <= _ONE:
            raise ValueError(
                "risk_contribution must be between 0 and 1"
            )

        if not isinstance(self.liquid, bool):
            raise TypeError(
                "liquid must be a bool"
            )

        object.__setattr__(
            self,
            "exposure_id",
            normalized_exposure_id,
        )
        object.__setattr__(
            self,
            "name",
            normalized_name,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )


@dataclass(frozen=True, slots=True)
class PortfolioRiskLimit:
    """Configured risk boundary used during assessment."""

    limit_id: str
    name: str
    limit_type: RiskLimitType
    threshold: Decimal
    severity: RiskLimitSeverity
    enabled: bool = True
    description: str = ""

    def __post_init__(self) -> None:
        normalized_limit_id = self.limit_id.strip()
        normalized_name = self.name.strip()
        normalized_description = self.description.strip()

        if not normalized_limit_id:
            raise ValueError(
                "limit_id must not be empty"
            )

        if not normalized_name:
            raise ValueError(
                "name must not be empty"
            )

        if not isinstance(
            self.limit_type,
            RiskLimitType,
        ):
            raise TypeError(
                "limit_type must be a RiskLimitType"
            )

        if not isinstance(self.threshold, Decimal):
            raise TypeError(
                "threshold must be a Decimal"
            )

        if self.threshold < _ZERO:
            raise ValueError(
                "threshold must not be negative"
            )

        if not isinstance(
            self.severity,
            RiskLimitSeverity,
        ):
            raise TypeError(
                "severity must be a RiskLimitSeverity"
            )

        if not isinstance(self.enabled, bool):
            raise TypeError(
                "enabled must be a bool"
            )

        object.__setattr__(
            self,
            "limit_id",
            normalized_limit_id,
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
class RiskLimitBreach:
    """One immutable portfolio risk-limit breach."""

    limit: PortfolioRiskLimit
    observed_value: Decimal
    exceeded_by: Decimal
    message: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.limit,
            PortfolioRiskLimit,
        ):
            raise TypeError(
                "limit must be a PortfolioRiskLimit"
            )

        if not isinstance(
            self.observed_value,
            Decimal,
        ):
            raise TypeError(
                "observed_value must be a Decimal"
            )

        if not isinstance(self.exceeded_by, Decimal):
            raise TypeError(
                "exceeded_by must be a Decimal"
            )

        if self.observed_value < _ZERO:
            raise ValueError(
                "observed_value must not be negative"
            )

        if self.exceeded_by <= _ZERO:
            raise ValueError(
                "exceeded_by must be greater than zero"
            )

        expected_exceeded_by = (
            self.observed_value
            - self.limit.threshold
        )

        if self.exceeded_by != expected_exceeded_by:
            raise ValueError(
                "exceeded_by must equal observed_value "
                "minus the limit threshold"
            )

        normalized_message = self.message.strip()

        if not normalized_message:
            raise ValueError(
                "message must not be empty"
            )

        object.__setattr__(
            self,
            "message",
            normalized_message,
        )


@dataclass(frozen=True, slots=True)
class PortfolioRiskMetrics:
    """Aggregate portfolio-level risk measurements."""

    portfolio_value: Decimal
    cash_value: Decimal
    gross_exposure: Decimal
    net_exposure: Decimal
    leverage_ratio: Decimal
    concentration_score: Decimal
    diversification_score: Decimal
    volatility: Decimal
    maximum_drawdown: Decimal
    value_at_risk: Decimal
    expected_shortfall: Decimal
    risk_budget_used: Decimal
    liquidity_score: Decimal

    def __post_init__(self) -> None:
        for field_name in (
            "portfolio_value",
            "cash_value",
            "gross_exposure",
            "net_exposure",
            "leverage_ratio",
            "concentration_score",
            "diversification_score",
            "volatility",
            "maximum_drawdown",
            "value_at_risk",
            "expected_shortfall",
            "risk_budget_used",
            "liquidity_score",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if self.portfolio_value <= _ZERO:
            raise ValueError(
                "portfolio_value must be greater than zero"
            )

        if self.cash_value < _ZERO:
            raise ValueError(
                "cash_value must not be negative"
            )

        if self.cash_value > self.portfolio_value:
            raise ValueError(
                "cash_value must not exceed portfolio_value"
            )

        for field_name in (
            "gross_exposure",
            "net_exposure",
            "leverage_ratio",
            "volatility",
            "maximum_drawdown",
            "value_at_risk",
            "expected_shortfall",
        ):
            value = getattr(self, field_name)

            if value < _ZERO:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        for field_name in (
            "concentration_score",
            "diversification_score",
            "risk_budget_used",
            "liquidity_score",
        ):
            value = getattr(self, field_name)

            if not _ZERO <= value <= _ONE:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        if self.expected_shortfall < self.value_at_risk:
            raise ValueError(
                "expected_shortfall must not be less than "
                "value_at_risk"
            )


@dataclass(frozen=True, slots=True)
class PortfolioRiskReport:
    """Unified result of a portfolio-level risk assessment."""

    status: PortfolioRiskStatus
    decision: PortfolioRiskDecision
    metrics: PortfolioRiskMetrics
    exposures: tuple[PortfolioExposure, ...] = field(
        default_factory=tuple
    )
    limits: tuple[PortfolioRiskLimit, ...] = field(
        default_factory=tuple
    )
    breaches: tuple[RiskLimitBreach, ...] = field(
        default_factory=tuple
    )
    recommendation: str = ""
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.status,
            PortfolioRiskStatus,
        ):
            raise TypeError(
                "status must be a PortfolioRiskStatus"
            )

        if not isinstance(
            self.decision,
            PortfolioRiskDecision,
        ):
            raise TypeError(
                "decision must be a PortfolioRiskDecision"
            )

        if not isinstance(
            self.metrics,
            PortfolioRiskMetrics,
        ):
            raise TypeError(
                "metrics must be PortfolioRiskMetrics"
            )

        normalized_exposures = tuple(self.exposures)
        normalized_limits = tuple(self.limits)
        normalized_breaches = tuple(self.breaches)

        for exposure in normalized_exposures:
            if not isinstance(
                exposure,
                PortfolioExposure,
            ):
                raise TypeError(
                    "every exposure must be a "
                    "PortfolioExposure"
                )

        for limit in normalized_limits:
            if not isinstance(
                limit,
                PortfolioRiskLimit,
            ):
                raise TypeError(
                    "every limit must be a "
                    "PortfolioRiskLimit"
                )

        for breach in normalized_breaches:
            if not isinstance(
                breach,
                RiskLimitBreach,
            ):
                raise TypeError(
                    "every breach must be a "
                    "RiskLimitBreach"
                )

        exposure_ids = [
            exposure.exposure_id
            for exposure in normalized_exposures
        ]

        if len(set(exposure_ids)) != len(exposure_ids):
            raise ValueError(
                "exposure_id values must be unique"
            )

        limit_ids = [
            limit.limit_id
            for limit in normalized_limits
        ]

        if len(set(limit_ids)) != len(limit_ids):
            raise ValueError(
                "limit_id values must be unique"
            )

        known_limit_ids = set(limit_ids)

        for breach in normalized_breaches:
            if breach.limit.limit_id not in known_limit_ids:
                raise ValueError(
                    "every breach must reference a report limit"
                )

        normalized_recommendation = (
            self.recommendation.strip()
        )

        if (
            self.status
            is PortfolioRiskStatus.COMPLETED
            and not normalized_recommendation
        ):
            raise ValueError(
                "completed reports must include a recommendation"
            )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if self.status is PortfolioRiskStatus.FAILED:
            if not normalized_error:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error:
            raise ValueError(
                "only failed reports may include an error"
            )

        if (
            self.decision
            is PortfolioRiskDecision.APPROVE
            and normalized_breaches
        ):
            raise ValueError(
                "approved reports must not include breaches"
            )

        if self.decision is PortfolioRiskDecision.REJECT:
            critical_breaches = [
                breach
                for breach in normalized_breaches
                if breach.limit.severity
                is RiskLimitSeverity.CRITICAL
            ]

            if not critical_breaches:
                raise ValueError(
                    "rejected reports must include a "
                    "critical breach"
                )

        object.__setattr__(
            self,
            "exposures",
            normalized_exposures,
        )
        object.__setattr__(
            self,
            "limits",
            normalized_limits,
        )
        object.__setattr__(
            self,
            "breaches",
            normalized_breaches,
        )
        object.__setattr__(
            self,
            "recommendation",
            normalized_recommendation,
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