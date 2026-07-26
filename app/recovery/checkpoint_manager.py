from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Mapping, Protocol, Sequence


class CheckpointType(str, Enum):
    FULL = "FULL"
    INCREMENTAL = "INCREMENTAL"
    MANUAL = "MANUAL"
    AUTOMATIC = "AUTOMATIC"
    EMERGENCY = "EMERGENCY"


class CheckpointStatus(str, Enum):
    CREATED = "CREATED"
    VERIFIED = "VERIFIED"
    CORRUPTED = "CORRUPTED"
    RESTORED = "RESTORED"
    FAILED = "FAILED"
    DELETED = "DELETED"


class RestoreMode(str, Enum):
    STRICT = "STRICT"
    BEST_EFFORT = "BEST_EFFORT"
    DRY_RUN = "DRY_RUN"


@dataclass(frozen=True, slots=True)
class CheckpointManagerConfig:
    storage_directory: str = "var/checkpoints"
    schema_version: int = 1
    compress: bool = True
    retain_checkpoints: int = 50
    automatic_interval_seconds: float | None = None
    verify_after_write: bool = True
    fsync_writes: bool = True
    publish_events: bool = True
    manifest_filename: str = "manifest.json"

    def __post_init__(self) -> None:
        if not self.storage_directory.strip():
            raise ValueError("storage_directory cannot be empty")
        if self.schema_version < 1:
            raise ValueError("schema_version must be positive")
        if self.retain_checkpoints < 1:
            raise ValueError("retain_checkpoints must be positive")
        if (
            self.automatic_interval_seconds is not None
            and self.automatic_interval_seconds <= 0
        ):
            raise ValueError(
                "automatic_interval_seconds must be positive when provided"
            )
        if not self.manifest_filename.strip():
            raise ValueError("manifest_filename cannot be empty")


@dataclass(frozen=True, slots=True)
class StateComponentSnapshot:
    component_name: str
    component_version: str
    required: bool
    captured_at_utc: str
    checksum_sha256: str
    size_bytes: int
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CheckpointManifest:
    checkpoint_id: str
    checkpoint_type: CheckpointType
    status: CheckpointStatus
    schema_version: int
    created_at_utc: str
    completed_at_utc: str
    parent_checkpoint_id: str | None
    platform_version: str
    host_id: str
    compressed: bool
    payload_filename: str
    payload_checksum_sha256: str
    payload_size_bytes: int
    components: tuple[StateComponentSnapshot, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["checkpoint_type"] = self.checkpoint_type.value
        data["status"] = self.status.value
        data["components"] = [
            component.to_dict() for component in self.components
        ]
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CheckpointManifest":
        return cls(
            checkpoint_id=str(data["checkpoint_id"]),
            checkpoint_type=CheckpointType(str(data["checkpoint_type"])),
            status=CheckpointStatus(str(data["status"])),
            schema_version=int(data["schema_version"]),
            created_at_utc=str(data["created_at_utc"]),
            completed_at_utc=str(data["completed_at_utc"]),
            parent_checkpoint_id=(
                str(data["parent_checkpoint_id"])
                if data.get("parent_checkpoint_id") is not None
                else None
            ),
            platform_version=str(data["platform_version"]),
            host_id=str(data["host_id"]),
            compressed=bool(data["compressed"]),
            payload_filename=str(data["payload_filename"]),
            payload_checksum_sha256=str(data["payload_checksum_sha256"]),
            payload_size_bytes=int(data["payload_size_bytes"]),
            components=tuple(
                StateComponentSnapshot(
                    component_name=str(item["component_name"]),
                    component_version=str(item["component_version"]),
                    required=bool(item["required"]),
                    captured_at_utc=str(item["captured_at_utc"]),
                    checksum_sha256=str(item["checksum_sha256"]),
                    size_bytes=int(item["size_bytes"]),
                    metadata=dict(item.get("metadata", {})),
                )
                for item in data.get("components", [])
            ),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class RestoreComponentResult:
    component_name: str
    restored: bool
    validated: bool
    skipped: bool
    message: str
    duration_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RestoreReport:
    restore_id: str
    checkpoint_id: str
    mode: RestoreMode
    started_at_utc: str
    completed_at_utc: str
    duration_seconds: float
    succeeded: bool
    component_results: tuple[RestoreComponentResult, ...]
    message: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["mode"] = self.mode.value
        data["component_results"] = [
            item.to_dict() for item in self.component_results
        ]
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


class StateProvider(Protocol):
    def capture_state(self) -> Mapping[str, Any] | Sequence[Any] | Any: ...
    def restore_state(self, state: Any) -> None: ...
    def validate_state(self, state: Any) -> bool: ...


@dataclass(slots=True)
class _RegisteredComponent:
    name: str
    provider: StateProvider
    version: str
    required: bool
    metadata: Mapping[str, Any]


class CheckpointError(RuntimeError):
    pass


class CheckpointNotFoundError(CheckpointError):
    pass


class CheckpointIntegrityError(CheckpointError):
    pass


class RestoreValidationError(CheckpointError):
    pass


class CheckpointManager:
    """
    Version 10.0.8.5 - Checkpoint & State Recovery.

    Provides versioned state capture, atomic checkpoint creation, optional
    compression, SHA-256 integrity validation, retention, incremental ancestry,
    dry-run validation, strict and best-effort restore modes, component-level
    restore reports, event publication, metrics, and thread-safe orchestration.
    """

    def __init__(
        self,
        *,
        config: CheckpointManagerConfig | None = None,
        platform_version: str = "10.0.8.5",
        host_id: str | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self.config = config or CheckpointManagerConfig()
        self.platform_version = platform_version
        self.host_id = host_id or os.environ.get("HOSTNAME", "local")
        self.event_publisher = event_publisher

        self._lock = RLock()
        self._components: dict[str, _RegisteredComponent] = {}
        self._last_checkpoint_monotonic: float | None = None
        self._restore_history: list[RestoreReport] = []
        self._metrics: dict[str, int | float] = {
            "checkpoints_created": 0,
            "checkpoints_failed": 0,
            "checkpoints_verified": 0,
            "checkpoints_corrupted": 0,
            "checkpoints_deleted": 0,
            "restores_attempted": 0,
            "restores_succeeded": 0,
            "restores_failed": 0,
            "components_captured": 0,
            "components_restored": 0,
            "total_checkpoint_bytes": 0,
            "total_checkpoint_duration_seconds": 0.0,
            "total_restore_duration_seconds": 0.0,
        }

        self.storage_directory.mkdir(parents=True, exist_ok=True)

    @property
    def storage_directory(self) -> Path:
        return Path(self.config.storage_directory)

    def register_component(
        self,
        name: str,
        provider: StateProvider,
        *,
        version: str = "1",
        required: bool = True,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if not name.strip():
            raise ValueError("component name cannot be empty")

        with self._lock:
            if name in self._components:
                raise KeyError(f"component already registered: {name}")
            self._components[name] = _RegisteredComponent(
                name=name,
                provider=provider,
                version=version,
                required=required,
                metadata=dict(metadata or {}),
            )

    def unregister_component(self, name: str) -> bool:
        with self._lock:
            return self._components.pop(name, None) is not None

    def create_checkpoint(
        self,
        *,
        checkpoint_type: CheckpointType = CheckpointType.MANUAL,
        parent_checkpoint_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        component_names: Sequence[str] | None = None,
    ) -> CheckpointManifest:
        checkpoint_id = str(uuid.uuid4())
        started_at = self._utc_now()
        started_monotonic = time.monotonic()
        checkpoint_dir = self.storage_directory / checkpoint_id
        temp_dir = Path(
            tempfile.mkdtemp(
                prefix=f".{checkpoint_id}-",
                dir=str(self.storage_directory),
            )
        )

        self._publish(
            "checkpoint.creation_started",
            {
                "checkpoint_id": checkpoint_id,
                "checkpoint_type": checkpoint_type.value,
            },
        )

        try:
            with self._lock:
                if component_names is None:
                    selected = tuple(self._components.values())
                else:
                    selected = tuple(
                        self._require_component_unlocked(name)
                        for name in component_names
                    )

            payload: dict[str, Any] = {}
            component_snapshots: list[StateComponentSnapshot] = []

            for component in selected:
                captured_at = self._utc_now()
                state = component.provider.capture_state()
                canonical = self._canonical_json_bytes(state)
                checksum = hashlib.sha256(canonical).hexdigest()

                payload[component.name] = {
                    "component_version": component.version,
                    "required": component.required,
                    "captured_at_utc": captured_at,
                    "metadata": dict(component.metadata),
                    "state": state,
                }

                component_snapshots.append(
                    StateComponentSnapshot(
                        component_name=component.name,
                        component_version=component.version,
                        required=component.required,
                        captured_at_utc=captured_at,
                        checksum_sha256=checksum,
                        size_bytes=len(canonical),
                        metadata=dict(component.metadata),
                    )
                )

            payload_bytes = self._canonical_json_bytes(payload)
            payload_filename = (
                "state.json.gz" if self.config.compress else "state.json"
            )
            payload_path = temp_dir / payload_filename

            if self.config.compress:
                with gzip.open(payload_path, "wb") as handle:
                    handle.write(payload_bytes)
            else:
                payload_path.write_bytes(payload_bytes)

            if self.config.fsync_writes:
                self._fsync_file(payload_path)

            stored_payload = payload_path.read_bytes()
            payload_checksum = hashlib.sha256(stored_payload).hexdigest()
            completed_at = self._utc_now()

            manifest = CheckpointManifest(
                checkpoint_id=checkpoint_id,
                checkpoint_type=checkpoint_type,
                status=CheckpointStatus.CREATED,
                schema_version=self.config.schema_version,
                created_at_utc=started_at,
                completed_at_utc=completed_at,
                parent_checkpoint_id=parent_checkpoint_id,
                platform_version=self.platform_version,
                host_id=self.host_id,
                compressed=self.config.compress,
                payload_filename=payload_filename,
                payload_checksum_sha256=payload_checksum,
                payload_size_bytes=len(stored_payload),
                components=tuple(component_snapshots),
                metadata=dict(metadata or {}),
            )

            manifest_path = temp_dir / self.config.manifest_filename
            manifest_path.write_text(
                json.dumps(
                    manifest.to_dict(),
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            if self.config.fsync_writes:
                self._fsync_file(manifest_path)
                self._fsync_directory(temp_dir)

            os.replace(temp_dir, checkpoint_dir)

            if self.config.fsync_writes:
                self._fsync_directory(self.storage_directory)

            if self.config.verify_after_write:
                self.verify_checkpoint(checkpoint_id)

            duration = time.monotonic() - started_monotonic
            with self._lock:
                self._last_checkpoint_monotonic = time.monotonic()
                self._metrics["checkpoints_created"] += 1
                self._metrics["components_captured"] += len(component_snapshots)
                self._metrics["total_checkpoint_bytes"] += len(stored_payload)
                self._metrics["total_checkpoint_duration_seconds"] += duration

            self._enforce_retention()
            self._publish("checkpoint.created", manifest.to_dict())
            return self.load_manifest(checkpoint_id)

        except Exception:
            with self._lock:
                self._metrics["checkpoints_failed"] += 1
            shutil.rmtree(temp_dir, ignore_errors=True)
            shutil.rmtree(checkpoint_dir, ignore_errors=True)
            self._publish(
                "checkpoint.creation_failed",
                {"checkpoint_id": checkpoint_id},
            )
            raise

    def maybe_create_automatic_checkpoint(
        self,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> CheckpointManifest | None:
        interval = self.config.automatic_interval_seconds
        if interval is None:
            return None

        with self._lock:
            last = self._last_checkpoint_monotonic

        if last is not None and time.monotonic() - last < interval:
            return None

        latest = self.latest_checkpoint()
        return self.create_checkpoint(
            checkpoint_type=CheckpointType.AUTOMATIC,
            parent_checkpoint_id=(
                latest.checkpoint_id if latest is not None else None
            ),
            metadata=metadata,
        )

    def verify_checkpoint(self, checkpoint_id: str) -> bool:
        checkpoint_dir = self.storage_directory / checkpoint_id
        manifest = self.load_manifest(checkpoint_id)
        payload_path = checkpoint_dir / manifest.payload_filename

        if not payload_path.exists():
            self._mark_corrupted(checkpoint_id)
            raise CheckpointIntegrityError(
                f"checkpoint payload missing: {checkpoint_id}"
            )

        payload_bytes = payload_path.read_bytes()
        actual_checksum = hashlib.sha256(payload_bytes).hexdigest()

        if actual_checksum != manifest.payload_checksum_sha256:
            self._mark_corrupted(checkpoint_id)
            raise CheckpointIntegrityError(
                f"checkpoint checksum mismatch: {checkpoint_id}"
            )

        state = self._load_payload(manifest)
        component_index = {
            component.component_name: component
            for component in manifest.components
        }

        for name, component_data in state.items():
            expected = component_index.get(name)
            if expected is None:
                self._mark_corrupted(checkpoint_id)
                raise CheckpointIntegrityError(
                    f"component missing from manifest: {name}"
                )

            canonical = self._canonical_json_bytes(component_data["state"])
            checksum = hashlib.sha256(canonical).hexdigest()
            if checksum != expected.checksum_sha256:
                self._mark_corrupted(checkpoint_id)
                raise CheckpointIntegrityError(
                    f"component checksum mismatch: {name}"
                )

        with self._lock:
            self._metrics["checkpoints_verified"] += 1

        self._publish(
            "checkpoint.verified",
            {"checkpoint_id": checkpoint_id},
        )
        return True

    def restore_checkpoint(
        self,
        checkpoint_id: str,
        *,
        mode: RestoreMode = RestoreMode.STRICT,
        component_names: Sequence[str] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> RestoreReport:
        restore_id = str(uuid.uuid4())
        started_at = self._utc_now()
        started_monotonic = time.monotonic()

        with self._lock:
            self._metrics["restores_attempted"] += 1

        self.verify_checkpoint(checkpoint_id)
        manifest = self.load_manifest(checkpoint_id)
        payload = self._load_payload(manifest)

        selected_names = (
            tuple(payload.keys())
            if component_names is None
            else tuple(component_names)
        )

        results: list[RestoreComponentResult] = []
        overall_success = True

        self._publish(
            "checkpoint.restore_started",
            {
                "restore_id": restore_id,
                "checkpoint_id": checkpoint_id,
                "mode": mode.value,
            },
        )

        for name in selected_names:
            component_started = time.monotonic()

            with self._lock:
                component = self._components.get(name)

            if component is None:
                message = "component is not registered"
                results.append(
                    RestoreComponentResult(
                        component_name=name,
                        restored=False,
                        validated=False,
                        skipped=True,
                        message=message,
                        duration_seconds=time.monotonic() - component_started,
                    )
                )
                if mode == RestoreMode.STRICT:
                    overall_success = False
                    break
                continue

            if name not in payload:
                message = "component state missing from checkpoint"
                results.append(
                    RestoreComponentResult(
                        component_name=name,
                        restored=False,
                        validated=False,
                        skipped=True,
                        message=message,
                        duration_seconds=time.monotonic() - component_started,
                    )
                )
                if component.required and mode == RestoreMode.STRICT:
                    overall_success = False
                    break
                continue

            state = payload[name]["state"]

            try:
                validated = component.provider.validate_state(state)
                if not validated:
                    raise RestoreValidationError(
                        f"validation failed for component: {name}"
                    )

                if mode != RestoreMode.DRY_RUN:
                    component.provider.restore_state(state)

                results.append(
                    RestoreComponentResult(
                        component_name=name,
                        restored=mode != RestoreMode.DRY_RUN,
                        validated=True,
                        skipped=False,
                        message=(
                            "validated only"
                            if mode == RestoreMode.DRY_RUN
                            else "restored successfully"
                        ),
                        duration_seconds=time.monotonic() - component_started,
                    )
                )

                if mode != RestoreMode.DRY_RUN:
                    with self._lock:
                        self._metrics["components_restored"] += 1

            except Exception as exc:
                overall_success = False
                results.append(
                    RestoreComponentResult(
                        component_name=name,
                        restored=False,
                        validated=False,
                        skipped=False,
                        message=f"{type(exc).__name__}: {exc}",
                        duration_seconds=time.monotonic() - component_started,
                    )
                )
                if mode == RestoreMode.STRICT:
                    break

        duration = time.monotonic() - started_monotonic
        report = RestoreReport(
            restore_id=restore_id,
            checkpoint_id=checkpoint_id,
            mode=mode,
            started_at_utc=started_at,
            completed_at_utc=self._utc_now(),
            duration_seconds=duration,
            succeeded=overall_success,
            component_results=tuple(results),
            message=(
                "restore completed successfully"
                if overall_success
                else "restore completed with failures"
            ),
            metadata=dict(metadata or {}),
        )

        with self._lock:
            self._restore_history.append(report)
            self._metrics["total_restore_duration_seconds"] += duration
            if overall_success:
                self._metrics["restores_succeeded"] += 1
            else:
                self._metrics["restores_failed"] += 1

        self._publish("checkpoint.restore_completed", report.to_dict())

        if not overall_success and mode == RestoreMode.STRICT:
            raise RestoreValidationError(report.message)

        return report

    def load_manifest(self, checkpoint_id: str) -> CheckpointManifest:
        checkpoint_dir = self.storage_directory / checkpoint_id
        manifest_path = checkpoint_dir / self.config.manifest_filename

        if not manifest_path.exists():
            raise CheckpointNotFoundError(
                f"checkpoint not found: {checkpoint_id}"
            )

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return CheckpointManifest.from_dict(data)

    def list_checkpoints(self) -> tuple[CheckpointManifest, ...]:
        manifests: list[CheckpointManifest] = []

        for item in self.storage_directory.iterdir():
            if not item.is_dir() or item.name.startswith("."):
                continue
            try:
                manifests.append(self.load_manifest(item.name))
            except Exception:
                continue

        return tuple(
            sorted(
                manifests,
                key=lambda manifest: manifest.created_at_utc,
                reverse=True,
            )
        )

    def latest_checkpoint(self) -> CheckpointManifest | None:
        checkpoints = self.list_checkpoints()
        return checkpoints[0] if checkpoints else None

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        checkpoint_dir = self.storage_directory / checkpoint_id
        if not checkpoint_dir.exists():
            return False

        shutil.rmtree(checkpoint_dir)

        with self._lock:
            self._metrics["checkpoints_deleted"] += 1

        self._publish(
            "checkpoint.deleted",
            {"checkpoint_id": checkpoint_id},
        )
        return True

    def restore_history(self) -> tuple[RestoreReport, ...]:
        with self._lock:
            return tuple(self._restore_history)

    def metrics(self) -> dict[str, int | float]:
        with self._lock:
            metrics = dict(self._metrics)

        created = float(metrics["checkpoints_created"])
        restores = float(metrics["restores_attempted"])

        metrics["average_checkpoint_size_bytes"] = (
            float(metrics["total_checkpoint_bytes"]) / created
            if created
            else 0.0
        )
        metrics["average_checkpoint_duration_seconds"] = (
            float(metrics["total_checkpoint_duration_seconds"]) / created
            if created
            else 0.0
        )
        metrics["restore_success_rate"] = (
            float(metrics["restores_succeeded"]) / restores
            if restores
            else 0.0
        )
        return metrics

    def health_check(self) -> dict[str, Any]:
        latest = self.latest_checkpoint()
        storage_exists = self.storage_directory.exists()
        writable = os.access(self.storage_directory, os.W_OK)

        return {
            "healthy": storage_exists and writable,
            "storage_directory": str(self.storage_directory),
            "storage_exists": storage_exists,
            "storage_writable": writable,
            "registered_components": len(self._components),
            "latest_checkpoint": (
                latest.to_dict() if latest is not None else None
            ),
            "metrics": self.metrics(),
        }

    def _load_payload(
        self,
        manifest: CheckpointManifest,
    ) -> dict[str, Any]:
        payload_path = (
            self.storage_directory
            / manifest.checkpoint_id
            / manifest.payload_filename
        )

        if manifest.compressed:
            with gzip.open(payload_path, "rb") as handle:
                raw = handle.read()
        else:
            raw = payload_path.read_bytes()

        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise CheckpointIntegrityError(
                "checkpoint payload must contain a JSON object"
            )
        return data

    def _enforce_retention(self) -> None:
        checkpoints = self.list_checkpoints()
        for manifest in checkpoints[self.config.retain_checkpoints :]:
            self.delete_checkpoint(manifest.checkpoint_id)

    def _mark_corrupted(self, checkpoint_id: str) -> None:
        with self._lock:
            self._metrics["checkpoints_corrupted"] += 1
        self._publish(
            "checkpoint.corrupted",
            {"checkpoint_id": checkpoint_id},
        )

    def _require_component_unlocked(
        self,
        name: str,
    ) -> _RegisteredComponent:
        component = self._components.get(name)
        if component is None:
            raise KeyError(f"unknown state component: {name}")
        return component

    def _publish(self, event_type: str, payload: Any) -> None:
        if self.config.publish_events and self.event_publisher is not None:
            self.event_publisher.publish_event(
                event_type,
                payload,
                source="checkpoint_manager",
            )

    @staticmethod
    def _canonical_json_bytes(value: Any) -> bytes:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=CheckpointManager._json_default,
        ).encode("utf-8")

    @staticmethod
    def _json_default(value: Any) -> Any:
        if hasattr(value, "to_dict") and callable(value.to_dict):
            return value.to_dict()
        if hasattr(value, "__dict__"):
            return vars(value)
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, Enum):
            return value.value
        raise TypeError(
            f"object of type {type(value).__name__} is not JSON serializable"
        )

    @staticmethod
    def _fsync_file(path: Path) -> None:
        with path.open("rb") as handle:
            os.fsync(handle.fileno())

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        if os.name == "nt":
            return
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
