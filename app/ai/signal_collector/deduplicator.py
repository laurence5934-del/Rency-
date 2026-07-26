from __future__ import annotations

from collections import OrderedDict
from threading import RLock


class SignalDeduplicator:
    def __init__(self, *, capacity: int = 100_000) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be greater than zero")
        self._capacity = capacity
        self._fingerprints: OrderedDict[str, None] = OrderedDict()
        self._lock = RLock()

    def seen(self, fingerprint: str) -> bool:
        with self._lock:
            if fingerprint in self._fingerprints:
                self._fingerprints.move_to_end(fingerprint)
                return True
            return False

    def remember(self, fingerprint: str) -> None:
        with self._lock:
            self._fingerprints[fingerprint] = None
            self._fingerprints.move_to_end(fingerprint)
            while len(self._fingerprints) > self._capacity:
                self._fingerprints.popitem(last=False)

    def check_and_remember(self, fingerprint: str) -> bool:
        with self._lock:
            duplicate = fingerprint in self._fingerprints
            self._fingerprints[fingerprint] = None
            self._fingerprints.move_to_end(fingerprint)
            while len(self._fingerprints) > self._capacity:
                self._fingerprints.popitem(last=False)
            return duplicate

    def size(self) -> int:
        with self._lock:
            return len(self._fingerprints)
