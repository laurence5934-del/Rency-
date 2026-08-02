from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")
_ONE = Decimal("1")


class AgentCoordinatorStatus(str, Enum):
    """Lifecycle status of an agent-coordination workflow."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AgentRole(str, Enum):
    """Supported specialized agent responsibilities."""

    STRATEGY = "STRATEGY"
    RISK = "RISK"
    REGIME = "REGIME"
    PORTFOLIO = "PORTFOLIO"
    EXECUTION = "EXECUTION"


class AgentRecommendation(str, Enum):
    """Recommendation produced by one specialized agent."""

    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    REJECT = "REJECT"
    ABSTAIN = "ABSTAIN"


class CoordinatedAction(str, Enum):
    """Final action selected by the coordinator."""

    EXECUTE = "EXECUTE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class AgentOpinion:
    """Immutable recommendation from one specialized agent."""

    agent_id: str
    role: AgentRole
    recommendation: AgentRecommendation
    confidence: Decimal
    weight: Decimal
    reason: str
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_agent_id = self.agent_id.strip()
        normalized_reason = self.reason.strip()

        if not normalized_agent_id:
            raise ValueError(
                "agent_id must not be empty"
            )

        if not isinstance(self.role, AgentRole):
            raise TypeError(
                "role must be an AgentRole"
            )

        if not isinstance(
            self.recommendation,
            AgentRecommendation,
        ):
            raise TypeError(
                "recommendation must be an AgentRecommendation"
            )

        for field_name in (
            "confidence",
            "weight",
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

        if not normalized_reason:
            raise ValueError(
                "reason must not be empty"
            )

        object.__setattr__(
            self,
            "agent_id",
            normalized_agent_id,
        )
        object.__setattr__(
            self,
            "reason",
            normalized_reason,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )


@dataclass(frozen=True, slots=True)
class AgentVoteSummary:
    """Weighted vote totals calculated by the coordinator."""

    approval_score: Decimal
    review_score: Decimal
    rejection_score: Decimal
    participating_agents: int
    abstaining_agents: int = 0

    def __post_init__(self) -> None:
        for field_name in (
            "approval_score",
            "review_score",
            "rejection_score",
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

        if self.participating_agents < 0:
            raise ValueError(
                "participating_agents must not be negative"
            )

        if self.abstaining_agents < 0:
            raise ValueError(
                "abstaining_agents must not be negative"
            )


@dataclass(frozen=True, slots=True)
class CoordinationReport:
    """Unified result from the enterprise agent coordinator."""

    status: AgentCoordinatorStatus
    action: CoordinatedAction
    confidence: Decimal
    opinions: tuple[AgentOpinion, ...]
    vote_summary: AgentVoteSummary
    rationale: str
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.status,
            AgentCoordinatorStatus,
        ):
            raise TypeError(
                "status must be an AgentCoordinatorStatus"
            )

        if not isinstance(
            self.action,
            CoordinatedAction,
        ):
            raise TypeError(
                "action must be a CoordinatedAction"
            )

        if not isinstance(self.confidence, Decimal):
            raise TypeError(
                "confidence must be a Decimal"
            )

        if not _ZERO <= self.confidence <= _ONE:
            raise ValueError(
                "confidence must be between 0 and 1"
            )

        if not isinstance(
            self.vote_summary,
            AgentVoteSummary,
        ):
            raise TypeError(
                "vote_summary must be an AgentVoteSummary"
            )

        normalized_rationale = self.rationale.strip()

        if not normalized_rationale:
            raise ValueError(
                "rationale must not be empty"
            )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if self.status is AgentCoordinatorStatus.FAILED:
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
            "opinions",
            tuple(self.opinions),
        )
        object.__setattr__(
            self,
            "rationale",
            normalized_rationale,
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