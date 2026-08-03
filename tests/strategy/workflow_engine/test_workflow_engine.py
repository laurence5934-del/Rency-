from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.workflow_engine.workflow_engine import (
    EnterpriseWorkflowEngine,
)
from app.strategy.workflow_engine.workflow_models import (
    WorkflowDecision,
    WorkflowFailurePolicy,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowStepDefinition,
    WorkflowStepStatus,
)


NOW = datetime(
    2026,
    8,
    3,
    18,
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


def engine() -> EnterpriseWorkflowEngine:
    return EnterpriseWorkflowEngine(
        clock=IncrementingClock(),
    )


def request(
    *,
    workflow_id: str = "workflow-001",
    workflow_type: str = "trade-execution",
) -> WorkflowRequest:
    return WorkflowRequest(
        workflow_id=workflow_id,
        correlation_id="correlation-001",
        workflow_type=workflow_type,
        requested_by="strategy-orchestrator",
        requested_at=NOW,
    )


def definition(
    step_id: str,
    *,
    position: int,
    failure_policy: WorkflowFailurePolicy = (
        WorkflowFailurePolicy.FAIL_FAST
    ),
    max_attempts: int = 1,
    required: bool = True,
    compensation_step_id: str | None = None,
) -> WorkflowStepDefinition:
    return WorkflowStepDefinition(
        step_id=step_id,
        name=f"Step {position}",
        position=position,
        component="workflow-component",
        failure_policy=failure_policy,
        max_attempts=max_attempts,
        required=required,
        compensation_step_id=compensation_step_id,
    )


def standard_definitions() -> tuple[
    WorkflowStepDefinition,
    ...,
]:
    return (
        definition(
            "risk-check",
            position=1,
        ),
        definition(
            "execute-order",
            position=2,
        ),
    )


def register_standard_workflow(
    value: EnterpriseWorkflowEngine,
    *,
    risk_handler=None,
    execution_handler=None,
) -> None:
    value.register_workflow(
        workflow_type="trade-execution",
        definitions=standard_definitions(),
        handlers={
            "risk-check": (
                risk_handler
                if risk_handler is not None
                else lambda workflow_request, results: {
                    "decision": "APPROVE",
                }
            ),
            "execute-order": (
                execution_handler
                if execution_handler is not None
                else lambda workflow_request, results: {
                    "order_id": "SIM-001",
                }
            ),
        },
    )


def test_register_workflow() -> None:
    value = engine()

    definitions = value.register_workflow(
        workflow_type="trade-execution",
        definitions=standard_definitions(),
        handlers={
            "risk-check": lambda workflow_request, results: None,
            "execute-order": lambda workflow_request, results: None,
        },
    )

    assert definitions == standard_definitions()
    assert value.registered_workflow_types == (
        "trade-execution",
    )


def test_workflow_type_is_normalized() -> None:
    value = engine()

    value.register_workflow(
        workflow_type="  trade-execution  ",
        definitions=standard_definitions(),
        handlers={
            "risk-check": lambda workflow_request, results: None,
            "execute-order": lambda workflow_request, results: None,
        },
    )

    assert value.registered_workflow_types == (
        "trade-execution",
    )


def test_duplicate_workflow_registration_is_rejected() -> None:
    value = engine()
    register_standard_workflow(value)

    with pytest.raises(
        ValueError,
        match="workflow_type is already registered",
    ):
        register_standard_workflow(value)


def test_definitions_must_be_iterable() -> None:
    with pytest.raises(
        TypeError,
        match="definitions must be iterable",
    ):
        engine().register_workflow(
            workflow_type="trade-execution",
            definitions=None,
            handlers={},
        )


def test_definitions_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="definitions must not be empty",
    ):
        engine().register_workflow(
            workflow_type="trade-execution",
            definitions=(),
            handlers={},
        )


def test_every_definition_must_be_valid() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "every definition must be a "
            "WorkflowStepDefinition"
        ),
    ):
        engine().register_workflow(
            workflow_type="trade-execution",
            definitions=(object(),),
            handlers={},
        )


def test_handlers_must_be_mapping() -> None:
    with pytest.raises(
        TypeError,
        match="handlers must be a mapping",
    ):
        engine().register_workflow(
            workflow_type="trade-execution",
            definitions=standard_definitions(),
            handlers=[],
        )


def test_handler_step_must_reference_known_step() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "handler step_id must reference "
            "a known workflow step"
        ),
    ):
        engine().register_workflow(
            workflow_type="trade-execution",
            definitions=standard_definitions(),
            handlers={
                "unknown-step": (
                    lambda workflow_request, results: None
                ),
            },
        )


def test_every_handler_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "every workflow handler must be callable"
        ),
    ):
        engine().register_workflow(
            workflow_type="trade-execution",
            definitions=standard_definitions(),
            handlers={
                "risk-check": object(),
            },
        )


def test_unregister_workflow() -> None:
    value = engine()
    register_standard_workflow(value)

    definitions = value.unregister_workflow(
        "trade-execution"
    )

    assert definitions == standard_definitions()
    assert value.registered_workflow_types == ()


def test_unregister_unknown_workflow() -> None:
    with pytest.raises(
        KeyError,
        match="workflow type not found",
    ):
        engine().unregister_workflow(
            "missing"
        )


def test_start_workflow() -> None:
    value = engine()
    register_standard_workflow(value)

    report = value.start(request())

    assert report.status is WorkflowStatus.RUNNING
    assert report.decision is WorkflowDecision.CONTINUE
    assert report.record is not None
    assert report.record.current_step_id == "risk-check"
    assert value.workflow_ids == ("workflow-001",)


def test_start_requires_workflow_request() -> None:
    with pytest.raises(
        TypeError,
        match="request must be a WorkflowRequest",
    ):
        engine().start(object())


def test_start_requires_registered_workflow_type() -> None:
    with pytest.raises(
        KeyError,
        match="workflow type not registered",
    ):
        engine().start(request())


def test_duplicate_workflow_id_is_rejected() -> None:
    value = engine()
    register_standard_workflow(value)

    value.start(request())

    with pytest.raises(
        ValueError,
        match="workflow_id is already started",
    ):
        value.start(request())


def test_advance_executes_first_step() -> None:
    value = engine()
    register_standard_workflow(value)

    value.start(request())
    report = value.advance("workflow-001")

    assert report.status is WorkflowStatus.RUNNING
    assert report.record is not None
    assert report.record.current_step_id == "execute-order"
    assert len(report.record.results) == 1
    assert (
        report.record.results[0].status
        is WorkflowStepStatus.COMPLETED
    )


def test_completed_step_output_is_recorded() -> None:
    value = engine()
    register_standard_workflow(
        value,
        risk_handler=lambda workflow_request, results: {
            "risk_score": Decimal("0.20"),
            "decision": "APPROVE",
        },
    )

    value.start(request())
    report = value.advance("workflow-001")

    assert report.record is not None
    assert report.record.results[0].output == (
        ("decision", "APPROVE"),
        ("risk_score", "0.20"),
    )


def test_non_mapping_output_is_recorded() -> None:
    value = engine()
    register_standard_workflow(
        value,
        risk_handler=lambda workflow_request, results: (
            "approved"
        ),
    )

    value.start(request())
    report = value.advance("workflow-001")

    assert report.record is not None
    assert report.record.results[0].output == (
        ("result", "approved"),
    )


def test_none_output_is_empty() -> None:
    value = engine()
    register_standard_workflow(
        value,
        risk_handler=lambda workflow_request, results: None,
    )

    value.start(request())
    report = value.advance("workflow-001")

    assert report.record is not None
    assert report.record.results[0].output == ()


def test_second_advance_completes_workflow() -> None:
    value = engine()
    register_standard_workflow(value)

    value.start(request())
    value.advance("workflow-001")
    report = value.advance("workflow-001")

    assert report.status is WorkflowStatus.COMPLETED
    assert report.decision is WorkflowDecision.COMPLETE
    assert report.record is not None
    assert report.record.current_step_id is None
    assert report.record.completed_at is not None
    assert len(report.record.results) == 2


def test_run_executes_entire_workflow() -> None:
    value = engine()
    register_standard_workflow(value)

    report = value.run(request())

    assert report.status is WorkflowStatus.COMPLETED
    assert report.record is not None
    assert len(report.record.results) == 2


def test_handlers_receive_previous_results() -> None:
    value = engine()
    observed_result_counts: list[int] = []

    def risk_handler(
        workflow_request: WorkflowRequest,
        results,
    ):
        observed_result_counts.append(len(results))
        return {"decision": "APPROVE"}

    def execution_handler(
        workflow_request: WorkflowRequest,
        results,
    ):
        observed_result_counts.append(len(results))
        return {"order_id": "SIM-001"}

    register_standard_workflow(
        value,
        risk_handler=risk_handler,
        execution_handler=execution_handler,
    )

    value.run(request())

    assert observed_result_counts == [0, 1]


def test_pause_running_workflow() -> None:
    value = engine()
    register_standard_workflow(value)
    value.start(request())

    report = value.pause("workflow-001")

    assert report.status is WorkflowStatus.PAUSED
    assert report.decision is WorkflowDecision.PAUSE
    assert report.record is not None
    assert report.record.current_step_id == "risk-check"


def test_paused_workflow_cannot_advance() -> None:
    value = engine()
    register_standard_workflow(value)
    value.start(request())
    value.pause("workflow-001")

    with pytest.raises(
        RuntimeError,
        match=(
            "paused workflows must be resumed "
            "before advancing"
        ),
    ):
        value.advance("workflow-001")


def test_resume_paused_workflow() -> None:
    value = engine()
    register_standard_workflow(value)
    value.start(request())
    value.pause("workflow-001")

    report = value.resume("workflow-001")

    assert report.status is WorkflowStatus.RUNNING
    assert report.decision is WorkflowDecision.CONTINUE


def test_resume_non_paused_workflow_is_rejected() -> None:
    value = engine()
    register_standard_workflow(value)
    value.start(request())

    with pytest.raises(
        RuntimeError,
        match=(
            "only paused workflows may be resumed"
        ),
    ):
        value.resume("workflow-001")


def test_cancel_workflow() -> None:
    value = engine()
    register_standard_workflow(value)
    value.start(request())

    report = value.cancel(
        "workflow-001",
        reason="User requested cancellation.",
    )

    assert report.status is WorkflowStatus.CANCELLED
    assert report.decision is WorkflowDecision.CANCEL
    assert report.record is not None
    assert report.record.current_step_id is None
    assert (
        report.record.cancelled_reason
        == "User requested cancellation."
    )


def test_cancellation_records_cancelled_step_result() -> None:
    value = engine()
    register_standard_workflow(value)
    value.start(request())

    report = value.cancel(
        "workflow-001",
        reason="Cancelled.",
    )

    assert report.record is not None
    assert len(report.record.results) == 1
    assert (
        report.record.results[0].status
        is WorkflowStepStatus.CANCELLED
    )
    assert (
        report.record.results[0].step_id
        == "risk-check"
    )


def test_cancellation_reason_must_not_be_empty() -> None:
    value = engine()
    register_standard_workflow(value)
    value.start(request())

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        value.cancel(
            "workflow-001",
            reason="   ",
        )


def test_terminal_workflow_cannot_advance() -> None:
    value = engine()
    register_standard_workflow(value)
    value.run(request())

    with pytest.raises(
        RuntimeError,
        match="workflow is already terminal",
    ):
        value.advance("workflow-001")

def test_fail_fast_failure_stops_workflow() -> None:
    value = engine()

    def failing_handler(
        workflow_request: WorkflowRequest,
        results,
    ) -> None:
        raise RuntimeError("risk rejected")

    register_standard_workflow(
        value,
        risk_handler=failing_handler,
    )

    value.start(request())
    report = value.advance("workflow-001")

    assert report.status is WorkflowStatus.FAILED
    assert report.decision is WorkflowDecision.FAIL
    assert report.record is not None
    assert report.record.current_step_id is None
    assert report.error == "risk rejected"


def test_fail_fast_records_failed_result() -> None:
    value = engine()

    def failing_handler(
        workflow_request: WorkflowRequest,
        results,
    ) -> None:
        raise RuntimeError("step failed")

    register_standard_workflow(
        value,
        risk_handler=failing_handler,
    )

    value.start(request())
    report = value.advance("workflow-001")

    assert report.record is not None
    assert len(report.record.results) == 1
    assert (
        report.record.results[0].status
        is WorkflowStepStatus.FAILED
    )
    assert report.record.results[0].error == "step failed"


def test_continue_policy_advances_after_failure() -> None:
    value = engine()

    definitions = (
        definition(
            "optional-analysis",
            position=1,
            failure_policy=(
                WorkflowFailurePolicy.CONTINUE
            ),
        ),
        definition(
            "execute-order",
            position=2,
        ),
    )

    def failing_handler(
        workflow_request: WorkflowRequest,
        results,
    ) -> None:
        raise RuntimeError("analysis unavailable")

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=definitions,
        handlers={
            "optional-analysis": failing_handler,
            "execute-order": (
                lambda workflow_request, results: {
                    "order_id": "SIM-001",
                }
            ),
        },
    )

    value.start(request())
    report = value.advance("workflow-001")

    assert report.status is WorkflowStatus.RUNNING
    assert report.record is not None
    assert (
        report.record.current_step_id
        == "execute-order"
    )
    assert len(report.record.warnings) == 1
    assert "execution continued" in (
        report.record.warnings[0]
    )


def test_continue_policy_can_complete_workflow() -> None:
    value = engine()

    definitions = (
        definition(
            "optional-analysis",
            position=1,
            failure_policy=(
                WorkflowFailurePolicy.CONTINUE
            ),
        ),
        definition(
            "execute-order",
            position=2,
        ),
    )

    def failing_handler(
        workflow_request: WorkflowRequest,
        results,
    ) -> None:
        raise RuntimeError("analysis unavailable")

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=definitions,
        handlers={
            "optional-analysis": failing_handler,
            "execute-order": (
                lambda workflow_request, results: None
            ),
        },
    )

    report = value.run(request())

    assert report.status is WorkflowStatus.COMPLETED
    assert report.record is not None
    assert len(report.record.results) == 2
    assert (
        report.record.results[0].status
        is WorkflowStepStatus.FAILED
    )
    assert (
        report.record.results[1].status
        is WorkflowStepStatus.COMPLETED
    )


def test_retry_policy_retries_until_success() -> None:
    value = engine()
    attempts = 0

    definitions = (
        definition(
            "risk-check",
            position=1,
            failure_policy=WorkflowFailurePolicy.RETRY,
            max_attempts=3,
        ),
    )

    def flaky_handler(
        workflow_request: WorkflowRequest,
        results,
    ):
        nonlocal attempts
        attempts += 1

        if attempts < 3:
            raise RuntimeError("temporary failure")

        return {"decision": "APPROVE"}

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=definitions,
        handlers={
            "risk-check": flaky_handler,
        },
    )

    report = value.run(request())

    assert attempts == 3
    assert report.status is WorkflowStatus.COMPLETED
    assert report.record is not None
    assert len(report.record.results) == 3
    assert tuple(
        result.attempt_number
        for result in report.record.results
    ) == (1, 2, 3)


def test_retry_policy_records_failed_attempts() -> None:
    value = engine()
    attempts = 0

    definitions = (
        definition(
            "risk-check",
            position=1,
            failure_policy=WorkflowFailurePolicy.RETRY,
            max_attempts=3,
        ),
    )

    def flaky_handler(
        workflow_request: WorkflowRequest,
        results,
    ) -> None:
        nonlocal attempts
        attempts += 1

        if attempts < 3:
            raise RuntimeError("temporary failure")

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=definitions,
        handlers={
            "risk-check": flaky_handler,
        },
    )

    report = value.run(request())

    assert report.record is not None
    assert tuple(
        result.status
        for result in report.record.results
    ) == (
        WorkflowStepStatus.FAILED,
        WorkflowStepStatus.FAILED,
        WorkflowStepStatus.COMPLETED,
    )


def test_retry_exhaustion_fails_workflow() -> None:
    value = engine()
    attempts = 0

    definitions = (
        definition(
            "risk-check",
            position=1,
            failure_policy=WorkflowFailurePolicy.RETRY,
            max_attempts=3,
        ),
    )

    def failing_handler(
        workflow_request: WorkflowRequest,
        results,
    ) -> None:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("persistent failure")

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=definitions,
        handlers={
            "risk-check": failing_handler,
        },
    )

    report = value.run(request())

    assert attempts == 3
    assert report.status is WorkflowStatus.FAILED
    assert report.error == "persistent failure"
    assert report.record is not None
    assert len(report.record.results) == 3


def test_retry_exhaustion_uses_final_attempt_number() -> None:
    value = engine()

    definitions = (
        definition(
            "risk-check",
            position=1,
            failure_policy=WorkflowFailurePolicy.RETRY,
            max_attempts=4,
        ),
    )

    def failing_handler(
        workflow_request: WorkflowRequest,
        results,
    ) -> None:
        raise RuntimeError("persistent failure")

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=definitions,
        handlers={
            "risk-check": failing_handler,
        },
    )

    report = value.run(request())

    assert report.record is not None
    assert (
        report.record.results[-1].attempt_number
        == 4
    )


def test_optional_missing_handler_is_skipped() -> None:
    value = engine()

    definitions = (
        definition(
            "optional-analysis",
            position=1,
            required=False,
        ),
        definition(
            "execute-order",
            position=2,
        ),
    )

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=definitions,
        handlers={
            "execute-order": (
                lambda workflow_request, results: None
            ),
        },
    )

    value.start(request())
    report = value.advance("workflow-001")

    assert report.status is WorkflowStatus.RUNNING
    assert report.record is not None
    assert (
        report.record.results[0].status
        is WorkflowStepStatus.SKIPPED
    )
    assert (
        report.record.current_step_id
        == "execute-order"
    )


def test_optional_missing_handler_adds_warning() -> None:
    value = engine()

    definitions = (
        definition(
            "optional-analysis",
            position=1,
            required=False,
        ),
        definition(
            "execute-order",
            position=2,
        ),
    )

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=definitions,
        handlers={
            "execute-order": (
                lambda workflow_request, results: None
            ),
        },
    )

    value.start(request())
    report = value.advance("workflow-001")

    assert report.record is not None
    assert report.record.warnings == (
        "Optional step optional-analysis was skipped.",
    )


def test_required_missing_handler_fails_workflow() -> None:
    value = engine()

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=standard_definitions(),
        handlers={
            "execute-order": (
                lambda workflow_request, results: None
            ),
        },
    )

    value.start(request())
    report = value.advance("workflow-001")

    assert report.status is WorkflowStatus.FAILED
    assert report.error is not None
    assert "has no handler" in report.error


def test_compensation_success_marks_workflow_compensated() -> None:
    value = engine()

    definitions = (
        definition(
            "execute-order",
            position=1,
            failure_policy=(
                WorkflowFailurePolicy.COMPENSATE
            ),
            compensation_step_id="cancel-order",
        ),
        definition(
            "cancel-order",
            position=2,
        ),
    )

    def failing_execution(
        workflow_request: WorkflowRequest,
        results,
    ) -> None:
        raise RuntimeError("broker rejected order")

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=definitions,
        handlers={
            "execute-order": failing_execution,
            "cancel-order": (
                lambda workflow_request, results: {
                    "cancelled": True,
                }
            ),
        },
    )

    report = value.run(request())

    assert report.status is WorkflowStatus.COMPENSATED
    assert report.decision is WorkflowDecision.COMPENSATE
    assert report.record is not None
    assert report.record.current_step_id is None
    assert len(report.record.results) == 2


def test_compensation_result_correlates_failed_step() -> None:
    value = engine()

    definitions = (
        definition(
            "execute-order",
            position=1,
            failure_policy=(
                WorkflowFailurePolicy.COMPENSATE
            ),
            compensation_step_id="cancel-order",
        ),
        definition(
            "cancel-order",
            position=2,
        ),
    )

    def failing_execution(
        workflow_request: WorkflowRequest,
        results,
    ) -> None:
        raise RuntimeError("execution failed")

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=definitions,
        handlers={
            "execute-order": failing_execution,
            "cancel-order": (
                lambda workflow_request, results: None
            ),
        },
    )

    report = value.run(request())

    assert report.record is not None
    compensation_result = report.record.results[-1]

    assert (
        compensation_result.status
        is WorkflowStepStatus.COMPENSATED
    )
    assert compensation_result.step_id == "cancel-order"
    assert (
        compensation_result.compensated_step_id
        == "execute-order"
    )


def test_compensation_output_is_recorded() -> None:
    value = engine()

    definitions = (
        definition(
            "execute-order",
            position=1,
            failure_policy=(
                WorkflowFailurePolicy.COMPENSATE
            ),
            compensation_step_id="cancel-order",
        ),
        definition(
            "cancel-order",
            position=2,
        ),
    )

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=definitions,
        handlers={
            "execute-order": (
                lambda workflow_request, results: (
                    (_ for _ in ()).throw(
                        RuntimeError("failure")
                    )
                )
            ),
            "cancel-order": (
                lambda workflow_request, results: {
                    "status": "CANCELLED",
                }
            ),
        },
    )

    report = value.run(request())

    assert report.record is not None
    assert report.record.results[-1].output == (
        ("status", "CANCELLED"),
    )


def test_compensation_failure_fails_workflow() -> None:
    value = engine()

    definitions = (
        definition(
            "execute-order",
            position=1,
            failure_policy=(
                WorkflowFailurePolicy.COMPENSATE
            ),
            compensation_step_id="cancel-order",
        ),
        definition(
            "cancel-order",
            position=2,
        ),
    )

    def execution_failure(
        workflow_request: WorkflowRequest,
        results,
    ) -> None:
        raise RuntimeError("execution failed")

    def compensation_failure(
        workflow_request: WorkflowRequest,
        results,
    ) -> None:
        raise RuntimeError("cancellation failed")

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=definitions,
        handlers={
            "execute-order": execution_failure,
            "cancel-order": compensation_failure,
        },
    )

    report = value.run(request())

    assert report.status is WorkflowStatus.FAILED
    assert report.error is not None
    assert "execution failed" in report.error
    assert "cancellation failed" in report.error


def test_compensation_handler_missing_fails_workflow() -> None:
    value = engine()

    definitions = (
        definition(
            "execute-order",
            position=1,
            failure_policy=(
                WorkflowFailurePolicy.COMPENSATE
            ),
            compensation_step_id="cancel-order",
        ),
        definition(
            "cancel-order",
            position=2,
        ),
    )

    def execution_failure(
        workflow_request: WorkflowRequest,
        results,
    ) -> None:
        raise RuntimeError("execution failed")

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=definitions,
        handlers={
            "execute-order": execution_failure,
        },
    )

    report = value.run(request())

    assert report.status is WorkflowStatus.FAILED
    assert report.error is not None
    assert "Compensation handler is missing" in (
        report.error
    )


def test_compensation_step_is_not_executed_normally() -> None:
    value = engine()
    compensation_calls = 0

    definitions = (
        definition(
            "execute-order",
            position=1,
            failure_policy=(
                WorkflowFailurePolicy.COMPENSATE
            ),
            compensation_step_id="cancel-order",
        ),
        definition(
            "cancel-order",
            position=2,
        ),
    )

    def compensation_handler(
        workflow_request: WorkflowRequest,
        results,
    ) -> None:
        nonlocal compensation_calls
        compensation_calls += 1

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=definitions,
        handlers={
            "execute-order": (
                lambda workflow_request, results: None
            ),
            "cancel-order": compensation_handler,
        },
    )

    report = value.run(request())

    assert report.status is WorkflowStatus.COMPLETED
    assert compensation_calls == 0
    assert report.record is not None
    assert len(report.record.results) == 1


def test_get_report_returns_current_snapshot() -> None:
    value = engine()
    register_standard_workflow(value)

    value.start(request())
    report = value.get_report("workflow-001")

    assert report.status is WorkflowStatus.RUNNING
    assert report.record is not None
    assert report.record.current_step_id == "risk-check"


def test_results_for_workflow() -> None:
    value = engine()
    register_standard_workflow(value)

    value.run(request())

    results = value.results_for_workflow(
        "workflow-001"
    )

    assert len(results) == 2
    assert all(
        result.status is WorkflowStepStatus.COMPLETED
        for result in results
    )


def test_reports_for_workflow() -> None:
    value = engine()
    register_standard_workflow(value)

    value.start(request())
    value.advance("workflow-001")
    value.advance("workflow-001")

    reports = value.reports_for_workflow(
        "workflow-001"
    )

    assert len(reports) == 3
    assert tuple(
        report.status
        for report in reports
    ) == (
        WorkflowStatus.RUNNING,
        WorkflowStatus.RUNNING,
        WorkflowStatus.COMPLETED,
    )


def test_global_history_records_reports() -> None:
    value = engine()
    register_standard_workflow(value)

    value.run(request())

    assert len(value.history) == 3


def test_multiple_workflows_are_isolated() -> None:
    value = engine()
    register_standard_workflow(value)

    first = value.run(
        request(workflow_id="workflow-001")
    )
    second = value.run(
        request(workflow_id="workflow-002")
    )

    assert first.status is WorkflowStatus.COMPLETED
    assert second.status is WorkflowStatus.COMPLETED
    assert value.workflow_ids == (
        "workflow-001",
        "workflow-002",
    )


def test_result_ids_are_deterministic() -> None:
    value = engine()
    register_standard_workflow(value)

    report = value.run(request())

    assert report.record is not None
    assert tuple(
        result.result_id
        for result in report.record.results
    ) == (
        "workflow-result-000001",
        "workflow-result-000002",
    )


def test_result_ids_continue_across_workflows() -> None:
    value = engine()
    register_standard_workflow(value)

    first = value.run(
        request(workflow_id="workflow-001")
    )
    second = value.run(
        request(workflow_id="workflow-002")
    )

    assert first.record is not None
    assert second.record is not None

    assert first.record.results[-1].result_id == (
        "workflow-result-000002"
    )
    assert second.record.results[0].result_id == (
        "workflow-result-000003"
    )


def test_unknown_workflow_lookup_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="workflow not found",
    ):
        engine().get_report("missing")


def test_terminal_workflow_cannot_be_cancelled() -> None:
    value = engine()
    register_standard_workflow(value)
    value.run(request())

    with pytest.raises(
        RuntimeError,
        match="workflow is already terminal",
    ):
        value.cancel(
            "workflow-001",
            reason="Too late.",
        )


def test_terminal_workflow_cannot_be_paused() -> None:
    value = engine()
    register_standard_workflow(value)
    value.run(request())

    with pytest.raises(
        RuntimeError,
        match="workflow is already terminal",
    ):
        value.pause("workflow-001")


def test_pause_already_paused_workflow_is_rejected() -> None:
    value = engine()
    register_standard_workflow(value)
    value.start(request())
    value.pause("workflow-001")

    with pytest.raises(
        RuntimeError,
        match="workflow is already paused",
    ):
        value.pause("workflow-001")


def test_workflow_type_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="workflow_type must not be empty",
    ):
        engine().register_workflow(
            workflow_type="   ",
            definitions=standard_definitions(),
            handlers={},
        )


def test_workflow_identifier_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="workflow_id must not be empty",
    ):
        engine().get_report("   ")


def test_output_key_must_not_be_empty() -> None:
    value = engine()

    value.register_workflow(
        workflow_type="trade-execution",
        definitions=(
            definition(
                "risk-check",
                position=1,
            ),
        ),
        handlers={
            "risk-check": (
                lambda workflow_request, results: {
                    "   ": "value",
                }
            ),
        },
    )

    value.start(request())

    with pytest.raises(
        ValueError,
        match=(
            "workflow output keys must not be empty"
        ),
    ):
        value.advance("workflow-001")


def test_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterpriseWorkflowEngine(clock=NOW)


def test_clock_must_return_datetime() -> None:
    value = EnterpriseWorkflowEngine(
        clock=lambda: "now"
    )
    register_standard_workflow(value)

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        value.start(request())


def test_clock_must_return_timezone_aware_datetime() -> None:
    value = EnterpriseWorkflowEngine(
        clock=lambda: datetime(2026, 8, 3)
    )
    register_standard_workflow(value)

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a timezone-aware datetime"
        ),
    ):
        value.start(request())