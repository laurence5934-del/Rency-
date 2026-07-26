from __future__ import annotations

from .models import (
    DecisionAction,
    DecisionContext,
    DecisionPriority,
    DecisionRuleResult,
)
from .policy_engine import DecisionPolicy


class DecisionRuleEngine:
    def evaluate(
        self,
        context: DecisionContext,
        policy: DecisionPolicy,
    ) -> tuple[DecisionRuleResult, ...]:
        desired = context.strategy.desired_action
        results: list[DecisionRuleResult] = []

        validation_pass = context.validation_score >= policy.minimum_validation_score
        results.append(
            DecisionRuleResult(
                "validation_gate",
                validation_pass,
                desired if validation_pass else DecisionAction.ESCALATE_REVIEW,
                DecisionPriority.HIGH,
                context.validation_score,
                "Validated signal quality threshold",
            )
        )

        consensus_pass = context.consensus_score >= policy.minimum_consensus_score
        results.append(
            DecisionRuleResult(
                "consensus_gate",
                consensus_pass,
                desired if consensus_pass else DecisionAction.HOLD,
                DecisionPriority.HIGH,
                context.consensus_score,
                "AI contributor agreement threshold",
            )
        )

        confidence_pass = context.confidence_score >= policy.minimum_confidence_score
        results.append(
            DecisionRuleResult(
                "confidence_gate",
                confidence_pass,
                desired if confidence_pass else DecisionAction.HOLD,
                DecisionPriority.HIGH,
                context.confidence_score,
                "Confidence threshold for automated action",
            )
        )

        risk_decision = context.risk.decision.upper()
        risk_pass = risk_decision in {"APPROVE", "REDUCE"}
        risk_action = desired
        if risk_decision == "REJECT":
            risk_action = DecisionAction.CANCEL
        elif risk_decision == "REVIEW":
            risk_action = DecisionAction.ESCALATE_REVIEW
        results.append(
            DecisionRuleResult(
                "risk_gate",
                risk_pass,
                risk_action,
                DecisionPriority.CRITICAL,
                1.0 - context.risk.risk_score,
                f"Risk engine decision: {risk_decision}",
            )
        )

        liquidity_pass = context.market.liquidity_score >= policy.minimum_liquidity_score
        results.append(
            DecisionRuleResult(
                "liquidity_gate",
                liquidity_pass,
                desired if liquidity_pass else DecisionAction.DEFER,
                DecisionPriority.HIGH,
                context.market.liquidity_score,
                "Market liquidity threshold",
            )
        )

        position_action = desired
        position_pass = True

        if desired == DecisionAction.BUY and context.position.has_open_position:
            position_action = DecisionAction.SCALE_IN
        elif desired == DecisionAction.SELL and context.position.has_open_position:
            position_action = DecisionAction.CLOSE_POSITION
        elif desired == DecisionAction.SELL and not context.position.has_open_position:
            position_action = DecisionAction.HOLD
            position_pass = False

        results.append(
            DecisionRuleResult(
                "position_state_rule",
                position_pass,
                position_action,
                DecisionPriority.NORMAL,
                1.0 if position_pass else 0.25,
                "Transforms strategy intent using current position state",
            )
        )

        return tuple(results)
