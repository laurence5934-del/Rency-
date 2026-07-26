from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from .models import ClosedTrade


class AttributionEngine:
    def calculate(self, trades: Iterable[ClosedTrade]) -> dict[str, dict[str, float]]:
        by_symbol: dict[str, float] = defaultdict(float)
        by_strategy: dict[str, float] = defaultdict(float)
        by_broker: dict[str, float] = defaultdict(float)
        for trade in trades:
            by_symbol[trade.symbol.upper()] += trade.pnl
            by_strategy[trade.strategy] += trade.pnl
            by_broker[trade.broker] += trade.pnl
        return {
            "by_symbol": dict(sorted(by_symbol.items())),
            "by_strategy": dict(sorted(by_strategy.items())),
            "by_broker": dict(sorted(by_broker.items())),
        }
