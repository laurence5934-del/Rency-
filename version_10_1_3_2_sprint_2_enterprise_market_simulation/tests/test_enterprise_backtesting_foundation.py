from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.strategy.backtesting import (
    BacktestConfig,
    BacktestEngine,
    BacktestStatus,
    BacktestValidationError,
)


def valid_config(**overrides):
    values = dict(
        strategy_id="mean-reversion",
        strategy_version="2.1.0",
        dataset_id="QQQ-1D-2018-2025",
        initial_capital=Decimal("250000"),
        start_time=datetime(2018, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        parameters={"lookback": 20},
    )
    values.update(overrides)
    return BacktestConfig(**values)


def test_id_is_deterministic_and_lifecycle_is_audited():
    engine = BacktestEngine()
    first = engine.run(valid_config())
    second = engine.run(valid_config())
    assert first.backtest_id == second.backtest_id
    assert first.status is BacktestStatus.COMPLETED
    events = engine.audit_log.events_for(first.backtest_id)
    assert any(event.event_type == "BACKTEST_VALIDATED" for event in events)
    assert any(event.event_type == "BACKTEST_COMPLETED" for event in events)
    metrics = engine.metrics.snapshot()
    assert metrics.created == 2
    assert metrics.completed == 2


def test_invalid_configuration_is_rejected():
    engine = BacktestEngine()
    config = valid_config(initial_capital=Decimal("0"))
    with pytest.raises(BacktestValidationError, match="initial_capital"):
        engine.prepare(config)
