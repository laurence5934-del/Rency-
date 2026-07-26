from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable


ZERO = Decimal("0")


class CommissionModelError(ValueError):
    """Raised when a commission model receives invalid inputs."""


@runtime_checkable
class CommissionModel(Protocol):
    """Contract for deterministic simulated trading-cost calculations."""

    def calculate(self, *, quantity: Decimal, price: Decimal) -> Decimal:
        """Return the non-negative commission charged for one execution."""


@dataclass(frozen=True, slots=True)
class NoCommission:
    def calculate(self, *, quantity: Decimal, price: Decimal) -> Decimal:
        _validate_trade_inputs(quantity=quantity, price=price)
        return ZERO


@dataclass(frozen=True, slots=True)
class FlatCommission:
    fee: Decimal

    def __post_init__(self) -> None:
        if self.fee < ZERO:
            raise CommissionModelError("flat commission fee cannot be negative")

    def calculate(self, *, quantity: Decimal, price: Decimal) -> Decimal:
        _validate_trade_inputs(quantity=quantity, price=price)
        return self.fee


@dataclass(frozen=True, slots=True)
class PercentageCommission:
    """Commission charged as a decimal fraction of execution notional.

    Example: ``rate=Decimal('0.001')`` means 0.10% of notional.
    """

    rate: Decimal
    minimum: Decimal = ZERO
    maximum: Decimal | None = None

    def __post_init__(self) -> None:
        if self.rate < ZERO:
            raise CommissionModelError("percentage commission rate cannot be negative")
        if self.minimum < ZERO:
            raise CommissionModelError("minimum commission cannot be negative")
        if self.maximum is not None and self.maximum < self.minimum:
            raise CommissionModelError("maximum commission cannot be below minimum commission")

    def calculate(self, *, quantity: Decimal, price: Decimal) -> Decimal:
        _validate_trade_inputs(quantity=quantity, price=price)
        commission = abs(quantity) * price * self.rate
        commission = max(commission, self.minimum)
        if self.maximum is not None:
            commission = min(commission, self.maximum)
        return commission


@dataclass(frozen=True, slots=True)
class PerShareCommission:
    fee_per_share: Decimal
    minimum: Decimal = ZERO
    maximum: Decimal | None = None

    def __post_init__(self) -> None:
        if self.fee_per_share < ZERO:
            raise CommissionModelError("per-share commission cannot be negative")
        if self.minimum < ZERO:
            raise CommissionModelError("minimum commission cannot be negative")
        if self.maximum is not None and self.maximum < self.minimum:
            raise CommissionModelError("maximum commission cannot be below minimum commission")

    def calculate(self, *, quantity: Decimal, price: Decimal) -> Decimal:
        _validate_trade_inputs(quantity=quantity, price=price)
        commission = abs(quantity) * self.fee_per_share
        commission = max(commission, self.minimum)
        if self.maximum is not None:
            commission = min(commission, self.maximum)
        return commission


def _validate_trade_inputs(*, quantity: Decimal, price: Decimal) -> None:
    if quantity == ZERO:
        raise CommissionModelError("quantity must be non-zero")
    if price <= ZERO:
        raise CommissionModelError("price must be greater than zero")
