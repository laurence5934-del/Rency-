from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Any, Callable, Mapping, Protocol, Sequence


class ProviderRole(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    TERTIARY = "TERTIARY"


class ProviderState(str, Enum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    DISABLED = "DISABLED"
    COOLDOWN = "COOLDOWN"


class FailoverReason(str, Enum):
    HEALTH_CHECK_FAILED = "HEALTH_CHECK_FAILED"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"
    TIMEOUT = "TIMEOUT"
    MANUAL = "MANUAL"
    PRIORITY_RESTORE = "PRIORITY_RESTORE"
    PROVIDER_DISABLED = "PROVIDER_DISABLED"
    STARTUP_SELECTION = "STARTUP_SELECTION"


class FailoverStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    NO_CHANGE = "NO_CHANGE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    provider_id: str
    name: str
    priority: int
    role: ProviderRole = ProviderRole.SECONDARY
    enabled: bool = True
    health_check_interval_seconds: float = 10.0
    failure_threshold: int = 3
    recovery_threshold: int = 2
    cooldown_seconds: float = 30.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id cannot be empty")
        if not self.name.strip():
            raise ValueError("name cannot be empty")
        if self.priority < 1:
            raise ValueError("priority must be positive")
        if self.health_check_interval_seconds <= 0:
            raise ValueError("health_check_interval_seconds must be positive")
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be positive")
        if self.recovery_threshold < 1:
            raise ValueError("recovery_threshold must be positive")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds cannot be negative")


@dataclass(frozen=True, slots=True)
class ProviderSnapshot:
    provider_id: str
    name: str
    priority: int
    role: ProviderRole
    state: ProviderState
    enabled: bool
    active: bool
    consecutive_failures: int
    consecutive_successes: int
    total_failures: int
    total_successes: int
    last_health_check_at_utc: str | None
    last_failure_at_utc: str | None
    last_success_at_utc: str | None
    cooldown_until_utc: str | None
    updated_at_utc: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["role"] = self.role.value
        data["state"] = self.state.value
        return data


@dataclass(frozen=True, slots=True)
class FailoverEvent:
    event_id: str
    from_provider_id: str | None
    to_provider_id: str | None
    reason: FailoverReason
    status: FailoverStatus
    occurred_at_utc: str
    message: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reason"] = self.reason.value
        data["status"] = self.status.value
        return data


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    provider_id: str
    healthy: bool
    degraded: bool = False
    message: str = ""
    latency_seconds: float | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FailoverManagerConfig:
    automatic_failover: bool = True
    automatic_failback: bool = True
    failback_stability_seconds: float = 60.0
    minimum_switch_interval_seconds: float = 5.0
    allow_degraded_provider: bool = True
    publish_events: bool = True
    retain_history: int = 1_000

    def __post_init__(self) -> None:
        if self.failback_stability_seconds < 0:
            raise ValueError("failback_stability_seconds cannot be negative")
        if self.minimum_switch_interval_seconds < 0:
            raise ValueError("minimum_switch_interval_seconds cannot be negative")
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


class ProviderHealthCheck(Protocol):
    def __call__(self) -> HealthCheckResult | bool | Mapping[str, Any]: ...


class ProviderActivator(Protocol):
    def __call__(self, provider_id: str) -> bool | Mapping[str, Any] | None: ...


class ProviderDeactivator(Protocol):
    def __call__(self, provider_id: str) -> bool | Mapping[str, Any] | None: ...


@dataclass(slots=True)
class _ProviderRuntime:
    config: ProviderConfig
    health_check: ProviderHealthCheck | None = None
    activator: ProviderActivator | None = None
    deactivator: ProviderDeactivator | None = None
    state: ProviderState = ProviderState.UNKNOWN
    active: bool = False
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_failures: int = 0
    total_successes: int = 0
    last_health_check_monotonic: float | None = None
    last_health_check_at_utc: str | None = None
    last_failure_at_utc: str | None = None
    last_success_at_utc: str | None = None
    healthy_since_monotonic: float | None = None
    cooldown_until_monotonic: float | None = None
    cooldown_until_utc: str | None = None
    updated_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class FailoverManager:
    """
    Version 10.0.8.4 - Failover Manager.

    Manages prioritized providers, health state, automatic failover,
    controlled failback, cooldowns, manual overrides, activation hooks,
    deactivation hooks, event publication, metrics, and thread-safe state.
    """

    def __init__(
        self,
        *,
        config: FailoverManagerConfig | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self.config = config or FailoverManagerConfig()
        self.event_publisher = event_publisher

        self._lock = RLock()
        self._providers: dict[str, _ProviderRuntime] = {}
        self._active_provider_id: str | None = None
        self._last_switch_monotonic: float | None = None
        self._history: list[FailoverEvent] = []
        self._metrics: dict[str, int | float] = {
            "health_checks_total": 0,
            "health_checks_failed": 0,
            "failovers_attempted": 0,
            "failovers_succeeded": 0,
            "failovers_failed": 0,
            "failbacks_succeeded": 0,
            "manual_switches": 0,
            "provider_disables": 0,
            "provider_enables": 0,
        }

    def register_provider(
        self,
        config: ProviderConfig,
        *,
        health_check: ProviderHealthCheck | None = None,
        activator: ProviderActivator | None = None,
        deactivator: ProviderDeactivator | None = None,
    ) -> None:
        with self._lock:
            if config.provider_id in self._providers:
                raise KeyError(f"provider already registered: {config.provider_id}")

            runtime = _ProviderRuntime(
                config=config,
                health_check=health_check,
                activator=activator,
                deactivator=deactivator,
                state=ProviderState.UNKNOWN if config.enabled else ProviderState.DISABLED,
            )
            self._providers[config.provider_id] = runtime

    def remove_provider(self, provider_id: str) -> bool:
        with self._lock:
            runtime = self._providers.get(provider_id)
            if runtime is None:
                return False
            if runtime.active:
                raise RuntimeError("cannot remove the active provider")
            del self._providers[provider_id]
            return True

    def initialize(self) -> FailoverEvent:
        with self._lock:
            if self._active_provider_id is not None:
                return self._make_event_unlocked(
                    from_provider_id=self._active_provider_id,
                    to_provider_id=self._active_provider_id,
                    reason=FailoverReason.STARTUP_SELECTION,
                    status=FailoverStatus.NO_CHANGE,
                    message="active provider already selected",
                )

        self.run_health_checks(force=True)
        candidate = self.select_best_provider()

        if candidate is None:
            event = self._record_event(
                from_provider_id=None,
                to_provider_id=None,
                reason=FailoverReason.STARTUP_SELECTION,
                status=FailoverStatus.FAILED,
                message="no eligible provider available during startup",
            )
            return event

        return self.switch_to(
            candidate.provider_id,
            reason=FailoverReason.STARTUP_SELECTION,
        )

    def run_health_checks(self, *, force: bool = False) -> tuple[HealthCheckResult, ...]:
        with self._lock:
            provider_ids = tuple(self._providers.keys())

        results: list[HealthCheckResult] = []
        for provider_id in provider_ids:
            result = self.check_provider(provider_id, force=force)
            if result is not None:
                results.append(result)

        if self.config.automatic_failover:
            self.evaluate_failover()
        if self.config.automatic_failback:
            self.evaluate_failback()

        return tuple(results)

    def check_provider(
        self,
        provider_id: str,
        *,
        force: bool = False,
    ) -> HealthCheckResult | None:
        with self._lock:
            runtime = self._require_provider_unlocked(provider_id)

            if not runtime.config.enabled:
                runtime.state = ProviderState.DISABLED
                runtime.updated_at_utc = self._utc_now()
                return HealthCheckResult(
                    provider_id=provider_id,
                    healthy=False,
                    message="provider is disabled",
                )

            now = time.monotonic()
            self._refresh_cooldown_unlocked(runtime, now)

            if (
                not force
                and runtime.last_health_check_monotonic is not None
                and now - runtime.last_health_check_monotonic
                < runtime.config.health_check_interval_seconds
            ):
                return None

            health_check = runtime.health_check

        started = time.monotonic()

        try:
            if health_check is None:
                raw: HealthCheckResult | bool | Mapping[str, Any] = True
            else:
                raw = health_check()

            result = self._normalize_health_result(
                provider_id=provider_id,
                raw=raw,
                latency_seconds=time.monotonic() - started,
            )
        except Exception as exc:
            result = HealthCheckResult(
                provider_id=provider_id,
                healthy=False,
                degraded=False,
                message=f"{type(exc).__name__}: {exc}",
                latency_seconds=time.monotonic() - started,
                details={
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )

        with self._lock:
            runtime = self._require_provider_unlocked(provider_id)
            self._apply_health_result_unlocked(runtime, result)
            self._metrics["health_checks_total"] += 1
            if not result.healthy:
                self._metrics["health_checks_failed"] += 1

        event_name = (
            "failover.provider_healthy"
            if result.healthy and not result.degraded
            else "failover.provider_degraded"
            if result.healthy and result.degraded
            else "failover.provider_unhealthy"
        )
        self._publish(event_name, self.get_provider(provider_id).to_dict())
        return result

    def select_best_provider(
        self,
        *,
        exclude_provider_ids: Sequence[str] = (),
    ) -> ProviderSnapshot | None:
        excluded = set(exclude_provider_ids)

        with self._lock:
            now = time.monotonic()
            candidates: list[_ProviderRuntime] = []

            for runtime in self._providers.values():
                self._refresh_cooldown_unlocked(runtime, now)

                if runtime.config.provider_id in excluded:
                    continue
                if not runtime.config.enabled:
                    continue
                if runtime.state == ProviderState.HEALTHY:
                    candidates.append(runtime)
                elif (
                    self.config.allow_degraded_provider
                    and runtime.state == ProviderState.DEGRADED
                ):
                    candidates.append(runtime)

            if not candidates:
                return None

            candidates.sort(
                key=lambda item: (
                    0 if item.state == ProviderState.HEALTHY else 1,
                    item.config.priority,
                    item.config.name,
                )
            )
            return self._snapshot_unlocked(candidates[0])

    def evaluate_failover(self) -> FailoverEvent | None:
        with self._lock:
            active_id = self._active_provider_id
            if active_id is None:
                candidate = self.select_best_provider()
                if candidate is None:
                    return None
            else:
                runtime = self._require_provider_unlocked(active_id)
                self._refresh_cooldown_unlocked(runtime, time.monotonic())
                if runtime.state in {
                    ProviderState.HEALTHY,
                    ProviderState.DEGRADED,
                }:
                    return None
                candidate = self.select_best_provider(
                    exclude_provider_ids=(active_id,)
                )
                if candidate is None:
                    return self._record_event(
                        from_provider_id=active_id,
                        to_provider_id=None,
                        reason=FailoverReason.HEALTH_CHECK_FAILED,
                        status=FailoverStatus.FAILED,
                        message="active provider failed and no backup is eligible",
                    )

        return self.switch_to(
            candidate.provider_id,
            reason=FailoverReason.HEALTH_CHECK_FAILED,
        )

    def evaluate_failback(self) -> FailoverEvent | None:
        with self._lock:
            active_id = self._active_provider_id
            if active_id is None:
                return None

            active = self._require_provider_unlocked(active_id)
            candidates = sorted(
                self._providers.values(),
                key=lambda item: item.config.priority,
            )

            now = time.monotonic()
            for candidate in candidates:
                if candidate.config.priority >= active.config.priority:
                    continue
                if not candidate.config.enabled:
                    continue

                self._refresh_cooldown_unlocked(candidate, now)

                if candidate.state != ProviderState.HEALTHY:
                    continue
                if candidate.healthy_since_monotonic is None:
                    continue
                if (
                    now - candidate.healthy_since_monotonic
                    < self.config.failback_stability_seconds
                ):
                    continue

                target_id = candidate.config.provider_id
                break
            else:
                return None

        return self.switch_to(
            target_id,
            reason=FailoverReason.PRIORITY_RESTORE,
        )

    def switch_to(
        self,
        provider_id: str,
        *,
        reason: FailoverReason = FailoverReason.MANUAL,
        force: bool = False,
    ) -> FailoverEvent:
        with self._lock:
            target = self._require_provider_unlocked(provider_id)
            current_id = self._active_provider_id

            if current_id == provider_id:
                return self._record_event(
                    from_provider_id=current_id,
                    to_provider_id=provider_id,
                    reason=reason,
                    status=FailoverStatus.NO_CHANGE,
                    message="requested provider is already active",
                )

            now = time.monotonic()
            self._refresh_cooldown_unlocked(target, now)

            if not target.config.enabled:
                return self._record_event(
                    from_provider_id=current_id,
                    to_provider_id=provider_id,
                    reason=reason,
                    status=FailoverStatus.BLOCKED,
                    message="target provider is disabled",
                )

            if (
                not force
                and target.state not in {
                    ProviderState.HEALTHY,
                    ProviderState.DEGRADED,
                }
            ):
                return self._record_event(
                    from_provider_id=current_id,
                    to_provider_id=provider_id,
                    reason=reason,
                    status=FailoverStatus.BLOCKED,
                    message=f"target provider state is {target.state.value}",
                )

            if (
                not force
                and self._last_switch_monotonic is not None
                and now - self._last_switch_monotonic
                < self.config.minimum_switch_interval_seconds
            ):
                return self._record_event(
                    from_provider_id=current_id,
                    to_provider_id=provider_id,
                    reason=reason,
                    status=FailoverStatus.BLOCKED,
                    message="minimum switch interval has not elapsed",
                )

            current = (
                self._providers.get(current_id)
                if current_id is not None
                else None
            )

            self._metrics["failovers_attempted"] += 1

        if not self._activate_provider(target):
            event = self._record_event(
                from_provider_id=current_id,
                to_provider_id=provider_id,
                reason=reason,
                status=FailoverStatus.FAILED,
                message="target provider activation failed",
            )
            with self._lock:
                self._metrics["failovers_failed"] += 1
            return event

        if current is not None and not self._deactivate_provider(current):
            self._deactivate_provider(target)
            event = self._record_event(
                from_provider_id=current_id,
                to_provider_id=provider_id,
                reason=reason,
                status=FailoverStatus.FAILED,
                message="current provider deactivation failed; switch rolled back",
            )
            with self._lock:
                self._metrics["failovers_failed"] += 1
            return event

        with self._lock:
            if current is not None:
                current.active = False
                current.updated_at_utc = self._utc_now()

            target.active = True
            target.updated_at_utc = self._utc_now()
            self._active_provider_id = provider_id
            self._last_switch_monotonic = time.monotonic()
            self._metrics["failovers_succeeded"] += 1

            if reason == FailoverReason.PRIORITY_RESTORE:
                self._metrics["failbacks_succeeded"] += 1
            if reason == FailoverReason.MANUAL:
                self._metrics["manual_switches"] += 1

        event = self._record_event(
            from_provider_id=current_id,
            to_provider_id=provider_id,
            reason=reason,
            status=FailoverStatus.SUCCEEDED,
            message=f"active provider switched to {target.config.name}",
        )
        self._publish("failover.provider_switched", event.to_dict())
        return event

    def disable_provider(
        self,
        provider_id: str,
        *,
        reason: str = "manually disabled",
    ) -> FailoverEvent | None:
        with self._lock:
            runtime = self._require_provider_unlocked(provider_id)
            runtime.config = replace(runtime.config, enabled=False)
            runtime.state = ProviderState.DISABLED
            runtime.updated_at_utc = self._utc_now()
            was_active = runtime.active
            self._metrics["provider_disables"] += 1

        self._publish(
            "failover.provider_disabled",
            {
                "provider_id": provider_id,
                "reason": reason,
            },
        )

        if was_active and self.config.automatic_failover:
            return self.evaluate_failover()
        return None

    def enable_provider(self, provider_id: str) -> ProviderSnapshot:
        with self._lock:
            runtime = self._require_provider_unlocked(provider_id)
            runtime.config = replace(runtime.config, enabled=True)
            runtime.state = ProviderState.UNKNOWN
            runtime.updated_at_utc = self._utc_now()
            self._metrics["provider_enables"] += 1

        self._publish(
            "failover.provider_enabled",
            {"provider_id": provider_id},
        )
        return self.get_provider(provider_id)

    def mark_unhealthy(
        self,
        provider_id: str,
        *,
        reason: FailoverReason = FailoverReason.CIRCUIT_OPEN,
        message: str = "provider marked unhealthy",
    ) -> FailoverEvent | None:
        with self._lock:
            runtime = self._require_provider_unlocked(provider_id)
            runtime.consecutive_failures = runtime.config.failure_threshold
            runtime.consecutive_successes = 0
            runtime.total_failures += 1
            runtime.state = ProviderState.UNHEALTHY
            runtime.last_failure_at_utc = self._utc_now()
            runtime.updated_at_utc = self._utc_now()
            self._enter_cooldown_unlocked(runtime)
            is_active = runtime.active

        self._publish(
            "failover.provider_unhealthy",
            {
                "provider_id": provider_id,
                "reason": reason.value,
                "message": message,
            },
        )

        if is_active and self.config.automatic_failover:
            return self.evaluate_failover()
        return None

    def active_provider(self) -> ProviderSnapshot | None:
        with self._lock:
            if self._active_provider_id is None:
                return None
            return self._snapshot_unlocked(
                self._require_provider_unlocked(self._active_provider_id)
            )

    def get_provider(self, provider_id: str) -> ProviderSnapshot:
        with self._lock:
            runtime = self._require_provider_unlocked(provider_id)
            self._refresh_cooldown_unlocked(runtime, time.monotonic())
            return self._snapshot_unlocked(runtime)

    def list_providers(self) -> tuple[ProviderSnapshot, ...]:
        with self._lock:
            now = time.monotonic()
            snapshots = []
            for runtime in self._providers.values():
                self._refresh_cooldown_unlocked(runtime, now)
                snapshots.append(self._snapshot_unlocked(runtime))

        return tuple(
            sorted(
                snapshots,
                key=lambda item: (item.priority, item.name),
            )
        )

    def history(self) -> tuple[FailoverEvent, ...]:
        with self._lock:
            return tuple(self._history)

    def metrics(self) -> dict[str, Any]:
        with self._lock:
            metrics = dict(self._metrics)
            providers = tuple(self._providers.values())

        state_counts = {
            state.value: sum(1 for provider in providers if provider.state == state)
            for state in ProviderState
        }
        metrics["registered_providers"] = len(providers)
        metrics["active_provider_id"] = self._active_provider_id
        metrics["provider_states"] = state_counts
        return metrics

    def health_check(self) -> dict[str, Any]:
        active = self.active_provider()
        providers = self.list_providers()
        healthy_count = sum(
            1
            for provider in providers
            if provider.state == ProviderState.HEALTHY
        )
        degraded_count = sum(
            1
            for provider in providers
            if provider.state == ProviderState.DEGRADED
        )

        return {
            "healthy": active is not None
            and active.state in {ProviderState.HEALTHY, ProviderState.DEGRADED},
            "degraded": active is not None
            and active.state == ProviderState.DEGRADED,
            "active_provider": active.to_dict() if active is not None else None,
            "healthy_provider_count": healthy_count,
            "degraded_provider_count": degraded_count,
            "registered_provider_count": len(providers),
            "metrics": self.metrics(),
        }

    def _apply_health_result_unlocked(
        self,
        runtime: _ProviderRuntime,
        result: HealthCheckResult,
    ) -> None:
        now = time.monotonic()
        runtime.last_health_check_monotonic = now
        runtime.last_health_check_at_utc = self._utc_now()
        runtime.updated_at_utc = self._utc_now()

        if result.healthy:
            runtime.total_successes += 1
            runtime.consecutive_successes += 1
            runtime.consecutive_failures = 0
            runtime.last_success_at_utc = self._utc_now()

            if runtime.healthy_since_monotonic is None:
                runtime.healthy_since_monotonic = now

            if runtime.consecutive_successes >= runtime.config.recovery_threshold:
                runtime.state = (
                    ProviderState.DEGRADED
                    if result.degraded
                    else ProviderState.HEALTHY
                )
                runtime.cooldown_until_monotonic = None
                runtime.cooldown_until_utc = None
            elif runtime.state in {
                ProviderState.UNKNOWN,
                ProviderState.UNHEALTHY,
                ProviderState.COOLDOWN,
            }:
                runtime.state = ProviderState.DEGRADED
        else:
            runtime.total_failures += 1
            runtime.consecutive_failures += 1
            runtime.consecutive_successes = 0
            runtime.healthy_since_monotonic = None
            runtime.last_failure_at_utc = self._utc_now()

            if runtime.consecutive_failures >= runtime.config.failure_threshold:
                runtime.state = ProviderState.UNHEALTHY
                self._enter_cooldown_unlocked(runtime)
            else:
                runtime.state = ProviderState.DEGRADED

    def _enter_cooldown_unlocked(self, runtime: _ProviderRuntime) -> None:
        if runtime.config.cooldown_seconds <= 0:
            return
        runtime.state = ProviderState.COOLDOWN
        runtime.cooldown_until_monotonic = (
            time.monotonic() + runtime.config.cooldown_seconds
        )
        runtime.cooldown_until_utc = datetime.fromtimestamp(
            time.time() + runtime.config.cooldown_seconds,
            tz=timezone.utc,
        ).isoformat()

    def _refresh_cooldown_unlocked(
        self,
        runtime: _ProviderRuntime,
        now: float,
    ) -> None:
        if runtime.state != ProviderState.COOLDOWN:
            return
        if runtime.cooldown_until_monotonic is None:
            return
        if now >= runtime.cooldown_until_monotonic:
            runtime.state = ProviderState.UNKNOWN
            runtime.cooldown_until_monotonic = None
            runtime.cooldown_until_utc = None
            runtime.consecutive_failures = 0
            runtime.consecutive_successes = 0
            runtime.updated_at_utc = self._utc_now()

    @staticmethod
    def _normalize_health_result(
        *,
        provider_id: str,
        raw: HealthCheckResult | bool | Mapping[str, Any],
        latency_seconds: float,
    ) -> HealthCheckResult:
        if isinstance(raw, HealthCheckResult):
            return raw
        if isinstance(raw, bool):
            return HealthCheckResult(
                provider_id=provider_id,
                healthy=raw,
                degraded=False,
                message="health check passed" if raw else "health check failed",
                latency_seconds=latency_seconds,
            )
        if isinstance(raw, Mapping):
            return HealthCheckResult(
                provider_id=provider_id,
                healthy=bool(raw.get("healthy", True)),
                degraded=bool(raw.get("degraded", False)),
                message=str(raw.get("message", "")),
                latency_seconds=float(
                    raw.get("latency_seconds", latency_seconds)
                ),
                details=dict(raw),
            )
        raise TypeError("unsupported health check result type")

    def _activate_provider(self, runtime: _ProviderRuntime) -> bool:
        if runtime.activator is None:
            return True
        try:
            response = runtime.activator(runtime.config.provider_id)
        except Exception:
            return False
        return self._normalize_hook_response(response)

    def _deactivate_provider(self, runtime: _ProviderRuntime) -> bool:
        if runtime.deactivator is None:
            return True
        try:
            response = runtime.deactivator(runtime.config.provider_id)
        except Exception:
            return False
        return self._normalize_hook_response(response)

    @staticmethod
    def _normalize_hook_response(
        response: bool | Mapping[str, Any] | None,
    ) -> bool:
        if response is None:
            return True
        if isinstance(response, bool):
            return response
        if isinstance(response, Mapping):
            return bool(response.get("success", True))
        return False

    def _snapshot_unlocked(
        self,
        runtime: _ProviderRuntime,
    ) -> ProviderSnapshot:
        return ProviderSnapshot(
            provider_id=runtime.config.provider_id,
            name=runtime.config.name,
            priority=runtime.config.priority,
            role=runtime.config.role,
            state=runtime.state,
            enabled=runtime.config.enabled,
            active=runtime.active,
            consecutive_failures=runtime.consecutive_failures,
            consecutive_successes=runtime.consecutive_successes,
            total_failures=runtime.total_failures,
            total_successes=runtime.total_successes,
            last_health_check_at_utc=runtime.last_health_check_at_utc,
            last_failure_at_utc=runtime.last_failure_at_utc,
            last_success_at_utc=runtime.last_success_at_utc,
            cooldown_until_utc=runtime.cooldown_until_utc,
            updated_at_utc=runtime.updated_at_utc,
            metadata=dict(runtime.config.metadata),
        )

    def _record_event(
        self,
        *,
        from_provider_id: str | None,
        to_provider_id: str | None,
        reason: FailoverReason,
        status: FailoverStatus,
        message: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> FailoverEvent:
        with self._lock:
            event = self._make_event_unlocked(
                from_provider_id=from_provider_id,
                to_provider_id=to_provider_id,
                reason=reason,
                status=status,
                message=message,
                metadata=metadata,
            )
            self._history.append(event)
            if len(self._history) > self.config.retain_history:
                del self._history[: len(self._history) - self.config.retain_history]

        self._publish("failover.event", event.to_dict())
        return event

    def _make_event_unlocked(
        self,
        *,
        from_provider_id: str | None,
        to_provider_id: str | None,
        reason: FailoverReason,
        status: FailoverStatus,
        message: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> FailoverEvent:
        return FailoverEvent(
            event_id=str(uuid.uuid4()),
            from_provider_id=from_provider_id,
            to_provider_id=to_provider_id,
            reason=reason,
            status=status,
            occurred_at_utc=self._utc_now(),
            message=message,
            metadata=dict(metadata or {}),
        )

    def _require_provider_unlocked(
        self,
        provider_id: str,
    ) -> _ProviderRuntime:
        runtime = self._providers.get(provider_id)
        if runtime is None:
            raise KeyError(f"unknown provider: {provider_id}")
        return runtime

    def _publish(self, event_type: str, payload: Any) -> None:
        if self.config.publish_events and self.event_publisher is not None:
            self.event_publisher.publish_event(
                event_type,
                payload,
                source="failover_manager",
            )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
