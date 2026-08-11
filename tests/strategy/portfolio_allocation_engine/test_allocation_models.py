from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.portfolio_allocation_engine import (
    AllocationAction,
    AllocationDecision,
    AllocationDirection,
    AllocationStatus,
    AllocationStrength,
    PortfolioAllocation,
    PortfolioAllocationReport,
    PortfolioAllocationRequest,
    PortfolioAllocationResult,
)

NOW = datetime(
    2026,
    8,
    10,
    23,
    0,
    tzinfo=timezone.utc,
)


def allocation_request(
    *,
    request_id: str = "request-001",
    correlation_id: str = "correlation-001",
    strategy_id: str = "strategy-001",
    portfolio_id: str = "portfolio-001",
    signal_id: str = "signal-001",
    symbol: str = "NVDA",
    action: AllocationAction = AllocationAction.OPEN,
    direction: AllocationDirection = AllocationDirection.LONG,
    strength: AllocationStrength = AllocationStrength.HIGH,
    target_allocation_percent: int = 10,
    confidence: int = 85,
    created_at: datetime = NOW,
    sequence_number: int = 1,
    requested_by: str = "allocation-engine",
    is_replay: bool = False,
) -> PortfolioAllocationRequest:
    return PortfolioAllocationRequest(
        request_id=request_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        signal_id=signal_id,
        symbol=symbol,
        action=action,
        direction=direction,
        strength=strength,
        target_allocation_percent=(
            target_allocation_percent
        ),
        confidence=confidence,
        created_at=created_at,
        sequence_number=sequence_number,
        requested_by=requested_by,
        is_replay=is_replay,
        metadata=(
            ("environment", "paper"),
        ),
    )


def test_portfolio_allocation_request() -> None:
    value = allocation_request()

    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.signal_id == "signal-001"
    assert value.symbol == "NVDA"
    assert value.action is AllocationAction.OPEN
    assert value.direction is AllocationDirection.LONG
    assert value.strength is AllocationStrength.HIGH
    assert value.target_allocation_percent == 10
    assert value.confidence == 85
    assert value.created_at == NOW
    assert value.sequence_number == 1
    assert value.requested_by == "allocation-engine"
    assert value.is_replay is False
    assert value.metadata == (
        ("environment", "paper"),
    )


def test_allocation_request_text_is_normalized() -> None:
    value = PortfolioAllocationRequest(
        request_id="  request-001  ",
        correlation_id="  correlation-001  ",
        strategy_id="  strategy-001  ",
        portfolio_id="  portfolio-001  ",
        signal_id="  signal-001  ",
        symbol="  nvda  ",
        action=AllocationAction.OPEN,
        direction=AllocationDirection.LONG,
        strength=AllocationStrength.HIGH,
        target_allocation_percent=10,
        confidence=85,
        created_at=NOW,
        sequence_number=1,
        requested_by="  allocation-engine  ",
        metadata=[
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.signal_id == "signal-001"
    assert value.symbol == "NVDA"
    assert value.requested_by == "allocation-engine"
    assert value.metadata == (
        ("environment", "paper"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "signal_id",
        "symbol",
        "requested_by",
    ],
)
def test_allocation_request_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "signal_id": "signal-001",
        "symbol": "NVDA",
        "action": AllocationAction.OPEN,
        "direction": AllocationDirection.LONG,
        "strength": AllocationStrength.HIGH,
        "target_allocation_percent": 10,
        "confidence": 85,
        "created_at": NOW,
        "sequence_number": 1,
        "requested_by": "allocation-engine",
    }

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        PortfolioAllocationRequest(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "signal_id",
        "symbol",
        "requested_by",
    ],
)
def test_allocation_request_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "signal_id": "signal-001",
        "symbol": "NVDA",
        "action": AllocationAction.OPEN,
        "direction": AllocationDirection.LONG,
        "strength": AllocationStrength.HIGH,
        "target_allocation_percent": 10,
        "confidence": 85,
        "created_at": NOW,
        "sequence_number": 1,
        "requested_by": "allocation-engine",
    }

    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        PortfolioAllocationRequest(**arguments)


def test_allocation_request_requires_action_enum() -> None:
    with pytest.raises(
        TypeError,
        match="action must be an AllocationAction",
    ):
        allocation_request(
            action="OPEN"
        )


def test_allocation_request_requires_direction_enum() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "direction must be an AllocationDirection"
        ),
    ):
        allocation_request(
            direction="LONG"
        )


def test_allocation_request_requires_strength_enum() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "strength must be an AllocationStrength"
        ),
    ):
        allocation_request(
            strength="HIGH"
        )


@pytest.mark.parametrize(
    "value",
    [
        -1,
        101,
    ],
)
def test_target_allocation_percent_bounds(
    value: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "target_allocation_percent must be "
            "between 0 and 100"
        ),
    ):
        allocation_request(
            target_allocation_percent=value
        )


def test_target_allocation_percent_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "target_allocation_percent must be an integer"
        ),
    ):
        allocation_request(
            target_allocation_percent="10"
        )


def test_target_allocation_percent_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "target_allocation_percent must be an integer"
        ),
    ):
        allocation_request(
            target_allocation_percent=True
        )


@pytest.mark.parametrize(
    "value",
    [
        0,
        100,
    ],
)
def test_target_allocation_percent_boundaries_allowed(
    value: int,
) -> None:
    kwargs = {}

    if value == 0:
        kwargs = {
            "action": AllocationAction.CLOSE,
            "direction": AllocationDirection.LONG,
        }

    request = allocation_request(
        target_allocation_percent=value,
        **kwargs,
    )

    assert request.target_allocation_percent == value


@pytest.mark.parametrize(
    "confidence",
    [
        -1,
        101,
    ],
)
def test_allocation_request_confidence_bounds(
    confidence: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="confidence must be between 0 and 100",
    ):
        allocation_request(
            confidence=confidence
        )


def test_allocation_request_confidence_requires_integer(
) -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        allocation_request(
            confidence="85"
        )


def test_allocation_request_confidence_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        allocation_request(
            confidence=True
        )


@pytest.mark.parametrize(
    "confidence",
    [
        0,
        100,
    ],
)
def test_allocation_request_confidence_boundaries_allowed(
    confidence: int,
) -> None:
    value = allocation_request(
        confidence=confidence
    )

    assert value.confidence == confidence


def test_allocation_request_created_at_requires_datetime(
) -> None:
    with pytest.raises(
        TypeError,
        match="created_at must be a datetime",
    ):
        PortfolioAllocationRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=AllocationAction.OPEN,
            direction=AllocationDirection.LONG,
            strength=AllocationStrength.HIGH,
            target_allocation_percent=10,
            confidence=85,
            created_at="2026-08-10",
            sequence_number=1,
            requested_by="allocation-engine",
        )


def test_allocation_request_created_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="created_at must be timezone-aware",
    ):
        allocation_request(
            created_at=datetime(
                2026,
                8,
                10,
                23,
                0,
            )
        )


def test_allocation_request_sequence_requires_integer(
) -> None:
    with pytest.raises(
        TypeError,
        match="sequence_number must be an integer",
    ):
        allocation_request(
            sequence_number="1"
        )


def test_allocation_request_sequence_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="sequence_number must be an integer",
    ):
        allocation_request(
            sequence_number=True
        )


def test_allocation_request_sequence_must_not_be_negative(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "sequence_number must not be negative"
        ),
    ):
        allocation_request(
            sequence_number=-1
        )


def test_zero_sequence_number_is_allowed() -> None:
    value = allocation_request(
        sequence_number=0
    )

    assert value.sequence_number == 0


def test_allocation_request_replay_requires_bool() -> None:
    with pytest.raises(
        TypeError,
        match="is_replay must be a bool",
    ):
        allocation_request(
            is_replay="yes"
        )


def test_replay_allocation_request() -> None:
    value = allocation_request(
        is_replay=True
    )

    assert value.is_replay is True


def test_hold_allocation_requires_flat_direction() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "HOLD allocations require FLAT direction"
        ),
    ):
        allocation_request(
            action=AllocationAction.HOLD,
            direction=AllocationDirection.LONG,
            target_allocation_percent=0,
        )


def test_hold_allocation_requires_zero_target() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "HOLD allocations require "
            "target_allocation_percent of 0"
        ),
    ):
        allocation_request(
            action=AllocationAction.HOLD,
            direction=AllocationDirection.FLAT,
            target_allocation_percent=10,
        )


def test_hold_allocation_is_not_actionable() -> None:
    value = allocation_request(
        action=AllocationAction.HOLD,
        direction=AllocationDirection.FLAT,
        target_allocation_percent=0,
    )

    assert value.is_actionable is False


def test_open_allocation_rejects_flat_direction() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "OPEN allocations require LONG or SHORT direction"
        ),
    ):
        allocation_request(
            action=AllocationAction.OPEN,
            direction=AllocationDirection.FLAT,
        )


@pytest.mark.parametrize(
    "action",
    [
        AllocationAction.INCREASE,
        AllocationAction.DECREASE,
        AllocationAction.REBALANCE,
    ],
)
def test_directional_allocation_rejects_flat_direction(
    action: AllocationAction,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            f"{action.value} allocations require "
            "LONG or SHORT direction"
        ),
    ):
        allocation_request(
            action=action,
            direction=AllocationDirection.FLAT,
        )


def test_close_allocation_requires_zero_target() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "CLOSE allocations require "
            "target_allocation_percent of 0"
        ),
    ):
        allocation_request(
            action=AllocationAction.CLOSE,
            direction=AllocationDirection.LONG,
            target_allocation_percent=5,
        )


def test_close_allocation_with_zero_target() -> None:
    value = allocation_request(
        action=AllocationAction.CLOSE,
        direction=AllocationDirection.LONG,
        target_allocation_percent=0,
    )

    assert value.is_closing is True
    assert value.is_opening is False
    assert value.is_actionable is True


def test_opening_property() -> None:
    value = allocation_request()

    assert value.is_opening is True
    assert value.is_closing is False
    assert value.is_actionable is True


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (79, False),
        (80, True),
        (100, True),
    ],
)
def test_high_confidence_property(
    confidence: int,
    expected: bool,
) -> None:
    value = allocation_request(
        confidence=confidence
    )

    assert value.is_high_confidence is expected


def test_allocation_request_metadata_is_normalized() -> None:
    value = PortfolioAllocationRequest(
        request_id="request-001",
        correlation_id="correlation-001",
        strategy_id="strategy-001",
        portfolio_id="portfolio-001",
        signal_id="signal-001",
        symbol="NVDA",
        action=AllocationAction.OPEN,
        direction=AllocationDirection.LONG,
        strength=AllocationStrength.HIGH,
        target_allocation_percent=10,
        confidence=85,
        created_at=NOW,
        sequence_number=1,
        requested_by="allocation-engine",
        metadata=[
            ("  environment  ", "  paper  "),
            ("  model  ", "  allocation-v1  "),
        ],
    )

    assert value.metadata == (
        ("environment", "paper"),
        ("model", "allocation-v1"),
    )


def test_allocation_request_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        PortfolioAllocationRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=AllocationAction.OPEN,
            direction=AllocationDirection.LONG,
            strength=AllocationStrength.HIGH,
            target_allocation_percent=10,
            confidence=85,
            created_at=NOW,
            sequence_number=1,
            requested_by="allocation-engine",
            metadata=(
                ("model", "one"),
                ("model", "two"),
            ),
        )


def test_allocation_request_metadata_items_must_be_pairs(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        PortfolioAllocationRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=AllocationAction.OPEN,
            direction=AllocationDirection.LONG,
            strength=AllocationStrength.HIGH,
            target_allocation_percent=10,
            confidence=85,
            created_at=NOW,
            sequence_number=1,
            requested_by="allocation-engine",
            metadata=(
                ("model",),
            ),
        )


def test_allocation_request_metadata_keys_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        PortfolioAllocationRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=AllocationAction.OPEN,
            direction=AllocationDirection.LONG,
            strength=AllocationStrength.HIGH,
            target_allocation_percent=10,
            confidence=85,
            created_at=NOW,
            sequence_number=1,
            requested_by="allocation-engine",
            metadata=(
                (123, "allocation-v1"),
            ),
        )


def test_allocation_request_metadata_values_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        PortfolioAllocationRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=AllocationAction.OPEN,
            direction=AllocationDirection.LONG,
            strength=AllocationStrength.HIGH,
            target_allocation_percent=10,
            confidence=85,
            created_at=NOW,
            sequence_number=1,
            requested_by="allocation-engine",
            metadata=(
                ("model", 123),
            ),
        )


def test_portfolio_allocation_request_is_immutable() -> None:
    value = allocation_request()

    with pytest.raises(FrozenInstanceError):
        value.request_id = "changed"
def portfolio_allocation(
    *,
    allocation_id: str = "allocation-001",
    request_id: str = "request-001",
    correlation_id: str = "correlation-001",
    strategy_id: str = "strategy-001",
    portfolio_id: str = "portfolio-001",
    signal_id: str = "signal-001",
    symbol: str = "NVDA",
    action: AllocationAction = AllocationAction.OPEN,
    direction: AllocationDirection = AllocationDirection.LONG,
    strength: AllocationStrength = AllocationStrength.HIGH,
    target_allocation_percent: int = 10,
    confidence: int = 85,
    generated_at: datetime = NOW,
    expires_at: datetime | None = None,
    rationale: str = "Portfolio sizing supports the allocation.",
    warnings: tuple[str, ...] = (),
) -> PortfolioAllocation:
    return PortfolioAllocation(
        allocation_id=allocation_id,
        request_id=request_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        signal_id=signal_id,
        symbol=symbol,
        action=action,
        direction=direction,
        strength=strength,
        target_allocation_percent=target_allocation_percent,
        confidence=confidence,
        generated_at=generated_at,
        expires_at=expires_at,
        rationale=rationale,
        warnings=warnings,
        metadata=(
            ("environment", "paper"),
        ),
    )


def test_portfolio_allocation() -> None:
    value = portfolio_allocation()

    assert value.allocation_id == "allocation-001"
    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.signal_id == "signal-001"
    assert value.symbol == "NVDA"
    assert value.action is AllocationAction.OPEN
    assert value.direction is AllocationDirection.LONG
    assert value.strength is AllocationStrength.HIGH
    assert value.target_allocation_percent == 10
    assert value.confidence == 85
    assert value.generated_at == NOW
    assert value.expires_at is None
    assert value.rationale == (
        "Portfolio sizing supports the allocation."
    )
    assert value.is_actionable is True
    assert value.is_high_confidence is True
    assert value.has_expiration is False


def test_portfolio_allocation_text_is_normalized() -> None:
    value = PortfolioAllocation(
        allocation_id="  allocation-001  ",
        request_id="  request-001  ",
        correlation_id="  correlation-001  ",
        strategy_id="  strategy-001  ",
        portfolio_id="  portfolio-001  ",
        signal_id="  signal-001  ",
        symbol="  nvda  ",
        action=AllocationAction.OPEN,
        direction=AllocationDirection.LONG,
        strength=AllocationStrength.HIGH,
        target_allocation_percent=10,
        confidence=85,
        generated_at=NOW,
        expires_at=None,
        rationale="  Portfolio sizing supports the allocation.  ",
        metadata=[
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.allocation_id == "allocation-001"
    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.signal_id == "signal-001"
    assert value.symbol == "NVDA"
    assert value.rationale == (
        "Portfolio sizing supports the allocation."
    )
    assert value.metadata == (
        ("environment", "paper"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "allocation_id",
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "signal_id",
        "symbol",
        "rationale",
    ],
)
def test_portfolio_allocation_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "allocation_id": "allocation-001",
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "signal_id": "signal-001",
        "symbol": "NVDA",
        "action": AllocationAction.OPEN,
        "direction": AllocationDirection.LONG,
        "strength": AllocationStrength.HIGH,
        "target_allocation_percent": 10,
        "confidence": 85,
        "generated_at": NOW,
        "expires_at": None,
        "rationale": "Portfolio sizing supports the allocation.",
    }

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        PortfolioAllocation(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "allocation_id",
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "signal_id",
        "symbol",
        "rationale",
    ],
)
def test_portfolio_allocation_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "allocation_id": "allocation-001",
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "signal_id": "signal-001",
        "symbol": "NVDA",
        "action": AllocationAction.OPEN,
        "direction": AllocationDirection.LONG,
        "strength": AllocationStrength.HIGH,
        "target_allocation_percent": 10,
        "confidence": 85,
        "generated_at": NOW,
        "expires_at": None,
        "rationale": "Portfolio sizing supports the allocation.",
    }

    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        PortfolioAllocation(**arguments)


def test_portfolio_allocation_requires_action_enum() -> None:
    with pytest.raises(
        TypeError,
        match="action must be an AllocationAction",
    ):
        portfolio_allocation(
            action="OPEN"
        )


def test_portfolio_allocation_requires_direction_enum() -> None:
    with pytest.raises(
        TypeError,
        match="direction must be an AllocationDirection",
    ):
        portfolio_allocation(
            direction="LONG"
        )


def test_portfolio_allocation_requires_strength_enum() -> None:
    with pytest.raises(
        TypeError,
        match="strength must be an AllocationStrength",
    ):
        portfolio_allocation(
            strength="HIGH"
        )


@pytest.mark.parametrize(
    "value",
    [
        -1,
        101,
    ],
)
def test_portfolio_allocation_target_bounds(
    value: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "target_allocation_percent must be "
            "between 0 and 100"
        ),
    ):
        portfolio_allocation(
            target_allocation_percent=value
        )


def test_portfolio_allocation_target_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "target_allocation_percent must be an integer"
        ),
    ):
        portfolio_allocation(
            target_allocation_percent="10"
        )


def test_portfolio_allocation_target_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "target_allocation_percent must be an integer"
        ),
    ):
        portfolio_allocation(
            target_allocation_percent=True
        )


@pytest.mark.parametrize(
    "confidence",
    [
        -1,
        101,
    ],
)
def test_portfolio_allocation_confidence_bounds(
    confidence: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="confidence must be between 0 and 100",
    ):
        portfolio_allocation(
            confidence=confidence
        )


def test_portfolio_allocation_confidence_requires_integer(
) -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        portfolio_allocation(
            confidence="85"
        )


def test_portfolio_allocation_confidence_rejects_bool() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        portfolio_allocation(
            confidence=True
        )


@pytest.mark.parametrize(
    "confidence",
    [
        0,
        100,
    ],
)
def test_portfolio_allocation_confidence_boundaries_allowed(
    confidence: int,
) -> None:
    value = portfolio_allocation(
        confidence=confidence
    )

    assert value.confidence == confidence


def test_portfolio_allocation_generated_at_requires_datetime(
) -> None:
    with pytest.raises(
        TypeError,
        match="generated_at must be a datetime",
    ):
        PortfolioAllocation(
            allocation_id="allocation-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=AllocationAction.OPEN,
            direction=AllocationDirection.LONG,
            strength=AllocationStrength.HIGH,
            target_allocation_percent=10,
            confidence=85,
            generated_at="2026-08-10",
            expires_at=None,
            rationale="Portfolio sizing supports the allocation.",
        )


def test_portfolio_allocation_generated_at_must_be_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="generated_at must be timezone-aware",
    ):
        portfolio_allocation(
            generated_at=datetime(
                2026,
                8,
                10,
                23,
                0,
            )
        )


def test_portfolio_allocation_expires_at_requires_datetime(
) -> None:
    with pytest.raises(
        TypeError,
        match="expires_at must be a datetime",
    ):
        portfolio_allocation(
            expires_at="2026-08-10"
        )


def test_portfolio_allocation_expires_at_must_be_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="expires_at must be timezone-aware",
    ):
        portfolio_allocation(
            expires_at=datetime(
                2026,
                8,
                10,
                23,
                5,
            )
        )


def test_portfolio_allocation_expiration_must_follow_generation(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "expires_at must not be earlier "
            "than generated_at"
        ),
    ):
        portfolio_allocation(
            expires_at=(
                NOW - timedelta(seconds=1)
            )
        )


def test_portfolio_allocation_expiration_may_equal_generation(
) -> None:
    value = portfolio_allocation(
        expires_at=NOW
    )

    assert value.expires_at == NOW
    assert value.has_expiration is True


def test_portfolio_allocation_has_expiration() -> None:
    value = portfolio_allocation(
        expires_at=(
            NOW + timedelta(minutes=5)
        )
    )

    assert value.has_expiration is True


def test_portfolio_allocation_without_expiration_never_expires(
) -> None:
    value = portfolio_allocation()

    assert value.is_expired_at(
        NOW + timedelta(days=1)
    ) is False


def test_portfolio_allocation_not_expired_at_boundary() -> None:
    expires_at = (
        NOW + timedelta(minutes=5)
    )

    value = portfolio_allocation(
        expires_at=expires_at
    )

    assert value.is_expired_at(
        expires_at
    ) is False


def test_portfolio_allocation_expires_after_boundary() -> None:
    expires_at = (
        NOW + timedelta(minutes=5)
    )

    value = portfolio_allocation(
        expires_at=expires_at
    )

    assert value.is_expired_at(
        expires_at + timedelta(microseconds=1)
    ) is True


def test_portfolio_allocation_expiry_check_requires_datetime(
) -> None:
    value = portfolio_allocation(
        expires_at=(
            NOW + timedelta(minutes=5)
        )
    )

    with pytest.raises(
        TypeError,
        match="value must be a datetime",
    ):
        value.is_expired_at(
            "2026-08-10"
        )


def test_portfolio_allocation_expiry_check_requires_aware_datetime(
) -> None:
    value = portfolio_allocation(
        expires_at=(
            NOW + timedelta(minutes=5)
        )
    )

    with pytest.raises(
        ValueError,
        match="value must be timezone-aware",
    ):
        value.is_expired_at(
            datetime(
                2026,
                8,
                10,
                23,
                10,
            )
        )


def test_portfolio_allocation_hold_requires_flat_direction(
) -> None:
    with pytest.raises(
        ValueError,
        match="HOLD allocations require FLAT direction",
    ):
        portfolio_allocation(
            action=AllocationAction.HOLD,
            direction=AllocationDirection.LONG,
            target_allocation_percent=0,
        )


def test_portfolio_allocation_hold_requires_zero_target(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "HOLD allocations require "
            "target_allocation_percent of 0"
        ),
    ):
        portfolio_allocation(
            action=AllocationAction.HOLD,
            direction=AllocationDirection.FLAT,
            target_allocation_percent=10,
        )


def test_portfolio_allocation_hold_is_not_actionable() -> None:
    value = portfolio_allocation(
        action=AllocationAction.HOLD,
        direction=AllocationDirection.FLAT,
        target_allocation_percent=0,
    )

    assert value.is_actionable is False


def test_portfolio_allocation_open_rejects_flat_direction(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "OPEN allocations require "
            "LONG or SHORT direction"
        ),
    ):
        portfolio_allocation(
            action=AllocationAction.OPEN,
            direction=AllocationDirection.FLAT,
        )


@pytest.mark.parametrize(
    "action",
    [
        AllocationAction.INCREASE,
        AllocationAction.DECREASE,
        AllocationAction.REBALANCE,
    ],
)
def test_portfolio_allocation_directional_actions_reject_flat(
    action: AllocationAction,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            f"{action.value} allocations require "
            "LONG or SHORT direction"
        ),
    ):
        portfolio_allocation(
            action=action,
            direction=AllocationDirection.FLAT,
        )


def test_portfolio_allocation_close_requires_zero_target(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "CLOSE allocations require "
            "target_allocation_percent of 0"
        ),
    ):
        portfolio_allocation(
            action=AllocationAction.CLOSE,
            direction=AllocationDirection.LONG,
            target_allocation_percent=5,
        )


def test_portfolio_allocation_close_with_zero_target() -> None:
    value = portfolio_allocation(
        action=AllocationAction.CLOSE,
        direction=AllocationDirection.LONG,
        target_allocation_percent=0,
    )

    assert value.is_actionable is True


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (79, False),
        (80, True),
        (100, True),
    ],
)
def test_portfolio_allocation_high_confidence_property(
    confidence: int,
    expected: bool,
) -> None:
    value = portfolio_allocation(
        confidence=confidence
    )

    assert value.is_high_confidence is expected


def test_portfolio_allocation_warnings_are_normalized(
) -> None:
    value = portfolio_allocation(
        warnings=(
            " exposure elevated ",
            "exposure elevated",
            " liquidity constrained ",
        )
    )

    assert value.warnings == (
        "exposure elevated",
        "liquidity constrained",
    )


def test_portfolio_allocation_warnings_reject_empty_values(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        portfolio_allocation(
            warnings=(
                "valid",
                "   ",
            )
        )


def test_portfolio_allocation_warnings_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        portfolio_allocation(
            warnings=(
                "valid",
                123,
            )
        )


def test_portfolio_allocation_metadata_is_normalized(
) -> None:
    value = PortfolioAllocation(
        allocation_id="allocation-001",
        request_id="request-001",
        correlation_id="correlation-001",
        strategy_id="strategy-001",
        portfolio_id="portfolio-001",
        signal_id="signal-001",
        symbol="NVDA",
        action=AllocationAction.OPEN,
        direction=AllocationDirection.LONG,
        strength=AllocationStrength.HIGH,
        target_allocation_percent=10,
        confidence=85,
        generated_at=NOW,
        expires_at=None,
        rationale="Portfolio sizing supports the allocation.",
        metadata=[
            ("  model  ", "  allocation-v1  "),
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.metadata == (
        ("model", "allocation-v1"),
        ("environment", "paper"),
    )


def test_portfolio_allocation_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        PortfolioAllocation(
            allocation_id="allocation-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=AllocationAction.OPEN,
            direction=AllocationDirection.LONG,
            strength=AllocationStrength.HIGH,
            target_allocation_percent=10,
            confidence=85,
            generated_at=NOW,
            expires_at=None,
            rationale="Portfolio sizing supports the allocation.",
            metadata=(
                ("model", "one"),
                ("model", "two"),
            ),
        )


def test_portfolio_allocation_metadata_items_must_be_pairs(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        PortfolioAllocation(
            allocation_id="allocation-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=AllocationAction.OPEN,
            direction=AllocationDirection.LONG,
            strength=AllocationStrength.HIGH,
            target_allocation_percent=10,
            confidence=85,
            generated_at=NOW,
            expires_at=None,
            rationale="Portfolio sizing supports the allocation.",
            metadata=(
                ("model",),
            ),
        )


def test_portfolio_allocation_metadata_keys_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        PortfolioAllocation(
            allocation_id="allocation-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=AllocationAction.OPEN,
            direction=AllocationDirection.LONG,
            strength=AllocationStrength.HIGH,
            target_allocation_percent=10,
            confidence=85,
            generated_at=NOW,
            expires_at=None,
            rationale="Portfolio sizing supports the allocation.",
            metadata=(
                (123, "allocation-v1"),
            ),
        )


def test_portfolio_allocation_metadata_values_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        PortfolioAllocation(
            allocation_id="allocation-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            signal_id="signal-001",
            symbol="NVDA",
            action=AllocationAction.OPEN,
            direction=AllocationDirection.LONG,
            strength=AllocationStrength.HIGH,
            target_allocation_percent=10,
            confidence=85,
            generated_at=NOW,
            expires_at=None,
            rationale="Portfolio sizing supports the allocation.",
            metadata=(
                ("model", 123),
            ),
        )


def test_portfolio_allocation_is_immutable() -> None:
    value = portfolio_allocation()

    with pytest.raises(FrozenInstanceError):
        value.allocation_id = "changed"
def allocation_result(
    *,
    request_id: str = "request-001",
    correlation_id: str = "correlation-001",
    status: AllocationStatus = AllocationStatus.ACTIVE,
    decision: AllocationDecision = AllocationDecision.PROCEED,
    started_at: datetime = NOW,
    updated_at: datetime = NOW,
    completed_at: datetime | None = None,
    allocation: PortfolioAllocation | None = None,
    warnings: tuple[str, ...] = (),
    error: str | None = None,
) -> PortfolioAllocationResult:
    return PortfolioAllocationResult(
        request_id=request_id,
        correlation_id=correlation_id,
        status=status,
        decision=decision,
        started_at=started_at,
        updated_at=updated_at,
        completed_at=completed_at,
        allocation=allocation,
        warnings=warnings,
        error=error,
        metadata=(
            ("environment", "paper"),
        ),
    )


def approved_allocation_result() -> PortfolioAllocationResult:
    return allocation_result(
        status=AllocationStatus.APPROVED,
        decision=AllocationDecision.APPROVE,
        completed_at=NOW,
        allocation=portfolio_allocation(),
    )


def failed_allocation_result(
    *,
    retryable: bool = True,
) -> PortfolioAllocationResult:
    return allocation_result(
        status=AllocationStatus.FAILED,
        decision=(
            AllocationDecision.RETRY
            if retryable
            else AllocationDecision.NO_ACTION
        ),
        completed_at=NOW,
        error="Allocation evaluation failed.",
    )


def test_active_portfolio_allocation_result() -> None:
    value = allocation_result()

    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.status is AllocationStatus.ACTIVE
    assert value.decision is AllocationDecision.PROCEED
    assert value.started_at == NOW
    assert value.updated_at == NOW
    assert value.completed_at is None
    assert value.allocation is None
    assert value.is_terminal is False
    assert value.is_successful is False
    assert value.has_allocation is False


def test_pending_portfolio_allocation_result() -> None:
    value = allocation_result(
        status=AllocationStatus.PENDING,
        decision=AllocationDecision.NO_ACTION,
    )

    assert value.status is AllocationStatus.PENDING
    assert value.is_terminal is False


def test_approved_portfolio_allocation_result() -> None:
    value = approved_allocation_result()

    assert value.status is AllocationStatus.APPROVED
    assert value.decision is AllocationDecision.APPROVE
    assert value.is_terminal is True
    assert value.is_successful is True
    assert value.has_allocation is True


def test_rejected_portfolio_allocation_result() -> None:
    value = allocation_result(
        status=AllocationStatus.REJECTED,
        decision=AllocationDecision.REJECT,
        completed_at=NOW,
    )

    assert value.status is AllocationStatus.REJECTED
    assert value.is_terminal is True
    assert value.is_successful is False


def test_cancelled_portfolio_allocation_result() -> None:
    value = allocation_result(
        status=AllocationStatus.CANCELLED,
        decision=AllocationDecision.CANCEL,
        completed_at=NOW,
    )

    assert value.status is AllocationStatus.CANCELLED
    assert value.is_terminal is True


def test_failed_portfolio_allocation_result_retryable() -> None:
    value = failed_allocation_result(
        retryable=True
    )

    assert value.status is AllocationStatus.FAILED
    assert value.decision is AllocationDecision.RETRY
    assert value.error == "Allocation evaluation failed."
    assert value.is_terminal is True


def test_failed_portfolio_allocation_result_non_retryable() -> None:
    value = failed_allocation_result(
        retryable=False
    )

    assert value.decision is AllocationDecision.NO_ACTION


def test_allocation_result_text_is_normalized() -> None:
    value = PortfolioAllocationResult(
        request_id="  request-001  ",
        correlation_id="  correlation-001  ",
        status=AllocationStatus.ACTIVE,
        decision=AllocationDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW,
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        ),
        metadata=[
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.warnings == (
        "warning one",
        "warning two",
    )
    assert value.metadata == (
        ("environment", "paper"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
    ],
)
def test_allocation_result_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "status": AllocationStatus.ACTIVE,
        "decision": AllocationDecision.PROCEED,
        "started_at": NOW,
        "updated_at": NOW,
    }

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        PortfolioAllocationResult(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
    ],
)
def test_allocation_result_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "status": AllocationStatus.ACTIVE,
        "decision": AllocationDecision.PROCEED,
        "started_at": NOW,
        "updated_at": NOW,
    }

    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        PortfolioAllocationResult(**arguments)


def test_allocation_result_requires_status_enum() -> None:
    with pytest.raises(
        TypeError,
        match="status must be an AllocationStatus",
    ):
        allocation_result(
            status="ACTIVE"
        )


def test_allocation_result_requires_decision_enum() -> None:
    with pytest.raises(
        TypeError,
        match="decision must be an AllocationDecision",
    ):
        allocation_result(
            decision="PROCEED"
        )


def test_allocation_result_started_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="started_at must be a datetime",
    ):
        PortfolioAllocationResult(
            request_id="request-001",
            correlation_id="correlation-001",
            status=AllocationStatus.ACTIVE,
            decision=AllocationDecision.PROCEED,
            started_at="2026-08-10",
            updated_at=NOW,
        )


def test_allocation_result_started_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="started_at must be timezone-aware",
    ):
        allocation_result(
            started_at=datetime(
                2026,
                8,
                10,
                23,
                0,
            )
        )


def test_allocation_result_updated_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="updated_at must be a datetime",
    ):
        PortfolioAllocationResult(
            request_id="request-001",
            correlation_id="correlation-001",
            status=AllocationStatus.ACTIVE,
            decision=AllocationDecision.PROCEED,
            started_at=NOW,
            updated_at="2026-08-10",
        )


def test_allocation_result_updated_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="updated_at must be timezone-aware",
    ):
        allocation_result(
            updated_at=datetime(
                2026,
                8,
                10,
                23,
                0,
            )
        )


def test_allocation_result_updated_at_must_follow_start() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "updated_at must not be earlier "
            "than started_at"
        ),
    ):
        allocation_result(
            started_at=NOW,
            updated_at=(
                NOW - timedelta(seconds=1)
            ),
        )


def test_allocation_result_completed_at_requires_datetime(
) -> None:
    with pytest.raises(
        TypeError,
        match="completed_at must be a datetime",
    ):
        PortfolioAllocationResult(
            request_id="request-001",
            correlation_id="correlation-001",
            status=AllocationStatus.REJECTED,
            decision=AllocationDecision.REJECT,
            started_at=NOW,
            updated_at=NOW,
            completed_at="2026-08-10",
        )


def test_allocation_result_completed_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="completed_at must be timezone-aware",
    ):
        allocation_result(
            status=AllocationStatus.REJECTED,
            decision=AllocationDecision.REJECT,
            completed_at=datetime(
                2026,
                8,
                10,
                23,
                0,
            ),
        )


def test_allocation_result_completed_at_must_follow_update(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed_at must not be earlier "
            "than updated_at"
        ),
    ):
        allocation_result(
            status=AllocationStatus.REJECTED,
            decision=AllocationDecision.REJECT,
            updated_at=NOW,
            completed_at=(
                NOW - timedelta(seconds=1)
            ),
        )


def test_allocation_result_requires_allocation_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "allocation must be a "
            "PortfolioAllocation or None"
        ),
    ):
        allocation_result(
            allocation=object()
        )


def test_allocation_request_id_must_match_result() -> None:
    value = portfolio_allocation(
        request_id="different-request"
    )

    with pytest.raises(
        ValueError,
        match=(
            "allocation request_id must match "
            "result request_id"
        ),
    ):
        allocation_result(
            allocation=value
        )


def test_allocation_correlation_id_must_match_result() -> None:
    value = portfolio_allocation(
        correlation_id="different-correlation"
    )

    with pytest.raises(
        ValueError,
        match=(
            "allocation correlation_id must match "
            "result correlation_id"
        ),
    ):
        allocation_result(
            allocation=value
        )


def test_allocation_generation_must_not_precede_result_start(
) -> None:
    value = portfolio_allocation(
        generated_at=(
            NOW - timedelta(seconds=1)
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "allocation generated_at must not be "
            "earlier than result started_at"
        ),
    ):
        allocation_result(
            allocation=value
        )


def test_allocation_generation_must_not_follow_result_update(
) -> None:
    value = portfolio_allocation(
        generated_at=(
            NOW + timedelta(seconds=1)
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "allocation generated_at must not be "
            "later than result updated_at"
        ),
    ):
        allocation_result(
            updated_at=NOW,
            allocation=value,
        )


@pytest.mark.parametrize(
    "status",
    [
        AllocationStatus.APPROVED,
        AllocationStatus.REJECTED,
        AllocationStatus.CANCELLED,
        AllocationStatus.FAILED,
    ],
)
def test_terminal_allocation_result_requires_completed_at(
    status: AllocationStatus,
) -> None:
    if status is AllocationStatus.APPROVED:
        decision = AllocationDecision.APPROVE
        allocation = portfolio_allocation()
        error = None
    elif status is AllocationStatus.REJECTED:
        decision = AllocationDecision.REJECT
        allocation = None
        error = None
    elif status is AllocationStatus.CANCELLED:
        decision = AllocationDecision.CANCEL
        allocation = None
        error = None
    else:
        decision = AllocationDecision.RETRY
        allocation = None
        error = "Allocation evaluation failed."

    with pytest.raises(
        ValueError,
        match=(
            "terminal allocation results require "
            "completed_at"
        ),
    ):
        allocation_result(
            status=status,
            decision=decision,
            completed_at=None,
            allocation=allocation,
            error=error,
        )


@pytest.mark.parametrize(
    ("status", "decision"),
    [
        (
            AllocationStatus.PENDING,
            AllocationDecision.NO_ACTION,
        ),
        (
            AllocationStatus.ACTIVE,
            AllocationDecision.PROCEED,
        ),
    ],
)
def test_non_terminal_allocation_result_rejects_completed_at(
    status: AllocationStatus,
    decision: AllocationDecision,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-terminal allocation results must not "
            "include completed_at"
        ),
    ):
        allocation_result(
            status=status,
            decision=decision,
            completed_at=NOW,
        )


def test_pending_allocation_result_requires_no_action() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "pending allocation results require "
            "NO_ACTION decision"
        ),
    ):
        allocation_result(
            status=AllocationStatus.PENDING,
            decision=AllocationDecision.PROCEED,
        )


def test_pending_allocation_result_rejects_allocation() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "pending allocation results must not "
            "include an allocation"
        ),
    ):
        allocation_result(
            status=AllocationStatus.PENDING,
            decision=AllocationDecision.NO_ACTION,
            allocation=portfolio_allocation(),
        )


def test_active_allocation_result_requires_proceed() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "active allocation results require "
            "PROCEED decision"
        ),
    ):
        allocation_result(
            status=AllocationStatus.ACTIVE,
            decision=AllocationDecision.HOLD,
        )


def test_approved_allocation_result_requires_approve() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "approved allocation results require "
            "APPROVE decision"
        ),
    ):
        allocation_result(
            status=AllocationStatus.APPROVED,
            decision=AllocationDecision.PROCEED,
            completed_at=NOW,
            allocation=portfolio_allocation(),
        )


def test_approved_allocation_result_requires_allocation() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "approved allocation results require "
            "an allocation"
        ),
    ):
        allocation_result(
            status=AllocationStatus.APPROVED,
            decision=AllocationDecision.APPROVE,
            completed_at=NOW,
            allocation=None,
        )


def test_rejected_allocation_result_requires_reject() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "rejected allocation results require "
            "REJECT decision"
        ),
    ):
        allocation_result(
            status=AllocationStatus.REJECTED,
            decision=AllocationDecision.NO_ACTION,
            completed_at=NOW,
        )


def test_cancelled_allocation_result_requires_cancel() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "cancelled allocation results require "
            "CANCEL decision"
        ),
    ):
        allocation_result(
            status=AllocationStatus.CANCELLED,
            decision=AllocationDecision.NO_ACTION,
            completed_at=NOW,
        )


@pytest.mark.parametrize(
    "decision",
    [
        AllocationDecision.RETRY,
        AllocationDecision.NO_ACTION,
    ],
)
def test_failed_allocation_result_allows_retry_or_no_action(
    decision: AllocationDecision,
) -> None:
    value = allocation_result(
        status=AllocationStatus.FAILED,
        decision=decision,
        completed_at=NOW,
        error="Allocation evaluation failed.",
    )

    assert value.decision is decision


def test_failed_allocation_result_rejects_success_decision(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed allocation results require "
            "RETRY or NO_ACTION decision"
        ),
    ):
        allocation_result(
            status=AllocationStatus.FAILED,
            decision=AllocationDecision.APPROVE,
            completed_at=NOW,
            error="Allocation evaluation failed.",
        )


def test_failed_allocation_result_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed allocation results require "
            "an error"
        ),
    ):
        allocation_result(
            status=AllocationStatus.FAILED,
            decision=AllocationDecision.RETRY,
            completed_at=NOW,
            error=None,
        )


def test_only_failed_allocation_result_may_include_error(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only failed allocation results may "
            "include an error"
        ),
    ):
        allocation_result(
            status=AllocationStatus.REJECTED,
            decision=AllocationDecision.REJECT,
            completed_at=NOW,
            error="Unexpected error.",
        )


def test_allocation_result_error_is_normalized() -> None:
    value = allocation_result(
        status=AllocationStatus.FAILED,
        decision=AllocationDecision.RETRY,
        completed_at=NOW,
        error="  Allocation evaluation failed.  ",
    )

    assert value.error == "Allocation evaluation failed."


def test_allocation_result_error_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="error must not be empty",
    ):
        allocation_result(
            status=AllocationStatus.FAILED,
            decision=AllocationDecision.RETRY,
            completed_at=NOW,
            error="   ",
        )


def test_allocation_result_warnings_are_normalized() -> None:
    value = allocation_result(
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        ),
    )

    assert value.warnings == (
        "warning one",
        "warning two",
    )


def test_allocation_result_warnings_reject_empty_values(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        allocation_result(
            warnings=(
                "valid",
                "   ",
            )
        )


def test_allocation_result_warnings_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        allocation_result(
            warnings=(
                "valid",
                123,
            )
        )


def test_allocation_result_metadata_is_normalized() -> None:
    value = PortfolioAllocationResult(
        request_id="request-001",
        correlation_id="correlation-001",
        status=AllocationStatus.ACTIVE,
        decision=AllocationDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW,
        metadata=[
            ("  engine  ", "  allocation  "),
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.metadata == (
        ("engine", "allocation"),
        ("environment", "paper"),
    )


def test_allocation_result_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        PortfolioAllocationResult(
            request_id="request-001",
            correlation_id="correlation-001",
            status=AllocationStatus.ACTIVE,
            decision=AllocationDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            metadata=(
                ("engine", "one"),
                ("engine", "two"),
            ),
        )


def test_portfolio_allocation_result_is_immutable() -> None:
    value = approved_allocation_result()

    with pytest.raises(FrozenInstanceError):
        value.status = AllocationStatus.FAILED

def allocation_report(
    *,
    report_id: str = "report-001",
    request: PortfolioAllocationRequest | None = None,
    result: PortfolioAllocationResult | None = None,
    reported_at: datetime = NOW,
    message: str = "Portfolio allocation evaluation updated.",
    warnings: tuple[str, ...] = (),
) -> PortfolioAllocationReport:
    return PortfolioAllocationReport(
        report_id=report_id,
        request=request or allocation_request(),
        result=result or allocation_result(),
        reported_at=reported_at,
        message=message,
        warnings=warnings,
        metadata=(
            ("source", "portfolio-allocation-engine"),
        ),
    )


def test_portfolio_allocation_report() -> None:
    value = allocation_report()

    assert value.report_id == "report-001"
    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.signal_id == "signal-001"
    assert value.symbol == "NVDA"
    assert value.status is AllocationStatus.ACTIVE
    assert value.decision is AllocationDecision.PROCEED
    assert value.allocation is None
    assert value.is_terminal is False
    assert value.reported_at == NOW
    assert value.message == (
        "Portfolio allocation evaluation updated."
    )
    assert value.metadata == (
        ("source", "portfolio-allocation-engine"),
    )


def test_approved_portfolio_allocation_report() -> None:
    value = allocation_report(
        result=approved_allocation_result(),
    )

    assert value.status is AllocationStatus.APPROVED
    assert value.decision is AllocationDecision.APPROVE
    assert value.allocation is not None
    assert value.is_terminal is True


def test_portfolio_allocation_report_text_is_normalized() -> None:
    value = PortfolioAllocationReport(
        report_id="  report-001  ",
        request=allocation_request(),
        result=allocation_result(),
        reported_at=NOW,
        message="  Portfolio allocation updated.  ",
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        ),
        metadata=[
            ("  source  ", "  portfolio-allocation-engine  "),
        ],
    )

    assert value.report_id == "report-001"
    assert value.message == "Portfolio allocation updated."
    assert value.warnings == (
        "warning one",
        "warning two",
    )
    assert value.metadata == (
        ("source", "portfolio-allocation-engine"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_portfolio_allocation_report_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "report_id": "report-001",
        "request": allocation_request(),
        "result": allocation_result(),
        "reported_at": NOW,
        "message": "Portfolio allocation updated.",
    }

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        PortfolioAllocationReport(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_portfolio_allocation_report_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "report_id": "report-001",
        "request": allocation_request(),
        "result": allocation_result(),
        "reported_at": NOW,
        "message": "Portfolio allocation updated.",
    }

    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        PortfolioAllocationReport(**arguments)


def test_portfolio_allocation_report_requires_request_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "request must be a "
            "PortfolioAllocationRequest"
        ),
    ):
        PortfolioAllocationReport(
            report_id="report-001",
            request=object(),
            result=allocation_result(),
            reported_at=NOW,
            message="Portfolio allocation updated.",
        )


def test_portfolio_allocation_report_requires_result_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "result must be a "
            "PortfolioAllocationResult"
        ),
    ):
        PortfolioAllocationReport(
            report_id="report-001",
            request=allocation_request(),
            result=object(),
            reported_at=NOW,
            message="Portfolio allocation updated.",
        )


def test_portfolio_allocation_reported_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="reported_at must be a datetime",
    ):
        PortfolioAllocationReport(
            report_id="report-001",
            request=allocation_request(),
            result=allocation_result(),
            reported_at="2026-08-10",
            message="Portfolio allocation updated.",
        )


def test_portfolio_allocation_reported_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="reported_at must be timezone-aware",
    ):
        allocation_report(
            reported_at=datetime(
                2026,
                8,
                10,
                23,
                0,
            )
        )


def test_allocation_report_request_id_must_match_result() -> None:
    result = allocation_result(
        request_id="different-request",
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result request_id values "
            "must match"
        ),
    ):
        allocation_report(
            result=result,
        )


def test_allocation_report_correlation_id_must_match_result() -> None:
    result = allocation_result(
        correlation_id="different-correlation",
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result correlation_id values "
            "must match"
        ),
    ):
        allocation_report(
            result=result,
        )


def test_allocation_report_result_must_not_start_before_request() -> None:
    request = allocation_request(
        created_at=NOW,
    )

    result = allocation_result(
        started_at=(
            NOW - timedelta(seconds=1)
        ),
        updated_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match=(
            "result started_at must not be earlier "
            "than request created_at"
        ),
    ):
        allocation_report(
            request=request,
            result=result,
        )


def test_allocation_reported_at_must_follow_result_update() -> None:
    result = allocation_result(
        started_at=NOW,
        updated_at=(
            NOW + timedelta(seconds=1)
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier "
            "than result updated_at"
        ),
    ):
        allocation_report(
            result=result,
            reported_at=NOW,
        )


def test_allocation_reported_at_must_follow_result_completion() -> None:
    allocation = portfolio_allocation(
        generated_at=NOW,
    )

    result = allocation_result(
        status=AllocationStatus.APPROVED,
        decision=AllocationDecision.APPROVE,
        started_at=NOW,
        updated_at=NOW,
        completed_at=(
            NOW + timedelta(seconds=1)
        ),
        allocation=allocation,
    )

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier "
            "than result completed_at"
        ),
    ):
        allocation_report(
            result=result,
            reported_at=NOW,
        )


def test_report_allocation_strategy_id_must_match_request() -> None:
    allocation = portfolio_allocation(
        strategy_id="different-strategy",
    )

    result = allocation_result(
        status=AllocationStatus.APPROVED,
        decision=AllocationDecision.APPROVE,
        completed_at=NOW,
        allocation=allocation,
    )

    with pytest.raises(
        ValueError,
        match=(
            "allocation strategy_id must match request"
        ),
    ):
        allocation_report(
            result=result,
        )


def test_report_allocation_portfolio_id_must_match_request() -> None:
    allocation = portfolio_allocation(
        portfolio_id="different-portfolio",
    )

    result = allocation_result(
        status=AllocationStatus.APPROVED,
        decision=AllocationDecision.APPROVE,
        completed_at=NOW,
        allocation=allocation,
    )

    with pytest.raises(
        ValueError,
        match=(
            "allocation portfolio_id must match request"
        ),
    ):
        allocation_report(
            result=result,
        )


def test_report_allocation_signal_id_must_match_request() -> None:
    allocation = portfolio_allocation(
        signal_id="different-signal",
    )

    result = allocation_result(
        status=AllocationStatus.APPROVED,
        decision=AllocationDecision.APPROVE,
        completed_at=NOW,
        allocation=allocation,
    )

    with pytest.raises(
        ValueError,
        match=(
            "allocation signal_id must match request"
        ),
    ):
        allocation_report(
            result=result,
        )


def test_report_allocation_symbol_must_match_request() -> None:
    allocation = portfolio_allocation(
        symbol="AAPL",
    )

    result = allocation_result(
        status=AllocationStatus.APPROVED,
        decision=AllocationDecision.APPROVE,
        completed_at=NOW,
        allocation=allocation,
    )

    with pytest.raises(
        ValueError,
        match="allocation symbol must match request",
    ):
        allocation_report(
            result=result,
        )


def test_report_allocation_action_must_match_request() -> None:
    allocation = portfolio_allocation(
        action=AllocationAction.INCREASE,
    )

    result = allocation_result(
        status=AllocationStatus.APPROVED,
        decision=AllocationDecision.APPROVE,
        completed_at=NOW,
        allocation=allocation,
    )

    with pytest.raises(
        ValueError,
        match="allocation action must match request",
    ):
        allocation_report(
            result=result,
        )


def test_report_allocation_direction_must_match_request() -> None:
    allocation = portfolio_allocation(
        direction=AllocationDirection.SHORT,
    )

    result = allocation_result(
        status=AllocationStatus.APPROVED,
        decision=AllocationDecision.APPROVE,
        completed_at=NOW,
        allocation=allocation,
    )

    with pytest.raises(
        ValueError,
        match=(
            "allocation direction must match request"
        ),
    ):
        allocation_report(
            result=result,
        )


def test_portfolio_allocation_report_warnings_are_normalized() -> None:
    value = allocation_report(
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        )
    )

    assert value.warnings == (
        "warning one",
        "warning two",
    )


def test_portfolio_allocation_report_warnings_reject_empty_values(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        allocation_report(
            warnings=(
                "valid",
                "   ",
            )
        )


def test_portfolio_allocation_report_warnings_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        allocation_report(
            warnings=(
                "valid",
                123,
            )
        )


def test_portfolio_allocation_report_metadata_is_normalized() -> None:
    value = PortfolioAllocationReport(
        report_id="report-001",
        request=allocation_request(),
        result=allocation_result(),
        reported_at=NOW,
        message="Portfolio allocation updated.",
        metadata=[
            ("  source  ", "  engine  "),
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.metadata == (
        ("source", "engine"),
        ("environment", "paper"),
    )


def test_portfolio_allocation_report_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        PortfolioAllocationReport(
            report_id="report-001",
            request=allocation_request(),
            result=allocation_result(),
            reported_at=NOW,
            message="Portfolio allocation updated.",
            metadata=(
                ("source", "engine"),
                ("source", "duplicate"),
            ),
        )


def test_portfolio_allocation_report_metadata_items_must_be_pairs(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        PortfolioAllocationReport(
            report_id="report-001",
            request=allocation_request(),
            result=allocation_result(),
            reported_at=NOW,
            message="Portfolio allocation updated.",
            metadata=(
                ("source",),
            ),
        )


def test_portfolio_allocation_report_metadata_keys_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        PortfolioAllocationReport(
            report_id="report-001",
            request=allocation_request(),
            result=allocation_result(),
            reported_at=NOW,
            message="Portfolio allocation updated.",
            metadata=(
                (123, "engine"),
            ),
        )


def test_portfolio_allocation_report_metadata_values_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        PortfolioAllocationReport(
            report_id="report-001",
            request=allocation_request(),
            result=allocation_result(),
            reported_at=NOW,
            message="Portfolio allocation updated.",
            metadata=(
                ("source", 123),
            ),
        )


def test_portfolio_allocation_report_is_immutable() -> None:
    value = allocation_report()

    with pytest.raises(FrozenInstanceError):
        value.report_id = "changed"