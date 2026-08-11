from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.strategy_signal_engine import (
    SignalDecision,
    SignalDirection,
    SignalStatus,
    SignalStrength,
    SignalType,
    StrategySignal,
    StrategySignalReport,
    StrategySignalRequest,
    StrategySignalResult,
)

NOW = datetime(
    2026,
    8,
    10,
    21,
    45,
    tzinfo=timezone.utc,
)


def signal_request(
    *,
    request_id: str = "request-001",
    correlation_id: str = "correlation-001",
    strategy_id: str = "strategy-001",
    portfolio_id: str = "portfolio-001",
    symbol: str = "NVDA",
    signal_type: SignalType = SignalType.ENTRY,
    direction: SignalDirection = SignalDirection.LONG,
    strength: SignalStrength = SignalStrength.STRONG,
    confidence: int = 85,
    market_data_correlation_id: str = "market-correlation-001",
    created_at: datetime = NOW,
    sequence_number: int = 1,
    requested_by: str = "strategy-engine",
    is_replay: bool = False,
) -> StrategySignalRequest:
    return StrategySignalRequest(
        request_id=request_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        signal_type=signal_type,
        direction=direction,
        strength=strength,
        confidence=confidence,
        market_data_correlation_id=(
            market_data_correlation_id
        ),
        created_at=created_at,
        sequence_number=sequence_number,
        requested_by=requested_by,
        is_replay=is_replay,
        metadata=(
            ("environment", "paper"),
        ),
    )


def test_strategy_signal_request() -> None:
    value = signal_request()

    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.symbol == "NVDA"
    assert value.signal_type is SignalType.ENTRY
    assert value.direction is SignalDirection.LONG
    assert value.strength is SignalStrength.STRONG
    assert value.confidence == 85
    assert value.market_data_correlation_id == (
        "market-correlation-001"
    )
    assert value.created_at == NOW
    assert value.sequence_number == 1
    assert value.requested_by == "strategy-engine"
    assert value.is_replay is False
    assert value.metadata == (
        ("environment", "paper"),
    )


def test_signal_request_text_is_normalized() -> None:
    value = StrategySignalRequest(
        request_id="  request-001  ",
        correlation_id="  correlation-001  ",
        strategy_id="  strategy-001  ",
        portfolio_id="  portfolio-001  ",
        symbol="  nvda  ",
        signal_type=SignalType.ENTRY,
        direction=SignalDirection.LONG,
        strength=SignalStrength.STRONG,
        confidence=85,
        market_data_correlation_id=(
            "  market-correlation-001  "
        ),
        created_at=NOW,
        sequence_number=1,
        requested_by="  strategy-engine  ",
        metadata=[
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.symbol == "NVDA"
    assert value.market_data_correlation_id == (
        "market-correlation-001"
    )
    assert value.requested_by == "strategy-engine"
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
        "symbol",
        "market_data_correlation_id",
        "requested_by",
    ],
)
def test_signal_request_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "symbol": "NVDA",
        "signal_type": SignalType.ENTRY,
        "direction": SignalDirection.LONG,
        "strength": SignalStrength.STRONG,
        "confidence": 85,
        "market_data_correlation_id": (
            "market-correlation-001"
        ),
        "created_at": NOW,
        "sequence_number": 1,
        "requested_by": "strategy-engine",
    }

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        StrategySignalRequest(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "symbol",
        "market_data_correlation_id",
        "requested_by",
    ],
)
def test_signal_request_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "symbol": "NVDA",
        "signal_type": SignalType.ENTRY,
        "direction": SignalDirection.LONG,
        "strength": SignalStrength.STRONG,
        "confidence": 85,
        "market_data_correlation_id": (
            "market-correlation-001"
        ),
        "created_at": NOW,
        "sequence_number": 1,
        "requested_by": "strategy-engine",
    }

    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        StrategySignalRequest(**arguments)


def test_signal_request_requires_signal_type() -> None:
    with pytest.raises(
        TypeError,
        match="signal_type must be a SignalType",
    ):
        signal_request(
            signal_type="ENTRY"
        )


def test_signal_request_requires_direction() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "direction must be a SignalDirection"
        ),
    ):
        signal_request(
            direction="LONG"
        )


def test_signal_request_requires_strength() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "strength must be a SignalStrength"
        ),
    ):
        signal_request(
            strength="STRONG"
        )


@pytest.mark.parametrize(
    "confidence",
    [
        -1,
        101,
    ],
)
def test_signal_request_confidence_bounds(
    confidence: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "confidence must be between 0 and 100"
        ),
    ):
        signal_request(
            confidence=confidence
        )


def test_signal_request_confidence_requires_integer(
) -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        signal_request(
            confidence="85"
        )


def test_signal_request_confidence_rejects_bool(
) -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        signal_request(
            confidence=True
        )


@pytest.mark.parametrize(
    "confidence",
    [
        0,
        100,
    ],
)
def test_signal_request_confidence_boundaries_allowed(
    confidence: int,
) -> None:
    value = signal_request(
        confidence=confidence
    )

    assert value.confidence == confidence


def test_signal_request_created_at_requires_datetime(
) -> None:
    with pytest.raises(
        TypeError,
        match="created_at must be a datetime",
    ):
        StrategySignalRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            signal_type=SignalType.ENTRY,
            direction=SignalDirection.LONG,
            strength=SignalStrength.STRONG,
            confidence=85,
            market_data_correlation_id=(
                "market-correlation-001"
            ),
            created_at="2026-08-10",
            sequence_number=1,
            requested_by="strategy-engine",
        )


def test_signal_request_created_at_must_be_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "created_at must be timezone-aware"
        ),
    ):
        signal_request(
            created_at=datetime(
                2026,
                8,
                10,
                21,
                45,
            )
        )


def test_signal_request_sequence_requires_integer(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "sequence_number must be an integer"
        ),
    ):
        signal_request(
            sequence_number="1"
        )


def test_signal_request_sequence_rejects_bool(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "sequence_number must be an integer"
        ),
    ):
        signal_request(
            sequence_number=True
        )


def test_signal_request_sequence_must_not_be_negative(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "sequence_number must not be negative"
        ),
    ):
        signal_request(
            sequence_number=-1
        )


def test_zero_sequence_number_is_allowed() -> None:
    value = signal_request(
        sequence_number=0
    )

    assert value.sequence_number == 0


def test_signal_request_replay_requires_bool() -> None:
    with pytest.raises(
        TypeError,
        match="is_replay must be a bool",
    ):
        signal_request(
            is_replay="yes"
        )


def test_replay_signal_request() -> None:
    value = signal_request(
        is_replay=True
    )

    assert value.is_replay is True


def test_hold_signal_requires_flat_direction() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "HOLD signals require FLAT direction"
        ),
    ):
        signal_request(
            signal_type=SignalType.HOLD,
            direction=SignalDirection.LONG,
        )


def test_hold_signal_with_flat_direction() -> None:
    value = signal_request(
        signal_type=SignalType.HOLD,
        direction=SignalDirection.FLAT,
    )

    assert value.is_actionable is False


def test_entry_signal_rejects_flat_direction() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "ENTRY signals require LONG or SHORT direction"
        ),
    ):
        signal_request(
            signal_type=SignalType.ENTRY,
            direction=SignalDirection.FLAT,
        )


@pytest.mark.parametrize(
    "signal_type",
    [
        SignalType.SCALE_IN,
        SignalType.SCALE_OUT,
        SignalType.HEDGE,
    ],
)
def test_directional_signal_rejects_flat_direction(
    signal_type: SignalType,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            f"{signal_type.value} signals require "
            "LONG or SHORT direction"
        ),
    ):
        signal_request(
            signal_type=signal_type,
            direction=SignalDirection.FLAT,
        )


def test_entry_signal_is_actionable() -> None:
    value = signal_request()

    assert value.is_actionable is True
    assert value.is_entry_signal is True
    assert value.is_exit_signal is False


def test_exit_signal_property() -> None:
    value = signal_request(
        signal_type=SignalType.EXIT,
        direction=SignalDirection.LONG,
    )

    assert value.is_entry_signal is False
    assert value.is_exit_signal is True


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
    value = signal_request(
        confidence=confidence
    )

    assert value.is_high_confidence is expected


def test_signal_request_metadata_is_normalized(
) -> None:
    value = StrategySignalRequest(
        request_id="request-001",
        correlation_id="correlation-001",
        strategy_id="strategy-001",
        portfolio_id="portfolio-001",
        symbol="NVDA",
        signal_type=SignalType.ENTRY,
        direction=SignalDirection.LONG,
        strength=SignalStrength.STRONG,
        confidence=85,
        market_data_correlation_id=(
            "market-correlation-001"
        ),
        created_at=NOW,
        sequence_number=1,
        requested_by="strategy-engine",
        metadata=[
            ("  environment  ", "  paper  "),
            ("  model  ", "  momentum  "),
        ],
    )

    assert value.metadata == (
        ("environment", "paper"),
        ("model", "momentum"),
    )


def test_signal_request_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        StrategySignalRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            signal_type=SignalType.ENTRY,
            direction=SignalDirection.LONG,
            strength=SignalStrength.STRONG,
            confidence=85,
            market_data_correlation_id=(
                "market-correlation-001"
            ),
            created_at=NOW,
            sequence_number=1,
            requested_by="strategy-engine",
            metadata=(
                ("model", "momentum"),
                ("model", "duplicate"),
            ),
        )


def test_signal_request_metadata_items_must_be_pairs(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        StrategySignalRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            signal_type=SignalType.ENTRY,
            direction=SignalDirection.LONG,
            strength=SignalStrength.STRONG,
            confidence=85,
            market_data_correlation_id=(
                "market-correlation-001"
            ),
            created_at=NOW,
            sequence_number=1,
            requested_by="strategy-engine",
            metadata=(
                ("model",),
            ),
        )


def test_signal_request_metadata_keys_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        StrategySignalRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            signal_type=SignalType.ENTRY,
            direction=SignalDirection.LONG,
            strength=SignalStrength.STRONG,
            confidence=85,
            market_data_correlation_id=(
                "market-correlation-001"
            ),
            created_at=NOW,
            sequence_number=1,
            requested_by="strategy-engine",
            metadata=(
                (123, "momentum"),
            ),
        )


def test_signal_request_metadata_values_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        StrategySignalRequest(
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            signal_type=SignalType.ENTRY,
            direction=SignalDirection.LONG,
            strength=SignalStrength.STRONG,
            confidence=85,
            market_data_correlation_id=(
                "market-correlation-001"
            ),
            created_at=NOW,
            sequence_number=1,
            requested_by="strategy-engine",
            metadata=(
                ("model", 123),
            ),
        )


def test_strategy_signal_request_is_immutable() -> None:
    value = signal_request()

    with pytest.raises(FrozenInstanceError):
        value.request_id = "changed"

def strategy_signal(
    *,
    signal_id: str = "signal-001",
    request_id: str = "request-001",
    correlation_id: str = "correlation-001",
    strategy_id: str = "strategy-001",
    portfolio_id: str = "portfolio-001",
    symbol: str = "NVDA",
    signal_type: SignalType = SignalType.ENTRY,
    direction: SignalDirection = SignalDirection.LONG,
    strength: SignalStrength = SignalStrength.STRONG,
    confidence: int = 85,
    generated_at: datetime = NOW,
    expires_at: datetime | None = None,
    rationale: str = "Momentum confirmation is strong.",
    warnings: tuple[str, ...] = (),
) -> StrategySignal:
    return StrategySignal(
        signal_id=signal_id,
        request_id=request_id,
        correlation_id=correlation_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        signal_type=signal_type,
        direction=direction,
        strength=strength,
        confidence=confidence,
        generated_at=generated_at,
        expires_at=expires_at,
        rationale=rationale,
        warnings=warnings,
        metadata=(
            ("environment", "paper"),
        ),
    )


def test_strategy_signal() -> None:
    value = strategy_signal()

    assert value.signal_id == "signal-001"
    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.symbol == "NVDA"
    assert value.signal_type is SignalType.ENTRY
    assert value.direction is SignalDirection.LONG
    assert value.strength is SignalStrength.STRONG
    assert value.confidence == 85
    assert value.generated_at == NOW
    assert value.expires_at is None
    assert value.rationale == (
        "Momentum confirmation is strong."
    )
    assert value.is_actionable is True
    assert value.is_high_confidence is True
    assert value.has_expiration is False


def test_strategy_signal_text_is_normalized() -> None:
    value = StrategySignal(
        signal_id="  signal-001  ",
        request_id="  request-001  ",
        correlation_id="  correlation-001  ",
        strategy_id="  strategy-001  ",
        portfolio_id="  portfolio-001  ",
        symbol="  nvda  ",
        signal_type=SignalType.ENTRY,
        direction=SignalDirection.LONG,
        strength=SignalStrength.STRONG,
        confidence=85,
        generated_at=NOW,
        expires_at=None,
        rationale="  Momentum confirmation is strong.  ",
        metadata=[
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.signal_id == "signal-001"
    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.symbol == "NVDA"
    assert value.rationale == (
        "Momentum confirmation is strong."
    )
    assert value.metadata == (
        ("environment", "paper"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "signal_id",
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "symbol",
        "rationale",
    ],
)
def test_strategy_signal_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "signal_id": "signal-001",
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "symbol": "NVDA",
        "signal_type": SignalType.ENTRY,
        "direction": SignalDirection.LONG,
        "strength": SignalStrength.STRONG,
        "confidence": 85,
        "generated_at": NOW,
        "expires_at": None,
        "rationale": "Momentum confirmation is strong.",
    }

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        StrategySignal(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "signal_id",
        "request_id",
        "correlation_id",
        "strategy_id",
        "portfolio_id",
        "symbol",
        "rationale",
    ],
)
def test_strategy_signal_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "signal_id": "signal-001",
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "strategy_id": "strategy-001",
        "portfolio_id": "portfolio-001",
        "symbol": "NVDA",
        "signal_type": SignalType.ENTRY,
        "direction": SignalDirection.LONG,
        "strength": SignalStrength.STRONG,
        "confidence": 85,
        "generated_at": NOW,
        "expires_at": None,
        "rationale": "Momentum confirmation is strong.",
    }

    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        StrategySignal(**arguments)


def test_strategy_signal_requires_signal_type() -> None:
    with pytest.raises(
        TypeError,
        match="signal_type must be a SignalType",
    ):
        strategy_signal(
            signal_type="ENTRY"
        )


def test_strategy_signal_requires_direction() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "direction must be a SignalDirection"
        ),
    ):
        strategy_signal(
            direction="LONG"
        )


def test_strategy_signal_requires_strength() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "strength must be a SignalStrength"
        ),
    ):
        strategy_signal(
            strength="STRONG"
        )


@pytest.mark.parametrize(
    "confidence",
    [
        -1,
        101,
    ],
)
def test_strategy_signal_confidence_bounds(
    confidence: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "confidence must be between 0 and 100"
        ),
    ):
        strategy_signal(
            confidence=confidence
        )


def test_strategy_signal_confidence_requires_integer(
) -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        strategy_signal(
            confidence="85"
        )


def test_strategy_signal_confidence_rejects_bool(
) -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be an integer",
    ):
        strategy_signal(
            confidence=True
        )


@pytest.mark.parametrize(
    "confidence",
    [
        0,
        100,
    ],
)
def test_strategy_signal_confidence_boundaries_allowed(
    confidence: int,
) -> None:
    value = strategy_signal(
        confidence=confidence
    )

    assert value.confidence == confidence


def test_strategy_signal_generated_at_requires_datetime(
) -> None:
    with pytest.raises(
        TypeError,
        match="generated_at must be a datetime",
    ):
        StrategySignal(
            signal_id="signal-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            signal_type=SignalType.ENTRY,
            direction=SignalDirection.LONG,
            strength=SignalStrength.STRONG,
            confidence=85,
            generated_at="2026-08-10",
            expires_at=None,
            rationale="Momentum confirmation is strong.",
        )


def test_strategy_signal_generated_at_must_be_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="generated_at must be timezone-aware",
    ):
        strategy_signal(
            generated_at=datetime(
                2026,
                8,
                10,
                21,
                45,
            )
        )


def test_strategy_signal_expires_at_requires_datetime(
) -> None:
    with pytest.raises(
        TypeError,
        match="expires_at must be a datetime",
    ):
        StrategySignal(
            signal_id="signal-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            signal_type=SignalType.ENTRY,
            direction=SignalDirection.LONG,
            strength=SignalStrength.STRONG,
            confidence=85,
            generated_at=NOW,
            expires_at="2026-08-10",
            rationale="Momentum confirmation is strong.",
        )


def test_strategy_signal_expires_at_must_be_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="expires_at must be timezone-aware",
    ):
        strategy_signal(
            expires_at=datetime(
                2026,
                8,
                10,
                22,
                0,
            )
        )


def test_strategy_signal_expiration_must_follow_generation(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "expires_at must not be earlier "
            "than generated_at"
        ),
    ):
        strategy_signal(
            expires_at=(
                NOW - timedelta(seconds=1)
            )
        )


def test_strategy_signal_expiration_may_equal_generation(
) -> None:
    value = strategy_signal(
        expires_at=NOW
    )

    assert value.expires_at == NOW
    assert value.has_expiration is True


def test_strategy_signal_has_expiration() -> None:
    value = strategy_signal(
        expires_at=(
            NOW + timedelta(minutes=5)
        )
    )

    assert value.has_expiration is True


def test_strategy_signal_without_expiration_never_expires(
) -> None:
    value = strategy_signal(
        expires_at=None
    )

    assert value.is_expired_at(
        NOW + timedelta(days=1)
    ) is False


def test_strategy_signal_is_not_expired_at_boundary(
) -> None:
    expires_at = (
        NOW + timedelta(minutes=5)
    )

    value = strategy_signal(
        expires_at=expires_at
    )

    assert value.is_expired_at(
        expires_at
    ) is False


def test_strategy_signal_is_expired_after_boundary(
) -> None:
    expires_at = (
        NOW + timedelta(minutes=5)
    )

    value = strategy_signal(
        expires_at=expires_at
    )

    assert value.is_expired_at(
        expires_at + timedelta(microseconds=1)
    ) is True


def test_strategy_signal_expiry_check_requires_datetime(
) -> None:
    value = strategy_signal(
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


def test_strategy_signal_expiry_check_requires_aware_datetime(
) -> None:
    value = strategy_signal(
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
                22,
                0,
            )
        )


def test_strategy_signal_hold_requires_flat_direction(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "HOLD signals require FLAT direction"
        ),
    ):
        strategy_signal(
            signal_type=SignalType.HOLD,
            direction=SignalDirection.LONG,
        )


def test_strategy_signal_hold_is_not_actionable() -> None:
    value = strategy_signal(
        signal_type=SignalType.HOLD,
        direction=SignalDirection.FLAT,
    )

    assert value.is_actionable is False


def test_strategy_signal_entry_rejects_flat_direction(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "ENTRY signals require LONG or SHORT direction"
        ),
    ):
        strategy_signal(
            signal_type=SignalType.ENTRY,
            direction=SignalDirection.FLAT,
        )


@pytest.mark.parametrize(
    "signal_type",
    [
        SignalType.SCALE_IN,
        SignalType.SCALE_OUT,
        SignalType.HEDGE,
    ],
)
def test_strategy_signal_directional_types_reject_flat(
    signal_type: SignalType,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            f"{signal_type.value} signals require "
            "LONG or SHORT direction"
        ),
    ):
        strategy_signal(
            signal_type=signal_type,
            direction=SignalDirection.FLAT,
        )


def test_strategy_signal_is_actionable() -> None:
    value = strategy_signal()

    assert value.is_actionable is True


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (79, False),
        (80, True),
        (100, True),
    ],
)
def test_strategy_signal_high_confidence_property(
    confidence: int,
    expected: bool,
) -> None:
    value = strategy_signal(
        confidence=confidence
    )

    assert value.is_high_confidence is expected


def test_strategy_signal_warnings_are_normalized(
) -> None:
    value = strategy_signal(
        warnings=(
            " spread elevated ",
            "spread elevated",
            " liquidity lower ",
        )
    )

    assert value.warnings == (
        "spread elevated",
        "liquidity lower",
    )


def test_strategy_signal_warnings_reject_empty_values(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        strategy_signal(
            warnings=(
                "valid warning",
                "   ",
            )
        )


def test_strategy_signal_warnings_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        strategy_signal(
            warnings=(
                "valid warning",
                123,
            )
        )


def test_strategy_signal_metadata_is_normalized(
) -> None:
    value = StrategySignal(
        signal_id="signal-001",
        request_id="request-001",
        correlation_id="correlation-001",
        strategy_id="strategy-001",
        portfolio_id="portfolio-001",
        symbol="NVDA",
        signal_type=SignalType.ENTRY,
        direction=SignalDirection.LONG,
        strength=SignalStrength.STRONG,
        confidence=85,
        generated_at=NOW,
        expires_at=None,
        rationale="Momentum confirmation is strong.",
        metadata=[
            ("  model  ", "  momentum  "),
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.metadata == (
        ("model", "momentum"),
        ("environment", "paper"),
    )


def test_strategy_signal_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        StrategySignal(
            signal_id="signal-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            signal_type=SignalType.ENTRY,
            direction=SignalDirection.LONG,
            strength=SignalStrength.STRONG,
            confidence=85,
            generated_at=NOW,
            expires_at=None,
            rationale="Momentum confirmation is strong.",
            metadata=(
                ("model", "momentum"),
                ("model", "duplicate"),
            ),
        )


def test_strategy_signal_metadata_items_must_be_pairs(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        StrategySignal(
            signal_id="signal-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            signal_type=SignalType.ENTRY,
            direction=SignalDirection.LONG,
            strength=SignalStrength.STRONG,
            confidence=85,
            generated_at=NOW,
            expires_at=None,
            rationale="Momentum confirmation is strong.",
            metadata=(
                ("model",),
            ),
        )


def test_strategy_signal_metadata_keys_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        StrategySignal(
            signal_id="signal-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            signal_type=SignalType.ENTRY,
            direction=SignalDirection.LONG,
            strength=SignalStrength.STRONG,
            confidence=85,
            generated_at=NOW,
            expires_at=None,
            rationale="Momentum confirmation is strong.",
            metadata=(
                (123, "momentum"),
            ),
        )


def test_strategy_signal_metadata_values_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        StrategySignal(
            signal_id="signal-001",
            request_id="request-001",
            correlation_id="correlation-001",
            strategy_id="strategy-001",
            portfolio_id="portfolio-001",
            symbol="NVDA",
            signal_type=SignalType.ENTRY,
            direction=SignalDirection.LONG,
            strength=SignalStrength.STRONG,
            confidence=85,
            generated_at=NOW,
            expires_at=None,
            rationale="Momentum confirmation is strong.",
            metadata=(
                ("model", 123),
            ),
        )


def test_strategy_signal_is_immutable() -> None:
    value = strategy_signal()

    with pytest.raises(FrozenInstanceError):
        value.signal_id = "changed"

def strategy_signal_result(
    *,
    request_id: str = "request-001",
    correlation_id: str = "correlation-001",
    status: SignalStatus = SignalStatus.ACTIVE,
    decision: SignalDecision = SignalDecision.PROCEED,
    started_at: datetime = NOW,
    updated_at: datetime = NOW,
    completed_at: datetime | None = None,
    signal: StrategySignal | None = None,
    warnings: tuple[str, ...] = (),
    error: str | None = None,
) -> StrategySignalResult:
    return StrategySignalResult(
        request_id=request_id,
        correlation_id=correlation_id,
        status=status,
        decision=decision,
        started_at=started_at,
        updated_at=updated_at,
        completed_at=completed_at,
        signal=signal,
        warnings=warnings,
        error=error,
        metadata=(
            ("environment", "paper"),
        ),
    )


def accepted_signal_result() -> StrategySignalResult:
    return strategy_signal_result(
        status=SignalStatus.ACCEPTED,
        decision=SignalDecision.ACCEPT,
        completed_at=NOW,
        signal=strategy_signal(),
    )


def failed_signal_result(
    *,
    retryable: bool = True,
) -> StrategySignalResult:
    return strategy_signal_result(
        status=SignalStatus.FAILED,
        decision=(
            SignalDecision.RETRY
            if retryable
            else SignalDecision.NO_ACTION
        ),
        completed_at=NOW,
        signal=None,
        error="Signal evaluation failed.",
    )


def test_active_strategy_signal_result() -> None:
    value = strategy_signal_result()

    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.status is SignalStatus.ACTIVE
    assert value.decision is SignalDecision.PROCEED
    assert value.started_at == NOW
    assert value.updated_at == NOW
    assert value.completed_at is None
    assert value.signal is None
    assert value.is_terminal is False
    assert value.is_successful is False
    assert value.has_signal is False


def test_pending_strategy_signal_result() -> None:
    value = strategy_signal_result(
        status=SignalStatus.PENDING,
        decision=SignalDecision.NO_ACTION,
    )

    assert value.status is SignalStatus.PENDING
    assert value.is_terminal is False


def test_accepted_strategy_signal_result() -> None:
    value = accepted_signal_result()

    assert value.status is SignalStatus.ACCEPTED
    assert value.decision is SignalDecision.ACCEPT
    assert value.is_terminal is True
    assert value.is_successful is True
    assert value.has_signal is True
    assert value.signal == strategy_signal()


def test_rejected_strategy_signal_result() -> None:
    value = strategy_signal_result(
        status=SignalStatus.REJECTED,
        decision=SignalDecision.REJECT,
        completed_at=NOW,
    )

    assert value.status is SignalStatus.REJECTED
    assert value.is_terminal is True
    assert value.is_successful is False


def test_expired_strategy_signal_result() -> None:
    value = strategy_signal_result(
        status=SignalStatus.EXPIRED,
        decision=SignalDecision.NO_ACTION,
        completed_at=NOW,
        signal=strategy_signal(),
    )

    assert value.status is SignalStatus.EXPIRED
    assert value.has_signal is True


def test_cancelled_strategy_signal_result() -> None:
    value = strategy_signal_result(
        status=SignalStatus.CANCELLED,
        decision=SignalDecision.CANCEL,
        completed_at=NOW,
    )

    assert value.status is SignalStatus.CANCELLED
    assert value.is_terminal is True


def test_failed_strategy_signal_result_retryable() -> None:
    value = failed_signal_result(
        retryable=True
    )

    assert value.status is SignalStatus.FAILED
    assert value.decision is SignalDecision.RETRY
    assert value.error == "Signal evaluation failed."
    assert value.is_terminal is True


def test_failed_strategy_signal_result_non_retryable() -> None:
    value = failed_signal_result(
        retryable=False
    )

    assert value.decision is SignalDecision.NO_ACTION


def test_signal_result_text_is_normalized() -> None:
    value = StrategySignalResult(
        request_id="  request-001  ",
        correlation_id="  correlation-001  ",
        status=SignalStatus.ACTIVE,
        decision=SignalDecision.PROCEED,
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
def test_signal_result_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "status": SignalStatus.ACTIVE,
        "decision": SignalDecision.PROCEED,
        "started_at": NOW,
        "updated_at": NOW,
    }

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        StrategySignalResult(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "correlation_id",
    ],
)
def test_signal_result_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "correlation_id": "correlation-001",
        "status": SignalStatus.ACTIVE,
        "decision": SignalDecision.PROCEED,
        "started_at": NOW,
        "updated_at": NOW,
    }

    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        StrategySignalResult(**arguments)


def test_signal_result_requires_status_enum() -> None:
    with pytest.raises(
        TypeError,
        match="status must be a SignalStatus",
    ):
        strategy_signal_result(
            status="ACTIVE"
        )


def test_signal_result_requires_decision_enum() -> None:
    with pytest.raises(
        TypeError,
        match="decision must be a SignalDecision",
    ):
        strategy_signal_result(
            decision="PROCEED"
        )


def test_signal_result_started_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="started_at must be a datetime",
    ):
        StrategySignalResult(
            request_id="request-001",
            correlation_id="correlation-001",
            status=SignalStatus.ACTIVE,
            decision=SignalDecision.PROCEED,
            started_at="2026-08-10",
            updated_at=NOW,
        )


def test_signal_result_started_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="started_at must be timezone-aware",
    ):
        strategy_signal_result(
            started_at=datetime(
                2026,
                8,
                10,
                21,
                45,
            )
        )


def test_signal_result_updated_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="updated_at must be a datetime",
    ):
        StrategySignalResult(
            request_id="request-001",
            correlation_id="correlation-001",
            status=SignalStatus.ACTIVE,
            decision=SignalDecision.PROCEED,
            started_at=NOW,
            updated_at="2026-08-10",
        )


def test_signal_result_updated_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="updated_at must be timezone-aware",
    ):
        strategy_signal_result(
            updated_at=datetime(
                2026,
                8,
                10,
                21,
                45,
            )
        )


def test_signal_result_updated_at_must_follow_start() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "updated_at must not be earlier "
            "than started_at"
        ),
    ):
        strategy_signal_result(
            started_at=NOW,
            updated_at=(
                NOW - timedelta(seconds=1)
            ),
        )


def test_signal_result_completed_at_requires_datetime(
) -> None:
    with pytest.raises(
        TypeError,
        match="completed_at must be a datetime",
    ):
        StrategySignalResult(
            request_id="request-001",
            correlation_id="correlation-001",
            status=SignalStatus.REJECTED,
            decision=SignalDecision.REJECT,
            started_at=NOW,
            updated_at=NOW,
            completed_at="2026-08-10",
        )


def test_signal_result_completed_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="completed_at must be timezone-aware",
    ):
        strategy_signal_result(
            status=SignalStatus.REJECTED,
            decision=SignalDecision.REJECT,
            completed_at=datetime(
                2026,
                8,
                10,
                21,
                45,
            ),
        )


def test_signal_result_completed_at_must_follow_update(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed_at must not be earlier "
            "than updated_at"
        ),
    ):
        strategy_signal_result(
            status=SignalStatus.REJECTED,
            decision=SignalDecision.REJECT,
            updated_at=NOW,
            completed_at=(
                NOW - timedelta(seconds=1)
            ),
        )


def test_signal_result_requires_signal_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "signal must be a StrategySignal or None"
        ),
    ):
        strategy_signal_result(
            signal=object()
        )


def test_signal_request_id_must_match_result() -> None:
    value = strategy_signal(
        request_id="different-request"
    )

    with pytest.raises(
        ValueError,
        match=(
            "signal request_id must match "
            "result request_id"
        ),
    ):
        strategy_signal_result(
            signal=value
        )


def test_signal_correlation_id_must_match_result() -> None:
    value = strategy_signal(
        correlation_id="different-correlation"
    )

    with pytest.raises(
        ValueError,
        match=(
            "signal correlation_id must match "
            "result correlation_id"
        ),
    ):
        strategy_signal_result(
            signal=value
        )


def test_signal_generation_must_not_precede_result_start(
) -> None:
    value = strategy_signal(
        generated_at=(
            NOW - timedelta(seconds=1)
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "signal generated_at must not be earlier "
            "than result started_at"
        ),
    ):
        strategy_signal_result(
            signal=value
        )


def test_signal_generation_must_not_follow_result_update(
) -> None:
    value = strategy_signal(
        generated_at=(
            NOW + timedelta(seconds=1)
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "signal generated_at must not be later "
            "than result updated_at"
        ),
    ):
        strategy_signal_result(
            updated_at=NOW,
            signal=value,
        )


@pytest.mark.parametrize(
    "status",
    [
        SignalStatus.ACCEPTED,
        SignalStatus.REJECTED,
        SignalStatus.EXPIRED,
        SignalStatus.CANCELLED,
        SignalStatus.FAILED,
    ],
)
def test_terminal_signal_result_requires_completed_at(
    status: SignalStatus,
) -> None:
    if status is SignalStatus.ACCEPTED:
        decision = SignalDecision.ACCEPT
        signal = strategy_signal()
        error = None
    elif status is SignalStatus.REJECTED:
        decision = SignalDecision.REJECT
        signal = None
        error = None
    elif status is SignalStatus.EXPIRED:
        decision = SignalDecision.NO_ACTION
        signal = strategy_signal()
        error = None
    elif status is SignalStatus.CANCELLED:
        decision = SignalDecision.CANCEL
        signal = None
        error = None
    else:
        decision = SignalDecision.RETRY
        signal = None
        error = "Signal evaluation failed."

    with pytest.raises(
        ValueError,
        match=(
            "terminal signal results require "
            "completed_at"
        ),
    ):
        strategy_signal_result(
            status=status,
            decision=decision,
            completed_at=None,
            signal=signal,
            error=error,
        )


@pytest.mark.parametrize(
    ("status", "decision"),
    [
        (
            SignalStatus.PENDING,
            SignalDecision.NO_ACTION,
        ),
        (
            SignalStatus.ACTIVE,
            SignalDecision.PROCEED,
        ),
    ],
)
def test_non_terminal_signal_result_rejects_completed_at(
    status: SignalStatus,
    decision: SignalDecision,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-terminal signal results must not "
            "include completed_at"
        ),
    ):
        strategy_signal_result(
            status=status,
            decision=decision,
            completed_at=NOW,
        )


def test_pending_result_requires_no_action() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "pending signal results require "
            "NO_ACTION decision"
        ),
    ):
        strategy_signal_result(
            status=SignalStatus.PENDING,
            decision=SignalDecision.PROCEED,
        )


def test_pending_result_rejects_signal() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "pending signal results must not "
            "include a signal"
        ),
    ):
        strategy_signal_result(
            status=SignalStatus.PENDING,
            decision=SignalDecision.NO_ACTION,
            signal=strategy_signal(),
        )


def test_active_result_requires_proceed() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "active signal results require "
            "PROCEED decision"
        ),
    ):
        strategy_signal_result(
            status=SignalStatus.ACTIVE,
            decision=SignalDecision.HOLD,
        )


def test_accepted_result_requires_accept() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "accepted signal results require "
            "ACCEPT decision"
        ),
    ):
        strategy_signal_result(
            status=SignalStatus.ACCEPTED,
            decision=SignalDecision.PROCEED,
            completed_at=NOW,
            signal=strategy_signal(),
        )


def test_accepted_result_requires_signal() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "accepted signal results require "
            "a signal"
        ),
    ):
        strategy_signal_result(
            status=SignalStatus.ACCEPTED,
            decision=SignalDecision.ACCEPT,
            completed_at=NOW,
            signal=None,
        )


def test_rejected_result_requires_reject() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "rejected signal results require "
            "REJECT decision"
        ),
    ):
        strategy_signal_result(
            status=SignalStatus.REJECTED,
            decision=SignalDecision.NO_ACTION,
            completed_at=NOW,
        )


def test_expired_result_requires_no_action() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "expired signal results require "
            "NO_ACTION decision"
        ),
    ):
        strategy_signal_result(
            status=SignalStatus.EXPIRED,
            decision=SignalDecision.HOLD,
            completed_at=NOW,
            signal=strategy_signal(),
        )


def test_expired_result_requires_signal() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "expired signal results require "
            "a signal"
        ),
    ):
        strategy_signal_result(
            status=SignalStatus.EXPIRED,
            decision=SignalDecision.NO_ACTION,
            completed_at=NOW,
            signal=None,
        )


def test_cancelled_result_requires_cancel() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "cancelled signal results require "
            "CANCEL decision"
        ),
    ):
        strategy_signal_result(
            status=SignalStatus.CANCELLED,
            decision=SignalDecision.NO_ACTION,
            completed_at=NOW,
        )


@pytest.mark.parametrize(
    "decision",
    [
        SignalDecision.RETRY,
        SignalDecision.NO_ACTION,
    ],
)
def test_failed_result_allows_retry_or_no_action(
    decision: SignalDecision,
) -> None:
    value = strategy_signal_result(
        status=SignalStatus.FAILED,
        decision=decision,
        completed_at=NOW,
        error="Signal evaluation failed.",
    )

    assert value.decision is decision


def test_failed_result_rejects_success_decision() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed signal results require "
            "RETRY or NO_ACTION decision"
        ),
    ):
        strategy_signal_result(
            status=SignalStatus.FAILED,
            decision=SignalDecision.ACCEPT,
            completed_at=NOW,
            error="Signal evaluation failed.",
        )


def test_failed_result_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed signal results require "
            "an error"
        ),
    ):
        strategy_signal_result(
            status=SignalStatus.FAILED,
            decision=SignalDecision.RETRY,
            completed_at=NOW,
            error=None,
        )


def test_only_failed_result_may_include_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only failed signal results may "
            "include an error"
        ),
    ):
        strategy_signal_result(
            status=SignalStatus.REJECTED,
            decision=SignalDecision.REJECT,
            completed_at=NOW,
            error="Unexpected error.",
        )


def test_signal_result_error_is_normalized() -> None:
    value = strategy_signal_result(
        status=SignalStatus.FAILED,
        decision=SignalDecision.RETRY,
        completed_at=NOW,
        error="  Signal evaluation failed.  ",
    )

    assert value.error == "Signal evaluation failed."


def test_signal_result_error_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="error must not be empty",
    ):
        strategy_signal_result(
            status=SignalStatus.FAILED,
            decision=SignalDecision.RETRY,
            completed_at=NOW,
            error="   ",
        )


def test_signal_result_warnings_are_normalized() -> None:
    value = strategy_signal_result(
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


def test_signal_result_warnings_reject_empty_values(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        strategy_signal_result(
            warnings=(
                "valid",
                "   ",
            )
        )


def test_signal_result_warnings_require_strings() -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        strategy_signal_result(
            warnings=(
                "valid",
                123,
            )
        )


def test_signal_result_metadata_is_normalized() -> None:
    value = StrategySignalResult(
        request_id="request-001",
        correlation_id="correlation-001",
        status=SignalStatus.ACTIVE,
        decision=SignalDecision.PROCEED,
        started_at=NOW,
        updated_at=NOW,
        metadata=[
            ("  engine  ", "  strategy-signal  "),
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.metadata == (
        ("engine", "strategy-signal"),
        ("environment", "paper"),
    )


def test_signal_result_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        StrategySignalResult(
            request_id="request-001",
            correlation_id="correlation-001",
            status=SignalStatus.ACTIVE,
            decision=SignalDecision.PROCEED,
            started_at=NOW,
            updated_at=NOW,
            metadata=(
                ("engine", "one"),
                ("engine", "two"),
            ),
        )


def test_strategy_signal_result_is_immutable() -> None:
    value = accepted_signal_result()

    with pytest.raises(FrozenInstanceError):
        value.status = SignalStatus.FAILED

def strategy_signal_report(
    *,
    report_id: str = "report-001",
    request: StrategySignalRequest | None = None,
    result: StrategySignalResult | None = None,
    reported_at: datetime = NOW,
    message: str = "Strategy signal evaluation updated.",
    warnings: tuple[str, ...] = (),
) -> StrategySignalReport:
    return StrategySignalReport(
        report_id=report_id,
        request=request or signal_request(),
        result=result or strategy_signal_result(),
        reported_at=reported_at,
        message=message,
        warnings=warnings,
        metadata=(
            ("source", "strategy-signal-engine"),
        ),
    )


def test_strategy_signal_report() -> None:
    value = strategy_signal_report()

    assert value.report_id == "report-001"
    assert value.request_id == "request-001"
    assert value.correlation_id == "correlation-001"
    assert value.strategy_id == "strategy-001"
    assert value.portfolio_id == "portfolio-001"
    assert value.symbol == "NVDA"
    assert value.status is SignalStatus.ACTIVE
    assert value.decision is SignalDecision.PROCEED
    assert value.signal is None
    assert value.is_terminal is False
    assert value.reported_at == NOW
    assert value.message == (
        "Strategy signal evaluation updated."
    )
    assert value.metadata == (
        ("source", "strategy-signal-engine"),
    )


def test_accepted_strategy_signal_report() -> None:
    value = strategy_signal_report(
        result=accepted_signal_result(),
    )

    assert value.status is SignalStatus.ACCEPTED
    assert value.decision is SignalDecision.ACCEPT
    assert value.signal is not None
    assert value.is_terminal is True


def test_strategy_signal_report_text_is_normalized() -> None:
    value = StrategySignalReport(
        report_id="  report-001  ",
        request=signal_request(),
        result=strategy_signal_result(),
        reported_at=NOW,
        message="  Strategy signal updated.  ",
        warnings=(
            " warning one ",
            "warning one",
            " warning two ",
        ),
        metadata=[
            ("  source  ", "  strategy-signal-engine  "),
        ],
    )

    assert value.report_id == "report-001"
    assert value.message == "Strategy signal updated."
    assert value.warnings == (
        "warning one",
        "warning two",
    )
    assert value.metadata == (
        ("source", "strategy-signal-engine"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_strategy_signal_report_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "report_id": "report-001",
        "request": signal_request(),
        "result": strategy_signal_result(),
        "reported_at": NOW,
        "message": "Strategy signal updated.",
    }

    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        StrategySignalReport(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_strategy_signal_report_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "report_id": "report-001",
        "request": signal_request(),
        "result": strategy_signal_result(),
        "reported_at": NOW,
        "message": "Strategy signal updated.",
    }

    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        StrategySignalReport(**arguments)


def test_strategy_signal_report_requires_request_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "request must be a StrategySignalRequest"
        ),
    ):
        StrategySignalReport(
            report_id="report-001",
            request=object(),
            result=strategy_signal_result(),
            reported_at=NOW,
            message="Strategy signal updated.",
        )


def test_strategy_signal_report_requires_result_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "result must be a StrategySignalResult"
        ),
    ):
        StrategySignalReport(
            report_id="report-001",
            request=signal_request(),
            result=object(),
            reported_at=NOW,
            message="Strategy signal updated.",
        )


def test_strategy_signal_reported_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="reported_at must be a datetime",
    ):
        StrategySignalReport(
            report_id="report-001",
            request=signal_request(),
            result=strategy_signal_result(),
            reported_at="2026-08-10",
            message="Strategy signal updated.",
        )


def test_strategy_signal_reported_at_must_be_aware() -> None:
    with pytest.raises(
        ValueError,
        match="reported_at must be timezone-aware",
    ):
        strategy_signal_report(
            reported_at=datetime(
                2026,
                8,
                10,
                21,
                45,
            )
        )


def test_report_request_id_must_match_result() -> None:
    result = strategy_signal_result(
        request_id="different-request",
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result request_id values "
            "must match"
        ),
    ):
        strategy_signal_report(
            result=result,
        )


def test_report_correlation_id_must_match_result() -> None:
    result = strategy_signal_result(
        correlation_id="different-correlation",
    )

    with pytest.raises(
        ValueError,
        match=(
            "request and result correlation_id values "
            "must match"
        ),
    ):
        strategy_signal_report(
            result=result,
        )


def test_report_result_must_not_start_before_request() -> None:
    request = signal_request(
        created_at=NOW,
    )

    result = strategy_signal_result(
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
        strategy_signal_report(
            request=request,
            result=result,
        )


def test_reported_at_must_follow_result_update() -> None:
    result = strategy_signal_result(
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
        strategy_signal_report(
            result=result,
            reported_at=NOW,
        )


def test_reported_at_must_follow_result_completion() -> None:
    signal = strategy_signal(
        generated_at=NOW,
    )

    result = strategy_signal_result(
        status=SignalStatus.ACCEPTED,
        decision=SignalDecision.ACCEPT,
        started_at=NOW,
        updated_at=NOW,
        completed_at=(
            NOW + timedelta(seconds=1)
        ),
        signal=signal,
    )

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier "
            "than result completed_at"
        ),
    ):
        strategy_signal_report(
            result=result,
            reported_at=NOW,
        )


def test_report_signal_strategy_id_must_match_request() -> None:
    signal = strategy_signal(
        strategy_id="different-strategy",
    )

    result = strategy_signal_result(
        status=SignalStatus.ACCEPTED,
        decision=SignalDecision.ACCEPT,
        completed_at=NOW,
        signal=signal,
    )

    with pytest.raises(
        ValueError,
        match=(
            "signal strategy_id must match request"
        ),
    ):
        strategy_signal_report(
            result=result,
        )


def test_report_signal_portfolio_id_must_match_request() -> None:
    signal = strategy_signal(
        portfolio_id="different-portfolio",
    )

    result = strategy_signal_result(
        status=SignalStatus.ACCEPTED,
        decision=SignalDecision.ACCEPT,
        completed_at=NOW,
        signal=signal,
    )

    with pytest.raises(
        ValueError,
        match=(
            "signal portfolio_id must match request"
        ),
    ):
        strategy_signal_report(
            result=result,
        )


def test_report_signal_symbol_must_match_request() -> None:
    signal = strategy_signal(
        symbol="AAPL",
    )

    result = strategy_signal_result(
        status=SignalStatus.ACCEPTED,
        decision=SignalDecision.ACCEPT,
        completed_at=NOW,
        signal=signal,
    )

    with pytest.raises(
        ValueError,
        match="signal symbol must match request",
    ):
        strategy_signal_report(
            result=result,
        )


def test_report_signal_type_must_match_request() -> None:
    signal = strategy_signal(
        signal_type=SignalType.EXIT,
        direction=SignalDirection.LONG,
    )

    result = strategy_signal_result(
        status=SignalStatus.ACCEPTED,
        decision=SignalDecision.ACCEPT,
        completed_at=NOW,
        signal=signal,
    )

    with pytest.raises(
        ValueError,
        match=(
            "signal signal_type must match request"
        ),
    ):
        strategy_signal_report(
            result=result,
        )


def test_report_signal_direction_must_match_request() -> None:
    signal = strategy_signal(
        direction=SignalDirection.SHORT,
    )

    result = strategy_signal_result(
        status=SignalStatus.ACCEPTED,
        decision=SignalDecision.ACCEPT,
        completed_at=NOW,
        signal=signal,
    )

    with pytest.raises(
        ValueError,
        match=(
            "signal direction must match request"
        ),
    ):
        strategy_signal_report(
            result=result,
        )


def test_strategy_signal_report_warnings_are_normalized(
) -> None:
    value = strategy_signal_report(
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


def test_strategy_signal_report_warnings_reject_empty_values(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "warnings must not contain empty values"
        ),
    ):
        strategy_signal_report(
            warnings=(
                "valid",
                "   ",
            )
        )


def test_strategy_signal_report_warnings_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="every warning must be a string",
    ):
        strategy_signal_report(
            warnings=(
                "valid",
                123,
            )
        )


def test_strategy_signal_report_metadata_is_normalized(
) -> None:
    value = StrategySignalReport(
        report_id="report-001",
        request=signal_request(),
        result=strategy_signal_result(),
        reported_at=NOW,
        message="Strategy signal updated.",
        metadata=[
            ("  source  ", "  engine  "),
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.metadata == (
        ("source", "engine"),
        ("environment", "paper"),
    )


def test_strategy_signal_report_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        StrategySignalReport(
            report_id="report-001",
            request=signal_request(),
            result=strategy_signal_result(),
            reported_at=NOW,
            message="Strategy signal updated.",
            metadata=(
                ("source", "engine"),
                ("source", "duplicate"),
            ),
        )


def test_strategy_signal_report_metadata_items_must_be_pairs(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        StrategySignalReport(
            report_id="report-001",
            request=signal_request(),
            result=strategy_signal_result(),
            reported_at=NOW,
            message="Strategy signal updated.",
            metadata=(
                ("source",),
            ),
        )


def test_strategy_signal_report_metadata_keys_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata keys must be strings",
    ):
        StrategySignalReport(
            report_id="report-001",
            request=signal_request(),
            result=strategy_signal_result(),
            reported_at=NOW,
            message="Strategy signal updated.",
            metadata=(
                (123, "engine"),
            ),
        )


def test_strategy_signal_report_metadata_values_require_strings(
) -> None:
    with pytest.raises(
        TypeError,
        match="metadata values must be strings",
    ):
        StrategySignalReport(
            report_id="report-001",
            request=signal_request(),
            result=strategy_signal_result(),
            reported_at=NOW,
            message="Strategy signal updated.",
            metadata=(
                ("source", 123),
            ),
        )


def test_strategy_signal_report_is_immutable() -> None:
    value = strategy_signal_report()

    with pytest.raises(FrozenInstanceError):
        value.report_id = "changed"