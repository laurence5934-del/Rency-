from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.strategy.decision.decision_models import (
    Decision,
    DecisionAction,
)


def test_paper_trade_decision_is_approved() -> None:
    decision = Decision(
        action=DecisionAction.PAPER_TRADE,
        confidence=Decimal("0.85"),
        reason="Strategy is ready for paper trading.",
    )

    assert decision.approved is True


def test_live_trade_decision_is_approved() -> None:
    decision = Decision(
        action=DecisionAction.LIVE_TRADE,
        confidence=Decimal("0.95"),
        reason="Strategy meets live deployment standards.",
    )

    assert decision.approved is True


def test_reject_decision_is_not_approved() -> None:
    decision = Decision(
        action=DecisionAction.REJECT,
        confidence=Decimal("0.20"),
        reason="Strategy does not meet deployment standards.",
    )

    assert decision.approved is False


def test_improve_decision_is_not_approved() -> None:
    decision = Decision(
        action=DecisionAction.IMPROVE,
        confidence=Decimal("0.55"),
        reason="Strategy requires additional optimization.",
    )

    assert decision.approved is False


@pytest.mark.parametrize(
    "confidence",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_confidence_must_be_between_zero_and_one(
    confidence: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="between 0 and 1",
    ):
        Decision(
            action=DecisionAction.REJECT,
            confidence=confidence,
            reason="Invalid confidence test.",
        )


def test_confidence_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="confidence must be a Decimal",
    ):
        Decision(
            action=DecisionAction.REJECT,
            confidence=0.50,
            reason="Invalid confidence type.",
        )


def test_reason_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        Decision(
            action=DecisionAction.REJECT,
            confidence=Decimal("0.50"),
            reason="   ",
        )


def test_warnings_are_converted_to_tuple() -> None:
    decision = Decision(
        action=DecisionAction.IMPROVE,
        confidence=Decimal("0.60"),
        reason="Strategy requires improvement.",
        warnings=[
            "Drawdown exceeds target.",
            "Profit factor is below target.",
        ],
    )

    assert decision.warnings == (
        "Drawdown exceeds target.",
        "Profit factor is below target.",
    )


def test_decision_is_immutable() -> None:
    decision = Decision(
        action=DecisionAction.PAPER_TRADE,
        confidence=Decimal("0.85"),
        reason="Strategy is ready for paper trading.",
    )

    with pytest.raises(FrozenInstanceError):
        decision.confidence = Decimal("0.90")