from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from typing import Callable, Iterable, Sequence

from .deduplicator import SignalDeduplicator
from .metrics import SignalCollectorMetrics
from .models import CollectionResult, NormalizedSignal, RawSignal, SignalStatus
from .normalizer import SignalNormalizer
from .quality import SignalQualityScorer
from .registry import SignalProviderRegistry

SignalPublisher = Callable[[NormalizedSignal], None]


class EnterpriseSignalCollector:
    def __init__(
        self,
        *,
        registry: SignalProviderRegistry,
        normalizer: SignalNormalizer | None = None,
        quality_scorer: SignalQualityScorer | None = None,
        deduplicator: SignalDeduplicator | None = None,
        metrics: SignalCollectorMetrics | None = None,
        publisher: SignalPublisher | None = None,
        minimum_quality_score: float = 0.35,
        max_workers: int = 8,
    ) -> None:
        if not 0.0 <= minimum_quality_score <= 1.0:
            raise ValueError("minimum_quality_score must be between 0.0 and 1.0")
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than zero")

        self._registry = registry
        self._normalizer = normalizer or SignalNormalizer()
        self._quality = quality_scorer or SignalQualityScorer()
        self._deduplicator = deduplicator or SignalDeduplicator()
        self._metrics = metrics or SignalCollectorMetrics()
        self._publisher = publisher
        self._minimum_quality_score = minimum_quality_score
        self._max_workers = max_workers

    def collect(self, *, provider_ids: Sequence[str] | None = None) -> CollectionResult:
        self._metrics.increment("collection_cycles")
        providers = (
            tuple(self._registry.get(provider_id) for provider_id in provider_ids)
            if provider_ids is not None
            else self._registry.list(enabled_only=True)
        )

        raw_signals: list[RawSignal] = []
        errors: list[str] = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_map = {
                executor.submit(provider.collect): provider
                for provider in providers
            }
            for future in as_completed(future_map):
                provider = future_map[future]
                self._metrics.increment("providers_polled")
                try:
                    collected = tuple(future.result())
                    raw_signals.extend(collected)
                    self._metrics.increment("raw_signals_received", len(collected))
                except Exception as exc:
                    self._metrics.increment("provider_failures")
                    errors.append(f"{provider.provider_id}: {type(exc).__name__}: {exc}")

        result = self.ingest(raw_signals)
        return CollectionResult(
            accepted=result.accepted,
            rejected=result.rejected,
            duplicates=result.duplicates,
            errors=tuple(errors) + result.errors,
        )

    def ingest(self, signals: Iterable[RawSignal]) -> CollectionResult:
        accepted: list[NormalizedSignal] = []
        rejected: list[NormalizedSignal] = []
        duplicates: list[NormalizedSignal] = []
        errors: list[str] = []

        for raw in signals:
            try:
                quality_score = self._quality.score(raw)
                normalized = self._normalizer.normalize(
                    raw,
                    quality_score=quality_score,
                )

                if self._quality.is_expired(raw):
                    rejected_signal = replace(normalized, status=SignalStatus.EXPIRED)
                    rejected.append(rejected_signal)
                    self._metrics.increment("signals_rejected")
                    continue

                if self._deduplicator.check_and_remember(normalized.fingerprint):
                    duplicate_signal = replace(normalized, status=SignalStatus.DUPLICATE)
                    duplicates.append(duplicate_signal)
                    self._metrics.increment("signals_duplicated")
                    continue

                if quality_score < self._minimum_quality_score:
                    rejected_signal = replace(normalized, status=SignalStatus.REJECTED)
                    rejected.append(rejected_signal)
                    self._metrics.increment("signals_rejected")
                    continue

                accepted_signal = replace(normalized, status=SignalStatus.ACCEPTED)
                if self._publisher is not None:
                    try:
                        self._publisher(accepted_signal)
                        accepted_signal = replace(
                            accepted_signal,
                            status=SignalStatus.PUBLISHED,
                        )
                    except Exception as exc:
                        self._metrics.increment("publish_failures")
                        errors.append(
                            f"{accepted_signal.signal_id}: "
                            f"{type(exc).__name__}: {exc}"
                        )
                        accepted_signal = replace(
                            accepted_signal,
                            status=SignalStatus.FAILED,
                        )

                accepted.append(accepted_signal)
                self._metrics.increment("signals_accepted")
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")

        accepted.sort(
            key=lambda item: (
                item.priority.value,
                item.quality_score,
                item.confidence,
            ),
            reverse=True,
        )

        return CollectionResult(
            accepted=tuple(accepted),
            rejected=tuple(rejected),
            duplicates=tuple(duplicates),
            errors=tuple(errors),
        )

    def health(self) -> dict[str, object]:
        return {
            "status": "HEALTHY",
            "registry": self._registry.health(),
            "deduplication_cache_size": self._deduplicator.size(),
            "metrics": self._metrics.snapshot(),
            "minimum_quality_score": self._minimum_quality_score,
            "max_workers": self._max_workers,
        }

    def metrics(self) -> dict[str, int]:
        return self._metrics.snapshot()
