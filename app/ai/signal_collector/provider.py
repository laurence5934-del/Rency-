from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from .models import RawSignal


@runtime_checkable
class SignalProvider(Protocol):
    @property
    def provider_id(self) -> str:
        ...

    @property
    def enabled(self) -> bool:
        ...

    def collect(self) -> Sequence[RawSignal]:
        """Return zero or more raw signals without mutating collector state."""
        ...

    def health(self) -> dict[str, object]:
        ...
