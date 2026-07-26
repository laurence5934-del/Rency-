from __future__ import annotations

from threading import RLock

from .broker_interface import BrokerInterface


class BrokerRegistry:
    def __init__(self) -> None:
        self._brokers: dict[str, BrokerInterface] = {}
        self._lock = RLock()

    def register(self, broker: BrokerInterface, *, replace: bool = False) -> None:
        key = broker.name.upper()
        with self._lock:
            if key in self._brokers and not replace:
                raise ValueError(f"broker already registered: {broker.name}")
            self._brokers[key] = broker

    def unregister(self, name: str) -> None:
        with self._lock:
            self._brokers.pop(name.upper(), None)

    def get(self, name: str) -> BrokerInterface:
        with self._lock:
            broker = self._brokers.get(name.upper())
            if broker is None:
                raise KeyError(f"broker not registered: {name}")
            return broker

    def names(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._brokers))

    def all(self) -> tuple[BrokerInterface, ...]:
        with self._lock:
            return tuple(self._brokers.values())
