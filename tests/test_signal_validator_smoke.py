from app.ai.signal_validator import (
    EnterpriseSignalValidator,
    PortfolioContext,
    RiskContext,
    ValidationContext,
    ValidationDecision,
)
from app.ai.signal_collector import RawSignal, NormalizedSignal, SignalType, SignalDirection, SignalStatus
from ai_trading_platform_v4_pro.ai_trading_platform_v4_pro.app.ai.signal_validator import EnterpriseSignalValidator, PortfolioContext, RiskContext, ValidationContext, ValidationDecision

raw=RawSignal(provider_id="smoke",signal_type=SignalType.TECHNICAL,symbol="PLTR",
    value=.8,confidence=.9,observed_at_utc=datetime.now(timezone.utc).isoformat(),
    direction=SignalDirection.BULLISH,source_event_id="smoke-1",payload={"indicator":"trend"})
signal=NormalizedSignal.create(fingerprint="validator-smoke",raw=raw,quality_score=.95,status=SignalStatus.ACCEPTED)
context=ValidationContext(portfolio=PortfolioContext(gross_exposure=.5,symbol_exposure={"PLTR":.05},
    available_buying_power=100000),risk=RiskContext(portfolio_drawdown=.02,daily_loss=.005))
validator=EnterpriseSignalValidator()
report=validator.validate(signal,context)
assert report.decision in {ValidationDecision.ACCEPT,ValidationDecision.REVIEW}
assert len(report.checks)==6
assert validator.metrics()["signals_validated"]==1
