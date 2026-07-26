from __future__ import annotations

from dataclasses import dataclass

from .models import DecisionAction, DecisionContext, DecisionStatus


@dataclass(frozen=True, slots=True)
class DecisionPolicy:
    minimum_validation_score: float = 0.60
    minimum_consensus_score: float = 0.60
    minimum_confidence_score: float = 0.65
    minimum_signal_strength: float = 0.60
    minimum_liquidity_score: float = 0.40
    approve_score_threshold: float = 0.70
    review_score_threshold: float = 0.55
    allow_market_closed_defer: bool = True
    require_risk_approval: bool = True

    def __post_init__(self) -> None:
        values = (
            self.minimum_validation_score,
            self.minimum_consensus_score,
            self.minimum_confidence_score,
            self.minimum_signal_strength,
            self.minimum_liquidity_score,
            self.approve_score_threshold,
            self.review_score_threshold,
        )
        if any(not 0.0 <= value <= 1.0 for value in values):
            raise ValueError("policy score values must be between 0.0 and 1.0")
        if self.review_score_threshold > self.approve_score_threshold:
            raise ValueError("review threshold cannot exceed approve threshold")


class DecisionPolicyEngine:
    def __init__(self, policy: DecisionPolicy | None = None) -> None:
        self.policy = policy or DecisionPolicy()

    def hard_gate(
        self,
        context: DecisionContext,
    ) -> tuple[DecisionAction | None, DecisionStatus | None, tuple[str, ...]]:
        reasons: list[str] = []

        if context.market.trading_halted:
            return (
                DecisionAction.CANCEL,
                DecisionStatus.REJECTED,
                ("TRADING_HALTED",),
            )

        if not context.market.market_open:
            if self.policy.allow_market_closed_defer:
                return (
                    DecisionAction.DEFER,
                    DecisionStatus.DEFERRED,
                    ("MARKET_CLOSED",),
                )
            return (
                DecisionAction.CANCEL,
                DecisionStatus.REJECTED,
                ("MARKET_CLOSED",),
            )

        risk_decision = context.risk.decision.upper()
        if self.policy.require_risk_approval and risk_decision == "REJECT":
            reasons.extend(context.risk.violations or ("RISK_ENGINE_REJECTED",))
            return (
                DecisionAction.CANCEL,
                DecisionStatus.REJECTED,
                tuple(reasons),
            )

        if context.validation_score < self.policy.minimum_validation_score:
            reasons.append("VALIDATION_SCORE_BELOW_MINIMUM")
        if context.consensus_score < self.policy.minimum_consensus_score:
            reasons.append("CONSENSUS_SCORE_BELOW_MINIMUM")
        if context.confidence_score < self.policy.minimum_confidence_score:
            reasons.append("CONFIDENCE_SCORE_BELOW_MINIMUM")
        if context.strategy.signal_strength < self.policy.minimum_signal_strength:
            reasons.append("SIGNAL_STRENGTH_BELOW_MINIMUM")
        if context.market.liquidity_score < self.policy.minimum_liquidity_score:
            reasons.append("LIQUIDITY_SCORE_BELOW_MINIMUM")

        if reasons:
            return (
                DecisionAction.ESCALATE_REVIEW,
                DecisionStatus.REVIEW_REQUIRED,
                tuple(reasons),
            )

        return None, None, ()
