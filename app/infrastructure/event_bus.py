from __future__ import annotations

import asyncio
import fnmatch
import inspect
import time
import uuid
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum, IntEnum
from heapq import heappop, heappush
from threading import Condition, RLock, Thread
from typing import Any, Awaitable, Callable, Deque, Mapping


class EventPriority(IntEnum):
    LOW = 10
    NORMAL = 20
    HIGH = 30
    CRITICAL = 40


class DeliveryMode(str, Enum):
    SYNCHRONOUS = "SYNCHRONOUS"
    ASYNCHRONOUS = "ASYNCHRONOUS"


class DeliveryStatus(str, Enum):
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    DEAD_LETTERED = "DEAD_LETTERED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class Event:
    event_type: str
    payload: Any = None
    source: str = "unknown"
    priority: EventPriority = EventPriority.NORMAL
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    causation_id: str | None = None
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    headers: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        event_type = self.event_type.strip()
        source = self.source.strip()
        if not event_type:
            raise ValueError("event_type cannot be empty")
        if not source:
            raise ValueError("source cannot be empty")
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "source", source)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["priority"] = self.priority.name
        return result


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_delay_seconds: float = 0.05
    backoff_multiplier: float = 2.0
    maximum_delay_seconds: float = 2.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_delay_seconds < 0:
            raise ValueError("initial_delay_seconds cannot be negative")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be at least 1")
        if self.maximum_delay_seconds < 0:
            raise ValueError("maximum_delay_seconds cannot be negative")

    def delay_for_attempt(self, attempt: int) -> float:
        if attempt <= 1:
            return 0.0
        delay = self.initial_delay_seconds * (
            self.backoff_multiplier ** (attempt - 2)
        )
        return min(delay, self.maximum_delay_seconds)


EventHandler = Callable[[Event], Any | Awaitable[Any]]
EventFilter = Callable[[Event], bool]


@dataclass(slots=True)
class EventSubscription:
    pattern: str
    handler: EventHandler
    subscriber_name: str
    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    delivery_mode: DeliveryMode = DeliveryMode.SYNCHRONOUS
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    event_filter: EventFilter | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        self.pattern = self.pattern.strip()
        self.subscriber_name = self.subscriber_name.strip()
        if not self.pattern:
            raise ValueError("pattern cannot be empty")
        if not self.subscriber_name:
            raise ValueError("subscriber_name cannot be empty")
        if not callable(self.handler):
            raise TypeError("handler must be callable")

    def matches(self, event: Event) -> bool:
        if not self.enabled:
            return False
        if not fnmatch.fnmatchcase(event.event_type, self.pattern):
            return False
        return self.event_filter(event) if self.event_filter else True


@dataclass(frozen=True, slots=True)
class DeliveryRecord:
    event_id: str
    subscription_id: str
    subscriber_name: str
    event_type: str
    attempt: int
    status: DeliveryStatus
    started_at_utc: str
    finished_at_utc: str
    duration_ms: float
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        return result


@dataclass(frozen=True, slots=True)
class DeadLetter:
    event: Event
    subscription_id: str
    subscriber_name: str
    attempts: int
    error: str
    failed_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event.to_dict(),
            "subscription_id": self.subscription_id,
            "subscriber_name": self.subscriber_name,
            "attempts": self.attempts,
            "error": self.error,
            "failed_at_utc": self.failed_at_utc,
        }


@dataclass(slots=True)
class EventBusConfig:
    history_capacity: int = 10_000
    delivery_history_capacity: int = 50_000
    dead_letter_capacity: int = 10_000
    worker_count: int = 2
    stop_timeout_seconds: float = 5.0
    record_unmatched_events: bool = True

    def __post_init__(self) -> None:
        if self.history_capacity < 1:
            raise ValueError("history_capacity must be positive")
        if self.delivery_history_capacity < 1:
            raise ValueError("delivery_history_capacity must be positive")
        if self.dead_letter_capacity < 1:
            raise ValueError("dead_letter_capacity must be positive")
        if self.worker_count < 1:
            raise ValueError("worker_count must be positive")
        if self.stop_timeout_seconds <= 0:
            raise ValueError("stop_timeout_seconds must be positive")


@dataclass(frozen=True, slots=True)
class EventBusMetrics:
    published: int
    dispatched: int
    delivered: int
    failed_attempts: int
    dead_lettered: int
    unmatched: int
    active_subscriptions: int
    queued_events: int
    published_by_type: Mapping[str, int]
    delivered_by_subscriber: Mapping[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EventBus:
    """
    Version 10.0.2 - Event Bus & Message Broker.

    Features:
    - Thread-safe publish/subscribe messaging
    - Exact and wildcard event subscriptions
    - Priority-based queued delivery
    - Synchronous and asynchronous handlers
    - Retry with exponential backoff
    - Dead-letter queue
    - Event and delivery history
    - Event replay
    - Subscription filters
    - Delivery metrics
    - Graceful worker startup and shutdown
    """

    def __init__(self, config: EventBusConfig | None = None) -> None:
        self.config = config or EventBusConfig()
        self._lock = RLock()
        self._condition = Condition(self._lock)
        self._subscriptions: dict[str, EventSubscription] = {}
        self._event_history: Deque[Event] = deque(
            maxlen=self.config.history_capacity
        )
        self._delivery_history: Deque[DeliveryRecord] = deque(
            maxlen=self.config.delivery_history_capacity
        )
        self._dead_letters: Deque[DeadLetter] = deque(
            maxlen=self.config.dead_letter_capacity
        )
        self._queue: list[tuple[int, int, Event]] = []
        self._sequence = 0
        self._running = False
        self._accepting_events = False
        self._workers: list[Thread] = []

        self._published = 0
        self._dispatched = 0
        self._delivered = 0
        self._failed_attempts = 0
        self._dead_lettered = 0
        self._unmatched = 0
        self._published_by_type: Counter[str] = Counter()
        self._delivered_by_subscriber: Counter[str] = Counter()

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def start(self) -> None:
        with self._condition:
            if self._running:
                return
            self._running = True
            self._accepting_events = True
            self._workers = [
                Thread(
                    target=self._worker_loop,
                    name=f"event-bus-worker-{index + 1}",
                    daemon=True,
                )
                for index in range(self.config.worker_count)
            ]
            for worker in self._workers:
                worker.start()

    def stop(self, drain: bool = True) -> None:
        with self._condition:
            self._accepting_events = False
            if not drain:
                self._queue.clear()
            self._running = False
            self._condition.notify_all()

        deadline = time.monotonic() + self.config.stop_timeout_seconds
        for worker in self._workers:
            remaining = max(0.0, deadline - time.monotonic())
            worker.join(timeout=remaining)
        self._workers.clear()

    def subscribe(
        self,
        pattern: str,
        handler: EventHandler,
        *,
        subscriber_name: str | None = None,
        delivery_mode: DeliveryMode = DeliveryMode.SYNCHRONOUS,
        retry_policy: RetryPolicy | None = None,
        event_filter: EventFilter | None = None,
    ) -> EventSubscription:
        subscription = EventSubscription(
            pattern=pattern,
            handler=handler,
            subscriber_name=subscriber_name
            or getattr(handler, "__name__", handler.__class__.__name__),
            delivery_mode=delivery_mode,
            retry_policy=retry_policy or RetryPolicy(),
            event_filter=event_filter,
        )
        with self._lock:
            self._subscriptions[subscription.subscription_id] = subscription
        return subscription

    def unsubscribe(self, subscription_id: str) -> bool:
        with self._lock:
            return self._subscriptions.pop(subscription_id, None) is not None

    def set_subscription_enabled(
        self,
        subscription_id: str,
        enabled: bool,
    ) -> None:
        with self._lock:
            subscription = self._subscriptions.get(subscription_id)
            if subscription is None:
                raise KeyError(f"unknown subscription: {subscription_id}")
            subscription.enabled = enabled

    def publish(
        self,
        event: Event,
        *,
        queued: bool = True,
    ) -> str:
        with self._condition:
            if queued and not self._accepting_events:
                raise RuntimeError("event bus is not accepting queued events")

            self._record_publication(event)

            if queued:
                self._sequence += 1
                heappush(
                    self._queue,
                    (-int(event.priority), self._sequence, event),
                )
                self._condition.notify()
            else:
                self._dispatch(event)

        return event.event_id

    def publish_event(
        self,
        event_type: str,
        payload: Any = None,
        *,
        source: str = "unknown",
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        headers: Mapping[str, Any] | None = None,
        queued: bool = True,
    ) -> Event:
        event = Event(
            event_type=event_type,
            payload=payload,
            source=source,
            priority=priority,
            correlation_id=correlation_id or str(uuid.uuid4()),
            causation_id=causation_id,
            headers=headers or {},
        )
        self.publish(event, queued=queued)
        return event

    def replay(
        self,
        *,
        event_type_pattern: str = "*",
        correlation_id: str | None = None,
        source: str | None = None,
        queued: bool = False,
    ) -> int:
        with self._lock:
            candidates = tuple(self._event_history)

        replayed = 0
        for event in candidates:
            if not fnmatch.fnmatchcase(event.event_type, event_type_pattern):
                continue
            if correlation_id and event.correlation_id != correlation_id:
                continue
            if source and event.source != source:
                continue

            replay_event = Event(
                event_type=event.event_type,
                payload=event.payload,
                source="event_replay",
                priority=event.priority,
                correlation_id=event.correlation_id,
                causation_id=event.event_id,
                headers={**dict(event.headers), "replayed": True},
            )
            self.publish(replay_event, queued=queued)
            replayed += 1
        return replayed

    def retry_dead_letter(
        self,
        index: int = -1,
        *,
        queued: bool = False,
    ) -> str:
        with self._lock:
            dead_letter = list(self._dead_letters)[index]
        retry_event = Event(
            event_type=dead_letter.event.event_type,
            payload=dead_letter.event.payload,
            source="dead_letter_retry",
            priority=dead_letter.event.priority,
            correlation_id=dead_letter.event.correlation_id,
            causation_id=dead_letter.event.event_id,
            headers={**dict(dead_letter.event.headers), "dead_letter_retry": True},
        )
        self.publish(retry_event, queued=queued)
        return retry_event.event_id

    def event_history(
        self,
        *,
        event_type_pattern: str = "*",
        limit: int | None = None,
    ) -> tuple[Event, ...]:
        with self._lock:
            events = [
                event
                for event in self._event_history
                if fnmatch.fnmatchcase(event.event_type, event_type_pattern)
            ]
        if limit is not None:
            events = events[-limit:]
        return tuple(events)

    def delivery_history(
        self,
        *,
        subscriber_name: str | None = None,
        event_type_pattern: str = "*",
        limit: int | None = None,
    ) -> tuple[DeliveryRecord, ...]:
        with self._lock:
            records = [
                record
                for record in self._delivery_history
                if fnmatch.fnmatchcase(record.event_type, event_type_pattern)
                and (
                    subscriber_name is None
                    or record.subscriber_name == subscriber_name
                )
            ]
        if limit is not None:
            records = records[-limit:]
        return tuple(records)

    def dead_letters(self) -> tuple[DeadLetter, ...]:
        with self._lock:
            return tuple(self._dead_letters)

    def metrics(self) -> EventBusMetrics:
        with self._lock:
            return EventBusMetrics(
                published=self._published,
                dispatched=self._dispatched,
                delivered=self._delivered,
                failed_attempts=self._failed_attempts,
                dead_lettered=self._dead_lettered,
                unmatched=self._unmatched,
                active_subscriptions=sum(
                    1 for subscription in self._subscriptions.values()
                    if subscription.enabled
                ),
                queued_events=len(self._queue),
                published_by_type=dict(self._published_by_type),
                delivered_by_subscriber=dict(
                    self._delivered_by_subscriber
                ),
            )

    def health_check(self) -> dict[str, Any]:
        metrics = self.metrics()
        return {
            "healthy": self.is_running,
            "running": self.is_running,
            "accepting_events": self._accepting_events,
            "worker_count": len(self._workers),
            "queued_events": metrics.queued_events,
            "dead_lettered": metrics.dead_lettered,
            "active_subscriptions": metrics.active_subscriptions,
        }

    def clear_history(self) -> None:
        with self._lock:
            self._event_history.clear()
            self._delivery_history.clear()
            self._dead_letters.clear()

    def _record_publication(self, event: Event) -> None:
        self._event_history.append(event)
        self._published += 1
        self._published_by_type[event.event_type] += 1

    def _worker_loop(self) -> None:
        while True:
            with self._condition:
                while not self._queue and self._running:
                    self._condition.wait()

                if not self._queue:
                    if not self._running:
                        return
                    continue

                _, _, event = heappop(self._queue)

            self._dispatch(event)

    def _dispatch(self, event: Event) -> None:
        with self._lock:
            subscriptions = tuple(
                subscription
                for subscription in self._subscriptions.values()
                if subscription.matches(event)
            )
            self._dispatched += 1
            if not subscriptions:
                self._unmatched += 1
                return

        for subscription in subscriptions:
            self._deliver(subscription, event)

    def _deliver(
        self,
        subscription: EventSubscription,
        event: Event,
    ) -> None:
        policy = subscription.retry_policy
        last_error = "unknown delivery failure"

        for attempt in range(1, policy.max_attempts + 1):
            delay = policy.delay_for_attempt(attempt)
            if delay:
                time.sleep(delay)

            started_wall = time.perf_counter()
            started_utc = self._utc_now()
            try:
                result = subscription.handler(event)
                if inspect.isawaitable(result):
                    self._run_awaitable(result)

                record = DeliveryRecord(
                    event_id=event.event_id,
                    subscription_id=subscription.subscription_id,
                    subscriber_name=subscription.subscriber_name,
                    event_type=event.event_type,
                    attempt=attempt,
                    status=DeliveryStatus.DELIVERED,
                    started_at_utc=started_utc,
                    finished_at_utc=self._utc_now(),
                    duration_ms=(time.perf_counter() - started_wall) * 1000,
                )
                with self._lock:
                    self._delivery_history.append(record)
                    self._delivered += 1
                    self._delivered_by_subscriber[
                        subscription.subscriber_name
                    ] += 1
                return

            except Exception as exc:
                last_error = str(exc)
                status = (
                    DeliveryStatus.RETRYING
                    if attempt < policy.max_attempts
                    else DeliveryStatus.FAILED
                )
                record = DeliveryRecord(
                    event_id=event.event_id,
                    subscription_id=subscription.subscription_id,
                    subscriber_name=subscription.subscriber_name,
                    event_type=event.event_type,
                    attempt=attempt,
                    status=status,
                    started_at_utc=started_utc,
                    finished_at_utc=self._utc_now(),
                    duration_ms=(time.perf_counter() - started_wall) * 1000,
                    error=last_error,
                )
                with self._lock:
                    self._delivery_history.append(record)
                    self._failed_attempts += 1

        dead_letter = DeadLetter(
            event=event,
            subscription_id=subscription.subscription_id,
            subscriber_name=subscription.subscriber_name,
            attempts=policy.max_attempts,
            error=last_error,
            failed_at_utc=self._utc_now(),
        )
        dead_letter_record = DeliveryRecord(
            event_id=event.event_id,
            subscription_id=subscription.subscription_id,
            subscriber_name=subscription.subscriber_name,
            event_type=event.event_type,
            attempt=policy.max_attempts,
            status=DeliveryStatus.DEAD_LETTERED,
            started_at_utc=self._utc_now(),
            finished_at_utc=self._utc_now(),
            duration_ms=0.0,
            error=last_error,
        )
        with self._lock:
            self._dead_letters.append(dead_letter)
            self._delivery_history.append(dead_letter_record)
            self._dead_lettered += 1

    @staticmethod
    def _run_awaitable(awaitable: Awaitable[Any]) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(awaitable)

        result: list[Any] = []
        errors: list[BaseException] = []

        def runner() -> None:
            try:
                result.append(asyncio.run(awaitable))
            except BaseException as exc:
                errors.append(exc)

        thread = Thread(target=runner, daemon=True)
        thread.start()
        thread.join()
        if errors:
            raise errors[0]
        return result[0] if result else None
