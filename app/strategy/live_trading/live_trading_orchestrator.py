from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable

from app.strategy.agent_coordinator import (
    AgentCoordinatorStatus,
    CoordinatedAction,
    CoordinationReport,
)
from app.strategy.audit import (
    AuditEventType,
    AuditSeverity,
    ExecutionAuditTrail,
)
from app.strategy.execution import (
    ExecutionGateway,
    ExecutionOrderType,
    ExecutionRequest,
    ExecutionSide,
    ExecutionStatus,
)
from app.strategy.portfolio_risk import (
    PortfolioRiskDecision,
    PortfolioRiskReport,
    PortfolioRiskStatus,
)

from .live_trading_models import (
    ExecutionPlanStatus,
    LiveOrderType,
    LiveTradeDecision,
    LiveTradeExecutionResult,
    LiveTradeRequest,
    LiveTradeSide,
    LiveTradingReport,
    LiveTradingStatus,
    TradeExecutionPlan,
    TradingEnvironment,
    TradingSession,
    TradingSessionStatus,
)


_ZERO = Decimal("0")

Clock = Callable[[], datetime]


class LiveTradingOrchestrator:
    """Coordinates approved trading workflows through execution."""

    def __init__(
        self,
        *,
        execution_gateway: ExecutionGateway,
        clock: Clock | None = None,
    ) -> None:
        if not isinstance(
            execution_gateway,
            ExecutionGateway,
        ):
            raise TypeError(
                "execution_gateway must be an ExecutionGateway"
            )

        if clock is not None and not callable(clock):
            raise TypeError(
                "clock must be callable"
            )

        self._execution_gateway = execution_gateway
        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

    def orchestrate(
        self,
        *,
        session: TradingSession,
        request: LiveTradeRequest,
        coordination_report: CoordinationReport,
        risk_report: PortfolioRiskReport,
    ) -> LiveTradingReport:
        self._validate_inputs(
            session=session,
            request=request,
            coordination_report=coordination_report,
            risk_report=risk_report,
        )

        completed_at = self._current_time()
        execution_id = (
            f"execution-{request.request_id}"
        )
        audit_id = f"audit-{request.request_id}"

        audit_trail = ExecutionAuditTrail(
            audit_id=audit_id,
            request_id=request.request_id,
            execution_id=execution_id,
            clock=self._clock,
        )

        audit_trail.append_event(
            event_type=(
                AuditEventType.COORDINATION_STARTED
            ),
            severity=AuditSeverity.INFO,
            message=(
                "Live-trading orchestration started."
            ),
            source="live-trading-orchestrator",
        )

        plan = self._build_plan(
            session=session,
            request=request,
            coordination_report=coordination_report,
            risk_report=risk_report,
        )

        warnings = self._aggregate_warnings(
            coordination_report=coordination_report,
            risk_report=risk_report,
            plan=plan,
        )

        if plan.decision is LiveTradeDecision.REJECT:
            audit_trail.append_event(
                event_type=AuditEventType.TRADE_REJECTED,
                severity=AuditSeverity.WARNING,
                message=plan.reason,
                source="live-trading-orchestrator",
            )

            audit_report = audit_trail.finalize_success(
                warnings=warnings,
            )

            result = LiveTradeExecutionResult(
                request_id=request.request_id,
                plan_id=plan.plan_id,
                decision=LiveTradeDecision.REJECT,
                submitted=False,
                broker_name=None,
                order_id=None,
                filled_quantity=_ZERO,
                average_price=None,
                commission=_ZERO,
                executed_at=None,
                reason=plan.reason,
                warnings=warnings,
            )

            return LiveTradingReport(
                status=LiveTradingStatus.COMPLETED,
                session=session,
                request=request,
                plan=plan,
                result=result,
                completed_at=completed_at,
                audit_id=(
                    audit_report.record.audit_id
                    if audit_report.record is not None
                    else audit_id
                ),
                warnings=warnings,
            )

        if (
            plan.decision
            is LiveTradeDecision.REVIEW_REQUIRED
        ):
            audit_trail.append_event(
                event_type=(
                    AuditEventType.TRADE_REVIEW_REQUIRED
                ),
                severity=AuditSeverity.WARNING,
                message=plan.reason,
                source="live-trading-orchestrator",
            )

            audit_report = audit_trail.finalize_success(
                warnings=warnings,
            )

            result = LiveTradeExecutionResult(
                request_id=request.request_id,
                plan_id=plan.plan_id,
                decision=(
                    LiveTradeDecision.REVIEW_REQUIRED
                ),
                submitted=False,
                broker_name=None,
                order_id=None,
                filled_quantity=_ZERO,
                average_price=None,
                commission=_ZERO,
                executed_at=None,
                reason=plan.reason,
                warnings=warnings,
            )

            return LiveTradingReport(
                status=LiveTradingStatus.COMPLETED,
                session=session,
                request=request,
                plan=plan,
                result=result,
                completed_at=completed_at,
                audit_id=(
                    audit_report.record.audit_id
                    if audit_report.record is not None
                    else audit_id
                ),
                warnings=warnings,
            )

        audit_trail.append_event(
            event_type=AuditEventType.TRADE_APPROVED,
            severity=AuditSeverity.INFO,
            message=plan.reason,
            source="live-trading-orchestrator",
        )

        audit_trail.append_event(
            event_type=(
                AuditEventType.BROKER_SUBMISSION_STARTED
            ),
            severity=AuditSeverity.INFO,
            message=(
                "Approved order was routed to the "
                "execution gateway."
            ),
            source="live-trading-orchestrator",
        )

        execution_request = self._execution_request(
            request=request,
            execution_id=execution_id,
        )

        execution_report = (
            self._execution_gateway.submit(
                execution_request
            )
        )

        if execution_report.status is ExecutionStatus.FAILED:
            error = (
                execution_report.error
                or "Execution gateway failed."
            )

            execution_warnings = (
                warnings
                + tuple(execution_report.warnings)
            )

            audit_trail.append_event(
                event_type=(
                    AuditEventType.BROKER_SUBMISSION_FAILED
                ),
                severity=AuditSeverity.ERROR,
                message=error,
                source="execution-gateway",
            )

            audit_trail.append_event(
                event_type=AuditEventType.EXECUTION_FAILED,
                severity=AuditSeverity.ERROR,
                message=(
                    "Live-trading execution failed."
                ),
                source="live-trading-orchestrator",
            )

            audit_report = audit_trail.finalize_failure(
                error=error,
                warnings=execution_warnings,
            )

            result = LiveTradeExecutionResult(
                request_id=request.request_id,
                plan_id=plan.plan_id,
                decision=LiveTradeDecision.EXECUTE,
                submitted=False,
                broker_name=None,
                order_id=None,
                filled_quantity=_ZERO,
                average_price=None,
                commission=_ZERO,
                executed_at=None,
                reason="Broker execution failed.",
                warnings=execution_warnings,
            )

            return LiveTradingReport(
                status=LiveTradingStatus.FAILED,
                session=session,
                request=request,
                plan=plan,
                result=result,
                completed_at=completed_at,
                audit_id=(
                    audit_report.record.audit_id
                    if audit_report.record is not None
                    else audit_id
                ),
                warnings=execution_warnings,
                error=error,
            )

        receipt = execution_report.receipt

        if receipt is None:
            raise RuntimeError(
                "completed execution report must "
                "include a receipt"
            )

        audit_trail.attach_order_id(
            receipt.order_id
        )

        audit_trail.append_event(
            event_type=(
                AuditEventType.BROKER_SUBMISSION_COMPLETED
            ),
            severity=AuditSeverity.INFO,
            message=(
                "Broker submission completed successfully."
            ),
            source=receipt.broker_name,
            order_id=receipt.order_id,
        )

        audit_trail.append_event(
            event_type=AuditEventType.EXECUTION_COMPLETED,
            severity=AuditSeverity.INFO,
            message=(
                "Live-trading execution completed."
            ),
            source="live-trading-orchestrator",
            order_id=receipt.order_id,
        )

        execution_warnings = (
            warnings
            + tuple(execution_report.warnings)
        )

        audit_report = audit_trail.finalize_success(
            warnings=execution_warnings,
        )

        result = LiveTradeExecutionResult(
            request_id=request.request_id,
            plan_id=plan.plan_id,
            decision=LiveTradeDecision.EXECUTE,
            submitted=True,
            broker_name=receipt.broker_name,
            order_id=receipt.order_id,
            filled_quantity=receipt.filled_quantity,
            average_price=receipt.average_price,
            commission=receipt.commission,
            executed_at=receipt.executed_at,
            reason=(
                "All orchestration gates passed and "
                "the order was executed."
            ),
            warnings=execution_warnings,
        )

        return LiveTradingReport(
            status=LiveTradingStatus.COMPLETED,
            session=session,
            request=request,
            plan=plan,
            result=result,
            completed_at=completed_at,
            audit_id=(
                audit_report.record.audit_id
                if audit_report.record is not None
                else audit_id
            ),
            warnings=execution_warnings,
        )

    @classmethod
    def _build_plan(
        cls,
        *,
        session: TradingSession,
        request: LiveTradeRequest,
        coordination_report: CoordinationReport,
        risk_report: PortfolioRiskReport,
    ) -> TradeExecutionPlan:
        plan_id = f"plan-{request.request_id}"

        if request.session_id != session.session_id:
            return cls._rejected_plan(
                plan_id=plan_id,
                request=request,
                session=session,
                reason=(
                    "Trade request does not belong to "
                    "the supplied trading session."
                ),
            )

        if (
            session.status
            is not TradingSessionStatus.ACTIVE
        ):
            return cls._rejected_plan(
                plan_id=plan_id,
                request=request,
                session=session,
                reason=(
                    "Trading session is not active."
                ),
            )

        if (
            coordination_report.status
            is AgentCoordinatorStatus.FAILED
        ):
            return cls._rejected_plan(
                plan_id=plan_id,
                request=request,
                session=session,
                reason=(
                    "Agent coordination failed."
                ),
            )

        if (
            coordination_report.action
            is CoordinatedAction.BLOCK
        ):
            return cls._rejected_plan(
                plan_id=plan_id,
                request=request,
                session=session,
                reason=(
                    "Agent coordinator blocked execution."
                ),
            )

        if (
            risk_report.status
            is PortfolioRiskStatus.FAILED
        ):
            return cls._rejected_plan(
                plan_id=plan_id,
                request=request,
                session=session,
                reason=(
                    "Portfolio risk assessment failed."
                ),
            )

        if (
            risk_report.decision
            is PortfolioRiskDecision.REJECT
        ):
            return cls._rejected_plan(
                plan_id=plan_id,
                request=request,
                session=session,
                reason=(
                    "Portfolio risk manager rejected "
                    "the proposed exposure."
                ),
            )

        if (
            coordination_report.action
            is CoordinatedAction.REVIEW_REQUIRED
            or risk_report.decision
            is PortfolioRiskDecision.REVIEW_REQUIRED
        ):
            return cls._review_plan(
                plan_id=plan_id,
                request=request,
                session=session,
                reason=(
                    "Manual review is required by one "
                    "or more orchestration gates."
                ),
            )

        estimated_order_value = (
            request.estimated_order_value
        )

        if estimated_order_value is None:
            return cls._review_plan(
                plan_id=plan_id,
                request=request,
                session=session,
                reason=(
                    "Estimated order value is unavailable."
                ),
            )

        if (
            estimated_order_value
            > session.max_order_value
        ):
            return cls._rejected_plan(
                plan_id=plan_id,
                request=request,
                session=session,
                reason=(
                    "Estimated order value exceeds the "
                    "session maximum."
                ),
                estimated_order_value=(
                    estimated_order_value
                ),
            )

        requires_manual_confirmation = (
            session.environment
            is TradingEnvironment.LIVE
        )

        return TradeExecutionPlan(
            plan_id=plan_id,
            request_id=request.request_id,
            environment=session.environment,
            status=ExecutionPlanStatus.READY,
            decision=LiveTradeDecision.EXECUTE,
            approved_quantity=request.quantity,
            estimated_order_value=(
                estimated_order_value
            ),
            reason=(
                "Coordinator, portfolio-risk, session, "
                "and order-value gates passed."
            ),
            risk_checks_passed=True,
            coordinator_approved=True,
            requires_manual_confirmation=(
                requires_manual_confirmation
            ),
        )

    @staticmethod
    def _rejected_plan(
        *,
        plan_id: str,
        request: LiveTradeRequest,
        session: TradingSession,
        reason: str,
        estimated_order_value: Decimal = _ZERO,
    ) -> TradeExecutionPlan:
        return TradeExecutionPlan(
            plan_id=plan_id,
            request_id=request.request_id,
            environment=session.environment,
            status=ExecutionPlanStatus.BLOCKED,
            decision=LiveTradeDecision.REJECT,
            approved_quantity=_ZERO,
            estimated_order_value=(
                estimated_order_value
            ),
            reason=reason,
            risk_checks_passed=False,
            coordinator_approved=False,
        )

    @staticmethod
    def _review_plan(
        *,
        plan_id: str,
        request: LiveTradeRequest,
        session: TradingSession,
        reason: str,
    ) -> TradeExecutionPlan:
        return TradeExecutionPlan(
            plan_id=plan_id,
            request_id=request.request_id,
            environment=session.environment,
            status=(
                ExecutionPlanStatus.REVIEW_REQUIRED
            ),
            decision=(
                LiveTradeDecision.REVIEW_REQUIRED
            ),
            approved_quantity=_ZERO,
            estimated_order_value=(
                request.estimated_order_value
                or _ZERO
            ),
            reason=reason,
            risk_checks_passed=False,
            coordinator_approved=False,
            requires_manual_confirmation=True,
        )

    @staticmethod
    def _execution_request(
        *,
        request: LiveTradeRequest,
        execution_id: str,
    ) -> ExecutionRequest:
        side = {
            LiveTradeSide.BUY: ExecutionSide.BUY,
            LiveTradeSide.SELL: ExecutionSide.SELL,
        }[request.side]

        order_type = {
            LiveOrderType.MARKET: (
                ExecutionOrderType.MARKET
            ),
            LiveOrderType.LIMIT: (
                ExecutionOrderType.LIMIT
            ),
        }[request.order_type]

        return ExecutionRequest(
            execution_id=execution_id,
            symbol=request.symbol,
            side=side,
            quantity=request.quantity,
            order_type=order_type,
            submitted_at=request.submitted_at,
            limit_price=request.limit_price,
            strategy_id=request.strategy_id,
            metadata=request.metadata,
        )

    @staticmethod
    def _aggregate_warnings(
        *,
        coordination_report: CoordinationReport,
        risk_report: PortfolioRiskReport,
        plan: TradeExecutionPlan,
    ) -> tuple[str, ...]:
        return (
            tuple(coordination_report.warnings)
            + tuple(risk_report.warnings)
            + tuple(plan.warnings)
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
        session: TradingSession,
        request: LiveTradeRequest,
        coordination_report: CoordinationReport,
        risk_report: PortfolioRiskReport,
    ) -> None:
        if not isinstance(session, TradingSession):
            raise TypeError(
                "session must be a TradingSession"
            )

        if not isinstance(request, LiveTradeRequest):
            raise TypeError(
                "request must be a LiveTradeRequest"
            )

        if not isinstance(
            coordination_report,
            CoordinationReport,
        ):
            raise TypeError(
                "coordination_report must be a "
                "CoordinationReport"
            )

        if not isinstance(
            risk_report,
            PortfolioRiskReport,
        ):
            raise TypeError(
                "risk_report must be a PortfolioRiskReport"
            )