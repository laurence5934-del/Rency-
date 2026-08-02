from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Protocol

from app.strategy.decision import (
    Decision,
    DecisionAction,
)
from app.strategy.regime import (
    MarketRegime,
    MarketRegimeReport,
    RegimeDetectionStatus,
)
from app.strategy.risk_dashboard import (
    DeploymentReadiness,
    InstitutionalRiskDashboard,
)

from .orchestrator_models import (
    OrchestratorReport,
    OrchestratorStatus,
    PaperTradeRequest,
    PaperTradeResult,
    TradeApproval,
)


_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class PaperBrokerReceipt:
    """Successful execution information returned by a paper broker."""

    order_id: str
    execution_price: Decimal
    executed_quantity: Decimal

    def __post_init__(self) -> None:
        normalized_order_id = self.order_id.strip()

        if not normalized_order_id:
            raise ValueError(
                "order_id must not be empty"
            )

        if not isinstance(
            self.execution_price,
            Decimal,
        ):
            raise TypeError(
                "execution_price must be a Decimal"
            )

        if self.execution_price <= _ZERO:
            raise ValueError(
                "execution_price must be greater than zero"
            )

        if not isinstance(
            self.executed_quantity,
            Decimal,
        ):
            raise TypeError(
                "executed_quantity must be a Decimal"
            )

        if self.executed_quantity <= _ZERO:
            raise ValueError(
                "executed_quantity must be greater than zero"
            )

        object.__setattr__(
            self,
            "order_id",
            normalized_order_id,
        )


class PaperBrokerGateway(Protocol):
    """Contract implemented by a paper-order broker gateway."""

    def submit(
        self,
        request: PaperTradeRequest,
    ) -> PaperBrokerReceipt:
        """Submit an approved paper-trading request."""
        ...


Clock = Callable[[], datetime]


class PaperTradingOrchestrator:
    """Coordinates enterprise gates before paper execution."""

    def __init__(
        self,
        *,
        broker: PaperBrokerGateway,
        clock: Clock | None = None,
    ) -> None:
        if not hasattr(broker, "submit"):
            raise TypeError(
                "broker must provide a submit method"
            )

        if clock is not None and not callable(clock):
            raise TypeError(
                "clock must be callable"
            )

        self._broker = broker
        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

    def execute(
        self,
        *,
        request: PaperTradeRequest,
        decision: Decision,
        risk_dashboard: InstitutionalRiskDashboard,
        regime_report: MarketRegimeReport,
    ) -> OrchestratorReport:
        self._validate_inputs(
            request=request,
            decision=decision,
            risk_dashboard=risk_dashboard,
            regime_report=regime_report,
        )

        completed_at = self._current_time()

        decision_approval = self._decision_approval(
            decision
        )
        risk_approval = self._risk_approval(
            risk_dashboard
        )
        regime_approval = self._regime_approval(
            regime_report
        )

        approval = self._final_approval(
            decision_approval=decision_approval,
            risk_approval=risk_approval,
            regime_approval=regime_approval,
        )

        decision_summary = self._decision_summary(
            decision
        )
        risk_summary = self._risk_summary(
            risk_dashboard
        )
        regime_summary = self._regime_summary(
            regime_report
        )

        warnings = self._aggregate_warnings(
            risk_dashboard=risk_dashboard,
            regime_report=regime_report,
        )

        if approval is TradeApproval.REJECTED:
            result = PaperTradeResult(
                request_id=request.request_id,
                approval=TradeApproval.REJECTED,
                submitted=False,
                reason=self._rejection_reason(
                    decision_approval=decision_approval,
                    risk_approval=risk_approval,
                    regime_approval=regime_approval,
                ),
                warnings=warnings,
            )

            return OrchestratorReport(
                status=OrchestratorStatus.COMPLETED,
                request=request,
                approval=TradeApproval.REJECTED,
                result=result,
                decision_summary=decision_summary,
                risk_summary=risk_summary,
                regime_summary=regime_summary,
                completed_at=completed_at,
                warnings=warnings,
            )

        if approval is TradeApproval.REVIEW_REQUIRED:
            result = PaperTradeResult(
                request_id=request.request_id,
                approval=TradeApproval.REVIEW_REQUIRED,
                submitted=False,
                reason=self._review_reason(
                    decision_approval=decision_approval,
                    risk_approval=risk_approval,
                    regime_approval=regime_approval,
                ),
                warnings=warnings,
            )

            return OrchestratorReport(
                status=OrchestratorStatus.COMPLETED,
                request=request,
                approval=TradeApproval.REVIEW_REQUIRED,
                result=result,
                decision_summary=decision_summary,
                risk_summary=risk_summary,
                regime_summary=regime_summary,
                completed_at=completed_at,
                warnings=warnings,
            )

        try:
            receipt = self._broker.submit(request)

            if not isinstance(
                receipt,
                PaperBrokerReceipt,
            ):
                raise TypeError(
                    "broker submit must return "
                    "PaperBrokerReceipt"
                )

            if (
                receipt.executed_quantity
                > request.quantity
            ):
                raise ValueError(
                    "executed quantity must not exceed "
                    "requested quantity"
                )

            result = PaperTradeResult(
                request_id=request.request_id,
                approval=TradeApproval.APPROVED,
                submitted=True,
                reason=(
                    "All orchestration gates passed and "
                    "the paper order was submitted."
                ),
                order_id=receipt.order_id,
                execution_price=(
                    receipt.execution_price
                ),
                executed_quantity=(
                    receipt.executed_quantity
                ),
                warnings=warnings,
            )

            return OrchestratorReport(
                status=OrchestratorStatus.COMPLETED,
                request=request,
                approval=TradeApproval.APPROVED,
                result=result,
                decision_summary=decision_summary,
                risk_summary=risk_summary,
                regime_summary=regime_summary,
                completed_at=completed_at,
                warnings=warnings,
            )

        except Exception as exc:
            result = PaperTradeResult(
                request_id=request.request_id,
                approval=TradeApproval.REJECTED,
                submitted=False,
                reason=(
                    "Paper broker execution failed."
                ),
                warnings=warnings,
            )

            return OrchestratorReport(
                status=OrchestratorStatus.FAILED,
                request=request,
                approval=TradeApproval.REJECTED,
                result=result,
                decision_summary=decision_summary,
                risk_summary=risk_summary,
                regime_summary=regime_summary,
                completed_at=completed_at,
                warnings=warnings,
                error=str(exc),
            )

    @staticmethod
    def _decision_approval(
        decision: Decision,
    ) -> TradeApproval:
        if decision.action in {
            DecisionAction.PAPER_TRADE,
            DecisionAction.LIVE_TRADE,
        }:
            return TradeApproval.APPROVED

        if decision.action is DecisionAction.IMPROVE:
            return TradeApproval.REVIEW_REQUIRED

        return TradeApproval.REJECTED

    @staticmethod
    def _risk_approval(
        dashboard: InstitutionalRiskDashboard,
    ) -> TradeApproval:
        if dashboard.readiness in {
            DeploymentReadiness.PAPER_READY,
            DeploymentReadiness.LIVE_READY,
        }:
            return TradeApproval.APPROVED

        if (
            dashboard.readiness
            is DeploymentReadiness.REVIEW_REQUIRED
        ):
            return TradeApproval.REVIEW_REQUIRED

        return TradeApproval.REJECTED

    @staticmethod
    def _regime_approval(
        report: MarketRegimeReport,
    ) -> TradeApproval:
        if (
            report.status
            is RegimeDetectionStatus.FAILED
        ):
            return TradeApproval.REJECTED

        if report.regime in {
            MarketRegime.RISK_OFF,
            MarketRegime.STRONG_BEAR,
        }:
            return TradeApproval.REJECTED

        if report.regime in {
            MarketRegime.UNKNOWN,
            MarketRegime.CORRECTION,
            MarketRegime.HIGH_VOLATILITY,
        }:
            return TradeApproval.REVIEW_REQUIRED

        return TradeApproval.APPROVED

    @staticmethod
    def _final_approval(
        *,
        decision_approval: TradeApproval,
        risk_approval: TradeApproval,
        regime_approval: TradeApproval,
    ) -> TradeApproval:
        approvals = (
            decision_approval,
            risk_approval,
            regime_approval,
        )

        if TradeApproval.REJECTED in approvals:
            return TradeApproval.REJECTED

        if TradeApproval.REVIEW_REQUIRED in approvals:
            return TradeApproval.REVIEW_REQUIRED

        return TradeApproval.APPROVED

    @staticmethod
    def _decision_summary(
        decision: Decision,
    ) -> str:
        return (
            f"Decision action: {decision.action.value}; "
            f"confidence: {decision.confidence}; "
            f"reason: {decision.reason}"
        )

    @staticmethod
    def _risk_summary(
        dashboard: InstitutionalRiskDashboard,
    ) -> str:
        return (
            f"Portfolio health: {dashboard.health.value}; "
            f"readiness: {dashboard.readiness.value}; "
            f"overall risk score: "
            f"{dashboard.overall_risk_score}"
        )

    @staticmethod
    def _regime_summary(
        report: MarketRegimeReport,
    ) -> str:
        return (
            f"Market regime: {report.regime.value}; "
            f"confidence: {report.confidence.value}; "
            f"overall score: {report.overall_score}"
        )

    @staticmethod
    def _aggregate_warnings(
        *,
        risk_dashboard: InstitutionalRiskDashboard,
        regime_report: MarketRegimeReport,
    ) -> tuple[str, ...]:
        return (
            tuple(risk_dashboard.warnings)
            + tuple(regime_report.warnings)
        )

    @staticmethod
    def _rejection_reason(
        *,
        decision_approval: TradeApproval,
        risk_approval: TradeApproval,
        regime_approval: TradeApproval,
    ) -> str:
        failed_gates: list[str] = []

        if decision_approval is TradeApproval.REJECTED:
            failed_gates.append("decision")

        if risk_approval is TradeApproval.REJECTED:
            failed_gates.append("risk")

        if regime_approval is TradeApproval.REJECTED:
            failed_gates.append("market regime")

        return (
            "Paper execution was rejected by the "
            + ", ".join(failed_gates)
            + " gate"
            + ("s." if len(failed_gates) != 1 else ".")
        )

    @staticmethod
    def _review_reason(
        *,
        decision_approval: TradeApproval,
        risk_approval: TradeApproval,
        regime_approval: TradeApproval,
    ) -> str:
        review_gates: list[str] = []

        if (
            decision_approval
            is TradeApproval.REVIEW_REQUIRED
        ):
            review_gates.append("decision")

        if (
            risk_approval
            is TradeApproval.REVIEW_REQUIRED
        ):
            review_gates.append("risk")

        if (
            regime_approval
            is TradeApproval.REVIEW_REQUIRED
        ):
            review_gates.append("market regime")

        return (
            "Manual review is required by the "
            + ", ".join(review_gates)
            + " gate"
            + ("s." if len(review_gates) != 1 else ".")
        )

    def _current_time(self) -> datetime:
        value = self._clock()

        if not isinstance(value, datetime):
            raise TypeError(
                "clock must return a datetime"
            )

        if value.tzinfo is None:
            raise ValueError(
                "clock must return a timezone-aware datetime"
            )

        return value

    @staticmethod
    def _validate_inputs(
        *,
        request: PaperTradeRequest,
        decision: Decision,
        risk_dashboard: InstitutionalRiskDashboard,
        regime_report: MarketRegimeReport,
    ) -> None:
        if not isinstance(
            request,
            PaperTradeRequest,
        ):
            raise TypeError(
                "request must be a PaperTradeRequest"
            )

        if not isinstance(decision, Decision):
            raise TypeError(
                "decision must be a Decision"
            )

        if not isinstance(
            risk_dashboard,
            InstitutionalRiskDashboard,
        ):
            raise TypeError(
                "risk_dashboard must be an "
                "InstitutionalRiskDashboard"
            )

        if not isinstance(
            regime_report,
            MarketRegimeReport,
        ):
            raise TypeError(
                "regime_report must be a "
                "MarketRegimeReport"
            )