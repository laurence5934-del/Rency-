from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")
_ONE = Decimal("1")
_NEGATIVE_ONE = Decimal("-1")


class PerformanceAttributionStatus(str, Enum):
    """Lifecycle status of a performance-attribution operation."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ContributionType(str, Enum):
    """Supported attribution dimensions."""

    STRATEGY = "STRATEGY"
    SYMBOL = "SYMBOL"
    SECTOR = "SECTOR"
    ASSET_CLASS = "ASSET_CLASS"
    AGENT = "AGENT"
    ALLOCATION = "ALLOCATION"
    SELECTION = "SELECTION"
    INTERACTION = "INTERACTION"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True, slots=True)
class PerformanceContribution:
    """One immutable contributor to portfolio performance."""

    contributor_id: str
    name: str
    contribution_type: ContributionType
    weight: Decimal
    return_rate: Decimal
    contribution_return: Decimal
    profit_loss: Decimal
    risk_contribution: Decimal = _ZERO
    observations: int = 0
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_contributor_id = self.contributor_id.strip()
        normalized_name = self.name.strip()

        if not normalized_contributor_id:
            raise ValueError(
                "contributor_id must not be empty"
            )

        if not normalized_name:
            raise ValueError(
                "name must not be empty"
            )

        if not isinstance(
            self.contribution_type,
            ContributionType,
        ):
            raise TypeError(
                "contribution_type must be a ContributionType"
            )

        for field_name in (
            "weight",
            "return_rate",
            "contribution_return",
            "profit_loss",
            "risk_contribution",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if not _ZERO <= self.weight <= _ONE:
            raise ValueError(
                "weight must be between 0 and 1"
            )

        if self.return_rate < _NEGATIVE_ONE:
            raise ValueError(
                "return_rate must not be less than -1"
            )

        if self.contribution_return < _NEGATIVE_ONE:
            raise ValueError(
                "contribution_return must not be less than -1"
            )

        if not _ZERO <= self.risk_contribution <= _ONE:
            raise ValueError(
                "risk_contribution must be between 0 and 1"
            )

        if not isinstance(self.observations, int):
            raise TypeError(
                "observations must be an integer"
            )

        if self.observations < 0:
            raise ValueError(
                "observations must not be negative"
            )

        object.__setattr__(
            self,
            "contributor_id",
            normalized_contributor_id,
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
class AttributionSummary:
    """Aggregate metrics for one attribution dimension."""

    contribution_type: ContributionType
    total_return_contribution: Decimal
    total_profit_loss: Decimal
    total_risk_contribution: Decimal
    contributor_count: int
    top_contributor_id: str | None = None
    bottom_contributor_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.contribution_type,
            ContributionType,
        ):
            raise TypeError(
                "contribution_type must be a ContributionType"
            )

        for field_name in (
            "total_return_contribution",
            "total_profit_loss",
            "total_risk_contribution",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if self.total_return_contribution < _NEGATIVE_ONE:
            raise ValueError(
                "total_return_contribution must not be less than -1"
            )

        if not _ZERO <= self.total_risk_contribution <= _ONE:
            raise ValueError(
                "total_risk_contribution must be between 0 and 1"
            )

        if not isinstance(self.contributor_count, int):
            raise TypeError(
                "contributor_count must be an integer"
            )

        if self.contributor_count < 0:
            raise ValueError(
                "contributor_count must not be negative"
            )

        normalized_top = self._normalize_optional_identifier(
            self.top_contributor_id,
            "top_contributor_id",
        )
        normalized_bottom = self._normalize_optional_identifier(
            self.bottom_contributor_id,
            "bottom_contributor_id",
        )

        if (
            self.contributor_count == 0
            and (
                normalized_top is not None
                or normalized_bottom is not None
            )
        ):
            raise ValueError(
                "empty summaries must not identify contributors"
            )

        object.__setattr__(
            self,
            "top_contributor_id",
            normalized_top,
        )
        object.__setattr__(
            self,
            "bottom_contributor_id",
            normalized_bottom,
        )

    @staticmethod
    def _normalize_optional_identifier(
        value: str | None,
        field_name: str,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string or None"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return normalized


@dataclass(frozen=True, slots=True)
class PortfolioPerformanceReport:
    """Unified portfolio performance-attribution report."""

    status: PerformanceAttributionStatus
    initial_value: Decimal
    ending_value: Decimal
    net_profit_loss: Decimal
    total_return: Decimal
    contributions: tuple[PerformanceContribution, ...] = field(
        default_factory=tuple
    )
    summaries: tuple[AttributionSummary, ...] = field(
        default_factory=tuple
    )
    top_contributor_id: str | None = None
    bottom_contributor_id: str | None = None
    concentration_score: Decimal = _ZERO
    risk_adjusted_score: Decimal = _ZERO
    recommendation: str = ""
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.status,
            PerformanceAttributionStatus,
        ):
            raise TypeError(
                "status must be a PerformanceAttributionStatus"
            )

        for field_name in (
            "initial_value",
            "ending_value",
            "net_profit_loss",
            "total_return",
            "concentration_score",
            "risk_adjusted_score",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if self.initial_value <= _ZERO:
            raise ValueError(
                "initial_value must be greater than zero"
            )

        if self.ending_value < _ZERO:
            raise ValueError(
                "ending_value must not be negative"
            )

        if self.total_return < _NEGATIVE_ONE:
            raise ValueError(
                "total_return must not be less than -1"
            )

        if not _ZERO <= self.concentration_score <= _ONE:
            raise ValueError(
                "concentration_score must be between 0 and 1"
            )

        if not _ZERO <= self.risk_adjusted_score <= _ONE:
            raise ValueError(
                "risk_adjusted_score must be between 0 and 1"
            )

        normalized_contributions = tuple(self.contributions)
        normalized_summaries = tuple(self.summaries)

        for contribution in normalized_contributions:
            if not isinstance(
                contribution,
                PerformanceContribution,
            ):
                raise TypeError(
                    "every contribution must be a "
                    "PerformanceContribution"
                )

        for summary in normalized_summaries:
            if not isinstance(summary, AttributionSummary):
                raise TypeError(
                    "every summary must be an AttributionSummary"
                )

        contribution_ids = [
            contribution.contributor_id
            for contribution in normalized_contributions
        ]

        if len(set(contribution_ids)) != len(contribution_ids):
            raise ValueError(
                "contributor_id values must be unique"
            )

        summary_types = [
            summary.contribution_type
            for summary in normalized_summaries
        ]

        if len(set(summary_types)) != len(summary_types):
            raise ValueError(
                "summary contribution types must be unique"
            )

        normalized_top = (
            AttributionSummary._normalize_optional_identifier(
                self.top_contributor_id,
                "top_contributor_id",
            )
        )
        normalized_bottom = (
            AttributionSummary._normalize_optional_identifier(
                self.bottom_contributor_id,
                "bottom_contributor_id",
            )
        )

        if normalized_top is not None:
            if normalized_top not in contribution_ids:
                raise ValueError(
                    "top_contributor_id must identify a contribution"
                )

        if normalized_bottom is not None:
            if normalized_bottom not in contribution_ids:
                raise ValueError(
                    "bottom_contributor_id must identify a contribution"
                )

        normalized_recommendation = self.recommendation.strip()

        if (
            self.status
            is PerformanceAttributionStatus.COMPLETED
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

        if self.status is PerformanceAttributionStatus.FAILED:
            if not normalized_error:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error:
            raise ValueError(
                "only failed reports may include an error"
            )

        expected_profit_loss = (
            self.ending_value - self.initial_value
        )

        if self.net_profit_loss != expected_profit_loss:
            raise ValueError(
                "net_profit_loss must equal ending_value "
                "minus initial_value"
            )

        expected_return = (
            self.net_profit_loss / self.initial_value
        )

        if self.total_return != expected_return:
            raise ValueError(
                "total_return must equal net_profit_loss "
                "divided by initial_value"
            )

        object.__setattr__(
            self,
            "contributions",
            normalized_contributions,
        )
        object.__setattr__(
            self,
            "summaries",
            normalized_summaries,
        )
        object.__setattr__(
            self,
            "top_contributor_id",
            normalized_top,
        )
        object.__setattr__(
            self,
            "bottom_contributor_id",
            normalized_bottom,
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