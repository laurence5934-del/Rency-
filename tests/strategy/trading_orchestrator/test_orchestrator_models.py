from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.broker_gateway import (
    BrokerEnvironment,
    BrokerOrderRequest,
)
from app.strategy.execution_coordinator import (
    ExecutionDecision,
    ExecutionReport,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStage,
    ExecutionStatus,
    ExecutionStep,
)
from app.strategy.order_manager import (
    OrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)
from app.strategy.portfolio_manager import AssetClass
from app.strategy.risk_gateway import (
    RiskEvaluationRequest,
)
from app.strategy.trading_orchestrator import (
    TradingWorkflowReport,
    TradingWorkflowRequest,
    TradingWorkflowResult,
    WorkflowCheckpoint,
    WorkflowDecision,
    WorkflowStage,
    WorkflowStatus,
)
from app.strategy.trading_session import (
    SessionState,
    SessionType,
    TradingSession,
)


NOW = datetime(
    2026,
    8,
    5,
    18,
    0,
    tzinfo=timezone.utc,
)

SESSION_TIME = NOW - timedelta(minutes=10)
ORDER_TIME = NOW - timedelta(minutes=8)
RISK_TIME = NOW - timedelta(minutes=5)
BROKER_TIME = NOW - timedelta(minutes=3)
EXECUTION_TIME = NOW - timedelta(minutes=1)


def trading_session() -> TradingSession:
    return TradingSession(
        session_id="session-001",
        calendar_id="calendar-001",
        market="NYSE",
        trading_date=date(2026, 8, 5),
        state=SessionState.OPEN,
        session_type=SessionType.REGULAR,
        opened_at=(
            SESSION_TIME - timedelta(minutes=30)
        ),
        closed_at=None,
        evaluated_at=SESSION_TIME,
        trading_allowed=True,
        reason="Regular trading session is open.",
    )


def order_request(
    *,
    order_id: str = "order-001",
    client_order_id: str = "client-order-001",
    portfolio_id: str = "portfolio-001",
    strategy_id: str = "strategy-001",
    symbol: str = "NVDA",
    quantity: str = "10",
) -> OrderRequest:
    return OrderRequest(
        order_id=order_id,
        client_order_id=client_order_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        asset_class=AssetClass.EQUITY,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal(quantity),
        created_at=ORDER_TIME,
        strategy_id=strategy_id,
    )


def risk_evaluation_request(
    order: OrderRequest,
) -> RiskEvaluationRequest:
    return RiskEvaluationRequest(
        evaluation_id=f"risk-{order.order_id}",
        request=order,
        account_id="account-001",
        portfolio_id=order.portfolio_id,
        requested_at=RISK_TIME,
        market_price=Decimal("125"),
        current_position_quantity=Decimal("20"),
        current_position_notional=Decimal("2500"),
        available_buying_power=Decimal("50000"),
        available_margin=Decimal("25000"),
        gross_exposure=Decimal("100000"),
        net_exposure=Decimal("60000"),
        daily_realized_pnl=Decimal("500"),
        daily_unrealized_pnl=Decimal("-100"),
        trading_session_allowed=True,
        short_selling_allowed=True,
    )


def broker_order_request(
    order: OrderRequest,
) -> BrokerOrderRequest:
    return BrokerOrderRequest(
        gateway_order_id=f"gateway-{order.order_id}",
        order_id=order.order_id,
        client_order_id=order.client_order_id,
        broker_name="Interactive Brokers",
        account_id="account-001",
        environment=BrokerEnvironment.PAPER,
        symbol=order.symbol,
        asset_class=order.asset_class,
        side=order.side,
        order_type=order.order_type,
        time_in_force=order.time_in_force,
        quantity=order.quantity,
        submitted_at=BROKER_TIME,
        limit_price=order.limit_price,
        stop_price=order.stop_price,
    )


def execution_request(
    *,
    execution_id: str = "execution-001",
    correlation_id: str = "correlation-001",
    strategy_id: str = "strategy-001",
    portfolio_id: str = "portfolio-001",
    order_id: str = "order-001",
    client_order_id: str = "client-order-001",
) -> ExecutionRequest:
    order = order_request(
        order_id=order_id,
        client_order_id=client_order_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
    )

    return ExecutionRequest(
        execution_id=execution_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        session=trading_session(),
        order_request=order,
        created_at=EXECUTION_TIME,
        risk_request=risk_evaluation_request(order),
        broker_request=broker_order_request(order),
        requested_by="strategy-orchestrator",
    )


def workflow_request(
    *,
    workflow_id: str = "workflow-001",
    correlation_id: str = "correlation-001",
    strategy_id: str = "strategy-001",
    portfolio_id: str = "portfolio-001",
    request: ExecutionRequest | None = None,
    created_at: datetime = NOW,
    priority: int = 100,
) -> TradingWorkflowRequest:
    effective_request = request or execution_request(
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
    )

    return TradingWorkflowRequest(
        workflow_id=workflow_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        execution_request=effective_request,
        created_at=created_at,
        requested_by="strategy-orchestrator",
        priority=priority,
        metadata=(
            ("source", "ai-strategy"),
        ),
    )


def successful_checkpoint(
    *,
    checkpoint_id: str = "checkpoint-001",
    workflow_id: str = "workflow-001",
    stage: WorkflowStage = WorkflowStage.STRATEGY,
    started_at: datetime = NOW,
    completed_at: datetime = NOW,
) -> WorkflowCheckpoint:
    return WorkflowCheckpoint(
        checkpoint_id=checkpoint_id,
        workflow_id=workflow_id,
        stage=stage,
        decision=WorkflowDecision.PROCEED,
        started_at=started_at,
        completed_at=completed_at,
        message="Workflow checkpoint completed.",
        successful=True,
        reference_id="reference-001",
    )


def test_trading_workflow_request() -> None:
    value = workflow_request()

    assert value.workflow_id == "workflow-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.execution_id == "execution-001"
    assert value.order_id == "order-001"
    assert value.priority == 100
    assert value.requested_by == (
        "strategy-orchestrator"
    )


def test_workflow_request_properties() -> None:
    value = workflow_request()

    assert value.execution_id == (
        value.execution_request.execution_id
    )
    assert value.order_id == (
        value.execution_request
        .order_request
        .order_id
    )


def test_workflow_request_defaults() -> None:
    request = execution_request()

    value = TradingWorkflowRequest(
        workflow_id="workflow-001",
        correlation_id="correlation-001",
        strategy_id="strategy-001",
        portfolio_id="portfolio-001",
        execution_request=request,
        created_at=NOW,
    )

    assert value.requested_by == (
        "strategy-orchestrator"
    )
    assert value.priority == 100
    assert value.metadata == ()


def test_workflow_request_text_is_normalized() -> None:
    request = execution_request()

    value = TradingWorkflowRequest(
        workflow_id="  workflow-001  ",
        correlation_id="  correlation-001  ",
        strategy_id="  strategy-001  ",
        portfolio_id="  portfolio-001  ",
        execution_request=request,
        created_at=NOW,
        requested_by="  strategy-orchestrator  ",
        metadata=[
            ("  source  ", "  ai-strategy  "),
        ],
    )

    assert value.workflow_id == "workflow-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.requested_by == (
        "strategy-orchestrator"
    )
    assert value.metadata == (
        ("source", "ai-strategy"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "workflow_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "requested_by",
    ],
)
def test_workflow_request_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "workflow_id": "workflow-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "execution_request": execution_request(),
        "created_at": NOW,
        "requested_by": "strategy-orchestrator",
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        TradingWorkflowRequest(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "workflow_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "requested_by",
    ],
)
def test_workflow_request_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "workflow_id": "workflow-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "execution_request": execution_request(),
        "created_at": NOW,
        "requested_by": "strategy-orchestrator",
    }
    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        TradingWorkflowRequest(**arguments)


def test_workflow_request_requires_execution_request() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "execution_request must be an "
            "ExecutionRequest"
        ),
    ):
        TradingWorkflowRequest(
            workflow_id="workflow-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            execution_request=object(),
            created_at=NOW,
        )


def test_workflow_created_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="created_at must be a datetime",
    ):
        TradingWorkflowRequest(
            workflow_id="workflow-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            execution_request=execution_request(),
            created_at="2026-08-05",
        )


def test_workflow_created_at_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="created_at must be timezone-aware",
    ):
        TradingWorkflowRequest(
            workflow_id="workflow-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            execution_request=execution_request(),
            created_at=datetime(
                2026,
                8,
                5,
                18,
                0,
            ),
        )


def test_workflow_priority_must_be_integer() -> None:
    with pytest.raises(
        TypeError,
        match="priority must be an integer",
    ):
        workflow_request(priority="high")


def test_workflow_priority_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="priority must not be negative",
    ):
        workflow_request(priority=-1)


def test_zero_priority_is_allowed() -> None:
    value = workflow_request(priority=0)

    assert value.priority == 0


def test_correlation_id_must_match_execution_request() -> None:
    request = execution_request(
        correlation_id="execution-correlation"
    )

    with pytest.raises(
        ValueError,
        match=(
            "correlation_id must match "
            "execution_request correlation_id"
        ),
    ):
        workflow_request(
            correlation_id="different-correlation",
            request=request,
        )


def test_strategy_id_must_match_execution_request() -> None:
    request = execution_request(
        strategy_id="execution-strategy"
    )

    with pytest.raises(
        ValueError,
        match=(
            "strategy_id must match "
            "execution_request strategy_id"
        ),
    ):
        workflow_request(
            strategy_id="different-strategy",
            request=request,
        )


def test_portfolio_id_must_match_execution_request() -> None:
    request = execution_request(
        portfolio_id="execution-portfolio"
    )

    with pytest.raises(
        ValueError,
        match=(
            "portfolio_id must match "
            "execution_request portfolio_id"
        ),
    ):
        workflow_request(
            portfolio_id="different-portfolio",
            request=request,
        )


def test_execution_request_must_not_follow_workflow_creation(
) -> None:
    request = execution_request()

    with pytest.raises(
        ValueError,
        match=(
            "execution_request created_at must not be "
            "later than workflow created_at"
        ),
    ):
        workflow_request(
            request=request,
            created_at=(
                request.created_at
                - timedelta(seconds=1)
            ),
        )


def test_execution_request_may_share_creation_time() -> None:
    request = execution_request()

    value = workflow_request(
        request=request,
        created_at=request.created_at,
    )

    assert value.created_at == request.created_at


def test_workflow_metadata_is_normalized() -> None:
    request = execution_request()

    value = TradingWorkflowRequest(
        workflow_id="workflow-001",
        correlation_id="correlation-001",
        strategy_id="strategy-001",
        portfolio_id="portfolio-001",
        execution_request=request,
        created_at=NOW,
        metadata=[
            ("  source  ", "  strategy  "),
            ("  channel  ", "  event-bus  "),
        ],
    )

    assert value.metadata == (
        ("source", "strategy"),
        ("channel", "event-bus"),
    )


def test_workflow_metadata_keys_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        TradingWorkflowRequest(
            workflow_id="workflow-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            execution_request=execution_request(),
            created_at=NOW,
            metadata=(
                ("source", "strategy"),
                ("source", "event-bus"),
            ),
        )


def test_workflow_metadata_items_must_be_pairs() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        TradingWorkflowRequest(
            workflow_id="workflow-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            execution_request=execution_request(),
            created_at=NOW,
            metadata=(
                ("source",),
            ),
        )


def test_workflow_request_is_immutable() -> None:
    value = workflow_request()

    with pytest.raises(FrozenInstanceError):
        value.priority = 1
def failed_checkpoint(
    *,
    checkpoint_id: str = "checkpoint-002",
    workflow_id: str = "workflow-001",
    stage: WorkflowStage = WorkflowStage.RISK,
    decision: WorkflowDecision = WorkflowDecision.REJECT,
    started_at: datetime = NOW,
    completed_at: datetime = NOW,
) -> WorkflowCheckpoint:
    return WorkflowCheckpoint(
        checkpoint_id=checkpoint_id,
        workflow_id=workflow_id,
        stage=stage,
        decision=decision,
        started_at=started_at,
        completed_at=completed_at,
        message="Workflow checkpoint failed.",
        successful=False,
        reference_id="reference-002",
        error="Checkpoint validation failed.",
    )


def test_successful_workflow_checkpoint() -> None:
    value = successful_checkpoint()

    assert value.checkpoint_id == "checkpoint-001"
    assert value.workflow_id == "workflow-001"
    assert value.stage is WorkflowStage.STRATEGY
    assert value.decision is WorkflowDecision.PROCEED
    assert value.successful is True
    assert value.error is None
    assert value.is_complete is True
    assert value.stage_position == 1


def test_failed_workflow_checkpoint() -> None:
    value = failed_checkpoint()

    assert value.stage is WorkflowStage.RISK
    assert value.decision is WorkflowDecision.REJECT
    assert value.successful is False
    assert value.error == (
        "Checkpoint validation failed."
    )
    assert value.is_complete is True


def test_checkpoint_may_be_incomplete() -> None:
    value = WorkflowCheckpoint(
        checkpoint_id="checkpoint-001",
        workflow_id="workflow-001",
        stage=WorkflowStage.STRATEGY,
        decision=WorkflowDecision.PROCEED,
        started_at=NOW,
        completed_at=None,
        message="Strategy validation started.",
        successful=True,
    )

    assert value.is_complete is False
    assert value.completed_at is None


def test_checkpoint_text_is_normalized() -> None:
    value = WorkflowCheckpoint(
        checkpoint_id="  checkpoint-001  ",
        workflow_id="  workflow-001  ",
        stage=WorkflowStage.ORDER,
        decision=WorkflowDecision.PROCEED,
        started_at=NOW,
        completed_at=NOW,
        message="  Order validation completed.  ",
        successful=True,
        reference_id="  order-001  ",
        warnings=[
            "  Review order quantity.  ",
        ],
        metadata=[
            ("  source  ", "  order-manager  "),
        ],
    )

    assert value.checkpoint_id == "checkpoint-001"
    assert value.workflow_id == "workflow-001"
    assert value.message == (
        "Order validation completed."
    )
    assert value.reference_id == "order-001"
    assert value.warnings == (
        "Review order quantity.",
    )
    assert value.metadata == (
        ("source", "order-manager"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "checkpoint_id",
        "workflow_id",
        "message",
    ],
)
def test_checkpoint_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "checkpoint_id": "checkpoint-001",
        "workflow_id": "workflow-001",
        "stage": WorkflowStage.STRATEGY,
        "decision": WorkflowDecision.PROCEED,
        "started_at": NOW,
        "completed_at": NOW,
        "message": "Checkpoint completed.",
        "successful": True,
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        WorkflowCheckpoint(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "checkpoint_id",
        "workflow_id",
        "message",
    ],
)
def test_checkpoint_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "checkpoint_id": "checkpoint-001",
        "workflow_id": "workflow-001",
        "stage": WorkflowStage.STRATEGY,
        "decision": WorkflowDecision.PROCEED,
        "started_at": NOW,
        "completed_at": NOW,
        "message": "Checkpoint completed.",
        "successful": True,
    }
    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        WorkflowCheckpoint(**arguments)


def test_checkpoint_requires_stage_enum() -> None:
    with pytest.raises(
        TypeError,
        match="stage must be a WorkflowStage",
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage="STRATEGY",
            decision=WorkflowDecision.PROCEED,
            started_at=NOW,
            message="Checkpoint completed.",
            successful=True,
        )


def test_checkpoint_requires_decision_enum() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "decision must be a WorkflowDecision"
        ),
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.STRATEGY,
            decision="PROCEED",
            started_at=NOW,
            message="Checkpoint completed.",
            successful=True,
        )


def test_checkpoint_successful_must_be_bool() -> None:
    with pytest.raises(
        TypeError,
        match="successful must be a bool",
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.STRATEGY,
            decision=WorkflowDecision.PROCEED,
            started_at=NOW,
            message="Checkpoint completed.",
            successful="yes",
        )


def test_checkpoint_started_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="started_at must be a datetime",
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.STRATEGY,
            decision=WorkflowDecision.PROCEED,
            started_at="2026-08-05",
            message="Checkpoint completed.",
            successful=True,
        )


def test_checkpoint_started_at_must_be_timezone_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="started_at must be timezone-aware",
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.STRATEGY,
            decision=WorkflowDecision.PROCEED,
            started_at=datetime(
                2026,
                8,
                5,
                18,
                0,
            ),
            message="Checkpoint completed.",
            successful=True,
        )


def test_checkpoint_completed_at_requires_datetime(
) -> None:
    with pytest.raises(
        TypeError,
        match="completed_at must be a datetime",
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.STRATEGY,
            decision=WorkflowDecision.PROCEED,
            started_at=NOW,
            completed_at="2026-08-05",
            message="Checkpoint completed.",
            successful=True,
        )


def test_checkpoint_completed_at_must_be_timezone_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="completed_at must be timezone-aware",
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.STRATEGY,
            decision=WorkflowDecision.PROCEED,
            started_at=NOW,
            completed_at=datetime(
                2026,
                8,
                5,
                18,
                1,
            ),
            message="Checkpoint completed.",
            successful=True,
        )


def test_checkpoint_completion_must_follow_start() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed_at must not be earlier "
            "than started_at"
        ),
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.STRATEGY,
            decision=WorkflowDecision.PROCEED,
            started_at=NOW,
            completed_at=(
                NOW - timedelta(seconds=1)
            ),
            message="Checkpoint completed.",
            successful=True,
        )


def test_successful_checkpoint_rejects_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "successful checkpoints must not "
            "include an error"
        ),
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.ORDER,
            decision=WorkflowDecision.PROCEED,
            started_at=NOW,
            completed_at=NOW,
            message="Order validation completed.",
            successful=True,
            error="Unexpected error.",
        )


@pytest.mark.parametrize(
    "decision",
    [
        WorkflowDecision.REJECT,
        WorkflowDecision.CANCEL,
    ],
)
def test_successful_checkpoint_rejects_terminal_decision(
    decision: WorkflowDecision,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "successful checkpoints must not use "
            "a reject or cancel decision"
        ),
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.RISK,
            decision=decision,
            started_at=NOW,
            completed_at=NOW,
            message="Invalid successful checkpoint.",
            successful=True,
        )


def test_unsuccessful_checkpoint_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "unsuccessful checkpoints must include "
            "an error"
        ),
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.RISK,
            decision=WorkflowDecision.REJECT,
            started_at=NOW,
            completed_at=NOW,
            message="Risk checkpoint failed.",
            successful=False,
        )


def test_unsuccessful_checkpoint_must_not_proceed() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "unsuccessful checkpoints must not proceed"
        ),
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.RISK,
            decision=WorkflowDecision.PROCEED,
            started_at=NOW,
            completed_at=NOW,
            message="Invalid unsuccessful checkpoint.",
            successful=False,
            error="Risk validation failed.",
        )


def test_checkpoint_reference_id_must_not_be_empty(
) -> None:
    with pytest.raises(
        ValueError,
        match="reference_id must not be empty",
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.ORDER,
            decision=WorkflowDecision.PROCEED,
            started_at=NOW,
            completed_at=NOW,
            message="Order checkpoint completed.",
            successful=True,
            reference_id="   ",
        )


def test_checkpoint_error_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="error must not be empty",
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.RISK,
            decision=WorkflowDecision.REJECT,
            started_at=NOW,
            completed_at=NOW,
            message="Risk checkpoint failed.",
            successful=False,
            error="   ",
        )


def test_checkpoint_warnings_are_normalized() -> None:
    value = WorkflowCheckpoint(
        checkpoint_id="checkpoint-001",
        workflow_id="workflow-001",
        stage=WorkflowStage.PORTFOLIO,
        decision=WorkflowDecision.HOLD,
        started_at=NOW,
        completed_at=NOW,
        message="Portfolio requires review.",
        successful=True,
        warnings=[
            "  Exposure is elevated.  ",
            "  Review concentration.  ",
        ],
    )

    assert value.warnings == (
        "Exposure is elevated.",
        "Review concentration.",
    )


def test_checkpoint_warnings_reject_empty_values() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.PORTFOLIO,
            decision=WorkflowDecision.HOLD,
            started_at=NOW,
            completed_at=NOW,
            message="Portfolio requires review.",
            successful=True,
            warnings=("   ",),
        )


def test_checkpoint_warnings_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.PORTFOLIO,
            decision=WorkflowDecision.HOLD,
            started_at=NOW,
            completed_at=NOW,
            message="Portfolio requires review.",
            successful=True,
            warnings=(123,),
        )


def test_checkpoint_metadata_is_normalized() -> None:
    value = WorkflowCheckpoint(
        checkpoint_id="checkpoint-001",
        workflow_id="workflow-001",
        stage=WorkflowStage.BROKER,
        decision=WorkflowDecision.PROCEED,
        started_at=NOW,
        completed_at=NOW,
        message="Broker checkpoint completed.",
        successful=True,
        metadata=[
            ("  broker  ", "  ibkr  "),
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.metadata == (
        ("broker", "ibkr"),
        ("environment", "paper"),
    )


def test_checkpoint_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        WorkflowCheckpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            stage=WorkflowStage.BROKER,
            decision=WorkflowDecision.PROCEED,
            started_at=NOW,
            completed_at=NOW,
            message="Broker checkpoint completed.",
            successful=True,
            metadata=(
                ("broker", "ibkr"),
                ("broker", "duplicate"),
            ),
        )


def test_checkpoint_stage_positions() -> None:
    positions = {
        WorkflowStage.STRATEGY: 1,
        WorkflowStage.SESSION: 2,
        WorkflowStage.PORTFOLIO: 3,
        WorkflowStage.ORDER: 4,
        WorkflowStage.RISK: 5,
        WorkflowStage.BROKER: 6,
        WorkflowStage.EXECUTION: 7,
    }

    for stage, expected_position in positions.items():
        checkpoint = successful_checkpoint(
            stage=stage
        )

        assert (
            checkpoint.stage_position
            == expected_position
        )


def test_checkpoint_is_immutable() -> None:
    value = successful_checkpoint()

    with pytest.raises(FrozenInstanceError):
        value.successful = False
WORKFLOW_START = NOW + timedelta(seconds=1)
WORKFLOW_UPDATE = NOW + timedelta(seconds=5)
WORKFLOW_COMPLETE = NOW + timedelta(seconds=5)


def execution_report() -> ExecutionReport:
    request = execution_request()

    step = ExecutionStep(
        step_id="execution-step-001",
        execution_id=request.execution_id,
        stage=ExecutionStage.BROKER,
        decision=ExecutionDecision.PROCEED,
        started_at=WORKFLOW_START,
        completed_at=WORKFLOW_START,
        message="Broker execution completed.",
        successful=True,
        reference_id="broker-order-001",
    )

    result = ExecutionResult(
        execution_id=request.execution_id,
        status=ExecutionStatus.COMPLETED,
        decision=ExecutionDecision.PROCEED,
        started_at=WORKFLOW_START,
        updated_at=WORKFLOW_UPDATE,
        completed_at=WORKFLOW_COMPLETE,
        steps=(step,),
        final_order_id=request.order_request.order_id,
        broker_order_id="broker-order-001",
    )

    return ExecutionReport(
        report_id="execution-report-001",
        request=request,
        result=result,
        reported_at=WORKFLOW_COMPLETE,
        message="Execution completed successfully.",
    )


def workflow_checkpoint(
    *,
    checkpoint_id: str = "checkpoint-001",
    workflow_id: str = "workflow-001",
    stage: WorkflowStage = WorkflowStage.STRATEGY,
    started_at: datetime = WORKFLOW_START,
    completed_at: datetime = WORKFLOW_START,
) -> WorkflowCheckpoint:
    return WorkflowCheckpoint(
        checkpoint_id=checkpoint_id,
        workflow_id=workflow_id,
        stage=stage,
        decision=WorkflowDecision.PROCEED,
        started_at=started_at,
        completed_at=completed_at,
        message="Workflow stage completed.",
        successful=True,
        reference_id=f"reference-{stage.value.lower()}",
    )


def unsuccessful_workflow_checkpoint(
    *,
    checkpoint_id: str = "checkpoint-002",
    workflow_id: str = "workflow-001",
    stage: WorkflowStage = WorkflowStage.RISK,
    decision: WorkflowDecision = WorkflowDecision.REJECT,
) -> WorkflowCheckpoint:
    return WorkflowCheckpoint(
        checkpoint_id=checkpoint_id,
        workflow_id=workflow_id,
        stage=stage,
        decision=decision,
        started_at=WORKFLOW_START,
        completed_at=WORKFLOW_START,
        message="Workflow stage did not pass.",
        successful=False,
        reference_id=f"reference-{stage.value.lower()}",
        error="Workflow stage validation failed.",
    )


def completed_workflow_result() -> TradingWorkflowResult:
    return TradingWorkflowResult(
        workflow_id="workflow-001",
        status=WorkflowStatus.COMPLETED,
        decision=WorkflowDecision.PROCEED,
        started_at=WORKFLOW_START,
        updated_at=WORKFLOW_UPDATE,
        completed_at=WORKFLOW_COMPLETE,
        checkpoints=(
            workflow_checkpoint(
                checkpoint_id="checkpoint-001",
                stage=WorkflowStage.STRATEGY,
                started_at=WORKFLOW_START,
                completed_at=WORKFLOW_START,
            ),
            workflow_checkpoint(
                checkpoint_id="checkpoint-002",
                stage=WorkflowStage.SESSION,
                started_at=(
                    WORKFLOW_START
                    + timedelta(seconds=1)
                ),
                completed_at=(
                    WORKFLOW_START
                    + timedelta(seconds=1)
                ),
            ),
            workflow_checkpoint(
                checkpoint_id="checkpoint-003",
                stage=WorkflowStage.RISK,
                started_at=(
                    WORKFLOW_START
                    + timedelta(seconds=2)
                ),
                completed_at=(
                    WORKFLOW_START
                    + timedelta(seconds=2)
                ),
            ),
            workflow_checkpoint(
                checkpoint_id="checkpoint-004",
                stage=WorkflowStage.EXECUTION,
                started_at=(
                    WORKFLOW_START
                    + timedelta(seconds=3)
                ),
                completed_at=(
                    WORKFLOW_START
                    + timedelta(seconds=3)
                ),
            ),
        ),
        execution_report=execution_report(),
    )


def test_running_workflow_result() -> None:
    value = TradingWorkflowResult(
        workflow_id="workflow-001",
        status=WorkflowStatus.RUNNING,
        decision=WorkflowDecision.PROCEED,
        started_at=WORKFLOW_START,
        updated_at=WORKFLOW_START,
    )

    assert value.status is WorkflowStatus.RUNNING
    assert value.decision is WorkflowDecision.PROCEED
    assert value.checkpoints == ()
    assert value.completed_at is None
    assert value.is_terminal is False
    assert value.successful_checkpoint_count == 0
    assert value.failed_checkpoint is None


def test_completed_workflow_result() -> None:
    value = completed_workflow_result()

    assert value.status is WorkflowStatus.COMPLETED
    assert value.decision is WorkflowDecision.PROCEED
    assert value.is_terminal is True
    assert value.execution_report is not None
    assert value.successful_checkpoint_count == 4
    assert value.failed_checkpoint is None


def test_held_workflow_result() -> None:
    checkpoint = unsuccessful_workflow_checkpoint(
        stage=WorkflowStage.PORTFOLIO,
        decision=WorkflowDecision.HOLD,
    )

    value = TradingWorkflowResult(
        workflow_id="workflow-001",
        status=WorkflowStatus.HELD,
        decision=WorkflowDecision.HOLD,
        started_at=WORKFLOW_START,
        updated_at=WORKFLOW_START,
        completed_at=WORKFLOW_START,
        checkpoints=(checkpoint,),
    )

    assert value.status is WorkflowStatus.HELD
    assert value.is_terminal is True
    assert value.failed_checkpoint == checkpoint


def test_rejected_workflow_result() -> None:
    checkpoint = unsuccessful_workflow_checkpoint()

    value = TradingWorkflowResult(
        workflow_id="workflow-001",
        status=WorkflowStatus.REJECTED,
        decision=WorkflowDecision.REJECT,
        started_at=WORKFLOW_START,
        updated_at=WORKFLOW_START,
        completed_at=WORKFLOW_START,
        checkpoints=(checkpoint,),
    )

    assert value.status is WorkflowStatus.REJECTED
    assert value.decision is WorkflowDecision.REJECT
    assert value.is_terminal is True


def test_cancelled_workflow_result() -> None:
    checkpoint = unsuccessful_workflow_checkpoint(
        stage=WorkflowStage.ORDER,
        decision=WorkflowDecision.CANCEL,
    )

    value = TradingWorkflowResult(
        workflow_id="workflow-001",
        status=WorkflowStatus.CANCELLED,
        decision=WorkflowDecision.CANCEL,
        started_at=WORKFLOW_START,
        updated_at=WORKFLOW_START,
        completed_at=WORKFLOW_START,
        checkpoints=(checkpoint,),
    )

    assert value.status is WorkflowStatus.CANCELLED
    assert value.decision is WorkflowDecision.CANCEL
    assert value.is_terminal is True


def test_failed_workflow_result() -> None:
    checkpoint = unsuccessful_workflow_checkpoint(
        stage=WorkflowStage.BROKER,
        decision=WorkflowDecision.NO_ACTION,
    )

    value = TradingWorkflowResult(
        workflow_id="workflow-001",
        status=WorkflowStatus.FAILED,
        decision=WorkflowDecision.NO_ACTION,
        started_at=WORKFLOW_START,
        updated_at=WORKFLOW_START,
        completed_at=WORKFLOW_START,
        checkpoints=(checkpoint,),
        error="Trading workflow failed.",
    )

    assert value.status is WorkflowStatus.FAILED
    assert value.error == "Trading workflow failed."
    assert value.is_terminal is True


def test_result_workflow_id_is_normalized() -> None:
    value = TradingWorkflowResult(
        workflow_id="  workflow-001  ",
        status=WorkflowStatus.RUNNING,
        decision=WorkflowDecision.PROCEED,
        started_at=WORKFLOW_START,
        updated_at=WORKFLOW_START,
    )

    assert value.workflow_id == "workflow-001"


def test_result_workflow_id_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="workflow_id must not be empty",
    ):
        TradingWorkflowResult(
            workflow_id="   ",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_START,
        )


def test_result_requires_status_enum() -> None:
    with pytest.raises(
        TypeError,
        match="status must be a WorkflowStatus",
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status="RUNNING",
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_START,
        )


def test_result_requires_decision_enum() -> None:
    with pytest.raises(
        TypeError,
        match="decision must be a WorkflowDecision",
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision="PROCEED",
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_START,
        )


def test_result_started_at_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="started_at must be timezone-aware",
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=datetime(2026, 8, 5, 18, 0),
            updated_at=WORKFLOW_START,
        )


def test_result_updated_at_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="updated_at must be timezone-aware",
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=datetime(2026, 8, 5, 18, 1),
        )


def test_result_updated_at_must_follow_start() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "updated_at must not be earlier than started_at"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=(
                WORKFLOW_START - timedelta(seconds=1)
            ),
        )


def test_result_completed_at_must_follow_update() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed_at must not be earlier "
            "than updated_at"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.REJECTED,
            decision=WorkflowDecision.REJECT,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            completed_at=WORKFLOW_START,
        )


def test_result_checkpoints_require_checkpoint_models() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "every checkpoint must be "
            "a WorkflowCheckpoint"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            checkpoints=(object(),),
        )


def test_checkpoint_workflow_id_must_match_result() -> None:
    checkpoint = workflow_checkpoint(
        workflow_id="different-workflow"
    )

    with pytest.raises(
        ValueError,
        match=(
            "checkpoint workflow_id must match result"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            checkpoints=(checkpoint,),
        )


def test_checkpoint_must_not_precede_result_start() -> None:
    checkpoint = workflow_checkpoint(
        started_at=(
            WORKFLOW_START - timedelta(seconds=1)
        ),
        completed_at=WORKFLOW_START,
    )

    with pytest.raises(
        ValueError,
        match=(
            "checkpoint started_at must not be earlier "
            "than result started_at"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            checkpoints=(checkpoint,),
        )


def test_checkpoint_must_not_follow_result_update() -> None:
    checkpoint = workflow_checkpoint(
        started_at=(
            WORKFLOW_UPDATE + timedelta(seconds=1)
        ),
        completed_at=(
            WORKFLOW_UPDATE + timedelta(seconds=1)
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "checkpoint started_at must not be later "
            "than result updated_at"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            checkpoints=(checkpoint,),
        )


def test_checkpoint_ids_must_be_unique() -> None:
    checkpoint = workflow_checkpoint()

    with pytest.raises(
        ValueError,
        match="checkpoint_id values must be unique",
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            checkpoints=(checkpoint, checkpoint),
        )


def test_checkpoints_must_be_ordered_by_stage() -> None:
    risk_checkpoint = workflow_checkpoint(
        checkpoint_id="checkpoint-001",
        stage=WorkflowStage.RISK,
    )
    order_checkpoint = workflow_checkpoint(
        checkpoint_id="checkpoint-002",
        stage=WorkflowStage.ORDER,
    )

    with pytest.raises(
        ValueError,
        match=(
            "checkpoints must be ordered "
            "by workflow stage"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            checkpoints=(
                risk_checkpoint,
                order_checkpoint,
            ),
        )


def test_workflow_stages_must_be_unique() -> None:
    first = workflow_checkpoint(
        checkpoint_id="checkpoint-001",
        stage=WorkflowStage.ORDER,
    )
    second = workflow_checkpoint(
        checkpoint_id="checkpoint-002",
        stage=WorkflowStage.ORDER,
    )

    with pytest.raises(
        ValueError,
        match="workflow stages must be unique",
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            checkpoints=(first, second),
        )


def test_execution_report_requires_correct_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "execution_report must be an "
            "ExecutionReport or None"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            execution_report=object(),
        )


def test_terminal_result_requires_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "terminal workflow results must include "
            "completed_at"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.REJECTED,
            decision=WorkflowDecision.REJECT,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
        )


def test_non_terminal_result_rejects_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-terminal workflow results must not "
            "include completed_at"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            completed_at=WORKFLOW_UPDATE,
        )


def test_completed_result_requires_proceed_decision() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed workflows require "
            "a proceed decision"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.COMPLETED,
            decision=WorkflowDecision.HOLD,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            completed_at=WORKFLOW_COMPLETE,
            checkpoints=(workflow_checkpoint(),),
            execution_report=execution_report(),
        )


def test_completed_result_requires_execution_report() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed workflows must include "
            "execution_report"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.COMPLETED,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            completed_at=WORKFLOW_COMPLETE,
            checkpoints=(workflow_checkpoint(),),
        )


def test_completed_result_requires_checkpoints() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed workflows must include checkpoints"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.COMPLETED,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            completed_at=WORKFLOW_COMPLETE,
            execution_report=execution_report(),
        )


def test_completed_result_requires_successful_checkpoints(
) -> None:
    checkpoint = unsuccessful_workflow_checkpoint()

    with pytest.raises(
        ValueError,
        match=(
            "completed workflows require all "
            "checkpoints to be successful"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.COMPLETED,
            decision=WorkflowDecision.PROCEED,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            completed_at=WORKFLOW_COMPLETE,
            checkpoints=(checkpoint,),
            execution_report=execution_report(),
        )


@pytest.mark.parametrize(
    ("status", "decision", "expected_message"),
    [
        (
            WorkflowStatus.HELD,
            WorkflowDecision.REJECT,
            "held workflows require a hold decision",
        ),
        (
            WorkflowStatus.REJECTED,
            WorkflowDecision.HOLD,
            "rejected workflows require a reject decision",
        ),
        (
            WorkflowStatus.CANCELLED,
            WorkflowDecision.REJECT,
            "cancelled workflows require a cancel decision",
        ),
    ],
)
def test_terminal_status_requires_matching_decision(
    status: WorkflowStatus,
    decision: WorkflowDecision,
    expected_message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=status,
            decision=decision,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            completed_at=WORKFLOW_COMPLETE,
        )


def test_failed_result_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed workflows must include an error",
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.FAILED,
            decision=WorkflowDecision.NO_ACTION,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            completed_at=WORKFLOW_COMPLETE,
        )


def test_non_failed_result_rejects_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only failed workflows may include an error"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.REJECTED,
            decision=WorkflowDecision.REJECT,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
            completed_at=WORKFLOW_COMPLETE,
            error="Unexpected error.",
        )


def test_running_result_requires_proceed_decision() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "running workflows require "
            "a proceed decision"
        ),
    ):
        TradingWorkflowResult(
            workflow_id="workflow-001",
            status=WorkflowStatus.RUNNING,
            decision=WorkflowDecision.HOLD,
            started_at=WORKFLOW_START,
            updated_at=WORKFLOW_UPDATE,
        )


def test_result_warnings_are_normalized() -> None:
    value = TradingWorkflowResult(
        workflow_id="workflow-001",
        status=WorkflowStatus.RUNNING,
        decision=WorkflowDecision.PROCEED,
        started_at=WORKFLOW_START,
        updated_at=WORKFLOW_UPDATE,
        warnings=[
            "  Review workflow latency.  ",
            "  Review execution costs.  ",
        ],
    )

    assert value.warnings == (
        "Review workflow latency.",
        "Review execution costs.",
    )


def test_result_is_immutable() -> None:
    value = completed_workflow_result()

    with pytest.raises(FrozenInstanceError):
        value.status = WorkflowStatus.FAILED
def workflow_report(
    *,
    report_id: str = "workflow-report-001",
    request: TradingWorkflowRequest | None = None,
    result: TradingWorkflowResult | None = None,
    reported_at: datetime = (
        WORKFLOW_COMPLETE + timedelta(seconds=1)
    ),
) -> TradingWorkflowReport:
    effective_request = request or workflow_request()
    effective_result = (
        result or completed_workflow_result()
    )

    return TradingWorkflowReport(
        report_id=report_id,
        request=effective_request,
        result=effective_result,
        reported_at=reported_at,
        message="Trading workflow completed.",
        metadata=(
            ("source", "trading-orchestrator"),
        ),
        warnings=(
            "Review final execution costs.",
        ),
    )


def test_trading_workflow_report() -> None:
    value = workflow_report()

    assert value.report_id == "workflow-report-001"
    assert value.request.workflow_id == "workflow-001"
    assert value.result.workflow_id == "workflow-001"
    assert value.message == (
        "Trading workflow completed."
    )
    assert value.reported_at == (
        WORKFLOW_COMPLETE + timedelta(seconds=1)
    )


def test_workflow_report_text_is_normalized() -> None:
    value = TradingWorkflowReport(
        report_id="  workflow-report-001  ",
        request=workflow_request(),
        result=completed_workflow_result(),
        reported_at=(
            WORKFLOW_COMPLETE + timedelta(seconds=1)
        ),
        message="  Trading workflow completed.  ",
        metadata=[
            (
                "  source  ",
                "  trading-orchestrator  ",
            ),
        ],
        warnings=[
            "  Review execution costs.  ",
        ],
    )

    assert value.report_id == "workflow-report-001"
    assert value.message == (
        "Trading workflow completed."
    )
    assert value.metadata == (
        ("source", "trading-orchestrator"),
    )
    assert value.warnings == (
        "Review execution costs.",
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_workflow_report_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "report_id": "workflow-report-001",
        "request": workflow_request(),
        "result": completed_workflow_result(),
        "reported_at": (
            WORKFLOW_COMPLETE + timedelta(seconds=1)
        ),
        "message": "Trading workflow completed.",
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        TradingWorkflowReport(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_workflow_report_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "report_id": "workflow-report-001",
        "request": workflow_request(),
        "result": completed_workflow_result(),
        "reported_at": (
            WORKFLOW_COMPLETE + timedelta(seconds=1)
        ),
        "message": "Trading workflow completed.",
    }
    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        TradingWorkflowReport(**arguments)


def test_workflow_report_requires_request_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "request must be a TradingWorkflowRequest"
        ),
    ):
        TradingWorkflowReport(
            report_id="workflow-report-001",
            request=object(),
            result=completed_workflow_result(),
            reported_at=(
                WORKFLOW_COMPLETE
                + timedelta(seconds=1)
            ),
            message="Trading workflow completed.",
        )


def test_workflow_report_requires_result_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "result must be a TradingWorkflowResult"
        ),
    ):
        TradingWorkflowReport(
            report_id="workflow-report-001",
            request=workflow_request(),
            result=object(),
            reported_at=(
                WORKFLOW_COMPLETE
                + timedelta(seconds=1)
            ),
            message="Trading workflow completed.",
        )


def test_workflow_reported_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="reported_at must be a datetime",
    ):
        TradingWorkflowReport(
            report_id="workflow-report-001",
            request=workflow_request(),
            result=completed_workflow_result(),
            reported_at="2026-08-05",
            message="Trading workflow completed.",
        )


def test_workflow_reported_at_must_be_timezone_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="reported_at must be timezone-aware",
    ):
        TradingWorkflowReport(
            report_id="workflow-report-001",
            request=workflow_request(),
            result=completed_workflow_result(),
            reported_at=datetime(
                2026,
                8,
                5,
                18,
                10,
            ),
            message="Trading workflow completed.",
        )


def test_workflow_report_ids_must_match() -> None:
    result = TradingWorkflowResult(
        workflow_id="different-workflow",
        status=WorkflowStatus.RUNNING,
        decision=WorkflowDecision.PROCEED,
        started_at=WORKFLOW_START,
        updated_at=WORKFLOW_UPDATE,
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result workflow_id values "
            "must match"
        ),
    ):
        TradingWorkflowReport(
            report_id="workflow-report-001",
            request=workflow_request(),
            result=result,
            reported_at=(
                WORKFLOW_UPDATE + timedelta(seconds=1)
            ),
            message="Trading workflow report.",
        )


def test_result_must_not_precede_workflow_request() -> None:
    request = workflow_request()

    result = TradingWorkflowResult(
        workflow_id=request.workflow_id,
        status=WorkflowStatus.RUNNING,
        decision=WorkflowDecision.PROCEED,
        started_at=(
            request.created_at - timedelta(seconds=1)
        ),
        updated_at=request.created_at,
    )

    with pytest.raises(
        ValueError,
        match=(
            "result started_at must not be earlier "
            "than request created_at"
        ),
    ):
        TradingWorkflowReport(
            report_id="workflow-report-001",
            request=request,
            result=result,
            reported_at=request.created_at,
            message="Trading workflow report.",
        )


def test_reported_at_must_follow_result_update() -> None:
    result = TradingWorkflowResult(
        workflow_id="workflow-001",
        status=WorkflowStatus.RUNNING,
        decision=WorkflowDecision.PROCEED,
        started_at=WORKFLOW_START,
        updated_at=WORKFLOW_UPDATE,
    )

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier "
            "than result updated_at"
        ),
    ):
        TradingWorkflowReport(
            report_id="workflow-report-001",
            request=workflow_request(),
            result=result,
            reported_at=(
                WORKFLOW_UPDATE - timedelta(seconds=1)
            ),
            message="Trading workflow report.",
        )


def test_reported_at_must_follow_completed_result_update(
) -> None:
    result = completed_workflow_result()

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier "
            "than result updated_at"
        ),
    ):
        TradingWorkflowReport(
            report_id="workflow-report-001",
            request=workflow_request(),
            result=result,
            reported_at=(
                result.updated_at - timedelta(seconds=1)
            ),
            message="Trading workflow report.",
        )

def test_workflow_report_metadata_is_normalized() -> None:
    value = TradingWorkflowReport(
        report_id="workflow-report-001",
        request=workflow_request(),
        result=completed_workflow_result(),
        reported_at=(
            WORKFLOW_COMPLETE + timedelta(seconds=1)
        ),
        message="Trading workflow completed.",
        metadata=[
            ("  source  ", "  orchestrator  "),
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.metadata == (
        ("source", "orchestrator"),
        ("environment", "paper"),
    )


def test_workflow_report_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        TradingWorkflowReport(
            report_id="workflow-report-001",
            request=workflow_request(),
            result=completed_workflow_result(),
            reported_at=(
                WORKFLOW_COMPLETE
                + timedelta(seconds=1)
            ),
            message="Trading workflow completed.",
            metadata=(
                ("source", "orchestrator"),
                ("source", "duplicate"),
            ),
        )


def test_workflow_report_metadata_items_must_be_pairs(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        TradingWorkflowReport(
            report_id="workflow-report-001",
            request=workflow_request(),
            result=completed_workflow_result(),
            reported_at=(
                WORKFLOW_COMPLETE
                + timedelta(seconds=1)
            ),
            message="Trading workflow completed.",
            metadata=(
                ("source",),
            ),
        )


def test_workflow_report_warnings_are_normalized() -> None:
    value = TradingWorkflowReport(
        report_id="workflow-report-001",
        request=workflow_request(),
        result=completed_workflow_result(),
        reported_at=(
            WORKFLOW_COMPLETE + timedelta(seconds=1)
        ),
        message="Trading workflow completed.",
        warnings=[
            "  Review latency.  ",
            "  Review commission.  ",
        ],
    )

    assert value.warnings == (
        "Review latency.",
        "Review commission.",
    )


def test_workflow_report_warnings_reject_empty_values(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        TradingWorkflowReport(
            report_id="workflow-report-001",
            request=workflow_request(),
            result=completed_workflow_result(),
            reported_at=(
                WORKFLOW_COMPLETE
                + timedelta(seconds=1)
            ),
            message="Trading workflow completed.",
            warnings=("   ",),
        )


def test_workflow_report_warnings_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        TradingWorkflowReport(
            report_id="workflow-report-001",
            request=workflow_request(),
            result=completed_workflow_result(),
            reported_at=(
                WORKFLOW_COMPLETE
                + timedelta(seconds=1)
            ),
            message="Trading workflow completed.",
            warnings=(123,),
        )


def test_workflow_report_is_immutable() -> None:
    value = workflow_report()

    with pytest.raises(FrozenInstanceError):
        value.message = "Changed."