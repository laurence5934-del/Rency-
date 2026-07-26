from __future__ import annotations

from .health_engine import HealthEngine
from .models import ReadinessReport, utc_now


class ReadinessValidator:
    def __init__(self, health_engine: HealthEngine) -> None:
        self.health_engine = health_engine

    def validate(self) -> ReadinessReport:
        snapshot = self.health_engine.evaluate()
        passed = tuple(item.name for item in snapshot.components if item.ready)
        failed = tuple(item.name for item in snapshot.components if not item.ready)
        warnings = tuple(item.name for item in snapshot.components if item.healthy and not item.ready)

        return ReadinessReport(
            created_at_utc=utc_now(),
            trading_allowed=snapshot.ready,
            score=snapshot.score,
            passed=passed,
            failed=failed,
            warnings=warnings,
        )
