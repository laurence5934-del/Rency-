from __future__ import annotations

import time
from collections import deque
from threading import RLock


class SlidingWindowRateLimiter:
    def __init__(self, maximum_calls: int = 100, window_seconds: float = 60.0) -> None:
        if maximum_calls <= 0 or window_seconds <= 0:
            raise ValueError("rate limiter values must be positive")
        self.maximum_calls = maximum_calls
        self.window_seconds = window_seconds
        self._calls: deque[float] = deque()
        self._lock = RLock()

    def acquire(self) -> bool:
        now = time.monotonic()
        with self._lock:
            while self._calls and now - self._calls[0] >= self.window_seconds:
                self._calls.popleft()
            if len(self._calls) >= self.maximum_calls:
                return False
            self._calls.append(now)
            return True
