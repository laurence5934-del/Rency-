from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.ai.signal_validator import (
    EnterpriseSignalValidator,
    PortfolioContext,
    RiskContext,
    ValidationContext,
    ValidationDecision,
)


def test_signal_validator_smoke() -> None:
    now = datetime.now(timezone.utc)

    signal = SimpleNamespace(
        signal_id="signal-001",
        provider_id="technical-engine",
        symbol="PLTR",
        direction=SimpleNamespace(value="BUY"),
        confidence=0.90,
        observed_at_utc=now.isoformat(),
        expires_at_utc=(now + timedelta(minutes=15)).isoformat(),
        fingerprint="technical-engine:PLTR:BUY:signal-001",
    )

    portfolio = PortfolioContext(
        gross_exposure=0.20,
        net_exposure=0.20,
        symbol_exposure={"PLTR": 0.02},
        sector_exposure={"Technology": 0.10},
        available_buying_power=50000.0,
    )

    risk = RiskContext(
        portfolio_drawdown=0.01,
        daily_loss=0.0,
        volatility_index=18.0,
        trading_halted=False,
        restricted_symbols=frozenset(),
    )

    context = ValidationContext(
        portfolio=portfolio,
        risk=risk,
        peer_signals=(),
    )

    validator = EnterpriseSignalValidator()
    report = validator.validate(
        signal,
        context,
        correlation_id="smoke-test-001",
    )

    assert report is not None
    assert report.signal_id == signal.signal_id
    assert report.provider_id == signal.provider_id
    assert report.symbol == signal.symbol
    assert report.decision in {
        ValidationDecision.ACCEPT,
        ValidationDecision.REVIEW,
    }
    assert 0.0 <= report.validation_score <= 1.0
    assert len(report.checks) == 6
    assert validator.metrics()["signals_validated"] == 1
