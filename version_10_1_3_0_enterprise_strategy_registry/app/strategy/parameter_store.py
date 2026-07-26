from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any, Mapping


class ParameterStore:
    """Thread-safe parameter profiles, separated from executable code."""

    def __init__(self) -> None:
        self._profiles: dict[str, dict[str, Any]] = {}
        self._lock = RLock()

    def put(self, profile_id: str, parameters: Mapping[str, Any], *, replace: bool = False) -> None:
        profile_id = profile_id.strip()
        if not profile_id:
            raise ValueError("profile_id is required")
        with self._lock:
            if profile_id in self._profiles and not replace:
                raise ValueError(f"parameter profile already exists: {profile_id}")
            self._profiles[profile_id] = deepcopy(dict(parameters))

    def get(self, profile_id: str) -> dict[str, Any]:
        with self._lock:
            try:
                return deepcopy(self._profiles[profile_id])
            except KeyError as exc:
                raise KeyError(f"unknown parameter profile: {profile_id}") from exc

    def merge(self, profile_id: str, overrides: Mapping[str, Any]) -> dict[str, Any]:
        result = self.get(profile_id)
        result.update(deepcopy(dict(overrides)))
        return result
