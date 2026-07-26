from __future__ import annotations

from threading import RLock
from typing import Iterable

from .provider import SignalProvider


class SignalProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, SignalProvider] = {}
        self._lock = RLock()

    def register(self, provider: SignalProvider, *, replace: bool = False) -> None:
        provider_id = provider.provider_id.strip()
        if not provider_id:
            raise ValueError("provider_id cannot be empty")
        with self._lock:
            if provider_id in self._providers and not replace:
                raise KeyError(f"provider already registered: {provider_id}")
            self._providers[provider_id] = provider

    def unregister(self, provider_id: str) -> SignalProvider | None:
        with self._lock:
            return self._providers.pop(provider_id, None)

    def get(self, provider_id: str) -> SignalProvider:
        with self._lock:
            try:
                return self._providers[provider_id]
            except KeyError as exc:
                raise KeyError(f"unknown signal provider: {provider_id}") from exc

    def list(self, *, enabled_only: bool = False) -> tuple[SignalProvider, ...]:
        with self._lock:
            providers = tuple(self._providers.values())
        if enabled_only:
            providers = tuple(p for p in providers if p.enabled)
        return providers

    def register_many(self, providers: Iterable[SignalProvider]) -> None:
        for provider in providers:
            self.register(provider)

    def health(self) -> dict[str, object]:
        providers = self.list()
        return {
            "registered": len(providers),
            "enabled": sum(1 for provider in providers if provider.enabled),
            "providers": {
                provider.provider_id: provider.health()
                for provider in providers
            },
        }
