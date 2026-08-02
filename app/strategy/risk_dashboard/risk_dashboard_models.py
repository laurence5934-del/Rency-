from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")
_ONE = Decimal("1")


class PortfolioHealth(str, Enum):
    """Overall institutional portfolio-health classification."""

    EXCELLENT = "EXCELLENT"
    HEALTHY = "HEALTHY"
    CAUTION = "CAUTION"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


class DeploymentReadiness(str, Enum):
    """Recommended portfolio deployment state."""

    LIVE_READY = "LIVE_READY"
    PAPER_READY = "PAPER_READY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class RiskDashboardSection:
    """One normalized risk section displayed by the dashboard."""

    section_id: str
    title: str
    score: Decimal
    status: str
    metrics: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_id = self.section_id.strip()
        normalized_title = self.title.strip()
        normalized_status = self.status.strip()

        if not normalized_id:
            raise ValueError(
                "section_id must not be empty"
            )

        if not normalized_title:
            raise ValueError(
                "title must not be empty"
            )

        if not normalized_status:
            raise ValueError(
                "status must not be empty"
            )

        if not isinstance(self.score, Decimal):
            raise TypeError(
                "score must be a Decimal"
            )

        if not _ZERO <= self.score <= _ONE:
            raise ValueError(
                "score must be between 0 and 1"
            )

        normalized_metrics: list[tuple[str, str]] = []

        for metric in self.metrics:
            if (
                not isinstance(metric, tuple)
                or len(metric) != 2
            ):
                raise TypeError(
                    "each metric must be a two-item tuple"
                )

            name, value = metric
            normalized_name = str(name).strip()
            normalized_value = str(value).strip()

            if not normalized_name:
                raise ValueError(
                    "metric names must not be empty"
                )

            normalized_metrics.append(
                (
                    normalized_name,
                    normalized_value,
                )
            )

        object.__setattr__(
            self,
            "section_id",
            normalized_id,
        )
        object.__setattr__(
            self,
            "title",
            normalized_title,
        )
        object.__setattr__(
            self,
            "status",
            normalized_status,
        )
        object.__setattr__(
            self,
            "metrics",
            tuple(normalized_metrics),
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )


@dataclass(frozen=True, slots=True)
class InstitutionalRiskDashboard:
    """Unified institutional risk summary for portfolio deployment."""

    overall_risk_score: Decimal
    confidence_score: Decimal
    capital_preservation_score: Decimal
    health: PortfolioHealth
    readiness: DeploymentReadiness
    recommendation: str
    sections: tuple[RiskDashboardSection, ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        for field_name in (
            "overall_risk_score",
            "confidence_score",
            "capital_preservation_score",
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

        if not isinstance(self.health, PortfolioHealth):
            raise TypeError(
                "health must be a PortfolioHealth"
            )

        if not isinstance(
            self.readiness,
            DeploymentReadiness,
        ):
            raise TypeError(
                "readiness must be a DeploymentReadiness"
            )

        normalized_recommendation = (
            self.recommendation.strip()
        )

        if not normalized_recommendation:
            raise ValueError(
                "recommendation must not be empty"
            )

        object.__setattr__(
            self,
            "recommendation",
            normalized_recommendation,
        )
        object.__setattr__(
            self,
            "sections",
            tuple(self.sections),
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )