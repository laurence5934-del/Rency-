from __future__ import annotations

import time
from collections import defaultdict
from threading import RLock
from typing import Any


class RecoveryMetricsEngine:
    def __init__(self) -> None:
        self._lock = RLock()
        self._started = time.monotonic()
        self._counters: dict[str, int] = defaultdict(int)
        self._durations: dict[str, list[float]] = defaultdict(list)
        self._last_failure_monotonic: float | None = None
        self._failure_intervals: list[float] = []

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount

    def observe(self, name: str, duration_seconds: float) -> None:
        with self._lock:
            self._durations[name].append(max(0.0, duration_seconds))

    def record_failure(self) -> None:
        now = time.monotonic()
        with self._lock:
            self._counters["failures"] += 1
            if self._last_failure_monotonic is not None:
                self._failure_intervals.append(now - self._last_failure_monotonic)
            self._last_failure_monotonic = now

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = dict(self._counters)
            duration_stats = {
                name: {
                    "count": len(values),
                    "average_seconds": sum(values) / len(values) if values else 0.0,
                    "maximum_seconds": max(values) if values else 0.0,
                }
                for name, values in self._durations.items()
            }
            mtbf = (
                sum(self._failure_intervals) / len(self._failure_intervals)
                if self._failure_intervals else None
            )

        recoveries = counters.get("recoveries_attempted", 0)
        successful = counters.get("recoveries_succeeded", 0)
        uptime = time.monotonic() - self._started

        return {
            "uptime_seconds": uptime,
            "counters": counters,
            "durations": duration_stats,
            "mtbf_seconds": mtbf,
            "recovery_success_rate": successful / recoveries if recoveries else 0.0,
        }
