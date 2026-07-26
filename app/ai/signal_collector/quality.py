from __future__ import annotations

from datetime import datetime, timezone

from .models import RawSignal


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class SignalQualityScorer:
    def __init__(
        self,
        *,
        max_age_seconds: float = 300.0,
        minimum_confidence: float = 0.05,
    ) -> None:
        if max_age_seconds <= 0.0:
            raise ValueError("max_age_seconds must be greater than zero")
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0.0 and 1.0")
        self._max_age_seconds = max_age_seconds
        self._minimum_confidence = minimum_confidence

    def score(self, signal: RawSignal) -> float:
        now = datetime.now(timezone.utc)
        observed = _parse_timestamp(signal.observed_at_utc)
        age = max(0.0, (now - observed).total_seconds())
        freshness = max(0.0, 1.0 - (age / self._max_age_seconds))

        completeness = 1.0
        if signal.source_event_id is None:
            completeness -= 0.10
        if not signal.payload:
            completeness -= 0.10

        confidence_quality = (
            0.0
            if signal.confidence < self._minimum_confidence
            else signal.confidence
        )

        score = (
            freshness * 0.45
            + confidence_quality * 0.40
            + max(0.0, completeness) * 0.15
        )
        return max(0.0, min(1.0, score))

    def is_expired(self, signal: RawSignal) -> bool:
        if signal.expires_at_utc is None:
            return False
        return _parse_timestamp(signal.expires_at_utc) <= datetime.now(timezone.utc)
