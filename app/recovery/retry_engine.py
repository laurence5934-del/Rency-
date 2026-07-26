from __future__ import annotations

import random
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Event, RLock
from typing import Any, Callable, Mapping, Protocol, TypeVar


T = TypeVar("T")


class BackoffStrategy(str, Enum):
    FIXED = "FIXED"
    LINEAR = "LINEAR"
    EXPONENTIAL = "EXPONENTIAL"
    FIBONACCI = "FIBONACCI"
    FULL_JITTER = "FULL_JITTER"
    EQUAL_JITTER = "EQUAL_JITTER"
    DECORRELATED_JITTER = "DECORRELATED_JITTER"


class RetryOutcome(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    EXHAUSTED = "EXHAUSTED"
    CANCELLED = "CANCELLED"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    NON_RETRYABLE = "NON_RETRYABLE"
    CIRCUIT_REJECTED = "CIRCUIT_REJECTED"


class RetryEvent(str, Enum):
    ATTEMPT_STARTED = "ATTEMPT_STARTED"
    ATTEMPT_SUCCEEDED = "ATTEMPT_SUCCEEDED"
    ATTEMPT_FAILED = "ATTEMPT_FAILED"
    SLEEP_SCHEDULED = "SLEEP_SCHEDULED"
    RETRY_COMPLETED = "RETRY_COMPLETED"
    RETRY_CANCELLED = "RETRY_CANCELLED"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 30.0
    multiplier: float = 2.0
    jitter_ratio: float = 0.20
    max_elapsed_seconds: float | None = 120.0
    retryable_exceptions: tuple[type[BaseException], ...] = (Exception,)
    ignored_exceptions: tuple[type[BaseException], ...] = ()
    retry_if: Callable[[BaseException], bool] | None = None
    retry_on_result: Callable[[Any], bool] | None = None
    respect_retry_after: bool = True
    publish_events: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if self.base_delay_seconds < 0:
            raise ValueError("base_delay_seconds cannot be negative")
        if self.max_delay_seconds < 0:
            raise ValueError("max_delay_seconds cannot be negative")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError(
                "max_delay_seconds cannot be lower than base_delay_seconds"
            )
        if self.multiplier < 1.0:
            raise ValueError("multiplier must be at least 1.0")
        if not 0.0 <= self.jitter_ratio <= 1.0:
            raise ValueError("jitter_ratio must be between 0 and 1")
        if self.max_elapsed_seconds is not None and self.max_elapsed_seconds <= 0:
            raise ValueError("max_elapsed_seconds must be positive when provided")


@dataclass(frozen=True, slots=True)
class RetryAttempt:
    retry_id: str
    operation_name: str
    attempt_number: int
    started_at_utc: str
    completed_at_utc: str
    duration_seconds: float
    succeeded: bool
    retry_scheduled: bool
    next_delay_seconds: float | None
    exception_type: str | None = None
    exception_message: str | None = None
    result_triggered_retry: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RetryReport:
    retry_id: str
    operation_name: str
    outcome: RetryOutcome
    started_at_utc: str
    completed_at_utc: str
    total_duration_seconds: float
    attempts: tuple[RetryAttempt, ...]
    final_exception_type: str | None = None
    final_exception_message: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.outcome == RetryOutcome.SUCCEEDED

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["outcome"] = self.outcome.value
        data["attempts"] = [attempt.to_dict() for attempt in self.attempts]
        data["succeeded"] = self.succeeded
        data["attempt_count"] = self.attempt_count
        return data


@dataclass(frozen=True, slots=True)
class RetryExecutionResult:
    value: Any
    report: RetryReport


class RetryCancelledError(RuntimeError):
    pass


class RetryExhaustedError(RuntimeError):
    def __init__(self, report: RetryReport) -> None:
        self.report = report
        message = (
            f"retry operation '{report.operation_name}' ended with "
            f"{report.outcome.value} after {report.attempt_count} attempt(s)"
        )
        super().__init__(message)


class CancellationToken:
    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def wait(self, timeout_seconds: float) -> bool:
        return self._event.wait(max(0.0, timeout_seconds))

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise RetryCancelledError("retry operation was cancelled")


class RetryBudget:
    """
    Thread-safe retry budget.

    The budget limits retry attempts across many operations during a rolling
    time window. Initial calls are not charged; only additional attempts are.
    """

    def __init__(
        self,
        *,
        max_retries: int,
        window_seconds: float,
        name: str = "default",
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if not name.strip():
            raise ValueError("budget name cannot be empty")

        self.name = name
        self.max_retries = max_retries
        self.window_seconds = window_seconds
        self._lock = RLock()
        self._usage: list[float] = []

    def try_consume(self, amount: int = 1) -> bool:
        if amount < 1:
            raise ValueError("amount must be positive")
        now = time.monotonic()
        with self._lock:
            self._trim_unlocked(now)
            if len(self._usage) + amount > self.max_retries:
                return False
            self._usage.extend([now] * amount)
            return True

    def remaining(self) -> int:
        now = time.monotonic()
        with self._lock:
            self._trim_unlocked(now)
            return max(0, self.max_retries - len(self._usage))

    def snapshot(self) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            self._trim_unlocked(now)
            used = len(self._usage)
        return {
            "name": self.name,
            "max_retries": self.max_retries,
            "used_retries": used,
            "remaining_retries": max(0, self.max_retries - used),
            "window_seconds": self.window_seconds,
        }

    def _trim_unlocked(self, now: float) -> None:
        cutoff = now - self.window_seconds
        self._usage = [timestamp for timestamp in self._usage if timestamp >= cutoff]


class EventPublisher(Protocol):
    def publish_event(
        self,
        event_type: str,
        payload: Any = None,
        *,
        source: str = "unknown",
        **kwargs: Any,
    ) -> Any: ...


class CircuitGuard(Protocol):
    def before_call(self) -> None: ...
    def record_success(self) -> None: ...
    def record_failure(self, exception: BaseException | None = None) -> None: ...


class BackoffCalculator:
    @staticmethod
    def calculate(
        policy: RetryPolicy,
        attempt_number: int,
        previous_delay_seconds: float | None = None,
        *,
        random_source: random.Random | None = None,
    ) -> float:
        if attempt_number < 1:
            raise ValueError("attempt_number must be positive")

        rng = random_source or random
        base = policy.base_delay_seconds
        cap = policy.max_delay_seconds
        strategy = policy.strategy

        if strategy == BackoffStrategy.FIXED:
            delay = base
        elif strategy == BackoffStrategy.LINEAR:
            delay = base * attempt_number
        elif strategy == BackoffStrategy.EXPONENTIAL:
            delay = base * (policy.multiplier ** (attempt_number - 1))
        elif strategy == BackoffStrategy.FIBONACCI:
            delay = base * BackoffCalculator._fibonacci(attempt_number)
        elif strategy == BackoffStrategy.FULL_JITTER:
            exponential = min(
                cap,
                base * (policy.multiplier ** (attempt_number - 1)),
            )
            delay = rng.uniform(0.0, exponential)
        elif strategy == BackoffStrategy.EQUAL_JITTER:
            exponential = min(
                cap,
                base * (policy.multiplier ** (attempt_number - 1)),
            )
            half = exponential / 2.0
            delay = half + rng.uniform(0.0, half)
        elif strategy == BackoffStrategy.DECORRELATED_JITTER:
            previous = previous_delay_seconds or base
            delay = rng.uniform(base, max(base, previous * 3.0))
        else:
            raise ValueError(f"unsupported backoff strategy: {strategy}")

        delay = min(cap, max(0.0, delay))

        if strategy not in {
            BackoffStrategy.FULL_JITTER,
            BackoffStrategy.EQUAL_JITTER,
            BackoffStrategy.DECORRELATED_JITTER,
        } and policy.jitter_ratio > 0:
            spread = delay * policy.jitter_ratio
            delay = rng.uniform(max(0.0, delay - spread), delay + spread)

        return min(cap, max(0.0, delay))

    @staticmethod
    def _fibonacci(number: int) -> int:
        if number <= 2:
            return 1
        previous, current = 1, 1
        for _ in range(3, number + 1):
            previous, current = current, previous + current
        return current


class RetryEngine:
    """
    Version 10.0.8.3 - Retry & Backoff Engine.

    Supports fixed, linear, exponential, Fibonacci, and jittered backoff;
    exception and result-based retry policies; deadlines; cancellation;
    shared retry budgets; circuit-breaker integration; event publication;
    reports; metrics; and decorator usage.
    """

    def __init__(
        self,
        *,
        default_policy: RetryPolicy | None = None,
        event_publisher: EventPublisher | None = None,
        retry_budget: RetryBudget | None = None,
        random_source: random.Random | None = None,
    ) -> None:
        self.default_policy = default_policy or RetryPolicy()
        self.event_publisher = event_publisher
        self.retry_budget = retry_budget
        self.random_source = random_source or random.Random()

        self._lock = RLock()
        self._reports: dict[str, RetryReport] = {}
        self._metrics: dict[str, int | float] = {
            "operations_started": 0,
            "operations_succeeded": 0,
            "operations_exhausted": 0,
            "operations_cancelled": 0,
            "operations_deadline_exceeded": 0,
            "operations_budget_exceeded": 0,
            "operations_non_retryable": 0,
            "operations_circuit_rejected": 0,
            "attempts_total": 0,
            "retries_total": 0,
            "attempt_failures": 0,
            "total_duration_seconds": 0.0,
            "total_sleep_seconds": 0.0,
        }

    def execute(
        self,
        operation: Callable[..., T],
        *args: Any,
        operation_name: str | None = None,
        policy: RetryPolicy | None = None,
        cancellation_token: CancellationToken | None = None,
        deadline_monotonic: float | None = None,
        circuit_guard: CircuitGuard | None = None,
        metadata: Mapping[str, Any] | None = None,
        raise_on_failure: bool = True,
        **kwargs: Any,
    ) -> RetryExecutionResult:
        chosen_policy = policy or self.default_policy
        retry_id = str(uuid.uuid4())
        name = operation_name or getattr(operation, "__name__", "anonymous_operation")
        token = cancellation_token or CancellationToken()
        started_at = self._utc_now()
        started_monotonic = time.monotonic()
        attempts: list[RetryAttempt] = []
        previous_delay: float | None = None
        final_exception: BaseException | None = None
        outcome = RetryOutcome.EXHAUSTED
        value: Any = None

        with self._lock:
            self._metrics["operations_started"] += 1

        for attempt_number in range(1, chosen_policy.max_attempts + 1):
            elapsed = time.monotonic() - started_monotonic

            if token.is_cancelled:
                outcome = RetryOutcome.CANCELLED
                break

            if self._deadline_exceeded(
                deadline_monotonic=deadline_monotonic,
                started_monotonic=started_monotonic,
                elapsed_seconds=elapsed,
                policy=chosen_policy,
            ):
                outcome = RetryOutcome.DEADLINE_EXCEEDED
                break

            if attempt_number > 1:
                if self.retry_budget is not None and not self.retry_budget.try_consume():
                    outcome = RetryOutcome.BUDGET_EXCEEDED
                    break

                delay = BackoffCalculator.calculate(
                    chosen_policy,
                    attempt_number - 1,
                    previous_delay,
                    random_source=self.random_source,
                )
                previous_delay = delay

                remaining = self._remaining_time(
                    deadline_monotonic=deadline_monotonic,
                    started_monotonic=started_monotonic,
                    policy=chosen_policy,
                )
                if remaining is not None and delay > remaining:
                    outcome = RetryOutcome.DEADLINE_EXCEEDED
                    break

                self._publish(
                    chosen_policy,
                    "retry.sleep_scheduled",
                    {
                        "retry_id": retry_id,
                        "operation_name": name,
                        "attempt_number": attempt_number,
                        "delay_seconds": delay,
                    },
                )

                sleep_started = time.monotonic()
                if token.wait(delay):
                    with self._lock:
                        self._metrics["total_sleep_seconds"] += (
                            time.monotonic() - sleep_started
                        )
                    outcome = RetryOutcome.CANCELLED
                    break

                with self._lock:
                    self._metrics["total_sleep_seconds"] += (
                        time.monotonic() - sleep_started
                    )
                    self._metrics["retries_total"] += 1

            attempt_started_at = self._utc_now()
            attempt_started_monotonic = time.monotonic()

            self._publish(
                chosen_policy,
                "retry.attempt_started",
                {
                    "retry_id": retry_id,
                    "operation_name": name,
                    "attempt_number": attempt_number,
                },
            )

            try:
                if circuit_guard is not None:
                    circuit_guard.before_call()

                value = operation(*args, **kwargs)
                result_requires_retry = (
                    chosen_policy.retry_on_result(value)
                    if chosen_policy.retry_on_result is not None
                    else False
                )

                if result_requires_retry:
                    synthetic_error = RuntimeError(
                        "operation result matched retry_on_result policy"
                    )
                    final_exception = synthetic_error
                    if circuit_guard is not None:
                        circuit_guard.record_failure(synthetic_error)

                    retry_scheduled = attempt_number < chosen_policy.max_attempts
                    attempt = RetryAttempt(
                        retry_id=retry_id,
                        operation_name=name,
                        attempt_number=attempt_number,
                        started_at_utc=attempt_started_at,
                        completed_at_utc=self._utc_now(),
                        duration_seconds=time.monotonic() - attempt_started_monotonic,
                        succeeded=False,
                        retry_scheduled=retry_scheduled,
                        next_delay_seconds=None,
                        exception_type=type(synthetic_error).__name__,
                        exception_message=str(synthetic_error),
                        result_triggered_retry=True,
                    )
                    attempts.append(attempt)
                    self._record_attempt_failure()
                    self._publish(
                        chosen_policy,
                        "retry.attempt_failed",
                        attempt.to_dict(),
                    )
                    if not retry_scheduled:
                        outcome = RetryOutcome.EXHAUSTED
                        break
                    continue

                if circuit_guard is not None:
                    circuit_guard.record_success()

                attempt = RetryAttempt(
                    retry_id=retry_id,
                    operation_name=name,
                    attempt_number=attempt_number,
                    started_at_utc=attempt_started_at,
                    completed_at_utc=self._utc_now(),
                    duration_seconds=time.monotonic() - attempt_started_monotonic,
                    succeeded=True,
                    retry_scheduled=False,
                    next_delay_seconds=None,
                )
                attempts.append(attempt)
                self._record_attempt_success()
                self._publish(
                    chosen_policy,
                    "retry.attempt_succeeded",
                    attempt.to_dict(),
                )
                outcome = RetryOutcome.SUCCEEDED
                final_exception = None
                break

            except BaseException as exc:
                final_exception = exc

                if circuit_guard is not None:
                    try:
                        circuit_guard.record_failure(exc)
                    except Exception:
                        pass

                if self._is_circuit_rejection(exc):
                    outcome = RetryOutcome.CIRCUIT_REJECTED
                    attempts.append(
                        self._failed_attempt(
                            retry_id=retry_id,
                            operation_name=name,
                            attempt_number=attempt_number,
                            started_at_utc=attempt_started_at,
                            started_monotonic=attempt_started_monotonic,
                            exception=exc,
                            retry_scheduled=False,
                        )
                    )
                    self._record_attempt_failure()
                    break

                retryable = self._is_retryable(exc, chosen_policy)
                retry_scheduled = (
                    retryable and attempt_number < chosen_policy.max_attempts
                )

                attempt = self._failed_attempt(
                    retry_id=retry_id,
                    operation_name=name,
                    attempt_number=attempt_number,
                    started_at_utc=attempt_started_at,
                    started_monotonic=attempt_started_monotonic,
                    exception=exc,
                    retry_scheduled=retry_scheduled,
                )
                attempts.append(attempt)
                self._record_attempt_failure()
                self._publish(
                    chosen_policy,
                    "retry.attempt_failed",
                    attempt.to_dict(),
                )

                if not retryable:
                    outcome = RetryOutcome.NON_RETRYABLE
                    break
                if not retry_scheduled:
                    outcome = RetryOutcome.EXHAUSTED
                    break

        report = RetryReport(
            retry_id=retry_id,
            operation_name=name,
            outcome=outcome,
            started_at_utc=started_at,
            completed_at_utc=self._utc_now(),
            total_duration_seconds=time.monotonic() - started_monotonic,
            attempts=tuple(attempts),
            final_exception_type=(
                type(final_exception).__name__ if final_exception is not None else None
            ),
            final_exception_message=(
                str(final_exception) if final_exception is not None else None
            ),
            metadata=dict(metadata or {}),
        )

        self._store_report(report)
        self._publish(
            chosen_policy,
            "retry.completed",
            report.to_dict(),
        )

        if not report.succeeded and raise_on_failure:
            if outcome == RetryOutcome.CANCELLED:
                raise RetryCancelledError(
                    f"retry operation '{name}' was cancelled"
                )
            raise RetryExhaustedError(report) from final_exception

        return RetryExecutionResult(value=value, report=report)

    def decorate(
        self,
        *,
        policy: RetryPolicy | None = None,
        operation_name: str | None = None,
        circuit_guard: CircuitGuard | None = None,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        def decorator(function: Callable[..., T]) -> Callable[..., T]:
            def wrapped(*args: Any, **kwargs: Any) -> T:
                result = self.execute(
                    function,
                    *args,
                    operation_name=operation_name or function.__name__,
                    policy=policy,
                    circuit_guard=circuit_guard,
                    **kwargs,
                )
                return result.value

            wrapped.__name__ = getattr(function, "__name__", "retry_wrapped")
            wrapped.__doc__ = getattr(function, "__doc__", None)
            wrapped.__module__ = getattr(function, "__module__", __name__)
            return wrapped

        return decorator

    def get_report(self, retry_id: str) -> RetryReport:
        with self._lock:
            report = self._reports.get(retry_id)
            if report is None:
                raise KeyError(f"unknown retry report: {retry_id}")
            return report

    def list_reports(
        self,
        *,
        outcome: RetryOutcome | None = None,
    ) -> tuple[RetryReport, ...]:
        with self._lock:
            reports = tuple(self._reports.values())
        if outcome is not None:
            reports = tuple(report for report in reports if report.outcome == outcome)
        return tuple(sorted(reports, key=lambda report: report.started_at_utc))

    def metrics(self) -> dict[str, int | float]:
        with self._lock:
            metrics = dict(self._metrics)

        started = float(metrics["operations_started"])
        attempts = float(metrics["attempts_total"])
        metrics["success_rate"] = (
            float(metrics["operations_succeeded"]) / started if started else 0.0
        )
        metrics["mean_attempts_per_operation"] = (
            attempts / started if started else 0.0
        )
        metrics["mean_operation_duration_seconds"] = (
            float(metrics["total_duration_seconds"]) / started
            if started
            else 0.0
        )
        return metrics

    def health_check(self) -> dict[str, Any]:
        metrics = self.metrics()
        started = int(metrics["operations_started"])
        failed = (
            int(metrics["operations_exhausted"])
            + int(metrics["operations_non_retryable"])
            + int(metrics["operations_circuit_rejected"])
        )
        failure_rate = failed / started if started else 0.0

        return {
            "healthy": failure_rate < 0.25,
            "degraded": 0.10 <= failure_rate < 0.25,
            "failure_rate": failure_rate,
            "budget": (
                self.retry_budget.snapshot()
                if self.retry_budget is not None
                else None
            ),
            "metrics": metrics,
        }

    def _is_retryable(
        self,
        exception: BaseException,
        policy: RetryPolicy,
    ) -> bool:
        if isinstance(exception, policy.ignored_exceptions):
            return False
        if not isinstance(exception, policy.retryable_exceptions):
            return False
        if policy.retry_if is not None:
            return bool(policy.retry_if(exception))
        return True

    @staticmethod
    def _is_circuit_rejection(exception: BaseException) -> bool:
        return type(exception).__name__ in {
            "CircuitOpenError",
            "HalfOpenLimitError",
        }

    @staticmethod
    def _deadline_exceeded(
        *,
        deadline_monotonic: float | None,
        started_monotonic: float,
        elapsed_seconds: float,
        policy: RetryPolicy,
    ) -> bool:
        if deadline_monotonic is not None and time.monotonic() >= deadline_monotonic:
            return True
        if (
            policy.max_elapsed_seconds is not None
            and elapsed_seconds >= policy.max_elapsed_seconds
        ):
            return True
        return False

    @staticmethod
    def _remaining_time(
        *,
        deadline_monotonic: float | None,
        started_monotonic: float,
        policy: RetryPolicy,
    ) -> float | None:
        limits: list[float] = []

        if deadline_monotonic is not None:
            limits.append(deadline_monotonic - time.monotonic())

        if policy.max_elapsed_seconds is not None:
            elapsed = time.monotonic() - started_monotonic
            limits.append(policy.max_elapsed_seconds - elapsed)

        if not limits:
            return None
        return max(0.0, min(limits))

    def _failed_attempt(
        self,
        *,
        retry_id: str,
        operation_name: str,
        attempt_number: int,
        started_at_utc: str,
        started_monotonic: float,
        exception: BaseException,
        retry_scheduled: bool,
    ) -> RetryAttempt:
        return RetryAttempt(
            retry_id=retry_id,
            operation_name=operation_name,
            attempt_number=attempt_number,
            started_at_utc=started_at_utc,
            completed_at_utc=self._utc_now(),
            duration_seconds=time.monotonic() - started_monotonic,
            succeeded=False,
            retry_scheduled=retry_scheduled,
            next_delay_seconds=None,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
        )

    def _record_attempt_success(self) -> None:
        with self._lock:
            self._metrics["attempts_total"] += 1

    def _record_attempt_failure(self) -> None:
        with self._lock:
            self._metrics["attempts_total"] += 1
            self._metrics["attempt_failures"] += 1

    def _store_report(self, report: RetryReport) -> None:
        with self._lock:
            self._reports[report.retry_id] = report
            self._metrics["total_duration_seconds"] += (
                report.total_duration_seconds
            )

            outcome_metric = {
                RetryOutcome.SUCCEEDED: "operations_succeeded",
                RetryOutcome.EXHAUSTED: "operations_exhausted",
                RetryOutcome.CANCELLED: "operations_cancelled",
                RetryOutcome.DEADLINE_EXCEEDED:
                    "operations_deadline_exceeded",
                RetryOutcome.BUDGET_EXCEEDED: "operations_budget_exceeded",
                RetryOutcome.NON_RETRYABLE: "operations_non_retryable",
                RetryOutcome.CIRCUIT_REJECTED:
                    "operations_circuit_rejected",
            }[report.outcome]
            self._metrics[outcome_metric] += 1

    def _publish(
        self,
        policy: RetryPolicy,
        event_type: str,
        payload: Any,
    ) -> None:
        if (
            policy.publish_events
            and self.event_publisher is not None
        ):
            self.event_publisher.publish_event(
                event_type,
                payload,
                source="retry_engine",
            )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
