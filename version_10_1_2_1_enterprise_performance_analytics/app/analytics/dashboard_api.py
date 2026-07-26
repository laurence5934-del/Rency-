from __future__ import annotations

from .performance_engine import EnterprisePerformanceAnalyticsEngine
from .report_generator import AnalyticsReportGenerator


class AnalyticsDashboardAPI:
    def __init__(self, engine: EnterprisePerformanceAnalyticsEngine) -> None:
        self._engine = engine
        self._reports = AnalyticsReportGenerator()

    def overview(self, *, invested_capital: float = 0.0) -> dict[str, object]:
        snapshot = self._engine.snapshot(invested_capital=invested_capital)
        return self._reports.dashboard_payload(snapshot)

    def executive_summary(self, *, invested_capital: float = 0.0) -> str:
        return self._reports.executive_summary(self._engine.snapshot(invested_capital=invested_capital))

    def health(self) -> dict[str, object]:
        return self._engine.health()
