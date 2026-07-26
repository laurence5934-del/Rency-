from __future__ import annotations

import json
from typing import Any

from .models import AnalyticsSnapshot


class AnalyticsReportGenerator:
    def executive_summary(self, snapshot: AnalyticsSnapshot) -> str:
        p, t, r, i, a = snapshot.portfolio, snapshot.trades, snapshot.risk, snapshot.income, snapshot.ai
        return "\n".join([
            "AITradingOS Enterprise Performance Analytics",
            "=" * 48,
            f"Portfolio Value: {p['portfolio_value']:.2f}",
            f"Total P&L: {p['total_pnl']:.2f}",
            f"Win Rate: {t['win_rate']:.2%}",
            f"Profit Factor: {t['profit_factor']}",
            f"Maximum Drawdown: {r['maximum_drawdown']:.2%}",
            f"Total Income: {i['total_income']:.2f}",
            f"AI Decision Accuracy: {a['decision_accuracy']:.2%}",
        ])

    def json_report(self, snapshot: AnalyticsSnapshot, *, indent: int | None = 2) -> str:
        return json.dumps(snapshot.to_dict(), indent=indent, sort_keys=True, default=str)

    def dashboard_payload(self, snapshot: AnalyticsSnapshot) -> dict[str, Any]:
        return snapshot.to_dict()
