from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.workflow_engine.workflow_models import (
    WorkflowDecision,
    WorkflowExecutionRecord,
    WorkflowFailurePolicy,
    WorkflowReport,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowStepDefinition,
    WorkflowStepResult,
    WorkflowStepStatus,
)


NOW = datetime(
    2026,
    8,
    3,
    17,
    0,
    tzinfo=timezone.utc,
)


def request() -> WorkflowRequest:
    return WorkflowRequest(
        workflow_id="workflow-001",
        correlation_id="correlation-001",
        workflow_type="trade-execution",
        requested_by="strategy-orchestrator",
        requested_at=NOW,
        priority=1,
    )


def definition(
    step_id: str = "step-001",
    *,
    position: int = 1,
    failure_policy: WorkflowFailurePolicy = (
        WorkflowFailurePolicy.FAIL_FAST
    ),
    max_attempts: int = 1,
    compensation_step_id: str | None = None,
) -> WorkflowStepDefinition:
    return WorkflowStepDefinition(
        step_id=step_id,
        name=f"Workflow step {position}",
        position=position,
        component="workflow-component",
        failure_policy=failure_policy,
        max_attempts=max_attempts,
        compensation_step_id=compensation_step_id,
    )


def completed_result(
    step_id: str = "step-001",
    *,
    result_id: str = "result-001",
) -> WorkflowStepResult:
    return WorkflowStepResult(
        result_id=result_id,
        workflow_id="workflow-001",
        step_id=step_id,
        status=WorkflowStepStatus.COMPLETED,
        attempt_number=1,
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
        message="Step completed.",
    )


def running_record() -> WorkflowExecutionRecord:
    return WorkflowExecutionRecord(
        workflow_id="workflow-001",
        status=WorkflowStatus.RUNNING,
        decision=WorkflowDecision.CONTINUE,
        definitions=(
            definition(),
            definition(
                "step-002",
                position=2,
            ),
        ),
        results=(
            completed_result(),
        ),
        current_step_id="step-002",
        started_at=NOW,
    )


def completed_record() -> WorkflowExecutionRecord:
    return WorkflowExecutionRecord(
        workflow_id="workflow-001",
        status=WorkflowStatus.COMPLETED,
        decision=WorkflowDecision.COMPLETE,
        definitions=(
            definition(),
        ),
        results=(
            completed_result(),
        ),
        current_step_id=None,
        started_at=NOW,
        completed_at=NOW + timedelta(minutes=1),
    )


def test_workflow_request() -> None:
    value = request()

    assert value.workflow_id == "workflow-001"
    assert value.priority == 1


def test_request_text_is_normalized() -> None:
    value = WorkflowRequest(
        workflow_id="  workflow-001  ",
        correlation_id="  correlation-001  ",
        workflow_type="  trade-execution  ",
        requested_by="  orchestrator  ",
        requested_at=NOW,
    )

    assert value.workflow_id == "workflow-001"
    assert value.requested_by == "orchestrator"


@pytest.mark.parametrize(
    "field_name",
    [
        "workflow_id",
        "correlation_id",
        "workflow_type",
        "requested_by",
    ],
)
def test_request_identifiers_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "workflow_id": "workflow-001",
        "correlation_id": "correlation-001",
        "workflow_type": "trade-execution",
        "requested_by": "orchestrator",
        "requested_at": NOW,
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        WorkflowRequest(**arguments)


def test_requested_at_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="requested_at must be timezone-aware",
    ):
        WorkflowRequest(
            workflow_id="workflow-001",
            correlation_id="correlation-001",
            workflow_type="trade-execution",
            requested_by="orchestrator",
            requested_at=datetime(2026, 8, 3),
        )


def test_priority_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="priority must not be negative",
    ):
        WorkflowRequest(
            workflow_id="workflow-001",
            correlation_id="correlation-001",
            workflow_type="trade-execution",
            requested_by="orchestrator",
            requested_at=NOW,
            priority=-1,
        )


def test_metadata_is_normalized() -> None:
    value = WorkflowRequest(
        workflow_id="workflow-001",
        correlation_id="correlation-001",
        workflow_type="trade-execution",
        requested_by="orchestrator",
        requested_at=NOW,
        metadata=[
            (
                "  source  ",
                "  dashboard  ",
            ),
        ],
    )

    assert value.metadata == (
        ("source", "dashboard"),
    )


def test_metadata_keys_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        WorkflowRequest(
            workflow_id="workflow-001",
            correlation_id="correlation-001",
            workflow_type="trade-execution",
            requested_by="orchestrator",
            requested_at=NOW,
            metadata=(
                ("source", "one"),
                ("source", "two"),
            ),
        )


def test_workflow_step_definition() -> None:
    value = definition()

    assert value.step_id == "step-001"
    assert value.position == 1


def test_step_position_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="position must be greater than zero",
    ):
        definition(position=0)


def test_max_attempts_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="max_attempts must be greater than zero",
    ):
        definition(max_attempts=0)


def test_retry_policy_requires_multiple_attempts() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "retry steps must allow at least two attempts"
        ),
    ):
        definition(
            failure_policy=WorkflowFailurePolicy.RETRY,
            max_attempts=1,
        )


def test_valid_retry_definition() -> None:
    value = definition(
        failure_policy=WorkflowFailurePolicy.RETRY,
        max_attempts=3,
    )

    assert value.max_attempts == 3


def test_compensation_policy_requires_step() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "compensating steps must include "
            "compensation_step_id"
        ),
    ):
        definition(
            failure_policy=(
                WorkflowFailurePolicy.COMPENSATE
            ),
        )


def test_compensation_step_must_differ() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "compensation_step_id must differ from step_id"
        ),
    ):
        definition(
            failure_policy=(
                WorkflowFailurePolicy.COMPENSATE
            ),
            compensation_step_id="step-001",
        )


def test_completed_step_result() -> None:
    value = completed_result()

    assert value.status is WorkflowStepStatus.COMPLETED
    assert value.completed_at is not None


def test_running_result_has_no_completed_at() -> None:
    value = WorkflowStepResult(
        result_id="result-001",
        workflow_id="workflow-001",
        step_id="step-001",
        status=WorkflowStepStatus.RUNNING,
        attempt_number=1,
        started_at=NOW,
        completed_at=None,
        message="Step running.",
    )

    assert value.completed_at is None


def test_running_result_rejects_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-terminal step results must not include "
            "completed_at"
        ),
    ):
        WorkflowStepResult(
            result_id="result-001",
            workflow_id="workflow-001",
            step_id="step-001",
            status=WorkflowStepStatus.RUNNING,
            attempt_number=1,
            started_at=NOW,
            completed_at=NOW,
            message="Step running.",
        )


def test_terminal_result_requires_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "terminal step results must include completed_at"
        ),
    ):
        WorkflowStepResult(
            result_id="result-001",
            workflow_id="workflow-001",
            step_id="step-001",
            status=WorkflowStepStatus.COMPLETED,
            attempt_number=1,
            started_at=NOW,
            completed_at=None,
            message="Step completed.",
        )


def test_failed_result_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed step results must include an error"
        ),
    ):
        WorkflowStepResult(
            result_id="result-001",
            workflow_id="workflow-001",
            step_id="step-001",
            status=WorkflowStepStatus.FAILED,
            attempt_number=1,
            started_at=NOW,
            completed_at=NOW,
            message="Step failed.",
        )


def test_failed_result() -> None:
    value = WorkflowStepResult(
        result_id="result-001",
        workflow_id="workflow-001",
        step_id="step-001",
        status=WorkflowStepStatus.FAILED,
        attempt_number=1,
        started_at=NOW,
        completed_at=NOW,
        message="Step failed.",
        error="Execution error.",
    )

    assert value.error == "Execution error."


def test_compensated_result_requires_reference() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "compensated results must include "
            "compensated_step_id"
        ),
    ):
        WorkflowStepResult(
            result_id="result-001",
            workflow_id="workflow-001",
            step_id="step-002",
            status=WorkflowStepStatus.COMPENSATED,
            attempt_number=1,
            started_at=NOW,
            completed_at=NOW,
            message="Compensation completed.",
        )


def test_running_execution_record() -> None:
    value = running_record()

    assert value.status is WorkflowStatus.RUNNING
    assert value.current_step_id == "step-002"


def test_completed_execution_record() -> None:
    value = completed_record()

    assert value.status is WorkflowStatus.COMPLETED
    assert value.current_step_id is None


def test_definitions_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="definitions must not be empty",
    ):
        WorkflowExecutionRecord(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.CONTINUE,
            definitions=(),
            results=(),
            current_step_id=None,
            started_at=NOW,
        )


def test_step_ids_must_be_unique() -> None:
    duplicate = definition()

    with pytest.raises(
        ValueError,
        match="step_id values must be unique",
    ):
        WorkflowExecutionRecord(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.CONTINUE,
            definitions=(duplicate, duplicate),
            results=(),
            current_step_id="step-001",
            started_at=NOW,
        )


def test_step_positions_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="step positions must be unique",
    ):
        WorkflowExecutionRecord(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.CONTINUE,
            definitions=(
                definition("step-001", position=1),
                definition("step-002", position=1),
            ),
            results=(),
            current_step_id="step-001",
            started_at=NOW,
        )


def test_definitions_must_be_ordered() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "step definitions must be ordered by position"
        ),
    ):
        WorkflowExecutionRecord(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.CONTINUE,
            definitions=(
                definition("step-002", position=2),
                definition("step-001", position=1),
            ),
            results=(),
            current_step_id="step-001",
            started_at=NOW,
        )


def test_result_must_reference_known_step() -> None:
    unknown_result = completed_result(
        step_id="unknown"
    )

    with pytest.raises(
        ValueError,
        match=(
            "every result must reference a known step"
        ),
    ):
        WorkflowExecutionRecord(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.CONTINUE,
            definitions=(definition(),),
            results=(unknown_result,),
            current_step_id="step-001",
            started_at=NOW,
        )


def test_current_step_must_be_known() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "current_step_id must reference a known step"
        ),
    ):
        WorkflowExecutionRecord(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.CONTINUE,
            definitions=(definition(),),
            results=(),
            current_step_id="unknown",
            started_at=NOW,
        )


def test_terminal_workflow_requires_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "terminal workflows must include completed_at"
        ),
    ):
        WorkflowExecutionRecord(
            workflow_id="workflow-001",
            status=WorkflowStatus.COMPLETED,
            decision=WorkflowDecision.COMPLETE,
            definitions=(definition(),),
            results=(completed_result(),),
            current_step_id=None,
            started_at=NOW,
        )


def test_terminal_workflow_rejects_current_step() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "terminal workflows must not include "
            "current_step_id"
        ),
    ):
        WorkflowExecutionRecord(
            workflow_id="workflow-001",
            status=WorkflowStatus.COMPLETED,
            decision=WorkflowDecision.COMPLETE,
            definitions=(definition(),),
            results=(completed_result(),),
            current_step_id="step-001",
            started_at=NOW,
            completed_at=NOW + timedelta(minutes=1),
        )


def test_cancelled_workflow_requires_reason() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "cancelled workflows must include "
            "cancelled_reason"
        ),
    ):
        WorkflowExecutionRecord(
            workflow_id="workflow-001",
            status=WorkflowStatus.CANCELLED,
            decision=WorkflowDecision.CANCEL,
            definitions=(definition(),),
            results=(),
            current_step_id=None,
            started_at=NOW,
            completed_at=NOW + timedelta(minutes=1),
        )


def test_workflow_report() -> None:
    value = WorkflowReport(
        status=WorkflowStatus.COMPLETED,
        decision=WorkflowDecision.COMPLETE,
        request=request(),
        record=completed_record(),
        recommendation="Workflow completed successfully.",
    )

    assert value.record is not None


def test_report_status_must_match_record() -> None:
    with pytest.raises(
        ValueError,
        match="report status must match the record",
    ):
        WorkflowReport(
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.COMPLETE,
            request=request(),
            record=completed_record(),
            recommendation="Workflow running.",
        )


def test_report_decision_must_match_record() -> None:
    with pytest.raises(
        ValueError,
        match="report decision must match the record",
    ):
        WorkflowReport(
            status=WorkflowStatus.COMPLETED,
            decision=WorkflowDecision.CONTINUE,
            request=request(),
            record=completed_record(),
            recommendation="Workflow completed.",
        )


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        WorkflowReport(
            status=WorkflowStatus.FAILED,
            decision=WorkflowDecision.FAIL,
            request=request(),
            record=None,
            recommendation="Workflow failed.",
        )


def test_non_failed_report_requires_record() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-failed reports must include a record"
        ),
    ):
        WorkflowReport(
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.CONTINUE,
            request=request(),
            record=None,
            recommendation="Workflow running.",
        )


def test_warnings_are_tuples() -> None:
    value = WorkflowReport(
        status=WorkflowStatus.COMPLETED,
        decision=WorkflowDecision.COMPLETE,
        request=request(),
        record=completed_record(),
        recommendation="Workflow completed.",
        warnings=["Workflow warning."],
    )

    assert value.warnings == (
        "Workflow warning.",
    )


def test_models_are_immutable() -> None:
    value = request()

    with pytest.raises(FrozenInstanceError):
        value.workflow_id = "changed"