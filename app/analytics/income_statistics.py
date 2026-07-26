from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime

from .models import IncomeEvent, IncomeType


class IncomeStatistics:
    def calculate(self, events: Iterable[IncomeEvent], invested_capital: float = 0.0) -> dict[str, object]:
        items = tuple(events)
        by_type: dict[str, float] = defaultdict(float)
        by_month: dict[str, float] = defaultdict(float)
        for event in items:
            by_type[event.income_type.value] += event.amount
            month = datetime.fromisoformat(event.timestamp_utc.replace("Z", "+00:00")).strftime("%Y-%m")
            by_month[month] += event.amount
        total = sum(event.amount for event in items)
        return {
            "total_income": total,
            "dividend_income": by_type[IncomeType.DIVIDEND.value],
            "option_premium_income": by_type[IncomeType.OPTION_PREMIUM.value],
            "interest_income": by_type[IncomeType.INTEREST.value],
            "other_income": by_type[IncomeType.OTHER.value],
            "income_by_month": dict(sorted(by_month.items())),
            "annualized_income_run_rate": self._annualized_run_rate(by_month),
            "yield_on_cost": total / invested_capital if invested_capital > 0 else 0.0,
            "event_count": len(items),
        }

    @staticmethod
    def _annualized_run_rate(by_month: dict[str, float]) -> float:
        if not by_month:
            return 0.0
        return sum(by_month.values()) / len(by_month) * 12.0
