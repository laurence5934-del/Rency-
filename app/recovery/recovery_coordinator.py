from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Any, Callable, Mapping, Protocol, Sequence


class FailureSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class FailureCategory(str, Enum):
    NETWORK = "NETWORK"
    BROKER = "BROKER"
    MARKET_DATA = "MARKET_DATA"
    EXECUTION = "EXECUTION"
    PORTFOLIO = "PORTFOLIO"
    RISK = "RISK"
    STORAGE = "STORAGE"
    AUTHENTICATION = "AUTHENTICATION"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    VALIDATION = "VALIDATION"
    DEPENDENCY = "DEPENDENCY"
    INTERNAL = "INTERNAL"
    UNKNOWN = "UNKNOWN"


class RecoveryAction(str, Enum):
    IGNORE = "IGNORE"
    RETRY = "RETRY"
    RECONNECT = "RECONNECT"
    FAILOVER = "FAILOVER"
    RESTART_COMPONENT = "RESTART_COMPONENT"
    RESTORE_CHECKPOINT = "RESTORE_CHECKPOINT"
    PAUSE_TRADING = "PAUSE_TRADING"
    CANCEL_ORDERS = "CANCEL_ORDERS"
    DEGRADE_SERVICE = "DEGRADE_SERVICE"
    ESCALATE = "ESCALATE"
    SHUTDOWN = "SHUTDOWN"


class RecoveryStatus(str, Enum):
    RECEIVED = "RECEIVED"
    CLASSIFIED = "CLASSIFIED"
    PLANNED = "PLANNED"
    EXECUTING = "EXECUTING"
    RECOVERED = "RECOVERED"
    PARTIALLY_RECOVERED = "PARTIALLY_RECOVERED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    IGNORED = "IGNORED"


@dataclass(frozen=True, slots=True)
class FailureEvent:
    failure_id: str
    source: str
    component: str
    exception_type: str
    message: str
    occurred_at_utc: str
    category: FailureCategory = FailureCategory.UNKNOWN
    severity: FailureSeverity = FailureSeverity.ERROR
    retryable: bool = False
    transient: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.failure_id.strip():
            raise ValueError("failure_id cannot be empty")
        if not self.source.strip():
            raise ValueError("source cannot be empty")
        if not self.component.strip():
            raise ValueError("component cannot be empty")
        if not self.exception_type.strip():
            raise ValueError("exception_type cannot be empty")
        if not self.message.strip():
            raise ValueError("message cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        data["severity"] = self.severity.value
        return data


@dataclass(frozen=True, slots=True)
class RecoveryStep:
    step_id: str
    action: RecoveryAction
    component: str
    priority: int
    timeout_seconds: float
    max_attempts: int = 1
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.step_id.strip():
            raise ValueError("step_id cannot be empty")
        if not self.component.strip():
            raise ValueError("component cannot be empty")
        if self.priority < 1:
            raise ValueError("priority must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["action"] = self.action.value
        return data


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    plan_id: str
    failure_id: str
    status: RecoveryStatus
    created_at_utc: str
    updated_at_utc: str
    steps: tuple[RecoveryStep, ...]
    rationale: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.plan_id.strip():
            raise ValueError("plan_id cannot be empty")
        if not self.failure_id.strip():
            raise ValueError("failure_id cannot be empty")
        if not self.rationale.strip():
            raise ValueError("rationale cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["steps"] = [step.to_dict() for step in self.steps]
        return data


@dataclass(frozen=True, slots=True)
class RecoveryStepResult:
    step_id: str
    action: RecoveryAction
    component: str
    success: bool
    attempts: int
    started_at_utc: str
    completed_at_utc: str
    duration_seconds: float
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["action"] = self.action.value
        return data


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    plan_id: str
    failure_id: str
    status: RecoveryStatus
    started_at_utc: str
    completed_at_utc: str
    step_results: tuple[RecoveryStepResult, ...]
    successful_steps: int
    failed_steps: int
    total_duration_seconds: float
    message: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["step_results"] = [result.to_dict() for result in self.step_results]
        return data


@dataclass(slots=True)
class RecoveryCoordinatorConfig:
    default_timeout_seconds: float = 30.0
    default_retry_attempts: int = 3
    stop_on_critical_failure: bool = True
    publish_events: bool = True
    retain_history: int = 1_000

    def __post_init__(self) -> None:
        if self.default_timeout_seconds <= 0:
            raise ValueError("default_timeout_seconds must be positive")
        if self.default_retry_attempts < 1:
            raise ValueError("default_retry_attempts must be positive")
        if self.retain_history < 1:
            raise ValueError("retain_history must be positive")


class EventPublisher(Protocol):
    def publish_event(
        self,
        event_type: str,
        payload: Any = None,
        *,
        source: str = "unknown",
        **kwargs: Any,
    ) -> Any: ...


class RecoveryHandler(Protocol):
    def __call__(
        self,
        failure: FailureEvent,
        step: RecoveryStep,
    ) -> Mapping[str, Any] | bool | None: ...


class FailureClassifier:
    """
    Deterministic failure classifier.

    It can be replaced later by a rule engine or AI-assisted classifier while
    preserving the same public interface.
    """

    _CATEGORY_RULES: tuple[tuple[FailureCategory, tuple[str, ...]], ...] = (
        (FailureCategory.AUTHENTICATION, ("auth", "credential", "unauthorized", "forbidden")),
        (FailureCategory.RATE_LIMIT, ("rate limit", "too many requests", "429")),
        (FailureCategory.TIMEOUT, ("timeout", "timed out", "deadline exceeded")),
        (FailureCategory.NETWORK, ("connection", "network", "socket", "dns", "transport")),
        (FailureCategory.BROKER, ("broker", "order rejected", "brokerage")),
        (FailureCategory.MARKET_DATA, ("market data", "quote", "feed", "stale data")),
        (FailureCategory.EXECUTION, ("execution", "fill", "order", "slippage")),
        (FailureCategory.PORTFOLIO, ("portfolio", "allocation", "rebalance")),
        (FailureCategory.RISK, ("risk", "limit breach", "exposure", "margin")),
        (FailureCategory.STORAGE, ("database", "storage", "disk", "checkpoint")),
        (FailureCategory.VALIDATION, ("validation", "invalid", "malformed")),
        (FailureCategory.DEPENDENCY, ("dependency", "upstream", "downstream")),
    )

    def classify(
        self,
        *,
        source: str,
        component: str,
        exception: BaseException | None = None,
        message: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> FailureEvent:
        exception_type = type(exception).__name__ if exception else "ReportedFailure"
        text = (message or str(exception) or exception_type).strip()
        searchable = f"{exception_type} {text} {source} {component}".lower()

        category = FailureCategory.UNKNOWN
        for candidate, keywords in self._CATEGORY_RULES:
            if any(keyword in searchable for keyword in keywords):
                category = candidate
                break

        retryable = self._is_retryable(category, exception_type, searchable)
        transient = category in {
            FailureCategory.NETWORK,
            FailureCategory.TIMEOUT,
            FailureCategory.RATE_LIMIT,
            FailureCategory.MARKET_DATA,
            FailureCategory.DEPENDENCY,
        }

        severity = self._severity_for(
            category=category,
            searchable=searchable,
            metadata=metadata or {},
        )

        return FailureEvent(
            failure_id=str(uuid.uuid4()),
            source=source,
            component=component,
            exception_type=exception_type,
            message=text,
            occurred_at_utc=datetime.now(timezone.utc).isoformat(),
            category=category,
            severity=severity,
            retryable=retryable,
            transient=transient,
            metadata=dict(metadata or {}),
        )

    @staticmethod
    def _is_retryable(
        category: FailureCategory,
        exception_type: str,
        searchable: str,
    ) -> bool:
        if category in {
            FailureCategory.NETWORK,
            FailureCategory.TIMEOUT,
            FailureCategory.RATE_LIMIT,
            FailureCategory.MARKET_DATA,
            FailureCategory.DEPENDENCY,
        }:
            return True
        retryable_types = {
            "ConnectionError",
            "TimeoutError",
            "BrokenPipeError",
            "ConnectionResetError",
        }
        return exception_type in retryable_types or "temporar" in searchable

    @staticmethod
    def _severity_for(
        *,
        category: FailureCategory,
        searchable: str,
        metadata: Mapping[str, Any],
    ) -> FailureSeverity:
        explicit = metadata.get("severity")
        if explicit:
            try:
                return FailureSeverity(str(explicit).upper())
            except ValueError:
                pass

        if any(word in searchable for word in ("fatal", "critical", "corrupt", "data loss")):
            return FailureSeverity.CRITICAL
        if category in {
            FailureCategory.RISK,
            FailureCategory.AUTHENTICATION,
            FailureCategory.STORAGE,
        }:
            return FailureSeverity.CRITICAL
        if category in {
            FailureCategory.NETWORK,
            FailureCategory.TIMEOUT,
            FailureCategory.RATE_LIMIT,
            FailureCategory.DEPENDENCY,
        }:
            return FailureSeverity.WARNING
        return FailureSeverity.ERROR


class RecoveryPolicyEngine:
    """
    Converts classified failures into ordered recovery steps.
    """

    def __init__(self, config: RecoveryCoordinatorConfig) -> None:
        self.config = config

    def create_plan(self, failure: FailureEvent) -> RecoveryPlan:
        steps: list[RecoveryStep] = []
        timeout = self.config.default_timeout_seconds
        retries = self.config.default_retry_attempts

        if failure.severity == FailureSeverity.INFO:
            steps.append(self._step(RecoveryAction.IGNORE, failure.component, 1, timeout))
            rationale = "Informational event does not require active recovery."
        elif failure.category == FailureCategory.RATE_LIMIT:
            steps.append(
                self._step(
                    RecoveryAction.RETRY,
                    failure.component,
                    1,
                    timeout,
                    retries,
                    {"backoff": "exponential", "respect_retry_after": True},
                )
            )
            rationale = "Rate-limit failures require delayed retries."
        elif failure.category in {FailureCategory.NETWORK, FailureCategory.TIMEOUT}:
            steps.extend(
                (
                    self._step(
                        RecoveryAction.RETRY,
                        failure.component,
                        1,
                        timeout,
                        retries,
                        {"backoff": "exponential", "jitter": True},
                    ),
                    self._step(
                        RecoveryAction.RECONNECT,
                        failure.component,
                        2,
                        timeout,
                        2,
                    ),
                    self._step(
                        RecoveryAction.FAILOVER,
                        failure.component,
                        3,
                        timeout,
                        1,
                    ),
                )
            )
            rationale = "Transient connectivity failure: retry, reconnect, then fail over."
        elif failure.category in {FailureCategory.BROKER, FailureCategory.MARKET_DATA}:
            steps.extend(
                (
                    self._step(RecoveryAction.RECONNECT, failure.component, 1, timeout, 2),
                    self._step(RecoveryAction.FAILOVER, failure.component, 2, timeout, 1),
                    self._step(RecoveryAction.PAUSE_TRADING, "trading", 3, timeout, 1),
                )
            )
            rationale = "Provider failure requires reconnection, failover, and safe trading pause."
        elif failure.category == FailureCategory.EXECUTION:
            steps.extend(
                (
                    self._step(RecoveryAction.PAUSE_TRADING, "execution", 1, timeout),
                    self._step(RecoveryAction.CANCEL_ORDERS, "execution", 2, timeout),
                    self._step(RecoveryAction.RESTORE_CHECKPOINT, failure.component, 3, timeout),
                    self._step(RecoveryAction.ESCALATE, failure.component, 4, timeout),
                )
            )
            rationale = "Execution failures require immediate containment and state reconciliation."
        elif failure.category == FailureCategory.RISK:
            steps.extend(
                (
                    self._step(RecoveryAction.PAUSE_TRADING, "trading", 1, timeout),
                    self._step(RecoveryAction.CANCEL_ORDERS, "execution", 2, timeout),
                    self._step(RecoveryAction.ESCALATE, "risk", 3, timeout),
                )
            )
            rationale = "Risk failures must stop new trading and escalate."
        elif failure.category == FailureCategory.STORAGE:
            steps.extend(
                (
                    self._step(RecoveryAction.RESTORE_CHECKPOINT, failure.component, 1, timeout),
                    self._step(RecoveryAction.RESTART_COMPONENT, failure.component, 2, timeout),
                    self._step(RecoveryAction.ESCALATE, failure.component, 3, timeout),
                )
            )
            rationale = "Storage failure requires restoration and controlled restart."
        elif failure.category == FailureCategory.AUTHENTICATION:
            steps.extend(
                (
                    self._step(RecoveryAction.PAUSE_TRADING, "trading", 1, timeout),
                    self._step(RecoveryAction.ESCALATE, failure.component, 2, timeout),
                )
            )
            rationale = "Authentication failures require manual credential intervention."
        elif failure.retryable:
            steps.extend(
                (
                    self._step(RecoveryAction.RETRY, failure.component, 1, timeout, retries),
                    self._step(RecoveryAction.RESTART_COMPONENT, failure.component, 2, timeout),
                )
            )
            rationale = "Retryable failure uses retry followed by component restart."
        else:
            steps.extend(
                (
                    self._step(RecoveryAction.DEGRADE_SERVICE, failure.component, 1, timeout),
                    self._step(RecoveryAction.ESCALATE, failure.component, 2, timeout),
                )
            )
            rationale = "Unknown or non-retryable failure requires degraded operation and escalation."

        if failure.severity == FailureSeverity.CRITICAL:
            if not any(step.action == RecoveryAction.PAUSE_TRADING for step in steps):
                steps.insert(
                    0,
                    self._step(RecoveryAction.PAUSE_TRADING, "trading", 1, timeout),
                )
            steps = [
                replace(step, priority=index)
                for index, step in enumerate(steps, start=1)
            ]

        now = datetime.now(timezone.utc).isoformat()
        return RecoveryPlan(
            plan_id=str(uuid.uuid4()),
            failure_id=failure.failure_id,
            status=RecoveryStatus.PLANNED,
            created_at_utc=now,
            updated_at_utc=now,
            steps=tuple(sorted(steps, key=lambda item: item.priority)),
            rationale=rationale,
            metadata={
                "failure_category": failure.category.value,
                "failure_severity": failure.severity.value,
            },
        )

    @staticmethod
    def _step(
        action: RecoveryAction,
        component: str,
        priority: int,
        timeout_seconds: float,
        max_attempts: int = 1,
        parameters: Mapping[str, Any] | None = None,
    ) -> RecoveryStep:
        return RecoveryStep(
            step_id=str(uuid.uuid4()),
            action=action,
            component=component,
            priority=priority,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            parameters=dict(parameters or {}),
        )


class RecoveryCoordinator:
    """
    Version 10.0.8.1 - Recovery Coordinator & Failure Classification.

    Central entry point for failure intake, classification, recovery planning,
    recovery execution, event publication, history, and operational metrics.
    """

    def __init__(
        self,
        *,
        config: RecoveryCoordinatorConfig | None = None,
        classifier: FailureClassifier | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self.config = config or RecoveryCoordinatorConfig()
        self.classifier = classifier or FailureClassifier()
        self.policy_engine = RecoveryPolicyEngine(self.config)
        self.event_publisher = event_publisher

        self._lock = RLock()
        self._handlers: dict[RecoveryAction, RecoveryHandler] = {}
        self._failures: dict[str, FailureEvent] = {}
        self._plans: dict[str, RecoveryPlan] = {}
        self._reports: dict[str, RecoveryReport] = {}
        self._metrics: dict[str, int | float] = {
            "failures_received": 0,
            "plans_created": 0,
            "recoveries_started": 0,
            "recoveries_completed": 0,
            "recoveries_failed": 0,
            "recoveries_partial": 0,
            "steps_executed": 0,
            "steps_failed": 0,
            "total_recovery_seconds": 0.0,
        }

        self._install_default_handlers()

    def register_handler(
        self,
        action: RecoveryAction,
        handler: RecoveryHandler,
    ) -> None:
        with self._lock:
            self._handlers[action] = handler

    def report_failure(
        self,
        *,
        source: str,
        component: str,
        exception: BaseException | None = None,
        message: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        auto_execute: bool = False,
    ) -> tuple[FailureEvent, RecoveryPlan, RecoveryReport | None]:
        failure = self.classifier.classify(
            source=source,
            component=component,
            exception=exception,
            message=message,
            metadata=metadata,
        )
        plan = self.policy_engine.create_plan(failure)

        with self._lock:
            self._failures[failure.failure_id] = failure
            self._plans[plan.plan_id] = plan
            self._metrics["failures_received"] += 1
            self._metrics["plans_created"] += 1
            self._trim_history_unlocked()

        self._publish("recovery.failure_classified", failure.to_dict())
        self._publish("recovery.plan_created", plan.to_dict())

        report = self.execute_plan(plan.plan_id) if auto_execute else None
        return failure, plan, report

    def execute_plan(self, plan_id: str) -> RecoveryReport:
        with self._lock:
            plan = self._require_plan(plan_id)
            if plan.status not in {RecoveryStatus.PLANNED, RecoveryStatus.FAILED}:
                raise RuntimeError(
                    f"plan cannot execute from status {plan.status.value}"
                )
            failure = self._require_failure(plan.failure_id)
            executing = replace(
                plan,
                status=RecoveryStatus.EXECUTING,
                updated_at_utc=self._utc_now(),
            )
            self._plans[plan_id] = executing
            self._metrics["recoveries_started"] += 1

        started_monotonic = time.monotonic()
        started_at = self._utc_now()
        results: list[RecoveryStepResult] = []

        for step in executing.steps:
            result = self._execute_step(failure, step)
            results.append(result)

            if (
                not result.success
                and failure.severity == FailureSeverity.CRITICAL
                and self.config.stop_on_critical_failure
            ):
                break

        successful = sum(1 for result in results if result.success)
        failed = sum(1 for result in results if not result.success)

        if failed == 0 and len(results) == len(executing.steps):
            status = RecoveryStatus.RECOVERED
            message = "Recovery plan completed successfully."
        elif successful > 0:
            status = RecoveryStatus.PARTIALLY_RECOVERED
            message = "Recovery plan completed with partial success."
        else:
            status = RecoveryStatus.FAILED
            message = "Recovery plan failed."

        completed_at = self._utc_now()
        duration = time.monotonic() - started_monotonic
        report = RecoveryReport(
            plan_id=plan_id,
            failure_id=failure.failure_id,
            status=status,
            started_at_utc=started_at,
            completed_at_utc=completed_at,
            step_results=tuple(results),
            successful_steps=successful,
            failed_steps=failed,
            total_duration_seconds=duration,
            message=message,
        )

        with self._lock:
            self._plans[plan_id] = replace(
                executing,
                status=status,
                updated_at_utc=completed_at,
            )
            self._reports[plan_id] = report
            self._metrics["total_recovery_seconds"] += duration

            if status == RecoveryStatus.RECOVERED:
                self._metrics["recoveries_completed"] += 1
            elif status == RecoveryStatus.PARTIALLY_RECOVERED:
                self._metrics["recoveries_partial"] += 1
            else:
                self._metrics["recoveries_failed"] += 1

            self._trim_history_unlocked()

        self._publish("recovery.plan_completed", report.to_dict())
        return report

    def get_failure(self, failure_id: str) -> FailureEvent:
        with self._lock:
            return self._require_failure(failure_id)

    def get_plan(self, plan_id: str) -> RecoveryPlan:
        with self._lock:
            return self._require_plan(plan_id)

    def get_report(self, plan_id: str) -> RecoveryReport:
        with self._lock:
            report = self._reports.get(plan_id)
            if report is None:
                raise KeyError(f"unknown recovery report: {plan_id}")
            return report

    def list_failures(
        self,
        *,
        category: FailureCategory | None = None,
        severity: FailureSeverity | None = None,
        component: str | None = None,
    ) -> tuple[FailureEvent, ...]:
        with self._lock:
            failures = tuple(self._failures.values())

        if category is not None:
            failures = tuple(item for item in failures if item.category == category)
        if severity is not None:
            failures = tuple(item for item in failures if item.severity == severity)
        if component is not None:
            failures = tuple(item for item in failures if item.component == component)

        return tuple(sorted(failures, key=lambda item: item.occurred_at_utc))

    def list_plans(
        self,
        *,
        status: RecoveryStatus | None = None,
    ) -> tuple[RecoveryPlan, ...]:
        with self._lock:
            plans = tuple(self._plans.values())
        if status is not None:
            plans = tuple(item for item in plans if item.status == status)
        return tuple(sorted(plans, key=lambda item: item.created_at_utc))

    def metrics(self) -> dict[str, int | float]:
        with self._lock:
            metrics = dict(self._metrics)

        attempts = float(metrics["recoveries_started"])
        if attempts:
            metrics["mean_recovery_seconds"] = (
                float(metrics["total_recovery_seconds"]) / attempts
            )
        else:
            metrics["mean_recovery_seconds"] = 0.0
        return metrics

    def health_check(self) -> dict[str, Any]:
        metrics = self.metrics()
        failures = int(metrics["recoveries_failed"])
        started = int(metrics["recoveries_started"])
        failure_rate = failures / started if started else 0.0

        return {
            "healthy": failure_rate < 0.25,
            "degraded": 0.10 <= failure_rate < 0.25,
            "failure_rate": failure_rate,
            "registered_handlers": len(self._handlers),
            "tracked_failures": len(self._failures),
            "tracked_plans": len(self._plans),
            "metrics": metrics,
        }

    def _execute_step(
        self,
        failure: FailureEvent,
        step: RecoveryStep,
    ) -> RecoveryStepResult:
        with self._lock:
            handler = self._handlers.get(step.action)

        if handler is None:
            return RecoveryStepResult(
                step_id=step.step_id,
                action=step.action,
                component=step.component,
                success=False,
                attempts=0,
                started_at_utc=self._utc_now(),
                completed_at_utc=self._utc_now(),
                duration_seconds=0.0,
                message=f"No handler registered for {step.action.value}.",
            )

        started_at = self._utc_now()
        started_monotonic = time.monotonic()
        last_message = ""
        details: Mapping[str, Any] = {}
        success = False
        attempts = 0

        for attempt in range(1, step.max_attempts + 1):
            attempts = attempt
            try:
                response = handler(failure, step)

                if isinstance(response, Mapping):
                    success = bool(response.get("success", True))
                    last_message = str(
                        response.get(
                            "message",
                            "Recovery step completed." if success else "Recovery step failed.",
                        )
                    )
                    details = dict(response)
                elif isinstance(response, bool):
                    success = response
                    last_message = (
                        "Recovery step completed."
                        if success
                        else "Recovery step failed."
                    )
                else:
                    success = True
                    last_message = "Recovery step completed."

                if success:
                    break
            except Exception as exc:
                success = False
                last_message = f"{type(exc).__name__}: {exc}"
                details = {
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                }

        duration = time.monotonic() - started_monotonic
        result = RecoveryStepResult(
            step_id=step.step_id,
            action=step.action,
            component=step.component,
            success=success,
            attempts=attempts,
            started_at_utc=started_at,
            completed_at_utc=self._utc_now(),
            duration_seconds=duration,
            message=last_message,
            details=details,
        )

        with self._lock:
            self._metrics["steps_executed"] += 1
            if not success:
                self._metrics["steps_failed"] += 1

        event_name = (
            "recovery.step_succeeded"
            if success
            else "recovery.step_failed"
        )
        self._publish(event_name, result.to_dict())
        return result

    def _install_default_handlers(self) -> None:
        def success_handler(
            failure: FailureEvent,
            step: RecoveryStep,
        ) -> Mapping[str, Any]:
            return {
                "success": True,
                "message": (
                    f"Default handler accepted {step.action.value} "
                    f"for {step.component}."
                ),
                "failure_id": failure.failure_id,
                "parameters": dict(step.parameters),
            }

        for action in RecoveryAction:
            self._handlers[action] = success_handler

    def _trim_history_unlocked(self) -> None:
        limit = self.config.retain_history

        if len(self._failures) > limit:
            ordered = sorted(
                self._failures.values(),
                key=lambda item: item.occurred_at_utc,
            )
            for item in ordered[: len(self._failures) - limit]:
                self._failures.pop(item.failure_id, None)

        if len(self._plans) > limit:
            ordered = sorted(
                self._plans.values(),
                key=lambda item: item.created_at_utc,
            )
            for item in ordered[: len(self._plans) - limit]:
                self._plans.pop(item.plan_id, None)
                self._reports.pop(item.plan_id, None)

    def _require_failure(self, failure_id: str) -> FailureEvent:
        failure = self._failures.get(failure_id)
        if failure is None:
            raise KeyError(f"unknown failure: {failure_id}")
        return failure

    def _require_plan(self, plan_id: str) -> RecoveryPlan:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise KeyError(f"unknown recovery plan: {plan_id}")
        return plan

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _publish(self, event_type: str, payload: Any) -> None:
        if self.config.publish_events and self.event_publisher is not None:
            self.event_publisher.publish_event(
                event_type,
                payload,
                source="recovery_coordinator",
            )
