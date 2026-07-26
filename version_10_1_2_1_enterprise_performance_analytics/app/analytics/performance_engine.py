from __future__ import annotations

from threading import RLock

from .ai_statistics import AIStatistics
from .attribution_engine import AttributionEngine
from .audit_log import AnalyticsAuditLog
from .benchmark_engine import BenchmarkEngine
from .income_statistics import IncomeStatistics
from .metrics import AnalyticsMetrics
from .models import AIDecisionObservation, AnalyticsSnapshot, ClosedTrade, EquityPoint, IncomeEvent, PortfolioObservation
from .portfolio_statistics import PortfolioStatistics
from .risk_statistics import RiskStatistics
from .trade_statistics import TradeStatistics


class EnterprisePerformanceAnalyticsEngine:
    def __init__(self) -> None:
        self._portfolio_statistics = PortfolioStatistics()
        self._trade_statistics = TradeStatistics()
        self._risk_statistics = RiskStatistics()
        self._income_statistics = IncomeStatistics()
        self._ai_statistics = AIStatistics()
        self._benchmark_engine = BenchmarkEngine()
        self._attribution_engine = AttributionEngine()
        self._audit = AnalyticsAuditLog()
        self._metrics = AnalyticsMetrics()
        self._portfolio: PortfolioObservation | None = None
        self._equity: list[EquityPoint] = []
        self._trades: list[ClosedTrade] = []
        self._income: list[IncomeEvent] = []
        self._ai: list[AIDecisionObservation] = []
        self._benchmark_values: list[float] = []
        self._snapshots: list[AnalyticsSnapshot] = []
        self._lock = RLock()

    def record_portfolio(self, observation: PortfolioObservation) -> None:
        with self._lock:
            self._portfolio = observation
            self._equity.append(EquityPoint(observation.portfolio_value, observation.timestamp_utc))
            self._metrics.increment("portfolio_observations")
            self._audit.append({"event": "PORTFOLIO_RECORDED", "portfolio_value": observation.portfolio_value})

    def record_trade(self, trade: ClosedTrade) -> None:
        with self._lock:
            self._trades.append(trade)
            self._metrics.increment("trades_recorded")

    def record_income(self, event: IncomeEvent) -> None:
        with self._lock:
            self._income.append(event)
            self._metrics.increment("income_events_recorded")

    def record_ai_decision(self, observation: AIDecisionObservation) -> None:
        with self._lock:
            self._ai.append(observation)
            self._metrics.increment("ai_decisions_recorded")

    def record_benchmark_value(self, value: float) -> None:
        if value < 0:
            raise ValueError("benchmark value cannot be negative")
        with self._lock:
            self._benchmark_values.append(float(value))

    def snapshot(self, *, invested_capital: float = 0.0) -> AnalyticsSnapshot:
        with self._lock:
            if self._portfolio is None:
                raise RuntimeError("portfolio observation is required before creating analytics snapshot")
            portfolio = self._portfolio_statistics.calculate(self._portfolio)
            trades = self._trade_statistics.calculate(self._trades)
            risk = self._risk_statistics.calculate(
                [point.value for point in self._equity],
                dict(portfolio["allocation"]),
            )
            income = self._income_statistics.calculate(self._income, invested_capital)
            ai = self._ai_statistics.calculate(self._ai)
            benchmark = self._benchmark_engine.compare(
                tuple(point.value for point in self._equity), tuple(self._benchmark_values)
            )
            attribution = self._attribution_engine.calculate(self._trades)
            snapshot = AnalyticsSnapshot.create(
                portfolio=portfolio,
                trades=trades,
                risk=risk,
                income=income,
                ai=ai,
                benchmark=benchmark,
                attribution=attribution,
            )
            self._snapshots.append(snapshot)
            self._metrics.increment("snapshots_created")
            self._audit.append({"event": "ANALYTICS_SNAPSHOT_CREATED", "snapshot_id": str(snapshot.snapshot_id)})
            return snapshot

    def metrics(self) -> dict[str, int]:
        return self._metrics.snapshot()

    def recent_audit_events(self, limit: int = 50):
        return self._audit.recent(limit)

    def health(self) -> dict[str, object]:
        return {
            "status": "HEALTHY" if self._portfolio is not None else "AWAITING_DATA",
            "portfolio_loaded": self._portfolio is not None,
            "equity_points": len(self._equity),
            "trades": len(self._trades),
            "income_events": len(self._income),
            "ai_decisions": len(self._ai),
            "snapshots": len(self._snapshots),
            "metrics": self.metrics(),
        }
