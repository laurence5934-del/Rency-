from datetime import datetime, timezone

from app.ai.signal_collector import (
    EnterpriseSignalCollector,
    RawSignal,
    SignalDirection,
    SignalProviderRegistry,
    SignalType,
)


class DemoProvider:
    provider_id = "demo"
    enabled = True

    def collect(self):
        return [
            RawSignal(
                provider_id=self.provider_id,
                signal_type=SignalType.TECHNICAL,
                symbol="PLTR",
                value=0.75,
                confidence=0.90,
                direction=SignalDirection.BULLISH,
                observed_at_utc=datetime.now(timezone.utc).isoformat(),
                source_event_id="demo-1",
                payload={"indicator": "trend"},
            )
        ]

    def health(self):
        return {"status": "HEALTHY"}


registry = SignalProviderRegistry()
registry.register(DemoProvider())
collector = EnterpriseSignalCollector(registry=registry)
result = collector.collect()

assert len(result.accepted) == 1
assert result.accepted[0].symbol == "PLTR"
assert result.accepted[0].weighted_score > 0.0
