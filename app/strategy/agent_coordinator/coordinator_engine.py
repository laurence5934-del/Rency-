from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from .coordinator_models import (
    AgentCoordinatorStatus,
    AgentOpinion,
    AgentRecommendation,
    AgentRole,
    AgentVoteSummary,
    CoordinatedAction,
    CoordinationReport,
)


_ZERO = Decimal("0")
_ONE = Decimal("1")

_DEFAULT_REQUIRED_ROLES = (
    AgentRole.STRATEGY,
    AgentRole.RISK,
    AgentRole.REGIME,
    AgentRole.PORTFOLIO,
    AgentRole.EXECUTION,
)


class EnterpriseAgentCoordinator:
    """Coordinates weighted opinions from specialized agents."""

    def __init__(
        self,
        *,
        required_roles: Iterable[AgentRole] | None = None,
    ) -> None:
        roles = tuple(
            required_roles
            if required_roles is not None
            else _DEFAULT_REQUIRED_ROLES
        )

        if not roles:
            raise ValueError(
                "required_roles must not be empty"
            )

        for role in roles:
            if not isinstance(role, AgentRole):
                raise TypeError(
                    "every required role must be an AgentRole"
                )

        if len(set(roles)) != len(roles):
            raise ValueError(
                "required_roles must not contain duplicates"
            )

        self._required_roles = roles

    @property
    def required_roles(self) -> tuple[AgentRole, ...]:
        """Return the immutable required-role configuration."""

        return self._required_roles

    def coordinate(
        self,
        opinions: Iterable[AgentOpinion],
    ) -> CoordinationReport:
        try:
            opinion_list = tuple(opinions)
        except TypeError as exc:
            raise TypeError(
                "opinions must be iterable"
            ) from exc

        valid_opinions: list[AgentOpinion] = []

        try:
            for opinion in opinion_list:
                if not isinstance(opinion, AgentOpinion):
                    raise TypeError(
                        "every opinion must be an AgentOpinion"
                    )

                valid_opinions.append(opinion)

            self._validate_unique_agent_ids(
                valid_opinions
            )
            self._validate_unique_roles(
                valid_opinions
            )
            self._validate_required_roles(
                valid_opinions
            )

            ordered_opinions = self._ordered_opinions(
                valid_opinions
            )

            vote_summary = self._vote_summary(
                ordered_opinions
            )

            action = self._coordinated_action(
                ordered_opinions
            )

            confidence = self._confidence(
                ordered_opinions,
                action=action,
            )

            warnings = self._aggregate_warnings(
                ordered_opinions
            )

            return CoordinationReport(
                status=AgentCoordinatorStatus.COMPLETED,
                action=action,
                confidence=confidence,
                opinions=ordered_opinions,
                vote_summary=vote_summary,
                rationale=self._rationale(
                    action=action,
                    opinions=ordered_opinions,
                ),
                warnings=warnings,
            )

        except Exception as exc:
            return CoordinationReport(
                status=AgentCoordinatorStatus.FAILED,
                action=CoordinatedAction.BLOCK,
                confidence=_ZERO,
                opinions=tuple(valid_opinions),
                vote_summary=AgentVoteSummary(
                    approval_score=_ZERO,
                    review_score=_ZERO,
                    rejection_score=_ZERO,
                    participating_agents=0,
                    abstaining_agents=0,
                ),
                rationale=(
                    "Agent coordination failed before a valid "
                    "enterprise decision could be produced."
                ),
                warnings=(
                    "Enterprise agent coordination failed.",
                ),
                error=str(exc),
            )

    @staticmethod
    def _validate_unique_agent_ids(
        opinions: Iterable[AgentOpinion],
    ) -> None:
        seen: set[str] = set()

        for opinion in opinions:
            if opinion.agent_id in seen:
                raise ValueError(
                    f"duplicate agent_id: {opinion.agent_id}"
                )

            seen.add(opinion.agent_id)

    @staticmethod
    def _validate_unique_roles(
        opinions: Iterable[AgentOpinion],
    ) -> None:
        seen: set[AgentRole] = set()

        for opinion in opinions:
            if opinion.role in seen:
                raise ValueError(
                    f"duplicate agent role: "
                    f"{opinion.role.value}"
                )

            seen.add(opinion.role)

    def _validate_required_roles(
        self,
        opinions: Iterable[AgentOpinion],
    ) -> None:
        supplied_roles = {
            opinion.role
            for opinion in opinions
        }

        missing_roles = [
            role
            for role in self._required_roles
            if role not in supplied_roles
        ]

        if missing_roles:
            names = ", ".join(
                role.value
                for role in missing_roles
            )

            raise ValueError(
                f"missing required agent roles: {names}"
            )

    def _ordered_opinions(
        self,
        opinions: Iterable[AgentOpinion],
    ) -> tuple[AgentOpinion, ...]:
        role_order = {
            role: index
            for index, role in enumerate(
                self._required_roles
            )
        }

        return tuple(
            sorted(
                opinions,
                key=lambda opinion: (
                    role_order.get(
                        opinion.role,
                        len(role_order),
                    ),
                    opinion.agent_id,
                ),
            )
        )

    @staticmethod
    def _vote_summary(
        opinions: Iterable[AgentOpinion],
    ) -> AgentVoteSummary:
        opinion_list = tuple(opinions)

        participating = tuple(
            opinion
            for opinion in opinion_list
            if (
                opinion.recommendation
                is not AgentRecommendation.ABSTAIN
            )
        )

        abstaining_count = sum(
            1
            for opinion in opinion_list
            if (
                opinion.recommendation
                is AgentRecommendation.ABSTAIN
            )
        )

        effective_weights = {
            AgentRecommendation.APPROVE: _ZERO,
            AgentRecommendation.REVIEW: _ZERO,
            AgentRecommendation.REJECT: _ZERO,
        }

        for opinion in participating:
            effective_weight = (
                opinion.weight
                * opinion.confidence
            )

            effective_weights[
                opinion.recommendation
            ] += effective_weight

        total_effective_weight = sum(
            effective_weights.values(),
            _ZERO,
        )

        if total_effective_weight == _ZERO:
            approval_score = _ZERO
            review_score = _ZERO
            rejection_score = _ZERO
        else:
            approval_score = (
                effective_weights[
                    AgentRecommendation.APPROVE
                ]
                / total_effective_weight
            )
            review_score = (
                effective_weights[
                    AgentRecommendation.REVIEW
                ]
                / total_effective_weight
            )
            rejection_score = (
                effective_weights[
                    AgentRecommendation.REJECT
                ]
                / total_effective_weight
            )

        return AgentVoteSummary(
            approval_score=approval_score,
            review_score=review_score,
            rejection_score=rejection_score,
            participating_agents=len(participating),
            abstaining_agents=abstaining_count,
        )

    @staticmethod
    def _coordinated_action(
        opinions: Iterable[AgentOpinion],
    ) -> CoordinatedAction:
        recommendations = tuple(
            opinion.recommendation
            for opinion in opinions
        )

        if AgentRecommendation.REJECT in recommendations:
            return CoordinatedAction.BLOCK

        if (
            AgentRecommendation.REVIEW
            in recommendations
            or AgentRecommendation.ABSTAIN
            in recommendations
        ):
            return CoordinatedAction.REVIEW_REQUIRED

        return CoordinatedAction.EXECUTE

    @staticmethod
    def _confidence(
        opinions: Iterable[AgentOpinion],
        *,
        action: CoordinatedAction,
    ) -> Decimal:
        relevant_recommendation = {
            CoordinatedAction.EXECUTE: (
                AgentRecommendation.APPROVE
            ),
            CoordinatedAction.REVIEW_REQUIRED: (
                AgentRecommendation.REVIEW
            ),
            CoordinatedAction.BLOCK: (
                AgentRecommendation.REJECT
            ),
        }[action]

        matching = tuple(
            opinion
            for opinion in opinions
            if (
                opinion.recommendation
                is relevant_recommendation
            )
        )

        if not matching:
            return _ZERO

        total_weight = sum(
            (
                opinion.weight
                for opinion in matching
            ),
            _ZERO,
        )

        if total_weight == _ZERO:
            return _ZERO

        weighted_confidence = sum(
            (
                opinion.confidence
                * opinion.weight
                for opinion in matching
            ),
            _ZERO,
        )

        return EnterpriseAgentCoordinator._clamp(
            weighted_confidence / total_weight
        )

    @staticmethod
    def _rationale(
        *,
        action: CoordinatedAction,
        opinions: Iterable[AgentOpinion],
    ) -> str:
        opinion_list = tuple(opinions)

        if action is CoordinatedAction.BLOCK:
            rejecting_roles = ", ".join(
                opinion.role.value
                for opinion in opinion_list
                if (
                    opinion.recommendation
                    is AgentRecommendation.REJECT
                )
            )

            return (
                "Execution was blocked because the "
                f"following required agents rejected it: "
                f"{rejecting_roles}."
            )

        if action is CoordinatedAction.REVIEW_REQUIRED:
            review_roles = ", ".join(
                opinion.role.value
                for opinion in opinion_list
                if opinion.recommendation in {
                    AgentRecommendation.REVIEW,
                    AgentRecommendation.ABSTAIN,
                }
            )

            return (
                "Manual review is required because the "
                "following agents did not approve execution: "
                f"{review_roles}."
            )

        return (
            "All required agents approved execution."
        )

    @staticmethod
    def _aggregate_warnings(
        opinions: Iterable[AgentOpinion],
    ) -> tuple[str, ...]:
        return tuple(
            warning
            for opinion in opinions
            for warning in opinion.warnings
        )

    @staticmethod
    def _clamp(value: Decimal) -> Decimal:
        return min(
            max(value, _ZERO),
            _ONE,
        )