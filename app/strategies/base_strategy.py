from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Mapping

from .strategy_signal import StrategySignal


class BaseStrategy(ABC):
    def __init__(
        self,
        name: str,
        description: str = "",
        config: Mapping[str, Any] | None = None,
        enabled: bool = True,
    ) -> None:
        normalized_name = name.strip()

        if not normalized_name:
            raise ValueError("strategy name must not be empty")

        if not isinstance(enabled, bool):
            raise TypeError("enabled must be a bool")

        if config is not None and not isinstance(config, Mapping):
            raise TypeError("config must be a mapping")

        self._name = normalized_name
        self._description = description.strip()
        self._config = dict(config or {})
        self._enabled = enabled
        self._signal_count = 0

        self.validate_config()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def config(self) -> dict[str, Any]:
        return dict(self._config)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def signal_count(self) -> int:
        return self._signal_count

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def reset(self) -> None:
        self._signal_count = 0
        self.on_reset()

    def validate_config(self) -> None:
        """Override when a strategy requires configuration validation."""

    def on_reset(self) -> None:
        """Override when a strategy has additional internal state."""

    def create_signal(
        self,
        *,
        symbol: str,
        timestamp: datetime,
        **kwargs: Any,
    ) -> StrategySignal:
        if not self.enabled:
            raise RuntimeError("strategy is disabled")

        signal = self.generate_signal(
            symbol=symbol,
            timestamp=timestamp,
            **kwargs,
        )

        if not isinstance(signal, StrategySignal):
            raise TypeError("generate_signal must return a StrategySignal")

        self._signal_count += 1
        return signal

    @abstractmethod
    def generate_signal(
        self,
        *,
        symbol: str,
        timestamp: datetime,
        **kwargs: Any,
    ) -> StrategySignal:
        """Generate one signal for the supplied market data."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "config": self.config,
            "enabled": self.enabled,
            "signal_count": self.signal_count,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"enabled={self.enabled}, "
            f"signal_count={self.signal_count}"
            f")"
        )