from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.strategy_orchestrator.orchestrator_models import (
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


NOW = datetime(
    2026,
    8,
    2,
    20,
    0,
    tzinfo=timezone.utc,
)


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


def step(
    step_id: str,
    stage: StrategyWorkflowStage,
    *,
    status: StrategyWorkflowStepStatus = (
        StrategyWorkflowStepStatus.COMPLETED
    ),
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    decision: StrategyWorkflowDecision | None = None,
) -> StrategyWorkflowStep:
    effective_start = (
        started_at
        if started_at is not None
        else NOW
    )

    effective_completed = completed_at

    if (
        effective_completed is None
        and status
        is not StrategyWorkflowStepStatus.PENDING
    ):
        effective_completed = (
            effective_start + timedelta(seconds=1)
        )

    return StrategyWorkflowStep(
        step_id=step_id,
        workflow_id="workflow-001",
        stage=stage,
        status=status,
        started_at=effective_start,
        completed_at=effective_completed,
        summary=f"{stage.value} completed.",
        component="strategy-orchestrator",
        decision=decision,
    )


def paper_plan() -> StrategyWorkflowPlan:
    steps = (
        step(
            "step-001",
            StrategyWorkflowStage.REQUEST_RECEIVED,
        ),
        step(
            "step-002",
            StrategyWorkflowStage.REGIME_EVALUATED,
        ),
        step(
            "step-003",
            StrategyWorkflowStage.AGENTS_COORDINATED,
        ),
        step(
            "step-004",
            StrategyWorkflowStage.RISK_EVALUATED,
        ),
        step(
            "step-005",
            StrategyWorkflowStage.EXECUTION_PLANNED,
            decision=(
                StrategyWorkflowDecision.EXECUTE_PAPER
            ),
        ),
    )

    return StrategyWorkflowPlan(
        plan_id="plan-001",
        workflow_id="workflow-001",
        environment=StrategyExecutionEnvironment.PAPER,
        decision=StrategyWorkflowDecision.EXECUTE_PAPER,
        current_stage=(
            StrategyWorkflowStage.EXECUTION_PLANNED
        ),
        steps=steps,
        created_at=NOW,
        terminal=False,
    )


def completed_performance_plan() -> StrategyWorkflowPlan:
    steps = (
        step(
            "step-001",
            StrategyWorkflowStage.REQUEST_RECEIVED,
        ),
        step(
            "step-002",
            StrategyWorkflowStage.REGIME_EVALUATED,
        ),
        step(
            "step-003",
            StrategyWorkflowStage.AGENTS_COORDINATED,
        ),
        step(
            "step-004",
            StrategyWorkflowStage.RISK_EVALUATED,
        ),
        step(
            "step-005",
            StrategyWorkflowStage.EXECUTION_PLANNED,
        ),
        step(
            "step-006",
            StrategyWorkflowStage.EXECUTION_COMPLETED,
        ),
        step(
            "step-007",
            StrategyWorkflowStage.AUDIT_COMPLETED,
        ),
        step(
            "step-008",
            StrategyWorkflowStage.PERFORMANCE_RECORDED,
            decision=(
                StrategyWorkflowDecision.EXECUTE_PAPER
            ),
        ),
    )

    return StrategyWorkflowPlan(
        plan_id="plan-001",
        workflow_id="workflow-001",
        environment=StrategyExecutionEnvironment.PAPER,
        decision=StrategyWorkflowDecision.EXECUTE_PAPER,
        current_stage=(
            StrategyWorkflowStage.PERFORMANCE_RECORDED
        ),
        steps=steps,
        created_at=NOW,
        terminal=True,
        completed_at=NOW + timedelta(minutes=1),
        execution_reference_id="execution-001",
        audit_reference_id="audit-001",
        performance_reference_id="performance-001",
    )


def test_workflow_request() -> None:
    value = request()

    assert value.workflow_id == "workflow-001"
    assert (
        value.environment
        is StrategyExecutionEnvironment.PAPER
    )


def test_request_text_is_normalized() -> None:
    value = StrategyWorkflowRequest(
        workflow_id="  workflow-001  ",
        correlation_id="  correlation-001  ",
        strategy_id="  momentum-001  ",
        portfolio_id="  portfolio-001  ",
        account_id="  account-001  ",
        environment=StrategyExecutionEnvironment.PAPER,
        requested_at=NOW,
    )

    assert value.workflow_id == "workflow-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "momentum-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.account_id == "account-001"


@pytest.mark.parametrize(
    "field_name",
    [
        "workflow_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "account_id",
    ],
)
def test_request_identifiers_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "workflow_id": "workflow-001",
        "correlation_id": "correlation-001",
        "strategy_id": "momentum-001",
        "portfolio_id": "portfolio-001",
        "account_id": "account-001",
        "environment": (
            StrategyExecutionEnvironment.PAPER
        ),
        "requested_at": NOW,
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        StrategyWorkflowRequest(**arguments)


def test_live_request_requires_confirmation() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "live workflows require explicit "
            "live-trading confirmation"
        ),
    ):
        StrategyWorkflowRequest(
            workflow_id="workflow-001",
            correlation_id="correlation-001",
            strategy_id="momentum-001",
            portfolio_id="portfolio-001",
            account_id="account-001",
            environment=StrategyExecutionEnvironment.LIVE,
            requested_at=NOW,
        )


def test_confirmed_live_request() -> None:
    value = request(
        environment=StrategyExecutionEnvironment.LIVE
    )

    assert value.live_trading_confirmed is True


def test_request_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="requested_at must be timezone-aware",
    ):
        StrategyWorkflowRequest(
            workflow_id="workflow-001",
            correlation_id="correlation-001",
            strategy_id="momentum-001",
            portfolio_id="portfolio-001",
            account_id="account-001",
            environment=StrategyExecutionEnvironment.PAPER,
            requested_at=datetime(2026, 8, 2),
        )


def test_request_metadata_is_normalized() -> None:
    value = StrategyWorkflowRequest(
        workflow_id="workflow-001",
        correlation_id="correlation-001",
        strategy_id="momentum-001",
        portfolio_id="portfolio-001",
        account_id="account-001",
        environment=StrategyExecutionEnvironment.PAPER,
        requested_at=NOW,
        metadata=[
            (
                "  source  ",
                "  dashboard  ",
            ),
        ],
    )

    assert value.metadata == (
        (
            "source",
            "dashboard",
        ),
    )


def test_completed_workflow_step() -> None:
    value = step(
        "step-001",
        StrategyWorkflowStage.REQUEST_RECEIVED,
    )

    assert (
        value.status
        is StrategyWorkflowStepStatus.COMPLETED
    )
    assert value.completed_at is not None


def test_pending_step_has_no_completed_at() -> None:
    value = step(
        "step-001",
        StrategyWorkflowStage.REQUEST_RECEIVED,
        status=StrategyWorkflowStepStatus.PENDING,
    )

    assert value.completed_at is None


def test_pending_step_rejects_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "pending steps must not include completed_at"
        ),
    ):
        step(
            "step-001",
            StrategyWorkflowStage.REQUEST_RECEIVED,
            status=StrategyWorkflowStepStatus.PENDING,
            completed_at=NOW + timedelta(seconds=1),
        )


def test_completed_step_requires_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-pending steps must include completed_at"
        ),
    ):
        StrategyWorkflowStep(
            step_id="step-001",
            workflow_id="workflow-001",
            stage=StrategyWorkflowStage.REQUEST_RECEIVED,
            status=StrategyWorkflowStepStatus.COMPLETED,
            started_at=NOW,
            completed_at=None,
            summary="Request received.",
            component="orchestrator",
        )


def test_failed_step_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed steps must include an error",
    ):
        StrategyWorkflowStep(
            step_id="step-001",
            workflow_id="workflow-001",
            stage=StrategyWorkflowStage.FAILED,
            status=StrategyWorkflowStepStatus.FAILED,
            started_at=NOW,
            completed_at=NOW + timedelta(seconds=1),
            summary="Workflow failed.",
            component="orchestrator",
        )


def test_non_failed_step_rejects_error() -> None:
    with pytest.raises(
        ValueError,
        match="only failed steps may include an error",
    ):
        StrategyWorkflowStep(
            step_id="step-001",
            workflow_id="workflow-001",
            stage=StrategyWorkflowStage.REQUEST_RECEIVED,
            status=StrategyWorkflowStepStatus.COMPLETED,
            started_at=NOW,
            completed_at=NOW + timedelta(seconds=1),
            summary="Request received.",
            component="orchestrator",
            error="Unexpected failure.",
        )


def test_paper_workflow_plan() -> None:
    value = paper_plan()

    assert (
        value.decision
        is StrategyWorkflowDecision.EXECUTE_PAPER
    )
    assert value.terminal is False
    assert len(value.steps) == 5


def test_plan_steps_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="steps must not be empty",
    ):
        StrategyWorkflowPlan(
            plan_id="plan-001",
            workflow_id="workflow-001",
            environment=StrategyExecutionEnvironment.PAPER,
            decision=StrategyWorkflowDecision.NO_ACTION,
            current_stage=(
                StrategyWorkflowStage.REQUEST_RECEIVED
            ),
            steps=(),
            created_at=NOW,
            terminal=False,
        )


def test_step_workflow_id_must_match_plan() -> None:
    bad_step = StrategyWorkflowStep(
        step_id="step-001",
        workflow_id="different",
        stage=StrategyWorkflowStage.REQUEST_RECEIVED,
        status=StrategyWorkflowStepStatus.COMPLETED,
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
        summary="Request received.",
        component="orchestrator",
    )

    with pytest.raises(
        ValueError,
        match=(
            "step workflow_id must match the plan"
        ),
    ):
        StrategyWorkflowPlan(
            plan_id="plan-001",
            workflow_id="workflow-001",
            environment=StrategyExecutionEnvironment.PAPER,
            decision=StrategyWorkflowDecision.NO_ACTION,
            current_stage=(
                StrategyWorkflowStage.REQUEST_RECEIVED
            ),
            steps=(bad_step,),
            created_at=NOW,
            terminal=False,
        )


def test_step_ids_must_be_unique() -> None:
    duplicate = step(
        "step-001",
        StrategyWorkflowStage.REQUEST_RECEIVED,
    )

    with pytest.raises(
        ValueError,
        match="step_id values must be unique",
    ):
        StrategyWorkflowPlan(
            plan_id="plan-001",
            workflow_id="workflow-001",
            environment=StrategyExecutionEnvironment.PAPER,
            decision=StrategyWorkflowDecision.NO_ACTION,
            current_stage=(
                StrategyWorkflowStage.REQUEST_RECEIVED
            ),
            steps=(duplicate, duplicate),
            created_at=NOW,
            terminal=False,
        )


def test_workflow_stages_must_be_ordered() -> None:
    with pytest.raises(
        ValueError,
        match="workflow stages must be ordered",
    ):
        StrategyWorkflowPlan(
            plan_id="plan-001",
            workflow_id="workflow-001",
            environment=StrategyExecutionEnvironment.PAPER,
            decision=StrategyWorkflowDecision.NO_ACTION,
            current_stage=(
                StrategyWorkflowStage.REGIME_EVALUATED
            ),
            steps=(
                step(
                    "step-001",
                    StrategyWorkflowStage.AGENTS_COORDINATED,
                ),
                step(
                    "step-002",
                    StrategyWorkflowStage.REGIME_EVALUATED,
                ),
            ),
            created_at=NOW,
            terminal=False,
        )


def test_current_stage_must_match_final_step() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "current_stage must match the final step"
        ),
    ):
        StrategyWorkflowPlan(
            plan_id="plan-001",
            workflow_id="workflow-001",
            environment=StrategyExecutionEnvironment.PAPER,
            decision=StrategyWorkflowDecision.NO_ACTION,
            current_stage=(
                StrategyWorkflowStage.REGIME_EVALUATED
            ),
            steps=(
                step(
                    "step-001",
                    StrategyWorkflowStage.REQUEST_RECEIVED,
                ),
            ),
            created_at=NOW,
            terminal=False,
        )


def test_terminal_plan_requires_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "terminal plans must include completed_at"
        ),
    ):
        StrategyWorkflowPlan(
            plan_id="plan-001",
            workflow_id="workflow-001",
            environment=StrategyExecutionEnvironment.PAPER,
            decision=(
                StrategyWorkflowDecision.REVIEW_REQUIRED
            ),
            current_stage=(
                StrategyWorkflowStage.REVIEW_REQUIRED
            ),
            steps=(
                step(
                    "step-001",
                    StrategyWorkflowStage.REVIEW_REQUIRED,
                ),
            ),
            created_at=NOW,
            terminal=True,
        )


def test_terminal_stage_requires_terminal_true() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "terminal stages require terminal=True"
        ),
    ):
        StrategyWorkflowPlan(
            plan_id="plan-001",
            workflow_id="workflow-001",
            environment=StrategyExecutionEnvironment.PAPER,
            decision=(
                StrategyWorkflowDecision.REVIEW_REQUIRED
            ),
            current_stage=(
                StrategyWorkflowStage.REVIEW_REQUIRED
            ),
            steps=(
                step(
                    "step-001",
                    StrategyWorkflowStage.REVIEW_REQUIRED,
                ),
            ),
            created_at=NOW,
            terminal=False,
        )


def test_execute_paper_requires_paper_environment() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "EXECUTE_PAPER requires PAPER environment"
        ),
    ):
        StrategyWorkflowPlan(
            plan_id="plan-001",
            workflow_id="workflow-001",
            environment=StrategyExecutionEnvironment.LIVE,
            decision=StrategyWorkflowDecision.EXECUTE_PAPER,
            current_stage=(
                StrategyWorkflowStage.EXECUTION_PLANNED
            ),
            steps=(
                step(
                    "step-001",
                    StrategyWorkflowStage.EXECUTION_PLANNED,
                ),
            ),
            created_at=NOW,
            terminal=False,
        )


def test_execute_live_requires_live_environment() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "EXECUTE_LIVE requires LIVE environment"
        ),
    ):
        StrategyWorkflowPlan(
            plan_id="plan-001",
            workflow_id="workflow-001",
            environment=StrategyExecutionEnvironment.PAPER,
            decision=StrategyWorkflowDecision.EXECUTE_LIVE,
            current_stage=(
                StrategyWorkflowStage.EXECUTION_PLANNED
            ),
            steps=(
                step(
                    "step-001",
                    StrategyWorkflowStage.EXECUTION_PLANNED,
                ),
            ),
            created_at=NOW,
            terminal=False,
        )


def test_execution_completed_requires_reference() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed execution stages require "
            "execution_reference_id"
        ),
    ):
        StrategyWorkflowPlan(
            plan_id="plan-001",
            workflow_id="workflow-001",
            environment=StrategyExecutionEnvironment.PAPER,
            decision=StrategyWorkflowDecision.EXECUTE_PAPER,
            current_stage=(
                StrategyWorkflowStage.EXECUTION_COMPLETED
            ),
            steps=(
                step(
                    "step-001",
                    StrategyWorkflowStage.EXECUTION_COMPLETED,
                ),
            ),
            created_at=NOW,
            terminal=False,
        )


def test_completed_performance_plan() -> None:
    value = completed_performance_plan()

    assert value.terminal is True
    assert (
        value.current_stage
        is StrategyWorkflowStage.PERFORMANCE_RECORDED
    )
    assert (
        value.performance_reference_id
        == "performance-001"
    )


def test_strategy_workflow_report() -> None:
    value = StrategyWorkflowReport(
        status=StrategyOrchestratorStatus.COMPLETED,
        request=request(),
        plan=completed_performance_plan(),
        decision=StrategyWorkflowDecision.EXECUTE_PAPER,
        completed_at=NOW + timedelta(minutes=2),
        recommendation=(
            "Workflow completed successfully."
        ),
    )

    assert (
        value.status
        is StrategyOrchestratorStatus.COMPLETED
    )
    assert value.plan is not None


def test_report_plan_workflow_id_must_match_request() -> None:
    bad_plan = StrategyWorkflowPlan(
        plan_id="plan-001",
        workflow_id="different",
        environment=StrategyExecutionEnvironment.PAPER,
        decision=StrategyWorkflowDecision.NO_ACTION,
        current_stage=(
            StrategyWorkflowStage.REQUEST_RECEIVED
        ),
        steps=(
            StrategyWorkflowStep(
                step_id="step-001",
                workflow_id="different",
                stage=(
                    StrategyWorkflowStage.REQUEST_RECEIVED
                ),
                status=(
                    StrategyWorkflowStepStatus.COMPLETED
                ),
                started_at=NOW,
                completed_at=NOW + timedelta(seconds=1),
                summary="Request received.",
                component="orchestrator",
            ),
        ),
        created_at=NOW,
        terminal=False,
    )

    with pytest.raises(
        ValueError,
        match=(
            "plan workflow_id must match the request"
        ),
    ):
        StrategyWorkflowReport(
            status=StrategyOrchestratorStatus.COMPLETED,
            request=request(),
            plan=bad_plan,
            decision=StrategyWorkflowDecision.NO_ACTION,
            completed_at=NOW + timedelta(minutes=1),
            recommendation="No action.",
        )


def test_report_decision_must_match_plan() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "report decision must match the plan"
        ),
    ):
        StrategyWorkflowReport(
            status=StrategyOrchestratorStatus.COMPLETED,
            request=request(),
            plan=paper_plan(),
            decision=(
                StrategyWorkflowDecision.REVIEW_REQUIRED
            ),
            completed_at=NOW + timedelta(minutes=1),
            recommendation="Review required.",
        )


def test_completed_report_requires_plan() -> None:
    with pytest.raises(
        ValueError,
        match="completed reports must include a plan",
    ):
        StrategyWorkflowReport(
            status=StrategyOrchestratorStatus.COMPLETED,
            request=request(),
            plan=None,
            decision=StrategyWorkflowDecision.NO_ACTION,
            completed_at=NOW + timedelta(minutes=1),
            recommendation="No action.",
        )


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        StrategyWorkflowReport(
            status=StrategyOrchestratorStatus.FAILED,
            request=request(),
            plan=None,
            decision=StrategyWorkflowDecision.REJECT,
            completed_at=NOW + timedelta(minutes=1),
            recommendation="Workflow failed.",
        )


def test_completed_report_cannot_include_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only failed reports may include an error"
        ),
    ):
        StrategyWorkflowReport(
            status=StrategyOrchestratorStatus.COMPLETED,
            request=request(),
            plan=paper_plan(),
            decision=StrategyWorkflowDecision.EXECUTE_PAPER,
            completed_at=NOW + timedelta(minutes=1),
            recommendation="Execute paper workflow.",
            error="Unexpected failure.",
        )


def test_report_warnings_are_tuples() -> None:
    value = StrategyWorkflowReport(
        status=StrategyOrchestratorStatus.COMPLETED,
        request=request(),
        plan=paper_plan(),
        decision=StrategyWorkflowDecision.EXECUTE_PAPER,
        completed_at=NOW + timedelta(minutes=1),
        recommendation="Execute paper workflow.",
        warnings=["Workflow warning."],
    )

    assert value.warnings == (
        "Workflow warning.",
    )


def test_models_are_immutable() -> None:
    value = request()

    with pytest.raises(FrozenInstanceError):
        value.strategy_id = "changed"