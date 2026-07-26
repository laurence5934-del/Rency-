from __future__ import annotations

from threading import RLock
from typing import Any, Callable, Mapping

from .models import RecoveryAction, RecoveryPolicy


class RecoveryPolicyEngine:
    def __init__(self) -> None:
        self._lock = RLock()
        self._policies: dict[str, RecoveryPolicy] = {}
        self._handlers: dict[RecoveryAction, Callable[[str, Mapping[str, Any]], Any]] = {}

    def register_policy(self, policy: RecoveryPolicy) -> None:
        with self._lock:
            if policy.name in self._policies:
                raise KeyError(f"policy already registered: {policy.name}")
            self._policies[policy.name] = policy

    def register_action_handler(
        self,
        action: RecoveryAction,
        handler: Callable[[str, Mapping[str, Any]], Any],
    ) -> None:
        with self._lock:
            self._handlers[action] = handler

    def policies_for(self, failure_type: str) -> tuple[RecoveryPolicy, ...]:
        with self._lock:
            return tuple(
                item for item in self._policies.values()
                if item.enabled and item.failure_type == failure_type
            )

    def execute(
        self,
        failure_type: str,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        payload = dict(context or {})

        for policy in self.policies_for(failure_type):
            for action in policy.actions:
                handler = self._handlers.get(action)
                if handler is None:
                    results.append({
                        "policy": policy.name,
                        "action": action.value,
                        "success": False,
                        "message": "no handler registered",
                    })
                    continue
                try:
                    response = handler(failure_type, payload)
                    results.append({
                        "policy": policy.name,
                        "action": action.value,
                        "success": True,
                        "response": response,
                    })
                except Exception as exc:
                    results.append({
                        "policy": policy.name,
                        "action": action.value,
                        "success": False,
                        "message": f"{type(exc).__name__}: {exc}",
                    })
        return results

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [item.to_dict() for item in self._policies.values()]
