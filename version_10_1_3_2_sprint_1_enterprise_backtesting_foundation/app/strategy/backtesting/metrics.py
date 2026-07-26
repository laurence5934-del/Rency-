from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import perf_counter
from typing import Iterator
from contextlib import contextmanager


@dataclass(frozen=True, slots=True)
class BacktestMetricsSnapshot:
    created: int
    validated: int
    completed: int
    failed: int
    total_runtime_seconds: float


class BacktestMetrics:
    def __init__(self) -> None:
        self._created = 0
        self._validated = 0
        self._completed = 0
        self._failed = 0
        self._runtime = 0.0
        self._lock = RLock()

    def increment_created(self) -> None:
        with self._lock:
            self._created += 1

    def increment_validated(self) -> None:
        with self._lock:
            self._validated += 1

    def increment_completed(self) -> None:
        with self._lock:
            self._completed += 1

    def increment_failed(self) -> None:
        with self._lock:
            self._failed += 1

    @contextmanager
    def measure_runtime(self) -> Iterator[None]:
        started = perf_counter()
        try:
            yield
        finally:
            elapsed = perf_counter() - started
            with self._lock:
                self._runtime += elapsed

    def snapshot(self) -> BacktestMetricsSnapshot:
        with self._lock:
            return BacktestMetricsSnapshot(
                created=self._created,
                validated=self._validated,
                completed=self._completed,
                failed=self._failed,
                total_runtime_seconds=self._runtime,
            )
