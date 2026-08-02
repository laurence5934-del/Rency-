from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.strategy.agent_coordinator.coordinator_models import (
    AgentCoordinatorStatus,
    AgentOpinion,
    AgentRecommendation,
    AgentRole,
    AgentVoteSummary,
    CoordinatedAction,
    CoordinationReport,
)


def opinion() -> AgentOpinion:
    return AgentOpinion(
        agent_id="strategy-agent",
        role=AgentRole.STRATEGY,
        recommendation=AgentRecommendation.APPROVE,
        confidence=Decimal("0.90"),
        weight=Decimal("0.25"),
        reason="Strategy quality is acceptable.",
    )


def vote_summary() -> AgentVoteSummary:
    return AgentVoteSummary(
        approval_score=Decimal("0.80"),
        review_score=Decimal("0.15"),
        rejection_score=Decimal("0.05"),
        participating_agents=4,
        abstaining_agents=1,
    )


def report() -> CoordinationReport:
    return CoordinationReport(
        status=AgentCoordinatorStatus.COMPLETED,
        action=CoordinatedAction.EXECUTE,
        confidence=Decimal("0.80"),
        opinions=(opinion(),),
        vote_summary=vote_summary(),
        rationale="Weighted agent consensus approved execution.",
    )


def test_agent_opinion() -> None:
    value = opinion()

    assert value.agent_id == "strategy-agent"
    assert value.role is AgentRole.STRATEGY
    assert (
        value.recommendation
        is AgentRecommendation.APPROVE
    )


def test_opinion_text_is_normalized() -> None:
    value = AgentOpinion(
        agent_id="  risk-agent  ",
        role=AgentRole.RISK,
        recommendation=AgentRecommendation.REVIEW,
        confidence=Decimal("0.70"),
        weight=Decimal("0.30"),
        reason="  Risk requires review.  ",
    )

    assert value.agent_id == "risk-agent"
    assert value.reason == "Risk requires review."


def test_agent_id_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="agent_id must not be empty",
    ):
        AgentOpinion(
            agent_id="   ",
            role=AgentRole.RISK,
            recommendation=AgentRecommendation.REVIEW,
            confidence=Decimal("0.70"),
            weight=Decimal("0.30"),
            reason="Risk review.",
        )


def test_reason_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        AgentOpinion(
            agent_id="risk-agent",
            role=AgentRole.RISK,
            recommendation=AgentRecommendation.REVIEW,
            confidence=Decimal("0.70"),
            weight=Decimal("0.30"),
            reason="   ",
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "confidence",
        "weight",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_opinion_scores_must_be_valid(
    field_name: str,
    value: Decimal,
) -> None:
    arguments = {
        "agent_id": "risk-agent",
        "role": AgentRole.RISK,
        "recommendation": AgentRecommendation.REVIEW,
        "confidence": Decimal("0.70"),
        "weight": Decimal("0.30"),
        "reason": "Risk review.",
    }
    arguments[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be between 0 and 1",
    ):
        AgentOpinion(**arguments)


def test_opinion_warnings_are_tuples() -> None:
    value = AgentOpinion(
        agent_id="risk-agent",
        role=AgentRole.RISK,
        recommendation=AgentRecommendation.REVIEW,
        confidence=Decimal("0.70"),
        weight=Decimal("0.30"),
        reason="Risk review.",
        warnings=["Drawdown elevated."],
    )

    assert value.warnings == (
        "Drawdown elevated.",
    )


def test_vote_summary() -> None:
    value = vote_summary()

    assert value.approval_score == Decimal("0.80")
    assert value.participating_agents == 4
    assert value.abstaining_agents == 1


@pytest.mark.parametrize(
    "field_name",
    [
        "approval_score",
        "review_score",
        "rejection_score",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_vote_scores_must_be_valid(
    field_name: str,
    value: Decimal,
) -> None:
    arguments = {
        "approval_score": Decimal("0.80"),
        "review_score": Decimal("0.15"),
        "rejection_score": Decimal("0.05"),
        "participating_agents": 4,
    }
    arguments[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be between 0 and 1",
    ):
        AgentVoteSummary(**arguments)


def test_agent_counts_cannot_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="participating_agents must not be negative",
    ):
        AgentVoteSummary(
            approval_score=Decimal("0"),
            review_score=Decimal("0"),
            rejection_score=Decimal("0"),
            participating_agents=-1,
        )


def test_coordination_report() -> None:
    value = report()

    assert (
        value.status
        is AgentCoordinatorStatus.COMPLETED
    )
    assert value.action is CoordinatedAction.EXECUTE
    assert value.confidence == Decimal("0.80")


def test_report_collections_are_tuples() -> None:
    value = CoordinationReport(
        status=AgentCoordinatorStatus.COMPLETED,
        action=CoordinatedAction.REVIEW_REQUIRED,
        confidence=Decimal("0.60"),
        opinions=[opinion()],
        vote_summary=vote_summary(),
        rationale="Review required.",
        warnings=["Coordinator warning."],
    )

    assert value.opinions == (opinion(),)
    assert value.warnings == (
        "Coordinator warning.",
    )


def test_rationale_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="rationale must not be empty",
    ):
        CoordinationReport(
            status=AgentCoordinatorStatus.COMPLETED,
            action=CoordinatedAction.BLOCK,
            confidence=Decimal("0.90"),
            opinions=(),
            vote_summary=vote_summary(),
            rationale="   ",
        )


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        CoordinationReport(
            status=AgentCoordinatorStatus.FAILED,
            action=CoordinatedAction.BLOCK,
            confidence=Decimal("0"),
            opinions=(),
            vote_summary=AgentVoteSummary(
                approval_score=Decimal("0"),
                review_score=Decimal("0"),
                rejection_score=Decimal("0"),
                participating_agents=0,
            ),
            rationale="Coordination failed.",
        )


def test_completed_report_cannot_include_error() -> None:
    with pytest.raises(
        ValueError,
        match="only failed reports may include an error",
    ):
        CoordinationReport(
            status=AgentCoordinatorStatus.COMPLETED,
            action=CoordinatedAction.EXECUTE,
            confidence=Decimal("0.90"),
            opinions=(opinion(),),
            vote_summary=vote_summary(),
            rationale="Approved.",
            error="Unexpected error.",
        )


def test_models_are_immutable() -> None:
    value = opinion()

    with pytest.raises(FrozenInstanceError):
        value.agent_id = "changed"