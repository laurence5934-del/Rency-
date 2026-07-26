from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .models import RiskProfile, StrategyDefinition, StrategyStatus, StrategyVersion


class StrategyLoader:
    """Loads declarative JSON definitions; never imports arbitrary executable code."""

    def load_json(self, path: str | Path) -> StrategyDefinition:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("strategy document must be a JSON object")
        return self.from_mapping(data)

    def from_mapping(self, data: Mapping[str, Any]) -> StrategyDefinition:
        return StrategyDefinition(
            strategy_id=str(data["strategy_id"]), name=str(data["name"]),
            version=StrategyVersion.parse(str(data["version"])),
            description=str(data["description"]), author=str(data["author"]),
            category=str(data["category"]), risk_profile=RiskProfile(str(data["risk_profile"])),
            supported_assets=tuple(data["supported_assets"]),
            supported_timeframes=tuple(data["supported_timeframes"]),
            parameters=dict(data.get("parameters", {})), dependencies=tuple(data.get("dependencies", ())),
            entry_rules=tuple(data.get("entry_rules", ())), exit_rules=tuple(data.get("exit_rules", ())),
            position_sizing_rule=str(data.get("position_sizing_rule", "fixed_fractional")),
            status=StrategyStatus(str(data.get("status", StrategyStatus.DRAFT.value))),
            metadata=dict(data.get("metadata", {})),
        )
