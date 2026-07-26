from __future__ import annotations

import hashlib
import json

from .models import NormalizedSignal, RawSignal


class SignalNormalizer:
    def fingerprint(self, signal: RawSignal) -> str:
        identity = {
            "provider_id": signal.provider_id,
            "signal_type": signal.signal_type.value,
            "symbol": signal.symbol.upper().strip(),
            "value": round(signal.value, 8),
            "direction": signal.direction.value,
            "observed_at_utc": signal.observed_at_utc,
            "source_event_id": signal.source_event_id,
        }
        encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def normalize(self, signal: RawSignal, *, quality_score: float) -> NormalizedSignal:
        return NormalizedSignal.create(
            fingerprint=self.fingerprint(signal),
            raw=signal,
            quality_score=quality_score,
        )
