from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Protocol, runtime_checkable


ZERO = Decimal("0")


class SlippageModelError(ValueError):
    """Raised when slippage inputs or model configuration are invalid."""


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

    @classmethod
    def parse(cls, value: OrderSide | str) -> OrderSide:
        if isinstance(value, cls):
            return value
        try:
            return cls(value.strip().lower())
        except (AttributeError, ValueError) as exc:
            raise SlippageModelError(f"unsupported order side: {value!r}") from exc


@runtime_checkable
class SlippageModel(Protocol):
    """Contract for deterministic execution-price adjustment."""

    def apply(self, *, reference_price: Decimal, side: OrderSide | str) -> Decimal:
        """Return an adjusted execution price."""


@dataclass(frozen=True, slots=True)
class NoSlippage:
    def apply(self, *, reference_price: Decimal, side: OrderSide | str) -> Decimal:
        _validate_reference_price(reference_price)
        OrderSide.parse(side)
        return reference_price


@dataclass(frozen=True, slots=True)
class FixedSlippage:
    """Adverse fixed price movement per executed unit."""

    amount: Decimal

    def __post_init__(self) -> None:
        if self.amount < ZERO:
            raise SlippageModelError("fixed slippage amount cannot be negative")

    def apply(self, *, reference_price: Decimal, side: OrderSide | str) -> Decimal:
        _validate_reference_price(reference_price)
        parsed_side = OrderSide.parse(side)
        adjusted = (
            reference_price + self.amount
            if parsed_side is OrderSide.BUY
            else reference_price - self.amount
        )
        if adjusted <= ZERO:
            raise SlippageModelError("slippage produced a non-positive execution price")
        return adjusted


@dataclass(frozen=True, slots=True)
class PercentageSlippage:
    """Adverse price movement expressed as a decimal fraction.

    Example: ``rate=Decimal('0.001')`` means 0.10% slippage.
    """

    rate: Decimal

    def __post_init__(self) -> None:
        if self.rate < ZERO:
            raise SlippageModelError("percentage slippage rate cannot be negative")
        if self.rate >= Decimal("1"):
            raise SlippageModelError("percentage slippage rate must be less than one")

    def apply(self, *, reference_price: Decimal, side: OrderSide | str) -> Decimal:
        _validate_reference_price(reference_price)
        parsed_side = OrderSide.parse(side)
        multiplier = Decimal("1") + self.rate if parsed_side is OrderSide.BUY else Decimal("1") - self.rate
        adjusted = reference_price * multiplier
        if adjusted <= ZERO:
            raise SlippageModelError("slippage produced a non-positive execution price")
        return adjusted


def _validate_reference_price(reference_price: Decimal) -> None:
    if reference_price <= ZERO:
        raise SlippageModelError("reference_price must be greater than zero")
