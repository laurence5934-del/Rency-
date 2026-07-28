from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Sequence


@dataclass(frozen=True, slots=True)
class ReturnMetrics:
    """Immutable return analytics produced from a backtest result."""

    initial_capital: Decimal
    final_equity: Decimal
    net_profit: Decimal
    total_return: Decimal
    annualized_return: Decimal
    cagr: Decimal
    periodic_returns: Sequence[Decimal] = field(default_factory=tuple)
    warnings: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "periodic_returns",
            tuple(self.periodic_returns),
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )