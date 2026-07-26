from __future__ import annotations

from .audit_log import DecisionAuditLog
from .conflict_resolver import DecisionConflictResolver
from .explanation_engine import DecisionExplanationEngine
from .metrics import DecisionMetrics
from .models import (
    DecisionAction,
    DecisionContext,
    DecisionEvidence,
    DecisionPriority,
    DecisionReport,
    DecisionStatus,
)
from .policy_engine import DecisionPolicy, DecisionPolicyEngine
from .rule_engine import DecisionRuleEngine


class EnterpriseDecisionEngine:
    def __init__(
        self,
        *,
        policy: DecisionPolicy | None = None,
        metrics: DecisionMetrics | None = None,
        audit_log: DecisionAuditLog | None = None,
    ) -> None:
        self._policy_engine = DecisionPolicyEngine(policy)
        self._rule_engine = DecisionRuleEngine()
        self._resolver = DecisionConflictResolver()
        self._explanation = DecisionExplanationEngine()
        self._metrics = metrics or DecisionMetrics()
        self._audit = audit_log or DecisionAuditLog()

    def decide(
        self,
        context: DecisionContext,
        *,
        correlation_id: str | None = None,
    ) -> DecisionReport:
        action, status, reasons = self._policy_engine.hard_gate(context)

        if action is not None and status is not None:
            rule_results = ()
            score = self._score(context)
        else:
            rule_results = self._rule_engine.evaluate(
                context,
                self._policy_engine.policy,
            )
            action = self._resolver.resolve(
                rule_results,
                context.strategy.desired_action,
            )
            score = self._score(context)
            status = self._status_for(action, score)
            reasons = self._reasons_from_rules(rule_results)

        approved_quantity = self._approved_quantity(context, action, status)

        evidence = (
            DecisionEvidence("validator", "validation_score", context.validation_score, 0.20),
            DecisionEvidence("consensus", "consensus_score", context.consensus_score, 0.20),
            DecisionEvidence("confidence", "confidence_score", context.confidence_score, 0.20),
            DecisionEvidence("risk", "risk_score", context.risk.risk_score, 0.25),
            DecisionEvidence("strategy", "signal_strength", context.strategy.signal_strength, 0.15),
        )

        explanation = self._explanation.explain(
            context,
            action,
            status,
            score,
            rule_results,
            reasons,
        )

        report = DecisionReport.create(
            symbol=context.symbol,
            action=action,
            status=status,
            requested_quantity=context.requested_quantity,
            approved_quantity=approved_quantity,
            decision_score=score,
            priority=context.priority,
            reasons=reasons,
            rule_results=rule_results,
            evidence=evidence,
            explanation=explanation,
            correlation_id=correlation_id,
        )

        self._audit.append(report)
        self._update_metrics(report)
        return report

    def _score(self, context: DecisionContext) -> float:
        risk_quality = 1.0 - context.risk.risk_score
        score = (
            context.validation_score * 0.20
            + context.consensus_score * 0.20
            + context.confidence_score * 0.20
            + risk_quality * 0.25
            + context.strategy.signal_strength * 0.15
        )
        return max(0.0, min(1.0, score))

    def _status_for(
        self,
        action: DecisionAction,
        score: float,
    ) -> DecisionStatus:
        policy = self._policy_engine.policy

        if action == DecisionAction.CANCEL:
            return DecisionStatus.REJECTED
        if action == DecisionAction.DEFER:
            return DecisionStatus.DEFERRED
        if action == DecisionAction.ESCALATE_REVIEW:
            return DecisionStatus.REVIEW_REQUIRED
        if score >= policy.approve_score_threshold:
            return DecisionStatus.APPROVED
        if score >= policy.review_score_threshold:
            return DecisionStatus.REVIEW_REQUIRED
        return DecisionStatus.REJECTED

    def _approved_quantity(
        self,
        context: DecisionContext,
        action: DecisionAction,
        status: DecisionStatus,
    ) -> int:
        if status != DecisionStatus.APPROVED:
            return 0
        if action in {
            DecisionAction.HOLD,
            DecisionAction.CANCEL,
            DecisionAction.DEFER,
            DecisionAction.ESCALATE_REVIEW,
        }:
            return 0

        risk_quantity = context.risk.approved_quantity
        if risk_quantity <= 0:
            risk_quantity = context.risk.maximum_allowed_quantity

        return max(
            0,
            min(
                context.requested_quantity,
                risk_quantity,
                context.risk.maximum_allowed_quantity,
            ),
        )

    def _reasons_from_rules(
        self,
        results,
    ) -> tuple[str, ...]:
        failed = tuple(
            f"{result.rule_name.upper()}:{result.rationale}"
            for result in results
            if not result.passed
        )
        return failed or ("ALL_DECISION_RULES_SATISFIED",)

    def _update_metrics(self, report: DecisionReport) -> None:
        self._metrics.increment("total")
        self._metrics.increment(report.status.value.lower())
        self._metrics.increment(report.action.value.lower())

    def metrics(self) -> dict[str, int]:
        return self._metrics.snapshot()

    def recent_decisions(self, limit: int = 50) -> tuple[DecisionReport, ...]:
        return self._audit.recent(limit)

    def health(self) -> dict[str, object]:
        return {
            "status": "HEALTHY",
            "metrics": self.metrics(),
            "audit_entries": self._audit.count(),
        }
