from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Any, Callable, Mapping, Protocol, TypeVar


T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitEvent(str, Enum):
    CALL_SUCCEEDED = "CALL_SUCCEEDED"
    CALL_FAILED = "CALL_FAILED"
    STATE_CHANGED = "STATE_CHANGED"
    CALL_REJECTED = "CALL_REJECTED"
    MANUAL_RESET = "MANUAL_RESET"
    MANUAL_OPEN = "MANUAL_OPEN"


class CircuitFailureMode(str, Enum):
    CONSECUTIVE = "CONSECUTIVE"
    ROLLING_WINDOW = "ROLLING_WINDOW"


@dataclass(frozen=True, slots=True)
class CircuitBreakerConfig:
    failure_threshold: int = 5
    success_threshold: int = 2
    recovery_timeout_seconds: float = 30.0
    failure_mode: CircuitFailureMode = CircuitFailureMode.CONSECUTIVE
    rolling_window_seconds: float = 60.0
    minimum_calls: int = 5
    failure_rate_threshold: float = 0.50
    half_open_max_calls: int = 1
    excluded_exceptions: tuple[type[BaseException], ...] = ()
    publish_events: bool = True

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be positive")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be positive")
        if self.recovery_timeout_seconds <= 0:
            raise ValueError("recovery_timeout_seconds must be positive")
        if self.rolling_window_seconds <= 0:
            raise ValueError("rolling_window_seconds must be positive")
        if self.minimum_calls < 1:
            raise ValueError("minimum_calls must be positive")
        if not 0.0 < self.failure_rate_threshold <= 1.0:
            raise ValueError("failure_rate_threshold must be between 0 and 1")
        if self.half_open_max_calls < 1:
            raise ValueError("half_open_max_calls must be positive")


@dataclass(frozen=True, slots=True)
class CircuitSnapshot:
    circuit_id: str
    name: str
    state: CircuitState
    failure_count: int
    success_count: int
    consecutive_failures: int
    consecutive_successes: int
    rejected_calls: int
    total_calls: int
    total_failures: int
    total_successes: int
    half_open_calls_in_flight: int
    last_failure_at_utc: str | None
    last_success_at_utc: str | None
    opened_at_utc: str | None
    updated_at_utc: str
    failure_rate: float

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data


@dataclass(frozen=True, slots=True)
class CircuitTransition:
    circuit_id: str
    name: str
    previous_state: CircuitState
    new_state: CircuitState
    reason: str
    occurred_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["previous_state"] = self.previous_state.value
        data["new_state"] = self.new_state.value
        return data


@dataclass(frozen=True, slots=True)
class CallRecord:
    succeeded: bool
    monotonic_time: float


class CircuitOpenError(RuntimeError):
    def __init__(self, circuit_name: str, retry_after_seconds: float) -> None:
        self.circuit_name = circuit_name
        self.retry_after_seconds = max(0.0, retry_after_seconds)
        super().__init__(
            f"circuit '{circuit_name}' is open; retry after "
            f"{self.retry_after_seconds:.3f} seconds"
        )


class HalfOpenLimitError(RuntimeError):
    def __init__(self, circuit_name: str) -> None:
        self.circuit_name = circuit_name
        super().__init__(
            f"circuit '{circuit_name}' half-open trial limit reached"
        )


class EventPublisher(Protocol):
    def publish_event(
        self,
        event_type: str,
        payload: Any = None,
        *,
        source: str = "unknown",
        **kwargs: Any,
    ) -> Any: ...


class CircuitBreaker:
    """
    Version 10.0.8.2 - Circuit Breaker Framework.

    Thread-safe CLOSED / OPEN / HALF_OPEN state machine with consecutive
    failure or rolling-window failure-rate policies, automatic recovery
    probes, metrics, event publishing, decorators, and manual controls.
    """

    def __init__(
        self,
        name: str,
        *,
        config: CircuitBreakerConfig | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        if not name.strip():
            raise ValueError("circuit name cannot be empty")

        self.circuit_id = str(uuid.uuid4())
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.event_publisher = event_publisher

        self._lock = RLock()
        self._state = CircuitState.CLOSED
        self._opened_monotonic: float | None = None
        self._opened_at_utc: str | None = None
        self._last_failure_at_utc: str | None = None
        self._last_success_at_utc: str | None = None
        self._updated_at_utc = self._utc_now()

        self._failure_count = 0
        self._success_count = 0
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._rejected_calls = 0
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._half_open_calls_in_flight = 0
        self._call_history: list[CallRecord] = []
        self._transitions: list[CircuitTransition] = []

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._refresh_state_unlocked()
            return self._state

    def allow_call(self) -> bool:
        with self._lock:
            self._refresh_state_unlocked()

            if self._state == CircuitState.OPEN:
                self._rejected_calls += 1
                self._updated_at_utc = self._utc_now()
                self._publish(
                    "circuit_breaker.call_rejected",
                    {
                        "circuit_id": self.circuit_id,
                        "name": self.name,
                        "state": self._state.value,
                        "retry_after_seconds": self.retry_after_seconds(),
                    },
                )
                return False

            if self._state == CircuitState.HALF_OPEN:
                if (
                    self._half_open_calls_in_flight
                    >= self.config.half_open_max_calls
                ):
                    self._rejected_calls += 1
                    self._updated_at_utc = self._utc_now()
                    return False
                self._half_open_calls_in_flight += 1

            self._total_calls += 1
            self._updated_at_utc = self._utc_now()
            return True

    def before_call(self) -> None:
        with self._lock:
            self._refresh_state_unlocked()

            if self._state == CircuitState.OPEN:
                self._rejected_calls += 1
                retry_after = self._retry_after_unlocked()
                self._updated_at_utc = self._utc_now()
                self._publish(
                    "circuit_breaker.call_rejected",
                    {
                        "circuit_id": self.circuit_id,
                        "name": self.name,
                        "state": self._state.value,
                        "retry_after_seconds": retry_after,
                    },
                )
                raise CircuitOpenError(self.name, retry_after)

            if self._state == CircuitState.HALF_OPEN:
                if (
                    self._half_open_calls_in_flight
                    >= self.config.half_open_max_calls
                ):
                    self._rejected_calls += 1
                    self._updated_at_utc = self._utc_now()
                    raise HalfOpenLimitError(self.name)
                self._half_open_calls_in_flight += 1

            self._total_calls += 1
            self._updated_at_utc = self._utc_now()

    def record_success(self) -> None:
        with self._lock:
            now = time.monotonic()
            self._last_success_at_utc = self._utc_now()
            self._success_count += 1
            self._total_successes += 1
            self._consecutive_successes += 1
            self._consecutive_failures = 0
            self._call_history.append(CallRecord(True, now))
            self._trim_history_unlocked(now)

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls_in_flight = max(
                    0, self._half_open_calls_in_flight - 1
                )
                if self._consecutive_successes >= self.config.success_threshold:
                    self._transition_unlocked(
                        CircuitState.CLOSED,
                        "half-open success threshold reached",
                    )
                    self._reset_window_counters_unlocked()

            self._updated_at_utc = self._utc_now()

        self._publish(
            "circuit_breaker.call_succeeded",
            self.snapshot().to_dict(),
        )

    def record_failure(self, exception: BaseException | None = None) -> None:
        if exception is not None and isinstance(
            exception, self.config.excluded_exceptions
        ):
            self.record_success()
            return

        with self._lock:
            now = time.monotonic()
            self._last_failure_at_utc = self._utc_now()
            self._failure_count += 1
            self._total_failures += 1
            self._consecutive_failures += 1
            self._consecutive_successes = 0
            self._call_history.append(CallRecord(False, now))
            self._trim_history_unlocked(now)

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls_in_flight = max(
                    0, self._half_open_calls_in_flight - 1
                )
                self._transition_unlocked(
                    CircuitState.OPEN,
                    "half-open trial failed",
                )
            elif self._state == CircuitState.CLOSED:
                if self._should_open_unlocked():
                    self._transition_unlocked(
                        CircuitState.OPEN,
                        self._open_reason_unlocked(),
                    )

            self._updated_at_utc = self._utc_now()

        payload = self.snapshot().to_dict()
        if exception is not None:
            payload["exception_type"] = type(exception).__name__
            payload["exception_message"] = str(exception)
        self._publish("circuit_breaker.call_failed", payload)

    def call(
        self,
        function: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        self.before_call()
        try:
            result = function(*args, **kwargs)
        except BaseException as exc:
            self.record_failure(exc)
            raise
        else:
            self.record_success()
            return result

    def decorate(self, function: Callable[..., T]) -> Callable[..., T]:
        def wrapped(*args: Any, **kwargs: Any) -> T:
            return self.call(function, *args, **kwargs)

        wrapped.__name__ = getattr(function, "__name__", "circuit_wrapped")
        wrapped.__doc__ = getattr(function, "__doc__", None)
        wrapped.__module__ = getattr(function, "__module__", __name__)
        return wrapped

    def force_open(self, *, reason: str = "manually opened") -> None:
        with self._lock:
            self._transition_unlocked(CircuitState.OPEN, reason)
        self._publish("circuit_breaker.manual_open", self.snapshot().to_dict())

    def reset(self, *, reason: str = "manually reset") -> None:
        with self._lock:
            previous = self._state
            self._state = CircuitState.CLOSED
            self._opened_monotonic = None
            self._opened_at_utc = None
            self._half_open_calls_in_flight = 0
            self._reset_window_counters_unlocked()
            self._updated_at_utc = self._utc_now()

            if previous != CircuitState.CLOSED:
                self._record_transition_unlocked(
                    previous,
                    CircuitState.CLOSED,
                    reason,
                )

        self._publish("circuit_breaker.manual_reset", self.snapshot().to_dict())

    def snapshot(self) -> CircuitSnapshot:
        with self._lock:
            self._refresh_state_unlocked()
            failure_rate = self._failure_rate_unlocked()
            return CircuitSnapshot(
                circuit_id=self.circuit_id,
                name=self.name,
                state=self._state,
                failure_count=self._failure_count,
                success_count=self._success_count,
                consecutive_failures=self._consecutive_failures,
                consecutive_successes=self._consecutive_successes,
                rejected_calls=self._rejected_calls,
                total_calls=self._total_calls,
                total_failures=self._total_failures,
                total_successes=self._total_successes,
                half_open_calls_in_flight=self._half_open_calls_in_flight,
                last_failure_at_utc=self._last_failure_at_utc,
                last_success_at_utc=self._last_success_at_utc,
                opened_at_utc=self._opened_at_utc,
                updated_at_utc=self._updated_at_utc,
                failure_rate=failure_rate,
            )

    def transitions(self) -> tuple[CircuitTransition, ...]:
        with self._lock:
            return tuple(self._transitions)

    def retry_after_seconds(self) -> float:
        with self._lock:
            return self._retry_after_unlocked()

    def metrics(self) -> dict[str, int | float | str]:
        snapshot = self.snapshot()
        return {
            "state": snapshot.state.value,
            "total_calls": snapshot.total_calls,
            "total_successes": snapshot.total_successes,
            "total_failures": snapshot.total_failures,
            "rejected_calls": snapshot.rejected_calls,
            "consecutive_failures": snapshot.consecutive_failures,
            "consecutive_successes": snapshot.consecutive_successes,
            "failure_rate": snapshot.failure_rate,
            "transition_count": len(self.transitions()),
        }

    def health_check(self) -> dict[str, Any]:
        snapshot = self.snapshot()
        if snapshot.state == CircuitState.CLOSED:
            healthy = True
            degraded = False
            score = 100.0
        elif snapshot.state == CircuitState.HALF_OPEN:
            healthy = True
            degraded = True
            score = 60.0
        else:
            healthy = False
            degraded = False
            score = 0.0

        return {
            "healthy": healthy,
            "degraded": degraded,
            "score": score,
            "message": f"circuit {self.name} is {snapshot.state.value}",
            "details": snapshot.to_dict(),
        }

    def _refresh_state_unlocked(self) -> None:
        if self._state != CircuitState.OPEN:
            return
        if self._opened_monotonic is None:
            return
        elapsed = time.monotonic() - self._opened_monotonic
        if elapsed >= self.config.recovery_timeout_seconds:
            self._transition_unlocked(
                CircuitState.HALF_OPEN,
                "recovery timeout elapsed",
            )
            self._half_open_calls_in_flight = 0
            self._consecutive_successes = 0
            self._consecutive_failures = 0

    def _should_open_unlocked(self) -> bool:
        if self.config.failure_mode == CircuitFailureMode.CONSECUTIVE:
            return (
                self._consecutive_failures
                >= self.config.failure_threshold
            )

        total = len(self._call_history)
        if total < self.config.minimum_calls:
            return False
        return self._failure_rate_unlocked() >= self.config.failure_rate_threshold

    def _open_reason_unlocked(self) -> str:
        if self.config.failure_mode == CircuitFailureMode.CONSECUTIVE:
            return (
                f"consecutive failure threshold reached: "
                f"{self._consecutive_failures}"
            )
        return (
            f"rolling failure rate threshold reached: "
            f"{self._failure_rate_unlocked():.4f}"
        )

    def _failure_rate_unlocked(self) -> float:
        now = time.monotonic()
        self._trim_history_unlocked(now)
        total = len(self._call_history)
        if total == 0:
            return 0.0
        failures = sum(1 for record in self._call_history if not record.succeeded)
        return failures / total

    def _trim_history_unlocked(self, now: float) -> None:
        cutoff = now - self.config.rolling_window_seconds
        if not self._call_history:
            return
        first_valid = 0
        for index, record in enumerate(self._call_history):
            if record.monotonic_time >= cutoff:
                first_valid = index
                break
        else:
            self._call_history.clear()
            return

        if first_valid > 0:
            del self._call_history[:first_valid]

    def _retry_after_unlocked(self) -> float:
        if (
            self._state != CircuitState.OPEN
            or self._opened_monotonic is None
        ):
            return 0.0
        elapsed = time.monotonic() - self._opened_monotonic
        return max(0.0, self.config.recovery_timeout_seconds - elapsed)

    def _transition_unlocked(
        self,
        new_state: CircuitState,
        reason: str,
    ) -> None:
        previous = self._state
        if previous == new_state:
            return

        self._state = new_state
        self._updated_at_utc = self._utc_now()

        if new_state == CircuitState.OPEN:
            self._opened_monotonic = time.monotonic()
            self._opened_at_utc = self._utc_now()
            self._half_open_calls_in_flight = 0
        elif new_state == CircuitState.CLOSED:
            self._opened_monotonic = None
            self._opened_at_utc = None
            self._half_open_calls_in_flight = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls_in_flight = 0

        self._record_transition_unlocked(previous, new_state, reason)

    def _record_transition_unlocked(
        self,
        previous: CircuitState,
        new_state: CircuitState,
        reason: str,
    ) -> None:
        transition = CircuitTransition(
            circuit_id=self.circuit_id,
            name=self.name,
            previous_state=previous,
            new_state=new_state,
            reason=reason,
            occurred_at_utc=self._utc_now(),
        )
        self._transitions.append(transition)
        self._publish(
            "circuit_breaker.state_changed",
            transition.to_dict(),
        )

    def _reset_window_counters_unlocked(self) -> None:
        self._failure_count = 0
        self._success_count = 0
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._call_history.clear()

    def _publish(self, event_type: str, payload: Any) -> None:
        if self.config.publish_events and self.event_publisher is not None:
            self.event_publisher.publish_event(
                event_type,
                payload,
                source="circuit_breaker",
            )


class CircuitBreakerRegistry:
    """
    Thread-safe registry for managing multiple named circuit breakers.
    """

    def __init__(
        self,
        *,
        default_config: CircuitBreakerConfig | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self.default_config = default_config or CircuitBreakerConfig()
        self.event_publisher = event_publisher
        self._lock = RLock()
        self._circuits: dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        *,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        with self._lock:
            existing = self._circuits.get(name)
            if existing is not None:
                return existing
            circuit = CircuitBreaker(
                name,
                config=config or self.default_config,
                event_publisher=self.event_publisher,
            )
            self._circuits[name] = circuit
            return circuit

    def get(self, name: str) -> CircuitBreaker:
        with self._lock:
            circuit = self._circuits.get(name)
            if circuit is None:
                raise KeyError(f"unknown circuit: {name}")
            return circuit

    def remove(self, name: str) -> bool:
        with self._lock:
            return self._circuits.pop(name, None) is not None

    def list(self) -> tuple[CircuitSnapshot, ...]:
        with self._lock:
            circuits = tuple(self._circuits.values())
        return tuple(
            sorted(
                (circuit.snapshot() for circuit in circuits),
                key=lambda item: item.name,
            )
        )

    def reset_all(self) -> None:
        with self._lock:
            circuits = tuple(self._circuits.values())
        for circuit in circuits:
            circuit.reset(reason="registry-wide reset")

    def metrics(self) -> dict[str, Any]:
        with self._lock:
            circuits = tuple(self._circuits.values())
        return {
            "registered_circuits": len(circuits),
            "states": {
                state.value: sum(
                    1 for circuit in circuits if circuit.state == state
                )
                for state in CircuitState
            },
            "circuits": {
                circuit.name: circuit.metrics()
                for circuit in circuits
            },
        }

    def health_check(self) -> dict[str, Any]:
        snapshots = self.list()
        open_count = sum(
            1 for snapshot in snapshots if snapshot.state == CircuitState.OPEN
        )
        half_open_count = sum(
            1
            for snapshot in snapshots
            if snapshot.state == CircuitState.HALF_OPEN
        )

        return {
            "healthy": open_count == 0,
            "degraded": open_count == 0 and half_open_count > 0,
            "registered_circuits": len(snapshots),
            "open_circuits": open_count,
            "half_open_circuits": half_open_count,
            "circuits": [snapshot.to_dict() for snapshot in snapshots],
        }
