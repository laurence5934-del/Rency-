from decimal import Decimal

import pytest

from app.strategy.agent_coordinator.coordinator_engine import (
    EnterpriseAgentCoordinator,
)
from app.strategy.agent_coordinator.coordinator_models import (
    AgentCoordinatorStatus,
    AgentOpinion,
    AgentRecommendation,
    AgentRole,
    CoordinatedAction,
)


def opinion(
    role: AgentRole,
    recommendation: AgentRecommendation = (
        AgentRecommendation.APPROVE
    ),
    *,
    confidence: str = "0.90",
    weight: str = "0.20",
    agent_id: str | None = None,
    warnings=(),
) -> AgentOpinion:
    return AgentOpinion(
        agent_id=(
            agent_id
            if agent_id is not None
            else f"{role.value.lower()}-agent"
        ),
        role=role,
        recommendation=recommendation,
        confidence=Decimal(confidence),
        weight=Decimal(weight),
        reason=(
            f"{role.value} agent produced "
            f"{recommendation.value}."
        ),
        warnings=tuple(warnings),
    )


def approved_opinions() -> tuple[AgentOpinion, ...]:
    return (
        opinion(AgentRole.STRATEGY),
        opinion(AgentRole.RISK),
        opinion(AgentRole.REGIME),
        opinion(AgentRole.PORTFOLIO),
        opinion(AgentRole.EXECUTION),
    )


def test_all_required_agents_approve_execution() -> None:
    report = EnterpriseAgentCoordinator().coordinate(
        approved_opinions()
    )

    assert (
        report.status
        is AgentCoordinatorStatus.COMPLETED
    )
    assert report.action is CoordinatedAction.EXECUTE
    assert report.confidence == Decimal("0.90")
    assert report.error is None


def test_execute_rationale() -> None:
    report = EnterpriseAgentCoordinator().coordinate(
        approved_opinions()
    )

    assert (
        report.rationale
        == "All required agents approved execution."
    )


@pytest.mark.parametrize(
    "rejecting_role",
    list(AgentRole),
)
def test_any_required_rejection_blocks_execution(
    rejecting_role: AgentRole,
) -> None:
    opinions = tuple(
        opinion(
            role,
            (
                AgentRecommendation.REJECT
                if role is rejecting_role
                else AgentRecommendation.APPROVE
            ),
        )
        for role in AgentRole
    )

    report = EnterpriseAgentCoordinator().coordinate(
        opinions
    )

    assert report.action is CoordinatedAction.BLOCK
    assert rejecting_role.value in report.rationale


@pytest.mark.parametrize(
    "reviewing_role",
    list(AgentRole),
)
def test_any_review_requires_manual_review(
    reviewing_role: AgentRole,
) -> None:
    opinions = tuple(
        opinion(
            role,
            (
                AgentRecommendation.REVIEW
                if role is reviewing_role
                else AgentRecommendation.APPROVE
            ),
        )
        for role in AgentRole
    )

    report = EnterpriseAgentCoordinator().coordinate(
        opinions
    )

    assert (
        report.action
        is CoordinatedAction.REVIEW_REQUIRED
    )
    assert reviewing_role.value in report.rationale


def test_rejection_has_precedence_over_review() -> None:
    opinions = (
        opinion(
            AgentRole.STRATEGY,
            AgentRecommendation.REVIEW,
        ),
        opinion(
            AgentRole.RISK,
            AgentRecommendation.REJECT,
        ),
        opinion(AgentRole.REGIME),
        opinion(AgentRole.PORTFOLIO),
        opinion(AgentRole.EXECUTION),
    )

    report = EnterpriseAgentCoordinator().coordinate(
        opinions
    )

    assert report.action is CoordinatedAction.BLOCK


def test_abstention_requires_review() -> None:
    opinions = (
        opinion(AgentRole.STRATEGY),
        opinion(AgentRole.RISK),
        opinion(
            AgentRole.REGIME,
            AgentRecommendation.ABSTAIN,
        ),
        opinion(AgentRole.PORTFOLIO),
        opinion(AgentRole.EXECUTION),
    )

    report = EnterpriseAgentCoordinator().coordinate(
        opinions
    )

    assert (
        report.action
        is CoordinatedAction.REVIEW_REQUIRED
    )
    assert report.vote_summary.abstaining_agents == 1


def test_missing_required_role_returns_failed_report() -> None:
    report = EnterpriseAgentCoordinator().coordinate(
        (
            opinion(AgentRole.STRATEGY),
            opinion(AgentRole.RISK),
            opinion(AgentRole.REGIME),
            opinion(AgentRole.PORTFOLIO),
        )
    )

    assert (
        report.status
        is AgentCoordinatorStatus.FAILED
    )
    assert report.action is CoordinatedAction.BLOCK
    assert "missing required agent roles" in report.error
    assert "EXECUTION" in report.error


def test_duplicate_role_returns_failed_report() -> None:
    opinions = (
        opinion(
            AgentRole.STRATEGY,
            agent_id="strategy-one",
        ),
        opinion(
            AgentRole.STRATEGY,
            agent_id="strategy-two",
        ),
        opinion(AgentRole.RISK),
        opinion(AgentRole.REGIME),
        opinion(AgentRole.PORTFOLIO),
        opinion(AgentRole.EXECUTION),
    )

    report = EnterpriseAgentCoordinator().coordinate(
        opinions
    )

    assert (
        report.status
        is AgentCoordinatorStatus.FAILED
    )
    assert (
        report.error
        == "duplicate agent role: STRATEGY"
    )


def test_duplicate_agent_id_returns_failed_report() -> None:
    opinions = (
        opinion(
            AgentRole.STRATEGY,
            agent_id="duplicate",
        ),
        opinion(
            AgentRole.RISK,
            agent_id="duplicate",
        ),
        opinion(AgentRole.REGIME),
        opinion(AgentRole.PORTFOLIO),
        opinion(AgentRole.EXECUTION),
    )

    report = EnterpriseAgentCoordinator().coordinate(
        opinions
    )

    assert (
        report.status
        is AgentCoordinatorStatus.FAILED
    )
    assert report.error == "duplicate agent_id: duplicate"


def test_invalid_opinion_returns_failed_report() -> None:
    report = EnterpriseAgentCoordinator().coordinate(
        (
            opinion(AgentRole.STRATEGY),
            object(),
        )
    )

    assert (
        report.status
        is AgentCoordinatorStatus.FAILED
    )
    assert (
        report.error
        == "every opinion must be an AgentOpinion"
    )


def test_non_iterable_opinions_raise_type_error() -> None:
    with pytest.raises(
        TypeError,
        match="opinions must be iterable",
    ):
        EnterpriseAgentCoordinator().coordinate(None)


def test_opinions_are_ordered_by_required_role() -> None:
    report = EnterpriseAgentCoordinator().coordinate(
        reversed(approved_opinions())
    )

    assert tuple(
        value.role
        for value in report.opinions
    ) == (
        AgentRole.STRATEGY,
        AgentRole.RISK,
        AgentRole.REGIME,
        AgentRole.PORTFOLIO,
        AgentRole.EXECUTION,
    )


def test_approval_vote_score_is_one_when_all_approve() -> None:
    report = EnterpriseAgentCoordinator().coordinate(
        approved_opinions()
    )

    assert (
        report.vote_summary.approval_score
        == Decimal("1")
    )
    assert report.vote_summary.review_score == Decimal("0")
    assert (
        report.vote_summary.rejection_score
        == Decimal("0")
    )


def test_weighted_vote_scores_are_normalized() -> None:
    opinions = (
        opinion(
            AgentRole.STRATEGY,
            AgentRecommendation.APPROVE,
            confidence="1",
            weight="0.40",
        ),
        opinion(
            AgentRole.RISK,
            AgentRecommendation.REVIEW,
            confidence="1",
            weight="0.20",
        ),
        opinion(
            AgentRole.REGIME,
            AgentRecommendation.REJECT,
            confidence="1",
            weight="0.10",
        ),
        opinion(
            AgentRole.PORTFOLIO,
            AgentRecommendation.APPROVE,
            confidence="1",
            weight="0.20",
        ),
        opinion(
            AgentRole.EXECUTION,
            AgentRecommendation.ABSTAIN,
            confidence="1",
            weight="0.10",
        ),
    )

    report = EnterpriseAgentCoordinator().coordinate(
        opinions
    )

    total_participating_weight = Decimal("0.90")

    assert (
        report.vote_summary.approval_score
        == Decimal("0.60")
        / total_participating_weight
    )
    assert (
        report.vote_summary.review_score
        == Decimal("0.20")
        / total_participating_weight
    )
    assert (
        report.vote_summary.rejection_score
        == Decimal("0.10")
        / total_participating_weight
    )


def test_confidence_uses_winning_recommendation() -> None:
    opinions = (
        opinion(
            AgentRole.STRATEGY,
            confidence="0.80",
            weight="0.25",
        ),
        opinion(
            AgentRole.RISK,
            confidence="0.90",
            weight="0.25",
        ),
        opinion(
            AgentRole.REGIME,
            confidence="1.00",
            weight="0.50",
        ),
        opinion(
            AgentRole.PORTFOLIO,
            confidence="0.70",
            weight="0",
        ),
        opinion(
            AgentRole.EXECUTION,
            confidence="0.60",
            weight="0",
        ),
    )

    report = EnterpriseAgentCoordinator().coordinate(
        opinions
    )

    expected = (
        Decimal("0.80") * Decimal("0.25")
        + Decimal("0.90") * Decimal("0.25")
        + Decimal("1.00") * Decimal("0.50")
    )

    assert report.confidence == expected


def test_block_confidence_uses_rejecting_agents() -> None:
    opinions = (
        opinion(AgentRole.STRATEGY),
        opinion(
            AgentRole.RISK,
            AgentRecommendation.REJECT,
            confidence="0.85",
            weight="0.30",
        ),
        opinion(
            AgentRole.REGIME,
            AgentRecommendation.REJECT,
            confidence="0.95",
            weight="0.20",
        ),
        opinion(AgentRole.PORTFOLIO),
        opinion(AgentRole.EXECUTION),
    )

    report = EnterpriseAgentCoordinator().coordinate(
        opinions
    )

    expected = (
        Decimal("0.85") * Decimal("0.30")
        + Decimal("0.95") * Decimal("0.20")
    ) / Decimal("0.50")

    assert report.confidence == expected


def test_review_confidence_uses_reviewing_agents() -> None:
    opinions = (
        opinion(AgentRole.STRATEGY),
        opinion(
            AgentRole.RISK,
            AgentRecommendation.REVIEW,
            confidence="0.60",
            weight="0.30",
        ),
        opinion(
            AgentRole.REGIME,
            AgentRecommendation.REVIEW,
            confidence="0.80",
            weight="0.20",
        ),
        opinion(AgentRole.PORTFOLIO),
        opinion(AgentRole.EXECUTION),
    )

    report = EnterpriseAgentCoordinator().coordinate(
        opinions
    )

    expected = (
        Decimal("0.60") * Decimal("0.30")
        + Decimal("0.80") * Decimal("0.20")
    ) / Decimal("0.50")

    assert report.confidence == expected


def test_all_abstain_produces_review_with_zero_confidence() -> None:
    opinions = tuple(
        opinion(
            role,
            AgentRecommendation.ABSTAIN,
        )
        for role in AgentRole
    )

    report = EnterpriseAgentCoordinator().coordinate(
        opinions
    )

    assert (
        report.action
        is CoordinatedAction.REVIEW_REQUIRED
    )
    assert report.confidence == Decimal("0")
    assert report.vote_summary.participating_agents == 0
    assert report.vote_summary.abstaining_agents == 5


def test_zero_effective_weights_produce_zero_scores() -> None:
    opinions = tuple(
        opinion(
            role,
            confidence="0",
            weight="0",
        )
        for role in AgentRole
    )

    report = EnterpriseAgentCoordinator().coordinate(
        opinions
    )

    assert report.action is CoordinatedAction.EXECUTE
    assert report.confidence == Decimal("0")
    assert (
        report.vote_summary.approval_score
        == Decimal("0")
    )


def test_agent_warnings_are_aggregated() -> None:
    opinions = (
        opinion(
            AgentRole.STRATEGY,
            warnings=("Strategy warning.",),
        ),
        opinion(
            AgentRole.RISK,
            warnings=("Risk warning.",),
        ),
        opinion(AgentRole.REGIME),
        opinion(AgentRole.PORTFOLIO),
        opinion(AgentRole.EXECUTION),
    )

    report = EnterpriseAgentCoordinator().coordinate(
        opinions
    )

    assert report.warnings == (
        "Strategy warning.",
        "Risk warning.",
    )


def test_custom_required_roles_are_supported() -> None:
    coordinator = EnterpriseAgentCoordinator(
        required_roles=(
            AgentRole.STRATEGY,
            AgentRole.RISK,
        )
    )

    report = coordinator.coordinate(
        (
            opinion(AgentRole.STRATEGY),
            opinion(AgentRole.RISK),
        )
    )

    assert report.status is AgentCoordinatorStatus.COMPLETED
    assert report.action is CoordinatedAction.EXECUTE


def test_required_roles_property_is_tuple() -> None:
    coordinator = EnterpriseAgentCoordinator()

    assert coordinator.required_roles == (
        AgentRole.STRATEGY,
        AgentRole.RISK,
        AgentRole.REGIME,
        AgentRole.PORTFOLIO,
        AgentRole.EXECUTION,
    )


def test_required_roles_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="required_roles must not be empty",
    ):
        EnterpriseAgentCoordinator(
            required_roles=()
        )


def test_required_roles_must_be_valid_enums() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "every required role must be an AgentRole"
        ),
    ):
        EnterpriseAgentCoordinator(
            required_roles=(
                AgentRole.STRATEGY,
                "RISK",
            )
        )


def test_required_roles_must_not_duplicate() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "required_roles must not contain duplicates"
        ),
    ):
        EnterpriseAgentCoordinator(
            required_roles=(
                AgentRole.RISK,
                AgentRole.RISK,
            )
        )