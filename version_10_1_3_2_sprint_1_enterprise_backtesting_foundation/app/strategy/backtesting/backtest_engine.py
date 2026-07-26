from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from threading import RLock
from typing import Callable

from .audit_log import BacktestAuditLog
from .metrics import BacktestMetrics
from .models import BacktestConfig, BacktestResult, BacktestStatus


BacktestRunner = Callable[[str, BacktestConfig], BacktestResult]


class BacktestValidationError(ValueError):
    pass


class BacktestEngine:
    """Lifecycle orchestrator for the Enterprise Backtesting Framework.

    Sprint 1 deliberately owns configuration validation, immutable IDs, lifecycle,
    metrics, and auditability. Market replay and execution arrive in later sprints.
    """

    def __init__(
        self,
        *,
        audit_log: BacktestAuditLog | None = None,
        metrics: BacktestMetrics | None = None,
    ) -> None:
        self.audit_log = audit_log or BacktestAuditLog()
        self.metrics = metrics or BacktestMetrics()
        self._results: dict[str, BacktestResult] = {}
        self._lock = RLock()

    def validate(self, config: BacktestConfig) -> None:
        problems: list[str] = []
        if not config.strategy_id.strip():
            problems.append("strategy_id is required")
        if not config.strategy_version.strip():
            problems.append("strategy_version is required")
        if not config.dataset_id.strip():
            problems.append("dataset_id is required")
        if config.initial_capital <= Decimal("0"):
            problems.append("initial_capital must be greater than zero")
        if config.start_time.tzinfo is None or config.end_time.tzinfo is None:
            problems.append("start_time and end_time must be timezone-aware")
        if config.start_time >= config.end_time:
            problems.append("start_time must be earlier than end_time")
        if len(config.base_currency.strip()) != 3:
            problems.append("base_currency must be a three-letter code")
        if problems:
            raise BacktestValidationError("; ".join(problems))

    def create_backtest_id(self, config: BacktestConfig) -> str:
        payload = {
            "strategy_id": config.strategy_id,
            "strategy_version": config.strategy_version,
            "dataset_id": config.dataset_id,
            "initial_capital": str(config.initial_capital),
            "start_time": config.start_time.isoformat(),
            "end_time": config.end_time.isoformat(),
            "timeframe": config.timeframe.value,
            "base_currency": config.base_currency.upper(),
            "random_seed": config.random_seed,
            "parameters": dict(sorted(config.parameters.items())),
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16].upper()
        return f"BT-{digest}"

    def prepare(self, config: BacktestConfig) -> BacktestResult:
        self.validate(config)
        backtest_id = self.create_backtest_id(config)
        result = BacktestResult(
            backtest_id=backtest_id,
            status=BacktestStatus.VALIDATED,
            config=config,
            started_at=datetime.now(timezone.utc),
        )
        with self._lock:
            self._results[backtest_id] = result
        self.metrics.increment_created()
        self.metrics.increment_validated()
        self.audit_log.record(backtest_id, "BACKTEST_VALIDATED", strategy_id=config.strategy_id)
        return result

    def run(self, config: BacktestConfig, runner: BacktestRunner | None = None) -> BacktestResult:
        prepared = self.prepare(config)
        self.audit_log.record(prepared.backtest_id, "BACKTEST_STARTED")
        try:
            with self.metrics.measure_runtime():
                if runner is None:
                    final = BacktestResult(
                        backtest_id=prepared.backtest_id,
                        status=BacktestStatus.COMPLETED,
                        config=config,
                        started_at=prepared.started_at,
                        completed_at=datetime.now(timezone.utc),
                        warnings=("Sprint 1 foundation run: simulation pipeline is not installed yet.",),
                    )
                else:
                    final = runner(prepared.backtest_id, config)
                    if final.backtest_id != prepared.backtest_id:
                        raise ValueError("runner returned a mismatched backtest_id")
                    if final.config != config:
                        raise ValueError("runner returned a mismatched configuration")
            with self._lock:
                self._results[final.backtest_id] = final
            if final.status is BacktestStatus.FAILED:
                self.metrics.increment_failed()
                self.audit_log.record(final.backtest_id, "BACKTEST_FAILED", error=final.error)
            else:
                self.metrics.increment_completed()
                self.audit_log.record(final.backtest_id, "BACKTEST_COMPLETED")
            return final
        except Exception as exc:
            failed = BacktestResult(
                backtest_id=prepared.backtest_id,
                status=BacktestStatus.FAILED,
                config=config,
                started_at=prepared.started_at,
                completed_at=datetime.now(timezone.utc),
                error=str(exc),
            )
            with self._lock:
                self._results[failed.backtest_id] = failed
            self.metrics.increment_failed()
            self.audit_log.record(failed.backtest_id, "BACKTEST_FAILED", error=str(exc))
            return failed

    def get_result(self, backtest_id: str) -> BacktestResult | None:
        with self._lock:
            return self._results.get(backtest_id)

    def list_results(self) -> tuple[BacktestResult, ...]:
        with self._lock:
            return tuple(self._results[key] for key in sorted(self._results))
