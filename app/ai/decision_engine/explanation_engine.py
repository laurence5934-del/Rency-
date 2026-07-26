from __future__ import annotations

from .models import DecisionAction, DecisionContext, DecisionRuleResult, DecisionStatus


class DecisionExplanationEngine:
    def explain(
        self,
        context: DecisionContext,
        action: DecisionAction,
        status: DecisionStatus,
        decision_score: float,
        results: tuple[DecisionRuleResult, ...],
        reasons: tuple[str, ...],
    ) -> str:
        passed = sum(1 for result in results if result.passed)
        failed = len(results) - passed
        reason_text = ", ".join(reasons) if reasons else "No blocking policy violations"

        return (
            f"{context.symbol}: {status.value} {action.value}. "
            f"Decision score={decision_score:.4f}; "
            f"rules passed={passed}; rules failed={failed}. "
            f"Consensus={context.consensus_score:.4f}, "
            f"confidence={context.confidence_score:.4f}, "
            f"validation={context.validation_score:.4f}, "
            f"risk={context.risk.risk_score:.4f}. "
            f"Reason: {reason_text}."
        )
