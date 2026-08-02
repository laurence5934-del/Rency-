from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .performance_models import (
    AttributionSummary,
    ContributionType,
    PerformanceAttributionStatus,
    PerformanceContribution,
    PortfolioPerformanceReport,
)


_ZERO = Decimal("0")
_ONE = Decimal("1")


@dataclass(frozen=True, slots=True)
class PerformanceObservation:
    """Raw performance input used to build attribution results."""

    observation_id: str
    contributor_id: str
    contributor_name: str
    contribution_type: ContributionType
    capital_weight: Decimal
    return_rate: Decimal
    profit_loss: Decimal
    risk_contribution: Decimal = _ZERO
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        normalized_observation_id = self.observation_id.strip()
        normalized_contributor_id = self.contributor_id.strip()
        normalized_contributor_name = (
            self.contributor_name.strip()
        )

        if not normalized_observation_id:
            raise ValueError(
                "observation_id must not be empty"
            )

        if not normalized_contributor_id:
            raise ValueError(
                "contributor_id must not be empty"
            )

        if not normalized_contributor_name:
            raise ValueError(
                "contributor_name must not be empty"
            )

        if not isinstance(
            self.contribution_type,
            ContributionType,
        ):
            raise TypeError(
                "contribution_type must be a ContributionType"
            )

        for field_name in (
            "capital_weight",
            "return_rate",
            "profit_loss",
            "risk_contribution",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if not _ZERO <= self.capital_weight <= _ONE:
            raise ValueError(
                "capital_weight must be between 0 and 1"
            )

        if self.return_rate < Decimal("-1"):
            raise ValueError(
                "return_rate must not be less than -1"
            )

        if not _ZERO <= self.risk_contribution <= _ONE:
            raise ValueError(
                "risk_contribution must be between 0 and 1"
            )

        object.__setattr__(
            self,
            "observation_id",
            normalized_observation_id,
        )
        object.__setattr__(
            self,
            "contributor_id",
            normalized_contributor_id,
        )
        object.__setattr__(
            self,
            "contributor_name",
            normalized_contributor_name,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )


class PerformanceAttributionEngine:
    """Builds grouped portfolio performance attribution reports."""

    def analyze(
        self,
        *,
        initial_value: Decimal,
        ending_value: Decimal,
        observations: Iterable[PerformanceObservation],
    ) -> PortfolioPerformanceReport:
        self._validate_values(
            initial_value=initial_value,
            ending_value=ending_value,
        )

        try:
            observation_list = tuple(observations)
        except TypeError as exc:
            raise TypeError(
                "observations must be iterable"
            ) from exc

        valid_observations: list[PerformanceObservation] = []

        try:
            for observation in observation_list:
                if not isinstance(
                    observation,
                    PerformanceObservation,
                ):
                    raise TypeError(
                        "every observation must be a "
                        "PerformanceObservation"
                    )

                valid_observations.append(observation)

            self._validate_unique_observation_ids(
                valid_observations
            )

            contributions = self._build_contributions(
                observations=valid_observations,
                initial_value=initial_value,
            )

            summaries = self._build_summaries(
                contributions
            )

            net_profit_loss = (
                ending_value - initial_value
            )
            total_return = (
                net_profit_loss / initial_value
            )

            top_contributor = self._top_contributor(
                contributions
            )
            bottom_contributor = self._bottom_contributor(
                contributions
            )

            concentration_score = (
                self._concentration_score(
                    contributions
                )
            )
            risk_adjusted_score = (
                self._risk_adjusted_score(
                    total_return=total_return,
                    contributions=contributions,
                )
            )

            warnings = self._aggregate_warnings(
                observations=valid_observations,
                contributions=contributions,
                concentration_score=concentration_score,
            )

            return PortfolioPerformanceReport(
                status=(
                    PerformanceAttributionStatus.COMPLETED
                ),
                initial_value=initial_value,
                ending_value=ending_value,
                net_profit_loss=net_profit_loss,
                total_return=total_return,
                contributions=contributions,
                summaries=summaries,
                top_contributor_id=(
                    top_contributor.contributor_id
                    if top_contributor is not None
                    else None
                ),
                bottom_contributor_id=(
                    bottom_contributor.contributor_id
                    if bottom_contributor is not None
                    else None
                ),
                concentration_score=concentration_score,
                risk_adjusted_score=risk_adjusted_score,
                recommendation=self._recommendation(
                    total_return=total_return,
                    concentration_score=(
                        concentration_score
                    ),
                    risk_adjusted_score=(
                        risk_adjusted_score
                    ),
                ),
                warnings=warnings,
            )

        except Exception as exc:
            net_profit_loss = (
                ending_value - initial_value
            )
            total_return = (
                net_profit_loss / initial_value
            )

            return PortfolioPerformanceReport(
                status=PerformanceAttributionStatus.FAILED,
                initial_value=initial_value,
                ending_value=ending_value,
                net_profit_loss=net_profit_loss,
                total_return=total_return,
                contributions=(),
                summaries=(),
                concentration_score=_ZERO,
                risk_adjusted_score=_ZERO,
                recommendation="",
                warnings=(
                    "Performance attribution analysis failed.",
                ),
                error=str(exc),
            )

    @staticmethod
    def _build_contributions(
        *,
        observations: Iterable[
            PerformanceObservation
        ],
        initial_value: Decimal,
    ) -> tuple[PerformanceContribution, ...]:
        grouped: dict[
            tuple[ContributionType, str],
            list[PerformanceObservation],
        ] = defaultdict(list)

        for observation in observations:
            grouped[
                (
                    observation.contribution_type,
                    observation.contributor_id,
                )
            ].append(observation)

        contributions: list[
            PerformanceContribution
        ] = []

        for (
            contribution_type,
            contributor_id,
        ), group in grouped.items():
            total_weight = sum(
                (
                    item.capital_weight
                    for item in group
                ),
                _ZERO,
            )

            total_profit_loss = sum(
                (
                    item.profit_loss
                    for item in group
                ),
                _ZERO,
            )

            contribution_return = (
                total_profit_loss / initial_value
            )

            weighted_return_numerator = sum(
                (
                    item.return_rate
                    * item.capital_weight
                    for item in group
                ),
                _ZERO,
            )

            return_rate = (
                weighted_return_numerator
                / total_weight
                if total_weight > _ZERO
                else _ZERO
            )

            risk_contribution = min(
                sum(
                    (
                        item.risk_contribution
                        for item in group
                    ),
                    _ZERO,
                ),
                _ONE,
            )

            warnings = tuple(
                warning
                for item in group
                for warning in item.warnings
            )

            contributions.append(
                PerformanceContribution(
                    contributor_id=contributor_id,
                    name=group[0].contributor_name,
                    contribution_type=(
                        contribution_type
                    ),
                    weight=min(total_weight, _ONE),
                    return_rate=return_rate,
                    contribution_return=(
                        contribution_return
                    ),
                    profit_loss=total_profit_loss,
                    risk_contribution=(
                        risk_contribution
                    ),
                    observations=len(group),
                    warnings=warnings,
                )
            )

        return tuple(
            sorted(
                contributions,
                key=lambda item: (
                    item.contribution_type.value,
                    item.contributor_id,
                ),
            )
        )

    @staticmethod
    def _build_summaries(
        contributions: Iterable[
            PerformanceContribution
        ],
    ) -> tuple[AttributionSummary, ...]:
        grouped: dict[
            ContributionType,
            list[PerformanceContribution],
        ] = defaultdict(list)

        for contribution in contributions:
            grouped[
                contribution.contribution_type
            ].append(contribution)

        summaries: list[AttributionSummary] = []

        for contribution_type, group in grouped.items():
            top = max(
                group,
                key=lambda item: (
                    item.contribution_return,
                    item.contributor_id,
                ),
            )
            bottom = min(
                group,
                key=lambda item: (
                    item.contribution_return,
                    item.contributor_id,
                ),
            )

            summaries.append(
                AttributionSummary(
                    contribution_type=contribution_type,
                    total_return_contribution=sum(
                        (
                            item.contribution_return
                            for item in group
                        ),
                        _ZERO,
                    ),
                    total_profit_loss=sum(
                        (
                            item.profit_loss
                            for item in group
                        ),
                        _ZERO,
                    ),
                    total_risk_contribution=min(
                        sum(
                            (
                                item.risk_contribution
                                for item in group
                            ),
                            _ZERO,
                        ),
                        _ONE,
                    ),
                    contributor_count=len(group),
                    top_contributor_id=(
                        top.contributor_id
                    ),
                    bottom_contributor_id=(
                        bottom.contributor_id
                    ),
                )
            )

        return tuple(
            sorted(
                summaries,
                key=lambda item: (
                    item.contribution_type.value
                ),
            )
        )

    @staticmethod
    def _top_contributor(
        contributions: Iterable[
            PerformanceContribution
        ],
    ) -> PerformanceContribution | None:
        contribution_list = tuple(contributions)

        if not contribution_list:
            return None

        return max(
            contribution_list,
            key=lambda item: (
                item.contribution_return,
                item.contributor_id,
            ),
        )

    @staticmethod
    def _bottom_contributor(
        contributions: Iterable[
            PerformanceContribution
        ],
    ) -> PerformanceContribution | None:
        contribution_list = tuple(contributions)

        if not contribution_list:
            return None

        return min(
            contribution_list,
            key=lambda item: (
                item.contribution_return,
                item.contributor_id,
            ),
        )

    @staticmethod
    def _concentration_score(
        contributions: Iterable[
            PerformanceContribution
        ],
    ) -> Decimal:
        contribution_list = tuple(contributions)

        if not contribution_list:
            return _ZERO

        total_absolute_contribution = sum(
            (
                abs(item.contribution_return)
                for item in contribution_list
            ),
            _ZERO,
        )

        if total_absolute_contribution == _ZERO:
            return _ZERO

        largest_contribution = max(
            abs(item.contribution_return)
            for item in contribution_list
        )

        return min(
            largest_contribution
            / total_absolute_contribution,
            _ONE,
        )

    @staticmethod
    def _risk_adjusted_score(
        *,
        total_return: Decimal,
        contributions: Iterable[
            PerformanceContribution
        ],
    ) -> Decimal:
        contribution_list = tuple(contributions)

        total_risk = sum(
            (
                item.risk_contribution
                for item in contribution_list
            ),
            _ZERO,
        )

        if total_return <= _ZERO:
            return _ZERO

        if total_risk <= _ZERO:
            return _ONE

        raw_score = total_return / total_risk

        return min(
            max(raw_score, _ZERO),
            _ONE,
        )

    @staticmethod
    def _aggregate_warnings(
        *,
        observations: Iterable[
            PerformanceObservation
        ],
        contributions: Iterable[
            PerformanceContribution
        ],
        concentration_score: Decimal,
    ) -> tuple[str, ...]:
        warnings = [
            warning
            for observation in observations
            for warning in observation.warnings
        ]

        if concentration_score >= Decimal("0.60"):
            warnings.append(
                "Portfolio performance is highly concentrated."
            )

        negative_contributors = sum(
            1
            for contribution in contributions
            if contribution.contribution_return < _ZERO
        )

        if negative_contributors:
            warnings.append(
                f"{negative_contributors} contributors "
                "produced negative performance."
            )

        return tuple(warnings)

    @staticmethod
    def _recommendation(
        *,
        total_return: Decimal,
        concentration_score: Decimal,
        risk_adjusted_score: Decimal,
    ) -> str:
        if total_return < _ZERO:
            return (
                "Review losing contributors and reduce "
                "exposure to persistently weak allocations."
            )

        if concentration_score >= Decimal("0.60"):
            return (
                "Reduce contributor concentration before "
                "increasing portfolio exposure."
            )

        if risk_adjusted_score < Decimal("0.30"):
            return (
                "Improve risk efficiency before expanding "
                "the current portfolio allocation."
            )

        if risk_adjusted_score >= Decimal("0.70"):
            return (
                "Maintain the current allocation while "
                "monitoring attribution stability."
            )

        return (
            "Continue monitoring portfolio contributors "
            "and maintain controlled exposure."
        )

    @staticmethod
    def _validate_unique_observation_ids(
        observations: Iterable[
            PerformanceObservation
        ],
    ) -> None:
        seen: set[str] = set()

        for observation in observations:
            if observation.observation_id in seen:
                raise ValueError(
                    "observation_id values must be unique"
                )

            seen.add(observation.observation_id)

    @staticmethod
    def _validate_values(
        *,
        initial_value: Decimal,
        ending_value: Decimal,
    ) -> None:
        if not isinstance(initial_value, Decimal):
            raise TypeError(
                "initial_value must be a Decimal"
            )

        if initial_value <= _ZERO:
            raise ValueError(
                "initial_value must be greater than zero"
            )

        if not isinstance(ending_value, Decimal):
            raise TypeError(
                "ending_value must be a Decimal"
            )

        if ending_value < _ZERO:
            raise ValueError(
                "ending_value must not be negative"
            )