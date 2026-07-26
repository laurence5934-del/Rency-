from __future__ import annotations

import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Event, RLock
from typing import Any, Callable, Mapping, Protocol, Sequence


class ShutdownPhase(str, Enum):
    PREPARE = "PREPARE"
    QUIESCE = "QUIESCE"
    DRAIN = "DRAIN"
    CHECKPOINT = "CHECKPOINT"
    FLUSH = "FLUSH"
    DISCONNECT = "DISCONNECT"
    FINALIZE = "FINALIZE"


class ShutdownStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    TIMED_OUT = "TIMED_OUT"
    FORCED = "FORCED"
    CANCELLED = "CANCELLED"


class ParticipantStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class GracefulShutdownConfig:
    overall_timeout_seconds: float = 120.0
    default_participant_timeout_seconds: float = 15.0
    max_parallel_workers: int = 4
    continue_on_error: bool = True
    force_on_timeout: bool = True
    create_final_checkpoint: bool = True
    publish_events: bool = True
    retain_reports: int = 100
    phase_order: tuple[ShutdownPhase, ...] = (
        ShutdownPhase.PREPARE,
        ShutdownPhase.QUIESCE,
        ShutdownPhase.DRAIN,
        ShutdownPhase.CHECKPOINT,
        ShutdownPhase.FLUSH,
        ShutdownPhase.DISCONNECT,
        ShutdownPhase.FINALIZE,
    )

    def __post_init__(self) -> None:
        if self.overall_timeout_seconds <= 0:
            raise ValueError("overall_timeout_seconds must be positive")
        if self.default_participant_timeout_seconds <= 0:
            raise ValueError(
                "default_participant_timeout_seconds must be positive"
            )
        if self.max_parallel_workers < 1:
            raise ValueError("max_parallel_workers must be positive")
        if self.retain_reports < 1:
            raise ValueError("retain_reports must be positive")
        if len(set(self.phase_order)) != len(self.phase_order):
            raise ValueError("phase_order cannot contain duplicate phases")


@dataclass(frozen=True, slots=True)
class ShutdownParticipantConfig:
    name: str
    phase: ShutdownPhase
    priority: int = 100
    timeout_seconds: float | None = None
    required: bool = True
    parallel_safe: bool = False
    dependencies: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("participant name cannot be empty")
        if self.priority < 0:
            raise ValueError("priority cannot be negative")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive when provided")
        if self.name in self.dependencies:
            raise ValueError("participant cannot depend on itself")


@dataclass(frozen=True, slots=True)
class ParticipantShutdownResult:
    name: str
    phase: ShutdownPhase
    status: ParticipantStatus
    started_at_utc: str | None
    completed_at_utc: str | None
    duration_seconds: float
    required: bool
    message: str
    exception_type: str | None = None
    exception_message: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["phase"] = self.phase.value
        data["status"] = self.status.value
        return data


@dataclass(frozen=True, slots=True)
class PhaseShutdownResult:
    phase: ShutdownPhase
    started_at_utc: str
    completed_at_utc: str
    duration_seconds: float
    succeeded: bool
    timed_out: bool
    participants: tuple[ParticipantShutdownResult, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["phase"] = self.phase.value
        data["participants"] = [
            participant.to_dict() for participant in self.participants
        ]
        return data


@dataclass(frozen=True, slots=True)
class ShutdownReport:
    shutdown_id: str
    reason: str
    status: ShutdownStatus
    started_at_utc: str
    completed_at_utc: str
    duration_seconds: float
    forced: bool
    phase_results: tuple[PhaseShutdownResult, ...]
    final_checkpoint_id: str | None
    message: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.status == ShutdownStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["phase_results"] = [
            phase.to_dict() for phase in self.phase_results
        ]
        data["succeeded"] = self.succeeded
        return data


class EventPublisher(Protocol):
    def publish_event(
        self,
        event_type: str,
        payload: Any = None,
        *,
        source: str = "unknown",
        **kwargs: Any,
    ) -> Any: ...


class CheckpointCreator(Protocol):
    def create_checkpoint(self, **kwargs: Any) -> Any: ...


class ShutdownParticipant(Protocol):
    def shutdown(self) -> Any: ...


class GracefulShutdownError(RuntimeError):
    pass


class ShutdownInProgressError(GracefulShutdownError):
    pass


class ShutdownCancelledError(GracefulShutdownError):
    pass


class ShutdownTimeoutError(GracefulShutdownError):
    pass


@dataclass(slots=True)
class _RegisteredParticipant:
    config: ShutdownParticipantConfig
    handler: Callable[[], Any]


class GracefulShutdownManager:
    """
    Version 10.0.8.6 - Graceful Shutdown.

    Coordinates dependency-aware, phased shutdown of platform components.
    Supports quiescing, queue draining, final checkpoint creation, event and
    telemetry flushing, broker and market-data disconnection, participant
    timeouts, forced fallback, cancellation, reports, metrics, event publishing,
    and thread-safe orchestration.
    """

    def __init__(
        self,
        *,
        config: GracefulShutdownConfig | None = None,
        event_publisher: EventPublisher | None = None,
        checkpoint_creator: CheckpointCreator | None = None,
    ) -> None:
        self.config = config or GracefulShutdownConfig()
        self.event_publisher = event_publisher
        self.checkpoint_creator = checkpoint_creator

        self._lock = RLock()
        self._participants: dict[str, _RegisteredParticipant] = {}
        self._reports: list[ShutdownReport] = []
        self._shutdown_requested = Event()
        self._force_requested = Event()
        self._cancel_requested = Event()
        self._status = ShutdownStatus.NOT_STARTED
        self._current_phase: ShutdownPhase | None = None
        self._active_shutdown_id: str | None = None

        self._metrics: dict[str, int | float] = {
            "shutdowns_started": 0,
            "shutdowns_completed": 0,
            "shutdowns_completed_with_errors": 0,
            "shutdowns_timed_out": 0,
            "shutdowns_forced": 0,
            "shutdowns_cancelled": 0,
            "participants_succeeded": 0,
            "participants_failed": 0,
            "participants_timed_out": 0,
            "participants_skipped": 0,
            "total_shutdown_duration_seconds": 0.0,
        }

    def register_participant(
        self,
        config: ShutdownParticipantConfig,
        handler: Callable[[], Any] | ShutdownParticipant,
    ) -> None:
        shutdown_callable: Callable[[], Any]

        if callable(handler):
            shutdown_callable = handler
        elif hasattr(handler, "shutdown") and callable(handler.shutdown):
            shutdown_callable = handler.shutdown
        else:
            raise TypeError(
                "handler must be callable or implement shutdown()"
            )

        with self._lock:
            if config.name in self._participants:
                raise KeyError(
                    f"shutdown participant already registered: {config.name}"
                )
            self._participants[config.name] = _RegisteredParticipant(
                config=config,
                handler=shutdown_callable,
            )
            self._validate_dependencies_unlocked()

    def unregister_participant(self, name: str) -> bool:
        with self._lock:
            if self._status == ShutdownStatus.IN_PROGRESS:
                raise ShutdownInProgressError(
                    "cannot unregister participants during shutdown"
                )
            return self._participants.pop(name, None) is not None

    def request_shutdown(self, *, force: bool = False) -> None:
        self._shutdown_requested.set()
        if force:
            self._force_requested.set()

    def request_force(self) -> None:
        self._force_requested.set()

    def cancel_shutdown(self) -> None:
        self._cancel_requested.set()

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown_requested.is_set()

    @property
    def force_requested(self) -> bool:
        return self._force_requested.is_set()

    @property
    def status(self) -> ShutdownStatus:
        with self._lock:
            return self._status

    @property
    def current_phase(self) -> ShutdownPhase | None:
        with self._lock:
            return self._current_phase

    def execute_shutdown(
        self,
        *,
        reason: str = "shutdown requested",
        metadata: Mapping[str, Any] | None = None,
    ) -> ShutdownReport:
        shutdown_id = str(uuid.uuid4())
        started_at = self._utc_now()
        started_monotonic = time.monotonic()
        overall_deadline = (
            started_monotonic + self.config.overall_timeout_seconds
        )

        with self._lock:
            if self._status == ShutdownStatus.IN_PROGRESS:
                raise ShutdownInProgressError(
                    "a shutdown operation is already in progress"
                )

            self._status = ShutdownStatus.IN_PROGRESS
            self._active_shutdown_id = shutdown_id
            self._current_phase = None
            self._shutdown_requested.set()
            self._cancel_requested.clear()
            self._metrics["shutdowns_started"] += 1

        self._publish(
            "shutdown.started",
            {
                "shutdown_id": shutdown_id,
                "reason": reason,
                "started_at_utc": started_at,
            },
        )

        phase_results: list[PhaseShutdownResult] = []
        final_checkpoint_id: str | None = None
        forced = self._force_requested.is_set()
        fatal_error = False
        timed_out = False
        cancelled = False

        try:
            for phase in self.config.phase_order:
                if self._cancel_requested.is_set():
                    cancelled = True
                    break

                if time.monotonic() >= overall_deadline:
                    timed_out = True
                    break

                with self._lock:
                    self._current_phase = phase

                self._publish(
                    "shutdown.phase_started",
                    {
                        "shutdown_id": shutdown_id,
                        "phase": phase.value,
                    },
                )

                if (
                    phase == ShutdownPhase.CHECKPOINT
                    and self.config.create_final_checkpoint
                    and self.checkpoint_creator is not None
                ):
                    checkpoint_result = self._create_final_checkpoint(
                        shutdown_id=shutdown_id,
                        reason=reason,
                    )
                    final_checkpoint_id = checkpoint_result[0]

                    if checkpoint_result[1] is not None:
                        phase_results.append(checkpoint_result[1])
                        if not checkpoint_result[1].succeeded:
                            fatal_error = True
                            if not self.config.continue_on_error:
                                break

                phase_result = self._execute_phase(
                    phase=phase,
                    overall_deadline=overall_deadline,
                )

                if phase_result.participants:
                    phase_results.append(phase_result)

                self._publish(
                    "shutdown.phase_completed",
                    phase_result.to_dict(),
                )

                if phase_result.timed_out:
                    timed_out = True
                    if not self.config.continue_on_error:
                        break

                required_failure = any(
                    participant.required
                    and participant.status
                    in {
                        ParticipantStatus.FAILED,
                        ParticipantStatus.TIMED_OUT,
                    }
                    for participant in phase_result.participants
                )

                if required_failure:
                    fatal_error = True
                    if not self.config.continue_on_error:
                        break

                if self._force_requested.is_set():
                    forced = True

            if timed_out and self.config.force_on_timeout:
                forced = True
                self._force_requested.set()

        finally:
            duration = time.monotonic() - started_monotonic

            if cancelled:
                status = ShutdownStatus.CANCELLED
                message = "shutdown was cancelled"
            elif timed_out:
                status = (
                    ShutdownStatus.FORCED
                    if forced
                    else ShutdownStatus.TIMED_OUT
                )
                message = (
                    "shutdown exceeded the overall timeout and forced fallback "
                    "was requested"
                    if forced
                    else "shutdown exceeded the overall timeout"
                )
            elif forced:
                status = ShutdownStatus.FORCED
                message = "shutdown completed using forced mode"
            elif fatal_error:
                status = ShutdownStatus.COMPLETED_WITH_ERRORS
                message = "shutdown completed with participant errors"
            else:
                status = ShutdownStatus.COMPLETED
                message = "shutdown completed successfully"

            report = ShutdownReport(
                shutdown_id=shutdown_id,
                reason=reason,
                status=status,
                started_at_utc=started_at,
                completed_at_utc=self._utc_now(),
                duration_seconds=duration,
                forced=forced,
                phase_results=tuple(phase_results),
                final_checkpoint_id=final_checkpoint_id,
                message=message,
                metadata=dict(metadata or {}),
            )

            self._store_report(report)

            with self._lock:
                self._status = status
                self._current_phase = None
                self._active_shutdown_id = None

            self._publish("shutdown.completed", report.to_dict())

        return report

    def _execute_phase(
        self,
        *,
        phase: ShutdownPhase,
        overall_deadline: float,
    ) -> PhaseShutdownResult:
        phase_started_at = self._utc_now()
        phase_started_monotonic = time.monotonic()

        participants = self._ordered_participants_for_phase(phase)

        if not participants:
            return PhaseShutdownResult(
                phase=phase,
                started_at_utc=phase_started_at,
                completed_at_utc=self._utc_now(),
                duration_seconds=0.0,
                succeeded=True,
                timed_out=False,
                participants=(),
            )

        completed_names: set[str] = set()
        results: list[ParticipantShutdownResult] = []
        timed_out = False

        pending = list(participants)

        while pending:
            if self._cancel_requested.is_set():
                for participant in pending:
                    results.append(
                        self._skipped_result(
                            participant,
                            "shutdown cancelled",
                        )
                    )
                break

            if time.monotonic() >= overall_deadline:
                timed_out = True
                for participant in pending:
                    results.append(
                        self._timeout_result(
                            participant,
                            "overall shutdown deadline exceeded",
                        )
                    )
                break

            ready: list[_RegisteredParticipant] = []
            blocked: list[_RegisteredParticipant] = []

            for participant in pending:
                dependencies = participant.config.dependencies
                if all(
                    dependency in completed_names
                    or dependency not in self._participants
                    for dependency in dependencies
                ):
                    ready.append(participant)
                else:
                    blocked.append(participant)

            if not ready:
                for participant in blocked:
                    results.append(
                        self._skipped_result(
                            participant,
                            "dependency requirements were not satisfied",
                        )
                    )
                break

            serial = [
                participant
                for participant in ready
                if not participant.config.parallel_safe
            ]
            parallel = [
                participant
                for participant in ready
                if participant.config.parallel_safe
            ]

            for participant in serial:
                result = self._execute_participant(
                    participant=participant,
                    overall_deadline=overall_deadline,
                )
                results.append(result)

                if result.status == ParticipantStatus.SUCCEEDED:
                    completed_names.add(participant.config.name)
                elif (
                    result.status == ParticipantStatus.TIMED_OUT
                    and participant.config.required
                ):
                    timed_out = True

                pending.remove(participant)

                if (
                    result.status
                    in {
                        ParticipantStatus.FAILED,
                        ParticipantStatus.TIMED_OUT,
                    }
                    and participant.config.required
                    and not self.config.continue_on_error
                ):
                    for remaining in pending:
                        results.append(
                            self._skipped_result(
                                remaining,
                                "shutdown stopped after required participant failure",
                            )
                        )
                    pending.clear()
                    break

            if not pending:
                break

            if parallel:
                parallel_results = self._execute_parallel_participants(
                    participants=parallel,
                    overall_deadline=overall_deadline,
                )
                results.extend(parallel_results)

                for participant, result in zip(parallel, parallel_results):
                    if result.status == ParticipantStatus.SUCCEEDED:
                        completed_names.add(participant.config.name)
                    elif (
                        result.status == ParticipantStatus.TIMED_OUT
                        and participant.config.required
                    ):
                        timed_out = True

                    if participant in pending:
                        pending.remove(participant)

                required_failure = any(
                    result.required
                    and result.status
                    in {
                        ParticipantStatus.FAILED,
                        ParticipantStatus.TIMED_OUT,
                    }
                    for result in parallel_results
                )

                if required_failure and not self.config.continue_on_error:
                    for remaining in pending:
                        results.append(
                            self._skipped_result(
                                remaining,
                                "shutdown stopped after required participant failure",
                            )
                        )
                    pending.clear()

        succeeded = all(
            result.status
            in {
                ParticipantStatus.SUCCEEDED,
                ParticipantStatus.SKIPPED,
            }
            or not result.required
            for result in results
        )

        return PhaseShutdownResult(
            phase=phase,
            started_at_utc=phase_started_at,
            completed_at_utc=self._utc_now(),
            duration_seconds=time.monotonic() - phase_started_monotonic,
            succeeded=succeeded,
            timed_out=timed_out,
            participants=tuple(results),
        )

    def _execute_parallel_participants(
        self,
        *,
        participants: Sequence[_RegisteredParticipant],
        overall_deadline: float,
    ) -> list[ParticipantShutdownResult]:
        results: dict[str, ParticipantShutdownResult] = {}

        with ThreadPoolExecutor(
            max_workers=min(
                self.config.max_parallel_workers,
                len(participants),
            ),
            thread_name_prefix="graceful-shutdown",
        ) as executor:
            futures: dict[
                Future[ParticipantShutdownResult],
                _RegisteredParticipant,
            ] = {
                executor.submit(
                    self._execute_participant,
                    participant=participant,
                    overall_deadline=overall_deadline,
                ): participant
                for participant in participants
            }

            for future, participant in futures.items():
                remaining = max(0.0, overall_deadline - time.monotonic())

                try:
                    results[participant.config.name] = future.result(
                        timeout=remaining
                    )
                except FutureTimeoutError:
                    results[participant.config.name] = self._timeout_result(
                        participant,
                        "overall shutdown deadline exceeded",
                    )
                except Exception as exc:
                    results[participant.config.name] = self._failed_result(
                        participant=participant,
                        exception=exc,
                        started_at_utc=None,
                        duration_seconds=0.0,
                    )

        return [
            results[participant.config.name]
            for participant in participants
        ]

    def _execute_participant(
        self,
        *,
        participant: _RegisteredParticipant,
        overall_deadline: float,
    ) -> ParticipantShutdownResult:
        started_at = self._utc_now()
        started_monotonic = time.monotonic()
        timeout = (
            participant.config.timeout_seconds
            or self.config.default_participant_timeout_seconds
        )
        remaining_overall = max(0.0, overall_deadline - started_monotonic)
        effective_timeout = min(timeout, remaining_overall)

        self._publish(
            "shutdown.participant_started",
            {
                "name": participant.config.name,
                "phase": participant.config.phase.value,
            },
        )

        if effective_timeout <= 0:
            result = self._timeout_result(
                participant,
                "no shutdown time remained",
            )
            self._record_participant_metric(result)
            return result

        with ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix=f"shutdown-{participant.config.name}",
        ) as executor:
            future = executor.submit(participant.handler)

            try:
                response = future.result(timeout=effective_timeout)
                success, message = self._normalize_handler_response(response)

                if success:
                    result = ParticipantShutdownResult(
                        name=participant.config.name,
                        phase=participant.config.phase,
                        status=ParticipantStatus.SUCCEEDED,
                        started_at_utc=started_at,
                        completed_at_utc=self._utc_now(),
                        duration_seconds=(
                            time.monotonic() - started_monotonic
                        ),
                        required=participant.config.required,
                        message=message or "shutdown completed",
                        metadata=dict(participant.config.metadata),
                    )
                else:
                    result = ParticipantShutdownResult(
                        name=participant.config.name,
                        phase=participant.config.phase,
                        status=ParticipantStatus.FAILED,
                        started_at_utc=started_at,
                        completed_at_utc=self._utc_now(),
                        duration_seconds=(
                            time.monotonic() - started_monotonic
                        ),
                        required=participant.config.required,
                        message=message or "shutdown handler reported failure",
                        metadata=dict(participant.config.metadata),
                    )

            except FutureTimeoutError:
                result = ParticipantShutdownResult(
                    name=participant.config.name,
                    phase=participant.config.phase,
                    status=ParticipantStatus.TIMED_OUT,
                    started_at_utc=started_at,
                    completed_at_utc=self._utc_now(),
                    duration_seconds=(
                        time.monotonic() - started_monotonic
                    ),
                    required=participant.config.required,
                    message=(
                        f"participant exceeded timeout of "
                        f"{effective_timeout:.3f} seconds"
                    ),
                    metadata=dict(participant.config.metadata),
                )

            except Exception as exc:
                result = self._failed_result(
                    participant=participant,
                    exception=exc,
                    started_at_utc=started_at,
                    duration_seconds=time.monotonic() - started_monotonic,
                )

        self._record_participant_metric(result)
        self._publish("shutdown.participant_completed", result.to_dict())
        return result

    def _create_final_checkpoint(
        self,
        *,
        shutdown_id: str,
        reason: str,
    ) -> tuple[str | None, PhaseShutdownResult | None]:
        phase_started_at = self._utc_now()
        phase_started_monotonic = time.monotonic()

        try:
            response = self.checkpoint_creator.create_checkpoint(
                metadata={
                    "shutdown_id": shutdown_id,
                    "shutdown_reason": reason,
                    "final_checkpoint": True,
                }
            )

            checkpoint_id = getattr(response, "checkpoint_id", None)
            if checkpoint_id is None and isinstance(response, Mapping):
                checkpoint_id = response.get("checkpoint_id")

            participant = ParticipantShutdownResult(
                name="final_checkpoint",
                phase=ShutdownPhase.CHECKPOINT,
                status=ParticipantStatus.SUCCEEDED,
                started_at_utc=phase_started_at,
                completed_at_utc=self._utc_now(),
                duration_seconds=time.monotonic() - phase_started_monotonic,
                required=True,
                message="final checkpoint created",
                metadata={
                    "checkpoint_id": checkpoint_id,
                },
            )

            self._record_participant_metric(participant)

            phase_result = PhaseShutdownResult(
                phase=ShutdownPhase.CHECKPOINT,
                started_at_utc=phase_started_at,
                completed_at_utc=self._utc_now(),
                duration_seconds=time.monotonic() - phase_started_monotonic,
                succeeded=True,
                timed_out=False,
                participants=(participant,),
            )
            return (
                str(checkpoint_id) if checkpoint_id is not None else None,
                phase_result,
            )

        except Exception as exc:
            participant = ParticipantShutdownResult(
                name="final_checkpoint",
                phase=ShutdownPhase.CHECKPOINT,
                status=ParticipantStatus.FAILED,
                started_at_utc=phase_started_at,
                completed_at_utc=self._utc_now(),
                duration_seconds=time.monotonic() - phase_started_monotonic,
                required=True,
                message="final checkpoint creation failed",
                exception_type=type(exc).__name__,
                exception_message=str(exc),
            )

            self._record_participant_metric(participant)

            phase_result = PhaseShutdownResult(
                phase=ShutdownPhase.CHECKPOINT,
                started_at_utc=phase_started_at,
                completed_at_utc=self._utc_now(),
                duration_seconds=time.monotonic() - phase_started_monotonic,
                succeeded=False,
                timed_out=False,
                participants=(participant,),
            )
            return None, phase_result

    def list_participants(
        self,
    ) -> tuple[ShutdownParticipantConfig, ...]:
        with self._lock:
            return tuple(
                sorted(
                    (
                        participant.config
                        for participant in self._participants.values()
                    ),
                    key=lambda item: (
                        self._phase_index(item.phase),
                        item.priority,
                        item.name,
                    ),
                )
            )

    def latest_report(self) -> ShutdownReport | None:
        with self._lock:
            return self._reports[-1] if self._reports else None

    def reports(self) -> tuple[ShutdownReport, ...]:
        with self._lock:
            return tuple(self._reports)

    def metrics(self) -> dict[str, int | float | str | None]:
        with self._lock:
            metrics: dict[str, int | float | str | None] = dict(
                self._metrics
            )
            metrics["status"] = self._status.value
            metrics["current_phase"] = (
                self._current_phase.value
                if self._current_phase is not None
                else None
            )
            metrics["registered_participants"] = len(self._participants)

        started = float(metrics["shutdowns_started"])
        metrics["average_shutdown_duration_seconds"] = (
            float(metrics["total_shutdown_duration_seconds"]) / started
            if started
            else 0.0
        )
        return metrics

    def health_check(self) -> dict[str, Any]:
        with self._lock:
            dependency_errors = self._dependency_errors_unlocked()

        return {
            "healthy": not dependency_errors
            and self._status != ShutdownStatus.TIMED_OUT,
            "status": self.status.value,
            "current_phase": (
                self.current_phase.value
                if self.current_phase is not None
                else None
            ),
            "shutdown_requested": self.shutdown_requested,
            "force_requested": self.force_requested,
            "dependency_errors": dependency_errors,
            "metrics": self.metrics(),
        }

    def _ordered_participants_for_phase(
        self,
        phase: ShutdownPhase,
    ) -> tuple[_RegisteredParticipant, ...]:
        with self._lock:
            selected = [
                participant
                for participant in self._participants.values()
                if participant.config.phase == phase
            ]

        return tuple(
            sorted(
                selected,
                key=lambda participant: (
                    participant.config.priority,
                    participant.config.name,
                ),
            )
        )

    def _validate_dependencies_unlocked(self) -> None:
        errors = self._dependency_errors_unlocked()
        if errors:
            raise ValueError("; ".join(errors))

    def _dependency_errors_unlocked(self) -> list[str]:
        errors: list[str] = []

        for participant in self._participants.values():
            for dependency_name in participant.config.dependencies:
                dependency = self._participants.get(dependency_name)

                if dependency is None:
                    continue

                if (
                    self._phase_index(dependency.config.phase)
                    > self._phase_index(participant.config.phase)
                ):
                    errors.append(
                        f"{participant.config.name} depends on "
                        f"{dependency_name}, but the dependency is scheduled "
                        "in a later phase"
                    )

        return errors

    def _phase_index(self, phase: ShutdownPhase) -> int:
        try:
            return self.config.phase_order.index(phase)
        except ValueError:
            return len(self.config.phase_order)

    def _store_report(self, report: ShutdownReport) -> None:
        with self._lock:
            self._reports.append(report)
            if len(self._reports) > self.config.retain_reports:
                del self._reports[
                    : len(self._reports) - self.config.retain_reports
                ]

            self._metrics["total_shutdown_duration_seconds"] += (
                report.duration_seconds
            )

            metric_name = {
                ShutdownStatus.COMPLETED: "shutdowns_completed",
                ShutdownStatus.COMPLETED_WITH_ERRORS:
                    "shutdowns_completed_with_errors",
                ShutdownStatus.TIMED_OUT: "shutdowns_timed_out",
                ShutdownStatus.FORCED: "shutdowns_forced",
                ShutdownStatus.CANCELLED: "shutdowns_cancelled",
                ShutdownStatus.NOT_STARTED: None,
                ShutdownStatus.IN_PROGRESS: None,
            }[report.status]

            if metric_name is not None:
                self._metrics[metric_name] += 1

    def _record_participant_metric(
        self,
        result: ParticipantShutdownResult,
    ) -> None:
        metric_name = {
            ParticipantStatus.SUCCEEDED: "participants_succeeded",
            ParticipantStatus.FAILED: "participants_failed",
            ParticipantStatus.TIMED_OUT: "participants_timed_out",
            ParticipantStatus.SKIPPED: "participants_skipped",
            ParticipantStatus.PENDING: None,
            ParticipantStatus.RUNNING: None,
        }[result.status]

        if metric_name is not None:
            with self._lock:
                self._metrics[metric_name] += 1

    def _failed_result(
        self,
        *,
        participant: _RegisteredParticipant,
        exception: BaseException,
        started_at_utc: str | None,
        duration_seconds: float,
    ) -> ParticipantShutdownResult:
        return ParticipantShutdownResult(
            name=participant.config.name,
            phase=participant.config.phase,
            status=ParticipantStatus.FAILED,
            started_at_utc=started_at_utc,
            completed_at_utc=self._utc_now(),
            duration_seconds=duration_seconds,
            required=participant.config.required,
            message="shutdown participant raised an exception",
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            metadata=dict(participant.config.metadata),
        )

    def _timeout_result(
        self,
        participant: _RegisteredParticipant,
        message: str,
    ) -> ParticipantShutdownResult:
        return ParticipantShutdownResult(
            name=participant.config.name,
            phase=participant.config.phase,
            status=ParticipantStatus.TIMED_OUT,
            started_at_utc=None,
            completed_at_utc=self._utc_now(),
            duration_seconds=0.0,
            required=participant.config.required,
            message=message,
            metadata=dict(participant.config.metadata),
        )

    def _skipped_result(
        self,
        participant: _RegisteredParticipant,
        message: str,
    ) -> ParticipantShutdownResult:
        result = ParticipantShutdownResult(
            name=participant.config.name,
            phase=participant.config.phase,
            status=ParticipantStatus.SKIPPED,
            started_at_utc=None,
            completed_at_utc=self._utc_now(),
            duration_seconds=0.0,
            required=participant.config.required,
            message=message,
            metadata=dict(participant.config.metadata),
        )
        self._record_participant_metric(result)
        return result

    @staticmethod
    def _normalize_handler_response(response: Any) -> tuple[bool, str]:
        if response is None:
            return True, ""
        if isinstance(response, bool):
            return response, ""
        if isinstance(response, Mapping):
            return (
                bool(response.get("success", True)),
                str(response.get("message", "")),
            )
        return True, str(response)

    def _publish(self, event_type: str, payload: Any) -> None:
        if self.config.publish_events and self.event_publisher is not None:
            self.event_publisher.publish_event(
                event_type,
                payload,
                source="graceful_shutdown_manager",
            )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
