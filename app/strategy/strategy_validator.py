from __future__ import annotations

from collections.abc import Iterable

from .models import StrategyDefinition, ValidationIssue, ValidationResult


class StrategyValidator:
    """Applies deterministic, side-effect-free validation rules."""

    ALLOWED_TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"}

    def validate(self, strategy: StrategyDefinition) -> ValidationResult:
        issues: list[ValidationIssue] = []
        self._required(strategy, issues)
        self._timeframes(strategy, issues)
        self._parameters(strategy, issues)
        self._rules(strategy, issues)
        return ValidationResult(valid=not issues, issues=tuple(issues))

    @staticmethod
    def _required(strategy: StrategyDefinition, issues: list[ValidationIssue]) -> None:
        for field, value in (
            ("strategy_id", strategy.strategy_id), ("name", strategy.name),
            ("author", strategy.author), ("category", strategy.category),
            ("description", strategy.description),
        ):
            if not str(value).strip():
                issues.append(ValidationIssue(field, "is required", "required"))
        if not strategy.supported_assets:
            issues.append(ValidationIssue("supported_assets", "at least one asset is required", "required"))
        if not strategy.supported_timeframes:
            issues.append(ValidationIssue("supported_timeframes", "at least one timeframe is required", "required"))

    def _timeframes(self, strategy: StrategyDefinition, issues: list[ValidationIssue]) -> None:
        invalid = sorted(set(strategy.supported_timeframes) - self.ALLOWED_TIMEFRAMES)
        if invalid:
            issues.append(ValidationIssue("supported_timeframes", f"unsupported: {', '.join(invalid)}", "unsupported"))

    @staticmethod
    def _parameters(strategy: StrategyDefinition, issues: list[ValidationIssue]) -> None:
        for name, value in strategy.parameters.items():
            if not str(name).strip():
                issues.append(ValidationIssue("parameters", "parameter names cannot be blank"))
            if isinstance(value, float) and (value != value):
                issues.append(ValidationIssue(f"parameters.{name}", "NaN is not allowed"))

    @staticmethod
    def _rules(strategy: StrategyDefinition, issues: list[ValidationIssue]) -> None:
        if not strategy.entry_rules:
            issues.append(ValidationIssue("entry_rules", "at least one entry rule is required", "required"))
        if not strategy.exit_rules:
            issues.append(ValidationIssue("exit_rules", "at least one exit rule is required", "required"))
        if not strategy.position_sizing_rule.strip():
            issues.append(ValidationIssue("position_sizing_rule", "is required", "required"))
