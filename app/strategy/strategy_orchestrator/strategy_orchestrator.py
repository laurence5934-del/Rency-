from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Iterable

from app.strategy.agent_coordinator.coordinator_models import (
    AgentCoordinatorStatus,
    CoordinatedAction,
)
from app.strategy.portfolio_risk.portfolio_risk_models import (
    PortfolioRiskDecision,
    PortfolioRiskStatus,
)
from app.strategy.rebalancing.rebalancing_models import (
    RebalancingDecision,
    RebalancingStatus,
)
from app.strategy.regime.regime_models import (
    MarketRegime,
    RegimeDetectionStatus,
)

from .orchestrator_models import (
    StrategyExecutionEnvironment,
    StrategyOrchestratorStatus,
    StrategyWorkflowDecision,
    StrategyWorkflowPlan,
    StrategyWorkflowReport,
    StrategyWorkflowRequest,
    StrategyWorkflowStage,
    StrategyWorkflowStep,
    StrategyWorkflowStepStatus,
)


Clock = Callable[[], datetime]


class EnterpriseStrategyOrchestrator:
    """Coordinates enterprise strategy workflow gate results."""

    def __init__(
        self,
        *,
        clock: Clock | None = None,
    ) -> None:
        if clock is not None and not callable(clock):
            raise TypeError(
                "clock must be callable"
            )

        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

    def orchestrate(
        self,
        *,
        request: StrategyWorkflowRequest,
        regime_status: RegimeDetectionStatus,
        regime: MarketRegime,
        coordination_status: AgentCoordinatorStatus,
        coordinated_action: CoordinatedAction,
        risk_status: PortfolioRiskStatus,
        risk_decision: PortfolioRiskDecision,
        rebalancing_status: RebalancingStatus,
        rebalancing_decision: RebalancingDecision,
        execution_reference_id: str | None = None,
        audit_reference_id: str | None = None,
        performance_reference_id: str | None = None,
        warnings: Iterable[str] = (),
    ) -> StrategyWorkflowReport:
        self._validate_inputs(
            request=request,
            regime_status=regime_status,
            regime=regime,
            coordination_status=coordination_status,
            coordinated_action=coordinated_action,
            risk_status=risk_status,
            risk_decision=risk_decision,
            rebalancing_status=rebalancing_status,
            rebalancing_decision=rebalancing_decision,
        )

        try:
            warning_values = tuple(warnings)
        except TypeError as exc:
            raise TypeError(
                "warnings must be iterable"
            ) from exc

        normalized_warnings = self._normalize_warnings(
            warning_values
        )

        created_at = self._current_time()
        steps: list[StrategyWorkflowStep] = []

        self._append_completed_step(
            steps=steps,
            request=request,
            stage=StrategyWorkflowStage.REQUEST_RECEIVED,
            component="strategy-orchestrator",
            summary="Strategy workflow request was received.",
        )

        failed_gate = self._failed_gate(
            regime_status=regime_status,
            coordination_status=coordination_status,
            risk_status=risk_status,
            rebalancing_status=rebalancing_status,
        )

        if failed_gate is not None:
            return self._failed_report(
                request=request,
                steps=steps,
                created_at=created_at,
                component=failed_gate,
                error=(
                    f"{failed_gate} failed during strategy "
                    "workflow orchestration."
                ),
                warnings=normalized_warnings,
            )

        self._append_completed_step(
            steps=steps,
            request=request,
            stage=StrategyWorkflowStage.REGIME_EVALUATED,
            component="market-regime-engine",
            summary=(
                f"Market regime was evaluated as "
                f"{regime.value}."
            ),
        )

        if regime is MarketRegime.UNKNOWN:
            return self._terminal_report(
                request=request,
                steps=steps,
                created_at=created_at,
                decision=(
                    StrategyWorkflowDecision.REVIEW_REQUIRED
                ),
                terminal_stage=(
                    StrategyWorkflowStage.REVIEW_REQUIRED
                ),
                component="market-regime-engine",
                summary=(
                    "Market regime is unknown and requires "
                    "manual review."
                ),
                recommendation=(
                    "Review market conditions before allowing "
                    "strategy execution."
                ),
                warnings=normalized_warnings
                + (
                    "The market regime could not be "
                    "classified confidently.",
                ),
            )

        self._append_completed_step(
            steps=steps,
            request=request,
            stage=StrategyWorkflowStage.AGENTS_COORDINATED,
            component="agent-coordinator",
            summary=(
                f"Agent coordination produced action "
                f"{coordinated_action.value}."
            ),
        )

        if coordinated_action is CoordinatedAction.BLOCK:
            return self._terminal_report(
                request=request,
                steps=steps,
                created_at=created_at,
                decision=StrategyWorkflowDecision.REJECT,
                terminal_stage=StrategyWorkflowStage.REJECTED,
                component="agent-coordinator",
                summary=(
                    "AI agent coordination blocked the "
                    "strategy workflow."
                ),
                recommendation=(
                    "Do not execute the strategy until the "
                    "coordinator block is resolved."
                ),
                warnings=normalized_warnings,
            )

        if (
            coordinated_action
            is CoordinatedAction.REVIEW_REQUIRED
        ):
            return self._terminal_report(
                request=request,
                steps=steps,
                created_at=created_at,
                decision=(
                    StrategyWorkflowDecision.REVIEW_REQUIRED
                ),
                terminal_stage=(
                    StrategyWorkflowStage.REVIEW_REQUIRED
                ),
                component="agent-coordinator",
                summary=(
                    "AI agent coordination requires "
                    "manual review."
                ),
                recommendation=(
                    "Review agent opinions before continuing "
                    "the strategy workflow."
                ),
                warnings=normalized_warnings,
            )

        self._append_completed_step(
            steps=steps,
            request=request,
            stage=StrategyWorkflowStage.PORTFOLIO_OPTIMIZED,
            component="portfolio-optimizer",
            summary=(
                "Portfolio optimization requirements were "
                "accepted for downstream evaluation."
            ),
        )

        self._append_completed_step(
            steps=steps,
            request=request,
            stage=StrategyWorkflowStage.RISK_EVALUATED,
            component="portfolio-risk-manager",
            summary=(
                f"Portfolio risk produced decision "
                f"{risk_decision.value}."
            ),
        )

        if risk_decision is PortfolioRiskDecision.REJECT:
            return self._terminal_report(
                request=request,
                steps=steps,
                created_at=created_at,
                decision=StrategyWorkflowDecision.REJECT,
                terminal_stage=StrategyWorkflowStage.REJECTED,
                component="portfolio-risk-manager",
                summary=(
                    "Portfolio risk rejected the proposed "
                    "strategy workflow."
                ),
                recommendation=(
                    "Resolve critical portfolio risk breaches "
                    "before executing the strategy."
                ),
                warnings=normalized_warnings,
            )

        if (
            risk_decision
            is PortfolioRiskDecision.REVIEW_REQUIRED
        ):
            return self._terminal_report(
                request=request,
                steps=steps,
                created_at=created_at,
                decision=(
                    StrategyWorkflowDecision.REVIEW_REQUIRED
                ),
                terminal_stage=(
                    StrategyWorkflowStage.REVIEW_REQUIRED
                ),
                component="portfolio-risk-manager",
                summary=(
                    "Portfolio risk requires manual review."
                ),
                recommendation=(
                    "Review portfolio risk warnings before "
                    "allowing execution."
                ),
                warnings=normalized_warnings,
            )

        self._append_completed_step(
            steps=steps,
            request=request,
            stage=StrategyWorkflowStage.REBALANCE_EVALUATED,
            component="portfolio-rebalancing-engine",
            summary=(
                f"Portfolio rebalancing produced decision "
                f"{rebalancing_decision.value}."
            ),
        )

        if (
            rebalancing_decision
            is RebalancingDecision.REJECT
        ):
            return self._terminal_report(
                request=request,
                steps=steps,
                created_at=created_at,
                decision=StrategyWorkflowDecision.REJECT,
                terminal_stage=StrategyWorkflowStage.REJECTED,
                component="portfolio-rebalancing-engine",
                summary=(
                    "Portfolio rebalancing rejected the "
                    "proposed workflow."
                ),
                recommendation=(
                    "Reduce turnover or correct rebalance "
                    "constraints before execution."
                ),
                warnings=normalized_warnings,
            )

        if (
            rebalancing_decision
            is RebalancingDecision.REVIEW_REQUIRED
        ):
            return self._terminal_report(
                request=request,
                steps=steps,
                created_at=created_at,
                decision=(
                    StrategyWorkflowDecision.REVIEW_REQUIRED
                ),
                terminal_stage=(
                    StrategyWorkflowStage.REVIEW_REQUIRED
                ),
                component="portfolio-rebalancing-engine",
                summary=(
                    "Portfolio rebalancing requires "
                    "manual review."
                ),
                recommendation=(
                    "Resolve rebalance pricing or funding "
                    "constraints before execution."
                ),
                warnings=normalized_warnings,
            )

        execution_decision = self._execution_decision(
            request
        )

        self._append_completed_step(
            steps=steps,
            request=request,
            stage=StrategyWorkflowStage.EXECUTION_PLANNED,
            component="strategy-orchestrator",
            summary=(
                f"Strategy workflow was approved for "
                f"{execution_decision.value}."
            ),
            decision=execution_decision,
            reference_id=execution_reference_id,
        )

        if execution_reference_id is None:
            plan = self._build_plan(
                request=request,
                steps=steps,
                created_at=created_at,
                decision=execution_decision,
                terminal=False,
                completed_at=None,
                execution_reference_id=None,
                audit_reference_id=None,
                performance_reference_id=None,
                warnings=normalized_warnings,
            )

            return StrategyWorkflowReport(
                status=StrategyOrchestratorStatus.PENDING,
                request=request,
                plan=plan,
                decision=execution_decision,
                completed_at=self._current_time(),
                recommendation=(
                    "Submit the approved execution plan to "
                    "the configured trading environment."
                ),
                warnings=normalized_warnings,
            )

        self._append_completed_step(
            steps=steps,
            request=request,
            stage=StrategyWorkflowStage.EXECUTION_COMPLETED,
            component="execution-layer",
            summary="Strategy execution completed.",
            decision=execution_decision,
            reference_id=execution_reference_id,
        )

        if audit_reference_id is None:
            plan = self._build_plan(
                request=request,
                steps=steps,
                created_at=created_at,
                decision=execution_decision,
                terminal=False,
                completed_at=None,
                execution_reference_id=(
                    execution_reference_id
                ),
                audit_reference_id=None,
                performance_reference_id=None,
                warnings=normalized_warnings,
            )

            return StrategyWorkflowReport(
                status=StrategyOrchestratorStatus.PENDING,
                request=request,
                plan=plan,
                decision=execution_decision,
                completed_at=self._current_time(),
                recommendation=(
                    "Complete execution audit recording "
                    "before closing the workflow."
                ),
                warnings=normalized_warnings,
            )

        self._append_completed_step(
            steps=steps,
            request=request,
            stage=StrategyWorkflowStage.AUDIT_COMPLETED,
            component="execution-audit-trail",
            summary="Execution audit recording completed.",
            decision=execution_decision,
            reference_id=audit_reference_id,
        )

        if performance_reference_id is None:
            plan = self._build_plan(
                request=request,
                steps=steps,
                created_at=created_at,
                decision=execution_decision,
                terminal=False,
                completed_at=None,
                execution_reference_id=(
                    execution_reference_id
                ),
                audit_reference_id=audit_reference_id,
                performance_reference_id=None,
                warnings=normalized_warnings,
            )

            return StrategyWorkflowReport(
                status=StrategyOrchestratorStatus.PENDING,
                request=request,
                plan=plan,
                decision=execution_decision,
                completed_at=self._current_time(),
                recommendation=(
                    "Record portfolio performance attribution "
                    "to complete the workflow."
                ),
                warnings=normalized_warnings,
            )

        completed_at = self._current_time()

        self._append_completed_step(
            steps=steps,
            request=request,
            stage=StrategyWorkflowStage.PERFORMANCE_RECORDED,
            component="performance-attribution-engine",
            summary=(
                "Strategy performance attribution was recorded."
            ),
            decision=execution_decision,
            reference_id=performance_reference_id,
            completed_at=completed_at,
        )

        plan = self._build_plan(
            request=request,
            steps=steps,
            created_at=created_at,
            decision=execution_decision,
            terminal=True,
            completed_at=completed_at,
            execution_reference_id=execution_reference_id,
            audit_reference_id=audit_reference_id,
            performance_reference_id=(
                performance_reference_id
            ),
            warnings=normalized_warnings,
        )

        return StrategyWorkflowReport(
            status=StrategyOrchestratorStatus.COMPLETED,
            request=request,
            plan=plan,
            decision=execution_decision,
            completed_at=completed_at,
            recommendation=(
                "Strategy workflow completed successfully "
                "with execution, audit, and performance records."
            ),
            warnings=normalized_warnings,
        )

    def _terminal_report(
        self,
        *,
        request: StrategyWorkflowRequest,
        steps: list[StrategyWorkflowStep],
        created_at: datetime,
        decision: StrategyWorkflowDecision,
        terminal_stage: StrategyWorkflowStage,
        component: str,
        summary: str,
        recommendation: str,
        warnings: tuple[str, ...],
    ) -> StrategyWorkflowReport:
        completed_at = self._current_time()

        self._append_completed_step(
            steps=steps,
            request=request,
            stage=terminal_stage,
            component=component,
            summary=summary,
            decision=decision,
            completed_at=completed_at,
        )

        plan = self._build_plan(
            request=request,
            steps=steps,
            created_at=created_at,
            decision=decision,
            terminal=True,
            completed_at=completed_at,
            execution_reference_id=None,
            audit_reference_id=None,
            performance_reference_id=None,
            warnings=warnings,
        )

        return StrategyWorkflowReport(
            status=StrategyOrchestratorStatus.COMPLETED,
            request=request,
            plan=plan,
            decision=decision,
            completed_at=completed_at,
            recommendation=recommendation,
            warnings=warnings,
        )

    def _failed_report(
        self,
        *,
        request: StrategyWorkflowRequest,
        steps: list[StrategyWorkflowStep],
        created_at: datetime,
        component: str,
        error: str,
        warnings: tuple[str, ...],
    ) -> StrategyWorkflowReport:
        completed_at = self._current_time()

        step_number = len(steps) + 1

        steps.append(
            StrategyWorkflowStep(
                step_id=self._step_id(
                    request.workflow_id,
                    step_number,
                ),
                workflow_id=request.workflow_id,
                stage=StrategyWorkflowStage.FAILED,
                status=StrategyWorkflowStepStatus.FAILED,
                started_at=completed_at,
                completed_at=completed_at,
                summary=error,
                component=component,
                decision=StrategyWorkflowDecision.REJECT,
                error=error,
            )
        )

        plan = self._build_plan(
            request=request,
            steps=steps,
            created_at=created_at,
            decision=StrategyWorkflowDecision.REJECT,
            terminal=True,
            completed_at=completed_at,
            execution_reference_id=None,
            audit_reference_id=None,
            performance_reference_id=None,
            warnings=warnings,
        )

        return StrategyWorkflowReport(
            status=StrategyOrchestratorStatus.FAILED,
            request=request,
            plan=plan,
            decision=StrategyWorkflowDecision.REJECT,
            completed_at=completed_at,
            recommendation=(
                "Correct the failed workflow component before "
                "attempting another strategy orchestration."
            ),
            warnings=warnings
            + (
                "Strategy orchestration terminated because "
                "a required component failed.",
            ),
            error=error,
        )

    @staticmethod
    def _build_plan(
        *,
        request: StrategyWorkflowRequest,
        steps: list[StrategyWorkflowStep],
        created_at: datetime,
        decision: StrategyWorkflowDecision,
        terminal: bool,
        completed_at: datetime | None,
        execution_reference_id: str | None,
        audit_reference_id: str | None,
        performance_reference_id: str | None,
        warnings: tuple[str, ...],
    ) -> StrategyWorkflowPlan:
        return StrategyWorkflowPlan(
            plan_id=f"plan-{request.workflow_id}",
            workflow_id=request.workflow_id,
            environment=request.environment,
            decision=decision,
            current_stage=steps[-1].stage,
            steps=tuple(steps),
            created_at=created_at,
            terminal=terminal,
            completed_at=completed_at,
            execution_reference_id=(
                execution_reference_id
            ),
            audit_reference_id=audit_reference_id,
            performance_reference_id=(
                performance_reference_id
            ),
            warnings=warnings,
        )

    def _append_completed_step(
    self,
    *,
    steps: list[StrategyWorkflowStep],
    request: StrategyWorkflowRequest,
    stage: StrategyWorkflowStage,
    component: str,
    summary: str,
    decision: StrategyWorkflowDecision | None = None,
    reference_id: str | None = None,
    completed_at: datetime | None = None,
) -> None:
     if completed_at is None:
        started_at = self._current_time()
        effective_completed_at = self._current_time()
     else:
        # When the caller already has a completion timestamp
        # (terminal workflow, performance completion, etc.),
        # use the same timestamp for started_at so the model
        # invariant started_at <= completed_at is preserved.
        started_at = completed_at
        effective_completed_at = completed_at

     steps.append(
        StrategyWorkflowStep(
            step_id=self._step_id(
                request.workflow_id,
                len(steps) + 1,
            ),
            workflow_id=request.workflow_id,
            stage=stage,
            status=StrategyWorkflowStepStatus.COMPLETED,
            started_at=started_at,
            completed_at=effective_completed_at,
            summary=summary,
            component=component,
            decision=decision,
            reference_id=reference_id,
        )
    )
    @staticmethod
    def _execution_decision(
        request: StrategyWorkflowRequest,
    ) -> StrategyWorkflowDecision:
        if (
            request.environment
            is StrategyExecutionEnvironment.LIVE
        ):
            return StrategyWorkflowDecision.EXECUTE_LIVE

        return StrategyWorkflowDecision.EXECUTE_PAPER

    @staticmethod
    def _failed_gate(
        *,
        regime_status: RegimeDetectionStatus,
        coordination_status: AgentCoordinatorStatus,
        risk_status: PortfolioRiskStatus,
        rebalancing_status: RebalancingStatus,
    ) -> str | None:
        if regime_status is RegimeDetectionStatus.FAILED:
            return "market-regime-engine"

        if (
            coordination_status
            is AgentCoordinatorStatus.FAILED
        ):
            return "agent-coordinator"

        if risk_status is PortfolioRiskStatus.FAILED:
            return "portfolio-risk-manager"

        if rebalancing_status is RebalancingStatus.FAILED:
            return "portfolio-rebalancing-engine"

        return None

    @staticmethod
    def _normalize_warnings(
        warnings: tuple[str, ...],
    ) -> tuple[str, ...]:
        normalized: list[str] = []

        for warning in warnings:
            if not isinstance(warning, str):
                raise TypeError(
                    "every warning must be a string"
                )

            value = warning.strip()

            if not value:
                raise ValueError(
                    "warnings must not contain empty values"
                )

            normalized.append(value)

        return tuple(normalized)

    @staticmethod
    def _step_id(
        workflow_id: str,
        sequence_number: int,
    ) -> str:
        return (
            f"{workflow_id}-step-"
            f"{sequence_number:03d}"
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
        request: StrategyWorkflowRequest,
        regime_status: RegimeDetectionStatus,
        regime: MarketRegime,
        coordination_status: AgentCoordinatorStatus,
        coordinated_action: CoordinatedAction,
        risk_status: PortfolioRiskStatus,
        risk_decision: PortfolioRiskDecision,
        rebalancing_status: RebalancingStatus,
        rebalancing_decision: RebalancingDecision,
    ) -> None:
        if not isinstance(
            request,
            StrategyWorkflowRequest,
        ):
            raise TypeError(
                "request must be a StrategyWorkflowRequest"
            )

        if not isinstance(
            regime_status,
            RegimeDetectionStatus,
        ):
            raise TypeError(
                "regime_status must be a "
                "RegimeDetectionStatus"
            )

        if not isinstance(regime, MarketRegime):
            raise TypeError(
                "regime must be a MarketRegime"
            )

        if not isinstance(
            coordination_status,
            AgentCoordinatorStatus,
        ):
            raise TypeError(
                "coordination_status must be an "
                "AgentCoordinatorStatus"
            )

        if not isinstance(
            coordinated_action,
            CoordinatedAction,
        ):
            raise TypeError(
                "coordinated_action must be a "
                "CoordinatedAction"
            )

        if not isinstance(
            risk_status,
            PortfolioRiskStatus,
        ):
            raise TypeError(
                "risk_status must be a PortfolioRiskStatus"
            )

        if not isinstance(
            risk_decision,
            PortfolioRiskDecision,
        ):
            raise TypeError(
                "risk_decision must be a "
                "PortfolioRiskDecision"
            )

        if not isinstance(
            rebalancing_status,
            RebalancingStatus,
        ):
            raise TypeError(
                "rebalancing_status must be a "
                "RebalancingStatus"
            )

        if not isinstance(
            rebalancing_decision,
            RebalancingDecision,
        ):
            raise TypeError(
                "rebalancing_decision must be a "
                "RebalancingDecision"
            )