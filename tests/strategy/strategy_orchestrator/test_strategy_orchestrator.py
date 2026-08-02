from datetime import datetime, timedelta, timezone

import pytest

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
from app.strategy.strategy_orchestrator.orchestrator_models import (
    StrategyExecutionEnvironment,
    StrategyOrchestratorStatus,
    StrategyWorkflowDecision,
    StrategyWorkflowRequest,
    StrategyWorkflowStage,
)
from app.strategy.strategy_orchestrator.strategy_orchestrator import (
    EnterpriseStrategyOrchestrator,
)


NOW = datetime(
    2026,
    8,
    2,
    21,
    0,
    tzinfo=timezone.utc,
)


class IncrementingClock:
    def __init__(self) -> None:
        self.value = NOW

    def __call__(self) -> datetime:
        current = self.value
        self.value += timedelta(seconds=1)
        return current


def request(
    *,
    environment: StrategyExecutionEnvironment = (
        StrategyExecutionEnvironment.PAPER
    ),
) -> StrategyWorkflowRequest:
    return StrategyWorkflowRequest(
        workflow_id="workflow-001",
        correlation_id="correlation-001",
        strategy_id="momentum-001",
        portfolio_id="portfolio-001",
        account_id="account-001",
        environment=environment,
        requested_at=NOW,
        live_trading_confirmed=(
            environment
            is StrategyExecutionEnvironment.LIVE
        ),
    )


def engine() -> EnterpriseStrategyOrchestrator:
    return EnterpriseStrategyOrchestrator(
        clock=IncrementingClock(),
    )


def inputs() -> dict:
    return {
        "request": request(),
        "regime_status": (
            RegimeDetectionStatus.COMPLETED
        ),
        "regime": MarketRegime.BULL,
        "coordination_status": (
            AgentCoordinatorStatus.COMPLETED
        ),
        "coordinated_action": CoordinatedAction.EXECUTE,
        "risk_status": PortfolioRiskStatus.COMPLETED,
        "risk_decision": PortfolioRiskDecision.APPROVE,
        "rebalancing_status": (
            RebalancingStatus.COMPLETED
        ),
        "rebalancing_decision": (
            RebalancingDecision.APPROVE
        ),
    }


def orchestrate(**overrides):
    values = inputs()
    values.update(overrides)

    return engine().orchestrate(**values)


def test_approved_paper_workflow_is_planned() -> None:
    report = orchestrate()

    assert (
        report.status
        is StrategyOrchestratorStatus.PENDING
    )
    assert (
        report.decision
        is StrategyWorkflowDecision.EXECUTE_PAPER
    )
    assert report.plan is not None
    assert (
        report.plan.current_stage
        is StrategyWorkflowStage.EXECUTION_PLANNED
    )


def test_approved_live_workflow_is_planned() -> None:
    report = orchestrate(
        request=request(
            environment=StrategyExecutionEnvironment.LIVE
        )
    )

    assert (
        report.decision
        is StrategyWorkflowDecision.EXECUTE_LIVE
    )
    assert report.plan is not None
    assert (
        report.plan.environment
        is StrategyExecutionEnvironment.LIVE
    )


def test_unknown_regime_requires_review() -> None:
    report = orchestrate(
        regime=MarketRegime.UNKNOWN
    )

    assert (
        report.decision
        is StrategyWorkflowDecision.REVIEW_REQUIRED
    )
    assert (
        report.status
        is StrategyOrchestratorStatus.COMPLETED
    )
    assert report.plan is not None
    assert (
        report.plan.current_stage
        is StrategyWorkflowStage.REVIEW_REQUIRED
    )


def test_regime_failure_fails_workflow() -> None:
    report = orchestrate(
        regime_status=RegimeDetectionStatus.FAILED
    )

    assert (
        report.status
        is StrategyOrchestratorStatus.FAILED
    )
    assert report.error is not None
    assert "market-regime-engine" in report.error


def test_coordination_failure_fails_workflow() -> None:
    report = orchestrate(
        coordination_status=(
            AgentCoordinatorStatus.FAILED
        )
    )

    assert (
        report.status
        is StrategyOrchestratorStatus.FAILED
    )
    assert "agent-coordinator" in report.error


def test_risk_failure_fails_workflow() -> None:
    report = orchestrate(
        risk_status=PortfolioRiskStatus.FAILED
    )

    assert (
        report.status
        is StrategyOrchestratorStatus.FAILED
    )
    assert "portfolio-risk-manager" in report.error


def test_rebalancing_failure_fails_workflow() -> None:
    report = orchestrate(
        rebalancing_status=RebalancingStatus.FAILED
    )

    assert (
        report.status
        is StrategyOrchestratorStatus.FAILED
    )
    assert "portfolio-rebalancing-engine" in report.error


def test_coordinator_block_rejects_workflow() -> None:
    report = orchestrate(
        coordinated_action=CoordinatedAction.BLOCK
    )

    assert (
        report.decision
        is StrategyWorkflowDecision.REJECT
    )
    assert report.plan is not None
    assert (
        report.plan.current_stage
        is StrategyWorkflowStage.REJECTED
    )


def test_coordinator_review_requires_review() -> None:
    report = orchestrate(
        coordinated_action=(
            CoordinatedAction.REVIEW_REQUIRED
        )
    )

    assert (
        report.decision
        is StrategyWorkflowDecision.REVIEW_REQUIRED
    )


def test_risk_rejection_rejects_workflow() -> None:
    report = orchestrate(
        risk_decision=PortfolioRiskDecision.REJECT
    )

    assert (
        report.decision
        is StrategyWorkflowDecision.REJECT
    )
    assert "risk" in report.recommendation.lower()


def test_risk_review_requires_review() -> None:
    report = orchestrate(
        risk_decision=(
            PortfolioRiskDecision.REVIEW_REQUIRED
        )
    )

    assert (
        report.decision
        is StrategyWorkflowDecision.REVIEW_REQUIRED
    )


def test_rebalancing_rejection_rejects_workflow() -> None:
    report = orchestrate(
        rebalancing_decision=(
            RebalancingDecision.REJECT
        )
    )

    assert (
        report.decision
        is StrategyWorkflowDecision.REJECT
    )


def test_rebalancing_review_requires_review() -> None:
    report = orchestrate(
        rebalancing_decision=(
            RebalancingDecision.REVIEW_REQUIRED
        )
    )

    assert (
        report.decision
        is StrategyWorkflowDecision.REVIEW_REQUIRED
    )


def test_execution_reference_advances_stage() -> None:
    report = orchestrate(
        execution_reference_id="execution-001"
    )

    assert report.plan is not None
    assert (
        report.plan.current_stage
        is StrategyWorkflowStage.EXECUTION_COMPLETED
    )
    assert (
        report.plan.execution_reference_id
        == "execution-001"
    )


def test_audit_reference_advances_stage() -> None:
    report = orchestrate(
        execution_reference_id="execution-001",
        audit_reference_id="audit-001",
    )

    assert report.plan is not None
    assert (
        report.plan.current_stage
        is StrategyWorkflowStage.AUDIT_COMPLETED
    )
    assert report.plan.audit_reference_id == "audit-001"


def test_complete_references_complete_workflow() -> None:
    report = orchestrate(
        execution_reference_id="execution-001",
        audit_reference_id="audit-001",
        performance_reference_id="performance-001",
    )

    assert (
        report.status
        is StrategyOrchestratorStatus.COMPLETED
    )
    assert report.plan is not None
    assert report.plan.terminal is True
    assert (
        report.plan.current_stage
        is StrategyWorkflowStage.PERFORMANCE_RECORDED
    )


def test_completed_workflow_preserves_references() -> None:
    report = orchestrate(
        execution_reference_id="execution-001",
        audit_reference_id="audit-001",
        performance_reference_id="performance-001",
    )

    assert report.plan is not None
    assert (
        report.plan.execution_reference_id
        == "execution-001"
    )
    assert report.plan.audit_reference_id == "audit-001"
    assert (
        report.plan.performance_reference_id
        == "performance-001"
    )


def test_workflow_steps_are_ordered() -> None:
    report = orchestrate(
        execution_reference_id="execution-001",
        audit_reference_id="audit-001",
        performance_reference_id="performance-001",
    )

    assert report.plan is not None

    assert tuple(
        step.stage
        for step in report.plan.steps
    ) == (
        StrategyWorkflowStage.REQUEST_RECEIVED,
        StrategyWorkflowStage.REGIME_EVALUATED,
        StrategyWorkflowStage.AGENTS_COORDINATED,
        StrategyWorkflowStage.PORTFOLIO_OPTIMIZED,
        StrategyWorkflowStage.RISK_EVALUATED,
        StrategyWorkflowStage.REBALANCE_EVALUATED,
        StrategyWorkflowStage.EXECUTION_PLANNED,
        StrategyWorkflowStage.EXECUTION_COMPLETED,
        StrategyWorkflowStage.AUDIT_COMPLETED,
        StrategyWorkflowStage.PERFORMANCE_RECORDED,
    )


def test_step_ids_are_deterministic() -> None:
    report = orchestrate()

    assert report.plan is not None

    assert tuple(
        step.step_id
        for step in report.plan.steps
    ) == (
        "workflow-001-step-001",
        "workflow-001-step-002",
        "workflow-001-step-003",
        "workflow-001-step-004",
        "workflow-001-step-005",
        "workflow-001-step-006",
        "workflow-001-step-007",
    )


def test_warnings_are_preserved() -> None:
    report = orchestrate(
        warnings=(
            "Regime confidence is moderate.",
            "Portfolio concentration is elevated.",
        )
    )

    assert report.warnings == (
        "Regime confidence is moderate.",
        "Portfolio concentration is elevated.",
    )


def test_warning_text_is_normalized() -> None:
    report = orchestrate(
        warnings=("  Workflow warning.  ",)
    )

    assert report.warnings == (
        "Workflow warning.",
    )


def test_empty_warning_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        orchestrate(
            warnings=("   ",)
        )


def test_non_string_warning_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        orchestrate(
            warnings=(object(),)
        )


def test_non_iterable_warnings_raise_type_error() -> None:
    with pytest.raises(
        TypeError,
        match="warnings must be iterable",
    ):
        orchestrate(
            warnings=None
        )


@pytest.mark.parametrize(
    (
        "argument_name",
        "invalid_value",
        "message",
    ),
    [
        (
            "request",
            object(),
            "request must be a StrategyWorkflowRequest",
        ),
        (
            "regime_status",
            object(),
            "regime_status must be a RegimeDetectionStatus",
        ),
        (
            "regime",
            object(),
            "regime must be a MarketRegime",
        ),
        (
            "coordination_status",
            object(),
            "coordination_status must be an "
            "AgentCoordinatorStatus",
        ),
        (
            "coordinated_action",
            object(),
            "coordinated_action must be a CoordinatedAction",
        ),
        (
            "risk_status",
            object(),
            "risk_status must be a PortfolioRiskStatus",
        ),
        (
            "risk_decision",
            object(),
            "risk_decision must be a "
            "PortfolioRiskDecision",
        ),
        (
            "rebalancing_status",
            object(),
            "rebalancing_status must be a "
            "RebalancingStatus",
        ),
        (
            "rebalancing_decision",
            object(),
            "rebalancing_decision must be a "
            "RebalancingDecision",
        ),
    ],
)
def test_inputs_are_validated(
    argument_name,
    invalid_value,
    message,
) -> None:
    values = inputs()
    values[argument_name] = invalid_value

    with pytest.raises(
        TypeError,
        match=message,
    ):
        engine().orchestrate(**values)


def test_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterpriseStrategyOrchestrator(
            clock=NOW
        )


def test_clock_must_return_datetime() -> None:
    value = EnterpriseStrategyOrchestrator(
        clock=lambda: "now"
    )

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        value.orchestrate(**inputs())


def test_clock_must_return_timezone_aware_datetime() -> None:
    value = EnterpriseStrategyOrchestrator(
        clock=lambda: datetime(2026, 8, 2)
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        value.orchestrate(**inputs())