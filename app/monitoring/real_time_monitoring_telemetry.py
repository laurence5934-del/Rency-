from __future__ import annotations

import json
import math
import os
import platform
import statistics
import threading
import time
import traceback
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Event, RLock, Thread
from typing import Any, Callable, Deque, Iterable, Iterator, Mapping, Protocol, Sequence


class MetricType(str, Enum):
    COUNTER = "COUNTER"
    GAUGE = "GAUGE"
    HISTOGRAM = "HISTOGRAM"
    TIMER = "TIMER"


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertState(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True, slots=True)
class MetricSample:
    name: str
    value: float
    metric_type: MetricType
    timestamp_utc: str
    labels: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("metric name cannot be empty")
        if not math.isfinite(self.value):
            raise ValueError("metric value must be finite")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["metric_type"] = self.metric_type.value
        return data


@dataclass(frozen=True, slots=True)
class HistogramSnapshot:
    count: int
    minimum: float | None
    maximum: float | None
    mean: float | None
    median: float | None
    p50: float | None
    p95: float | None
    p99: float | None
    sum: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    component: str
    status: HealthStatus
    score: float
    message: str
    checked_at_utc: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.component.strip():
            raise ValueError("component cannot be empty")
        if not 0.0 <= self.score <= 100.0:
            raise ValueError("health score must be between 0 and 100")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True, slots=True)
class Heartbeat:
    component: str
    timestamp_utc: str
    monotonic_time: float
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Alert:
    alert_id: str
    source: str
    code: str
    severity: AlertSeverity
    state: AlertState
    message: str
    created_at_utc: str
    updated_at_utc: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.alert_id.strip():
            raise ValueError("alert_id cannot be empty")
        if not self.source.strip():
            raise ValueError("alert source cannot be empty")
        if not self.code.strip():
            raise ValueError("alert code cannot be empty")
        if not self.message.strip():
            raise ValueError("alert message cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        data["state"] = self.state.value
        return data


@dataclass(frozen=True, slots=True)
class TelemetrySnapshot:
    timestamp_utc: str
    metrics: Mapping[str, Any]
    component_health: tuple[ComponentHealth, ...]
    open_alerts: tuple[Alert, ...]
    system: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "metrics": dict(self.metrics),
            "component_health": [item.to_dict() for item in self.component_health],
            "open_alerts": [item.to_dict() for item in self.open_alerts],
            "system": dict(self.system),
        }


@dataclass(slots=True)
class AlertRule:
    metric_name: str
    threshold: float
    severity: AlertSeverity
    comparison: str = ">="
    labels: Mapping[str, str] = field(default_factory=dict)
    code: str | None = None
    message: str | None = None
    cooldown_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.metric_name.strip():
            raise ValueError("metric_name cannot be empty")
        if self.comparison not in {">", ">=", "<", "<=", "==", "!="}:
            raise ValueError("unsupported comparison operator")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds cannot be negative")

    def triggered(self, value: float) -> bool:
        if self.comparison == ">":
            return value > self.threshold
        if self.comparison == ">=":
            return value >= self.threshold
        if self.comparison == "<":
            return value < self.threshold
        if self.comparison == "<=":
            return value <= self.threshold
        if self.comparison == "==":
            return value == self.threshold
        return value != self.threshold


@dataclass(slots=True)
class TelemetryConfig:
    max_samples_per_metric: int = 2_000
    max_snapshots: int = 1_000
    heartbeat_timeout_seconds: float = 30.0
    collection_interval_seconds: float = 5.0
    enable_background_collection: bool = False
    enable_system_metrics: bool = True
    publish_events: bool = True
    structured_log_path: str | None = None

    def __post_init__(self) -> None:
        if self.max_samples_per_metric < 10:
            raise ValueError("max_samples_per_metric must be at least 10")
        if self.max_snapshots < 1:
            raise ValueError("max_snapshots must be positive")
        if self.heartbeat_timeout_seconds <= 0:
            raise ValueError("heartbeat_timeout_seconds must be positive")
        if self.collection_interval_seconds <= 0:
            raise ValueError("collection_interval_seconds must be positive")


class EventPublisher(Protocol):
    def publish_event(
        self,
        event_type: str,
        payload: Any = None,
        *,
        source: str = "unknown",
        **kwargs: Any,
    ) -> Any: ...


class HealthProbe(Protocol):
    def __call__(self) -> Mapping[str, Any] | ComponentHealth: ...


class AlertSink(Protocol):
    def __call__(self, alert: Alert) -> None: ...


class StructuredLogger:
    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path) if path else None
        self._lock = RLock()
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        level: str,
        message: str,
        *,
        event: str | None = None,
        fields: Mapping[str, Any] | None = None,
    ) -> None:
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "message": message,
            "event": event,
            "thread": threading.current_thread().name,
            "fields": dict(fields or {}),
        }
        line = json.dumps(record, default=str, separators=(",", ":"))
        if self.path is None:
            return
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")


class RealTimeMonitoringTelemetry:
    """
    Version 10.0.7 - Real-Time Monitoring & Telemetry.

    Provides thread-safe counters, gauges, timers, histograms, heartbeats,
    component health probes, alert rules, structured logging, snapshots,
    event publishing, and Prometheus-compatible text export.
    """

    def __init__(
        self,
        *,
        config: TelemetryConfig | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self.config = config or TelemetryConfig()
        self.event_publisher = event_publisher
        self.logger = StructuredLogger(self.config.structured_log_path)

        self._lock = RLock()
        self._samples: dict[str, Deque[MetricSample]] = {}
        self._metric_types: dict[str, MetricType] = {}
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._heartbeats: dict[str, Heartbeat] = {}
        self._health_probes: dict[str, HealthProbe] = {}
        self._alerts: dict[str, Alert] = {}
        self._alert_rules: list[AlertRule] = []
        self._rule_last_triggered: dict[str, float] = {}
        self._alert_sinks: list[AlertSink] = []
        self._snapshots: Deque[TelemetrySnapshot] = deque(
            maxlen=self.config.max_snapshots
        )

        self._started_monotonic = time.monotonic()
        self._stop_event = Event()
        self._collector_thread: Thread | None = None

        if self.config.enable_background_collection:
            self.start()

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _metric_key(name: str, labels: Mapping[str, str] | None = None) -> str:
        if not labels:
            return name
        encoded = ",".join(f"{key}={labels[key]}" for key in sorted(labels))
        return f"{name}{{{encoded}}}"

    def increment(
        self,
        name: str,
        amount: float = 1.0,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> float:
        if amount < 0:
            raise ValueError("counter increment cannot be negative")
        key = self._metric_key(name, labels)
        with self._lock:
            self._assert_metric_type(key, MetricType.COUNTER)
            self._counters[key] += amount
            value = self._counters[key]
            self._record_sample_unlocked(
                name,
                value,
                MetricType.COUNTER,
                labels or {},
            )
        self._evaluate_rules(name, value, labels or {})
        return value

    def set_gauge(
        self,
        name: str,
        value: float,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        if not math.isfinite(value):
            raise ValueError("gauge value must be finite")
        key = self._metric_key(name, labels)
        with self._lock:
            self._assert_metric_type(key, MetricType.GAUGE)
            self._gauges[key] = value
            self._record_sample_unlocked(
                name,
                value,
                MetricType.GAUGE,
                labels or {},
            )
        self._evaluate_rules(name, value, labels or {})

    def observe(
        self,
        name: str,
        value: float,
        *,
        metric_type: MetricType = MetricType.HISTOGRAM,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        if metric_type not in {MetricType.HISTOGRAM, MetricType.TIMER}:
            raise ValueError("observe only accepts HISTOGRAM or TIMER")
        if not math.isfinite(value):
            raise ValueError("observed value must be finite")
        key = self._metric_key(name, labels)
        with self._lock:
            self._assert_metric_type(key, metric_type)
            self._record_sample_unlocked(
                name,
                value,
                metric_type,
                labels or {},
            )
        self._evaluate_rules(name, value, labels or {})

    @contextmanager
    def timer(
        self,
        name: str,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        except Exception:
            self.increment(
                f"{name}_errors_total",
                labels=labels,
            )
            raise
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            self.observe(
                name,
                elapsed_ms,
                metric_type=MetricType.TIMER,
                labels=labels,
            )

    def measure(
        self,
        name: str,
        function: Callable[..., Any],
        *args: Any,
        labels: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> Any:
        with self.timer(name, labels=labels):
            return function(*args, **kwargs)

    def record_heartbeat(
        self,
        component: str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> Heartbeat:
        if not component.strip():
            raise ValueError("component cannot be empty")
        heartbeat = Heartbeat(
            component=component,
            timestamp_utc=self._utc_now(),
            monotonic_time=time.monotonic(),
            metadata=dict(metadata or {}),
        )
        with self._lock:
            self._heartbeats[component] = heartbeat
        self.set_gauge(
            "component_heartbeat_age_seconds",
            0.0,
            labels={"component": component},
        )
        return heartbeat

    def register_health_probe(
        self,
        component: str,
        probe: HealthProbe,
    ) -> None:
        if not component.strip():
            raise ValueError("component cannot be empty")
        with self._lock:
            self._health_probes[component] = probe

    def unregister_health_probe(self, component: str) -> bool:
        with self._lock:
            return self._health_probes.pop(component, None) is not None

    def check_component(self, component: str) -> ComponentHealth:
        with self._lock:
            probe = self._health_probes.get(component)
            heartbeat = self._heartbeats.get(component)

        heartbeat_age = None
        heartbeat_status = HealthStatus.UNKNOWN
        if heartbeat is not None:
            heartbeat_age = max(0.0, time.monotonic() - heartbeat.monotonic_time)
            heartbeat_status = (
                HealthStatus.HEALTHY
                if heartbeat_age <= self.config.heartbeat_timeout_seconds
                else HealthStatus.UNHEALTHY
            )
            self.set_gauge(
                "component_heartbeat_age_seconds",
                heartbeat_age,
                labels={"component": component},
            )

        if probe is None:
            if heartbeat is None:
                return ComponentHealth(
                    component=component,
                    status=HealthStatus.UNKNOWN,
                    score=0.0,
                    message="no health probe or heartbeat registered",
                    checked_at_utc=self._utc_now(),
                )
            score = 100.0 if heartbeat_status == HealthStatus.HEALTHY else 0.0
            return ComponentHealth(
                component=component,
                status=heartbeat_status,
                score=score,
                message=f"heartbeat age: {heartbeat_age:.3f}s",
                checked_at_utc=self._utc_now(),
                details={"heartbeat_age_seconds": heartbeat_age},
            )

        try:
            result = probe()
            if isinstance(result, ComponentHealth):
                health = result
            else:
                healthy = bool(result.get("healthy", False))
                degraded = bool(result.get("degraded", False))
                if healthy and not degraded:
                    status = HealthStatus.HEALTHY
                    score = float(result.get("score", 100.0))
                elif healthy or degraded:
                    status = HealthStatus.DEGRADED
                    score = float(result.get("score", 60.0))
                else:
                    status = HealthStatus.UNHEALTHY
                    score = float(result.get("score", 0.0))
                health = ComponentHealth(
                    component=component,
                    status=status,
                    score=max(0.0, min(100.0, score)),
                    message=str(result.get("message", status.value.lower())),
                    checked_at_utc=self._utc_now(),
                    details=dict(result),
                )

            if heartbeat_status == HealthStatus.UNHEALTHY:
                return ComponentHealth(
                    component=component,
                    status=HealthStatus.UNHEALTHY,
                    score=min(health.score, 25.0),
                    message="component heartbeat timed out",
                    checked_at_utc=self._utc_now(),
                    details={
                        **dict(health.details),
                        "heartbeat_age_seconds": heartbeat_age,
                    },
                )
            return health
        except Exception as exc:
            self.capture_exception(
                exc,
                source=component,
                context={"operation": "health_probe"},
            )
            return ComponentHealth(
                component=component,
                status=HealthStatus.UNHEALTHY,
                score=0.0,
                message=f"health probe failed: {exc}",
                checked_at_utc=self._utc_now(),
                details={"exception_type": type(exc).__name__},
            )

    def check_all_components(self) -> tuple[ComponentHealth, ...]:
        with self._lock:
            components = sorted(
                set(self._health_probes) | set(self._heartbeats)
            )
        results = tuple(self.check_component(component) for component in components)
        for result in results:
            self.set_gauge(
                "component_health_score",
                result.score,
                labels={"component": result.component},
            )
        return results

    def add_alert_rule(self, rule: AlertRule) -> None:
        with self._lock:
            self._alert_rules.append(rule)

    def add_alert_sink(self, sink: AlertSink) -> None:
        with self._lock:
            self._alert_sinks.append(sink)

    def raise_alert(
        self,
        *,
        source: str,
        code: str,
        severity: AlertSeverity,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> Alert:
        now = self._utc_now()
        alert_id = f"{source}:{code}"
        with self._lock:
            existing = self._alerts.get(alert_id)
            created_at = existing.created_at_utc if existing else now
            alert = Alert(
                alert_id=alert_id,
                source=source,
                code=code,
                severity=severity,
                state=AlertState.OPEN,
                message=message,
                created_at_utc=created_at,
                updated_at_utc=now,
                details=dict(details or {}),
            )
            self._alerts[alert_id] = alert
            sinks = tuple(self._alert_sinks)

        self.logger.log(
            severity.value,
            message,
            event="alert.opened",
            fields=alert.to_dict(),
        )
        self._publish("telemetry.alert_opened", alert.to_dict())
        for sink in sinks:
            try:
                sink(alert)
            except Exception as exc:
                self.logger.log(
                    "ERROR",
                    f"alert sink failed: {exc}",
                    event="alert.sink_failed",
                )
        return alert

    def acknowledge_alert(self, alert_id: str) -> Alert:
        return self._set_alert_state(alert_id, AlertState.ACKNOWLEDGED)

    def resolve_alert(self, alert_id: str) -> Alert:
        alert = self._set_alert_state(alert_id, AlertState.RESOLVED)
        self._publish("telemetry.alert_resolved", alert.to_dict())
        return alert

    def list_alerts(
        self,
        *,
        state: AlertState | None = None,
        severity: AlertSeverity | None = None,
    ) -> tuple[Alert, ...]:
        with self._lock:
            alerts = tuple(self._alerts.values())
        if state is not None:
            alerts = tuple(item for item in alerts if item.state == state)
        if severity is not None:
            alerts = tuple(item for item in alerts if item.severity == severity)
        return tuple(sorted(alerts, key=lambda item: item.updated_at_utc))

    def capture_exception(
        self,
        exception: BaseException,
        *,
        source: str,
        context: Mapping[str, Any] | None = None,
    ) -> Alert:
        details = {
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "traceback": "".join(
                traceback.format_exception(
                    type(exception),
                    exception,
                    exception.__traceback__,
                )
            ),
            "context": dict(context or {}),
        }
        self.increment(
            "exceptions_total",
            labels={
                "source": source,
                "type": type(exception).__name__,
            },
        )
        return self.raise_alert(
            source=source,
            code=f"exception.{type(exception).__name__}",
            severity=AlertSeverity.CRITICAL,
            message=str(exception) or type(exception).__name__,
            details=details,
        )

    def metric_summary(
        self,
        name: str,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        key = self._metric_key(name, labels)
        with self._lock:
            metric_type = self._metric_types.get(key)
            samples = tuple(self._samples.get(key, ()))
            counter = self._counters.get(key)
            gauge = self._gauges.get(key)

        if metric_type is None:
            raise KeyError(f"unknown metric: {key}")

        result: dict[str, Any] = {
            "name": name,
            "key": key,
            "type": metric_type.value,
            "sample_count": len(samples),
            "latest": samples[-1].value if samples else None,
        }

        if metric_type == MetricType.COUNTER:
            result["value"] = counter
        elif metric_type == MetricType.GAUGE:
            result["value"] = gauge
        else:
            result["histogram"] = self._histogram(samples).to_dict()
        return result

    def collect_snapshot(self) -> TelemetrySnapshot:
        if self.config.enable_system_metrics:
            self._collect_system_metrics()

        health = self.check_all_components()
        with self._lock:
            metric_keys = sorted(self._metric_types)
        metrics = {}
        for key in metric_keys:
            name, labels = self._split_metric_key(key)
            try:
                metrics[key] = self.metric_summary(name, labels=labels)
            except KeyError:
                continue

        snapshot = TelemetrySnapshot(
            timestamp_utc=self._utc_now(),
            metrics=metrics,
            component_health=health,
            open_alerts=self.list_alerts(state=AlertState.OPEN),
            system=self._system_info(),
        )
        with self._lock:
            self._snapshots.append(snapshot)
        self._publish("telemetry.snapshot", snapshot.to_dict())
        return snapshot

    def snapshots(self) -> tuple[TelemetrySnapshot, ...]:
        with self._lock:
            return tuple(self._snapshots)

    def overall_health(self) -> ComponentHealth:
        health = self.check_all_components()
        open_alerts = self.list_alerts(state=AlertState.OPEN)

        if not health:
            base_score = 100.0
            status = HealthStatus.HEALTHY
        else:
            base_score = sum(item.score for item in health) / len(health)
            if any(item.status == HealthStatus.UNHEALTHY for item in health):
                status = HealthStatus.UNHEALTHY
            elif any(item.status == HealthStatus.DEGRADED for item in health):
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY

        critical_count = sum(
            1 for item in open_alerts if item.severity == AlertSeverity.CRITICAL
        )
        warning_count = sum(
            1 for item in open_alerts if item.severity == AlertSeverity.WARNING
        )
        score = max(0.0, base_score - critical_count * 25 - warning_count * 10)

        if critical_count:
            status = HealthStatus.UNHEALTHY
        elif warning_count and status == HealthStatus.HEALTHY:
            status = HealthStatus.DEGRADED

        return ComponentHealth(
            component="platform",
            status=status,
            score=score,
            message=(
                f"{len(health)} components, "
                f"{critical_count} critical alerts, "
                f"{warning_count} warning alerts"
            ),
            checked_at_utc=self._utc_now(),
            details={
                "component_count": len(health),
                "critical_alerts": critical_count,
                "warning_alerts": warning_count,
            },
        )

    def export_prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            metric_keys = sorted(self._metric_types)

        for key in metric_keys:
            name, labels = self._split_metric_key(key)
            safe_name = self._prometheus_name(name)
            label_text = self._prometheus_labels(labels)
            summary = self.metric_summary(name, labels=labels)
            metric_type = summary["type"]

            if metric_type in {
                MetricType.COUNTER.value,
                MetricType.GAUGE.value,
            }:
                lines.append(f"{safe_name}{label_text} {summary['value']}")
                continue

            histogram = summary["histogram"]
            lines.append(f"{safe_name}_count{label_text} {histogram['count']}")
            lines.append(f"{safe_name}_sum{label_text} {histogram['sum']}")
            for suffix in ("p50", "p95", "p99", "minimum", "maximum", "mean"):
                value = histogram[suffix]
                if value is not None:
                    lines.append(f"{safe_name}_{suffix}{label_text} {value}")

        return "\n".join(lines) + ("\n" if lines else "")

    def start(self) -> None:
        with self._lock:
            if self._collector_thread and self._collector_thread.is_alive():
                return
            self._stop_event.clear()
            self._collector_thread = Thread(
                target=self._collector_loop,
                name="telemetry-collector",
                daemon=True,
            )
            self._collector_thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        thread = self._collector_thread
        if thread is not None:
            thread.join(timeout=timeout)

    def close(self) -> None:
        self.stop()

    def _collector_loop(self) -> None:
        while not self._stop_event.wait(self.config.collection_interval_seconds):
            try:
                self.collect_snapshot()
            except Exception as exc:
                self.capture_exception(
                    exc,
                    source="telemetry_collector",
                    context={"operation": "collect_snapshot"},
                )

    def _collect_system_metrics(self) -> None:
        uptime = time.monotonic() - self._started_monotonic
        self.set_gauge("process_uptime_seconds", uptime)
        self.set_gauge("process_thread_count", float(threading.active_count()))

        try:
            load = os.getloadavg()
        except (AttributeError, OSError):
            load = None
        if load is not None:
            self.set_gauge("system_load_1m", float(load[0]))
            self.set_gauge("system_load_5m", float(load[1]))
            self.set_gauge("system_load_15m", float(load[2]))

    def _system_info(self) -> dict[str, Any]:
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
            "pid": os.getpid(),
            "thread_count": threading.active_count(),
            "uptime_seconds": time.monotonic() - self._started_monotonic,
        }

    def _evaluate_rules(
        self,
        metric_name: str,
        value: float,
        labels: Mapping[str, str],
    ) -> None:
        with self._lock:
            rules = tuple(self._alert_rules)

        now = time.monotonic()
        for rule in rules:
            if rule.metric_name != metric_name:
                continue
            if any(labels.get(key) != expected for key, expected in rule.labels.items()):
                continue

            rule_key = self._rule_key(rule)
            last_triggered = self._rule_last_triggered.get(rule_key, 0.0)
            triggered = rule.triggered(value)

            if triggered and now - last_triggered >= rule.cooldown_seconds:
                self._rule_last_triggered[rule_key] = now
                code = rule.code or f"threshold.{metric_name}"
                message = rule.message or (
                    f"{metric_name} value {value} triggered "
                    f"{rule.comparison} {rule.threshold}"
                )
                self.raise_alert(
                    source="telemetry",
                    code=code,
                    severity=rule.severity,
                    message=message,
                    details={
                        "metric_name": metric_name,
                        "value": value,
                        "threshold": rule.threshold,
                        "comparison": rule.comparison,
                        "labels": dict(labels),
                    },
                )
            elif not triggered:
                alert_id = f"telemetry:{rule.code or f'threshold.{metric_name}'}"
                with self._lock:
                    existing = self._alerts.get(alert_id)
                if existing and existing.state != AlertState.RESOLVED:
                    self.resolve_alert(alert_id)

    def _record_sample_unlocked(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        labels: Mapping[str, str],
    ) -> None:
        key = self._metric_key(name, labels)
        samples = self._samples.setdefault(
            key,
            deque(maxlen=self.config.max_samples_per_metric),
        )
        samples.append(
            MetricSample(
                name=name,
                value=value,
                metric_type=metric_type,
                timestamp_utc=self._utc_now(),
                labels=dict(labels),
            )
        )

    def _assert_metric_type(self, key: str, metric_type: MetricType) -> None:
        current = self._metric_types.get(key)
        if current is not None and current != metric_type:
            raise TypeError(
                f"metric {key} already registered as {current.value}"
            )
        self._metric_types[key] = metric_type

    def _set_alert_state(
        self,
        alert_id: str,
        state: AlertState,
    ) -> Alert:
        with self._lock:
            existing = self._alerts.get(alert_id)
            if existing is None:
                raise KeyError(f"unknown alert: {alert_id}")
            updated = Alert(
                alert_id=existing.alert_id,
                source=existing.source,
                code=existing.code,
                severity=existing.severity,
                state=state,
                message=existing.message,
                created_at_utc=existing.created_at_utc,
                updated_at_utc=self._utc_now(),
                details=existing.details,
            )
            self._alerts[alert_id] = updated
        return updated

    @staticmethod
    def _histogram(samples: Sequence[MetricSample]) -> HistogramSnapshot:
        values = sorted(sample.value for sample in samples)
        if not values:
            return HistogramSnapshot(
                count=0,
                minimum=None,
                maximum=None,
                mean=None,
                median=None,
                p50=None,
                p95=None,
                p99=None,
                sum=0.0,
            )
        return HistogramSnapshot(
            count=len(values),
            minimum=values[0],
            maximum=values[-1],
            mean=statistics.fmean(values),
            median=statistics.median(values),
            p50=RealTimeMonitoringTelemetry._percentile(values, 0.50),
            p95=RealTimeMonitoringTelemetry._percentile(values, 0.95),
            p99=RealTimeMonitoringTelemetry._percentile(values, 0.99),
            sum=sum(values),
        )

    @staticmethod
    def _percentile(values: Sequence[float], quantile: float) -> float:
        if len(values) == 1:
            return values[0]
        position = (len(values) - 1) * quantile
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return values[lower]
        weight = position - lower
        return values[lower] * (1.0 - weight) + values[upper] * weight

    @staticmethod
    def _split_metric_key(
        key: str,
    ) -> tuple[str, Mapping[str, str] | None]:
        if "{" not in key or not key.endswith("}"):
            return key, None
        name, raw = key[:-1].split("{", 1)
        labels: dict[str, str] = {}
        if raw:
            for item in raw.split(","):
                label_key, label_value = item.split("=", 1)
                labels[label_key] = label_value
        return name, labels

    @staticmethod
    def _prometheus_name(name: str) -> str:
        return "".join(
            character if character.isalnum() or character in "_:" else "_"
            for character in name
        )

    @staticmethod
    def _prometheus_labels(
        labels: Mapping[str, str] | None,
    ) -> str:
        if not labels:
            return ""
        encoded = ",".join(
            f'{key}="{str(value).replace(chr(34), chr(92) + chr(34))}"'
            for key, value in sorted(labels.items())
        )
        return "{" + encoded + "}"

    @staticmethod
    def _rule_key(rule: AlertRule) -> str:
        labels = ",".join(
            f"{key}={value}" for key, value in sorted(rule.labels.items())
        )
        return (
            f"{rule.metric_name}|{rule.comparison}|{rule.threshold}|"
            f"{labels}|{rule.code or ''}"
        )

    def _publish(self, event_type: str, payload: Any) -> None:
        if self.config.publish_events and self.event_publisher is not None:
            self.event_publisher.publish_event(
                event_type,
                payload,
                source="real_time_monitoring_telemetry",
            )


class TelemetryDecorator:
    """
    Optional helper for instrumenting existing callables without changing them.
    """

    def __init__(
        self,
        telemetry: RealTimeMonitoringTelemetry,
        *,
        metric_name: str,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        self.telemetry = telemetry
        self.metric_name = metric_name
        self.labels = dict(labels or {})

    def __call__(self, function: Callable[..., Any]) -> Callable[..., Any]:
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            return self.telemetry.measure(
                self.metric_name,
                function,
                *args,
                labels=self.labels,
                **kwargs,
            )
        return wrapped
