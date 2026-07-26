from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from numbers import Real
from typing import Any, Mapping


class ConfidenceLevel(str, Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class ConfidenceDecision(str, Enum):
    REJECT = "REJECT"
    REDUCE = "REDUCE"
    ACCEPT = "ACCEPT"
    INCREASE = "INCREASE"


@dataclass(frozen=True, slots=True)
class ConfidenceInputs:
    """
    Normalized inputs used by the AI Confidence Engine.

    Every score must be between 0 and 1.
    """

    regime_confidence: float
    strategy_confidence: float
    strategy_consensus: float
    historical_accuracy: float
    recent_performance: float
    risk_quality: float
    data_quality: float
    volatility_stability: float
    signal_strength: float
    model_agreement: float = 1.0

    def __post_init__(self) -> None:
        for field_name in (
            "regime_confidence",
            "strategy_confidence",
            "strategy_consensus",
            "historical_accuracy",
            "recent_performance",
            "risk_quality",
            "data_quality",
            "volatility_stability",
            "signal_strength",
            "model_agreement",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")

            numeric = float(value)

            if not isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")

            if not 0.0 <= numeric <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

            object.__setattr__(self, field_name, numeric)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ConfidenceInputs":
        if not isinstance(data, Mapping):
            raise TypeError("data must be a mapping")

        allowed = {
            "regime_confidence",
            "strategy_confidence",
            "strategy_consensus",
            "historical_accuracy",
            "recent_performance",
            "risk_quality",
            "data_quality",
            "volatility_stability",
            "signal_strength",
            "model_agreement",
        }

        unknown = set(data) - allowed
        if unknown:
            raise ValueError(
                "unknown confidence input fields: "
                + ", ".join(sorted(unknown))
            )

        required = allowed - {"model_agreement"}
        missing = required - set(data)
        if missing:
            raise ValueError(
                "missing confidence input fields: "
                + ", ".join(sorted(missing))
            )

        return cls(
            regime_confidence=data["regime_confidence"],
            strategy_confidence=data["strategy_confidence"],
            strategy_consensus=data["strategy_consensus"],
            historical_accuracy=data["historical_accuracy"],
            recent_performance=data["recent_performance"],
            risk_quality=data["risk_quality"],
            data_quality=data["data_quality"],
            volatility_stability=data["volatility_stability"],
            signal_strength=data["signal_strength"],
            model_agreement=data.get("model_agreement", 1.0),
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "regime_confidence": self.regime_confidence,
            "strategy_confidence": self.strategy_confidence,
            "strategy_consensus": self.strategy_consensus,
            "historical_accuracy": self.historical_accuracy,
            "recent_performance": self.recent_performance,
            "risk_quality": self.risk_quality,
            "data_quality": self.data_quality,
            "volatility_stability": self.volatility_stability,
            "signal_strength": self.signal_strength,
            "model_agreement": self.model_agreement,
        }


@dataclass(frozen=True, slots=True)
class ConfidenceComponent:
    name: str
    raw_score: float
    weight: float
    weighted_score: float
    explanation: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("name must be a string")

        name = self.name.strip()
        if not name:
            raise ValueError("name cannot be empty")

        for field_name in ("raw_score", "weight", "weighted_score"):
            value = getattr(self, field_name)

            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")

            numeric = float(value)

            if not isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")

            if not 0.0 <= numeric <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

            object.__setattr__(self, field_name, numeric)

        if not isinstance(self.explanation, str):
            raise TypeError("explanation must be a string")

        object.__setattr__(self, "name", name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "raw_score": self.raw_score,
            "weight": self.weight,
            "weighted_score": self.weighted_score,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class ConfidenceReport:
    overall_confidence: float
    base_confidence: float
    penalty: float
    level: ConfidenceLevel
    decision: ConfidenceDecision
    position_size_multiplier: float
    components: tuple[ConfidenceComponent, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "overall_confidence",
            "base_confidence",
            "penalty",
            "position_size_multiplier",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")

            numeric = float(value)

            if not isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")

            if field_name == "position_size_multiplier":
                if not 0.0 <= numeric <= 1.5:
                    raise ValueError(
                        "position_size_multiplier must be between 0 and 1.5"
                    )
            elif not 0.0 <= numeric <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

            object.__setattr__(self, field_name, numeric)

        if not isinstance(self.level, ConfidenceLevel):
            raise TypeError("level must be a ConfidenceLevel")

        if not isinstance(self.decision, ConfidenceDecision):
            raise TypeError("decision must be a ConfidenceDecision")

        if not isinstance(self.components, tuple):
            object.__setattr__(
                self,
                "components",
                tuple(self.components),
            )

        if any(
            not isinstance(component, ConfidenceComponent)
            for component in self.components
        ):
            raise TypeError(
                "components must contain ConfidenceComponent instances"
            )

        if not isinstance(self.reasons, tuple):
            object.__setattr__(self, "reasons", tuple(self.reasons))

        if any(not isinstance(reason, str) for reason in self.reasons):
            raise TypeError("all reasons must be strings")

    @property
    def approved(self) -> bool:
        return self.decision in {
            ConfidenceDecision.ACCEPT,
            ConfidenceDecision.INCREASE,
        }

    def component_scores(self) -> dict[str, float]:
        return {
            component.name: component.raw_score
            for component in self.components
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_confidence": self.overall_confidence,
            "base_confidence": self.base_confidence,
            "penalty": self.penalty,
            "level": self.level.value,
            "decision": self.decision.value,
            "approved": self.approved,
            "position_size_multiplier": self.position_size_multiplier,
            "components": [
                component.to_dict()
                for component in self.components
            ],
            "component_scores": self.component_scores(),
            "reasons": list(self.reasons),
        }


class AIConfidenceEngine:
    """
    Version 9.8.0.4 AI Confidence Engine.

    Produces an explainable confidence score by combining market,
    strategy, performance, risk, volatility, and data-quality evidence.
    """

    DEFAULT_WEIGHTS = {
        "regime_confidence": 0.12,
        "strategy_confidence": 0.14,
        "strategy_consensus": 0.12,
        "historical_accuracy": 0.12,
        "recent_performance": 0.10,
        "risk_quality": 0.12,
        "data_quality": 0.10,
        "volatility_stability": 0.07,
        "signal_strength": 0.07,
        "model_agreement": 0.04,
    }

    COMPONENT_LABELS = {
        "regime_confidence": "Market regime confidence",
        "strategy_confidence": "Strategy confidence",
        "strategy_consensus": "Strategy consensus",
        "historical_accuracy": "Historical accuracy",
        "recent_performance": "Recent performance",
        "risk_quality": "Risk quality",
        "data_quality": "Data quality",
        "volatility_stability": "Volatility stability",
        "signal_strength": "Signal strength",
        "model_agreement": "Model agreement",
    }

    def __init__(
        self,
        *,
        weights: Mapping[str, Real] | None = None,
        reject_threshold: float = 0.40,
        reduce_threshold: float = 0.60,
        increase_threshold: float = 0.85,
        low_data_quality_threshold: float = 0.50,
        low_consensus_threshold: float = 0.45,
        instability_threshold: float = 0.40,
        max_penalty: float = 0.35,
    ) -> None:
        raw_weights = dict(weights or self.DEFAULT_WEIGHTS)

        expected = set(self.DEFAULT_WEIGHTS)
        actual = set(raw_weights)

        if actual != expected:
            missing = expected - actual
            extra = actual - expected
            details: list[str] = []

            if missing:
                details.append(
                    "missing=" + ",".join(sorted(missing))
                )

            if extra:
                details.append(
                    "extra=" + ",".join(sorted(extra))
                )

            raise ValueError(
                "weights keys are invalid: " + "; ".join(details)
            )

        total = 0.0
        normalized: dict[str, float] = {}

        for name, value in raw_weights.items():
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"weight {name} must be numeric")

            numeric = float(value)

            if not isfinite(numeric):
                raise ValueError(f"weight {name} must be finite")

            if numeric < 0.0:
                raise ValueError(f"weight {name} cannot be negative")

            normalized[name] = numeric
            total += numeric

        if total <= 0.0:
            raise ValueError("weights must have a positive total")

        self.weights = {
            name: value / total
            for name, value in normalized.items()
        }

        self.reject_threshold = self._validate_unit_interval(
            "reject_threshold",
            reject_threshold,
        )
        self.reduce_threshold = self._validate_unit_interval(
            "reduce_threshold",
            reduce_threshold,
        )
        self.increase_threshold = self._validate_unit_interval(
            "increase_threshold",
            increase_threshold,
        )

        if not (
            self.reject_threshold
            < self.reduce_threshold
            < self.increase_threshold
        ):
            raise ValueError(
                "thresholds must satisfy "
                "reject_threshold < reduce_threshold < increase_threshold"
            )

        self.low_data_quality_threshold = self._validate_unit_interval(
            "low_data_quality_threshold",
            low_data_quality_threshold,
        )
        self.low_consensus_threshold = self._validate_unit_interval(
            "low_consensus_threshold",
            low_consensus_threshold,
        )
        self.instability_threshold = self._validate_unit_interval(
            "instability_threshold",
            instability_threshold,
        )
        self.max_penalty = self._validate_unit_interval(
            "max_penalty",
            max_penalty,
        )

        self._last_report: ConfidenceReport | None = None

    @staticmethod
    def _validate_unit_interval(name: str, value: Real) -> float:
        if not isinstance(value, Real) or isinstance(value, bool):
            raise TypeError(f"{name} must be numeric")

        numeric = float(value)

        if not isfinite(numeric):
            raise ValueError(f"{name} must be finite")

        if not 0.0 <= numeric <= 1.0:
            raise ValueError(f"{name} must be between 0 and 1")

        return numeric

    @property
    def last_report(self) -> ConfidenceReport | None:
        return self._last_report

    @staticmethod
    def confidence_level(score: Real) -> ConfidenceLevel:
        numeric = AIConfidenceEngine._validate_unit_interval(
            "score",
            score,
        )

        if numeric < 0.30:
            return ConfidenceLevel.VERY_LOW
        if numeric < 0.50:
            return ConfidenceLevel.LOW
        if numeric < 0.70:
            return ConfidenceLevel.MODERATE
        if numeric < 0.85:
            return ConfidenceLevel.HIGH
        return ConfidenceLevel.VERY_HIGH

    def confidence_decision(
        self,
        score: Real,
    ) -> ConfidenceDecision:
        numeric = self._validate_unit_interval("score", score)

        if numeric < self.reject_threshold:
            return ConfidenceDecision.REJECT
        if numeric < self.reduce_threshold:
            return ConfidenceDecision.REDUCE
        if numeric < self.increase_threshold:
            return ConfidenceDecision.ACCEPT
        return ConfidenceDecision.INCREASE

    @staticmethod
    def _component_explanation(
        label: str,
        score: float,
    ) -> str:
        if score >= 0.85:
            description = "very strong supporting evidence"
        elif score >= 0.70:
            description = "strong supporting evidence"
        elif score >= 0.55:
            description = "moderate supporting evidence"
        elif score >= 0.40:
            description = "weak supporting evidence"
        else:
            description = "very weak supporting evidence"

        return f"{label}: {description} ({score:.1%})"

    def _calculate_penalty(
        self,
        inputs: ConfidenceInputs,
    ) -> tuple[float, tuple[str, ...]]:
        penalty = 0.0
        reasons: list[str] = []

        if inputs.data_quality < self.low_data_quality_threshold:
            amount = (
                self.low_data_quality_threshold
                - inputs.data_quality
            ) * 0.30
            penalty += amount
            reasons.append(
                f"Low data quality penalty applied: {amount:.3f}"
            )

        if inputs.strategy_consensus < self.low_consensus_threshold:
            amount = (
                self.low_consensus_threshold
                - inputs.strategy_consensus
            ) * 0.25
            penalty += amount
            reasons.append(
                f"Low strategy consensus penalty applied: {amount:.3f}"
            )

        if inputs.volatility_stability < self.instability_threshold:
            amount = (
                self.instability_threshold
                - inputs.volatility_stability
            ) * 0.25
            penalty += amount
            reasons.append(
                f"Market instability penalty applied: {amount:.3f}"
            )

        if inputs.risk_quality < 0.40:
            amount = (0.40 - inputs.risk_quality) * 0.20
            penalty += amount
            reasons.append(
                f"Low risk-quality penalty applied: {amount:.3f}"
            )

        if inputs.model_agreement < 0.40:
            amount = (0.40 - inputs.model_agreement) * 0.15
            penalty += amount
            reasons.append(
                f"Low model-agreement penalty applied: {amount:.3f}"
            )

        return min(self.max_penalty, penalty), tuple(reasons)

    def _position_size_multiplier(
        self,
        score: float,
        decision: ConfidenceDecision,
    ) -> float:
        if decision is ConfidenceDecision.REJECT:
            return 0.0

        if decision is ConfidenceDecision.REDUCE:
            return max(0.10, min(0.60, score))

        if decision is ConfidenceDecision.ACCEPT:
            return max(0.60, min(1.00, score + 0.10))

        return min(1.25, 1.00 + (score - self.increase_threshold))

    def evaluate(
        self,
        inputs: ConfidenceInputs | Mapping[str, Any],
    ) -> ConfidenceReport:
        if isinstance(inputs, Mapping):
            inputs = ConfidenceInputs.from_mapping(inputs)

        if not isinstance(inputs, ConfidenceInputs):
            raise TypeError(
                "inputs must be ConfidenceInputs or a mapping"
            )

        components: list[ConfidenceComponent] = []
        base_confidence = 0.0

        for name, weight in self.weights.items():
            raw_score = getattr(inputs, name)
            weighted_score = raw_score * weight
            base_confidence += weighted_score

            label = self.COMPONENT_LABELS[name]

            components.append(
                ConfidenceComponent(
                    name=name,
                    raw_score=raw_score,
                    weight=weight,
                    weighted_score=weighted_score,
                    explanation=self._component_explanation(
                        label,
                        raw_score,
                    ),
                )
            )

        penalty, penalty_reasons = self._calculate_penalty(inputs)
        overall_confidence = max(
            0.0,
            min(1.0, base_confidence - penalty),
        )

        level = self.confidence_level(overall_confidence)
        decision = self.confidence_decision(overall_confidence)
        multiplier = self._position_size_multiplier(
            overall_confidence,
            decision,
        )

        reasons = [
            f"Base confidence: {base_confidence:.3f}",
            f"Total penalty: {penalty:.3f}",
            f"Final confidence: {overall_confidence:.3f}",
            f"Confidence level: {level.value}",
            f"Decision: {decision.value}",
            (
                "Position-size multiplier: "
                f"{multiplier:.3f}"
            ),
        ]
        reasons.extend(penalty_reasons)

        report = ConfidenceReport(
            overall_confidence=round(overall_confidence, 12),
            base_confidence=round(base_confidence, 12),
            penalty=round(penalty, 12),
            level=level,
            decision=decision,
            position_size_multiplier=round(multiplier, 12),
            components=tuple(components),
            reasons=tuple(reasons),
        )

        self._last_report = report
        return report

    def evaluate_from_sources(
        self,
        *,
        regime_confidence: Real,
        strategy_confidence: Real,
        strategy_consensus: Real,
        historical_accuracy: Real,
        recent_performance: Real,
        risk_quality: Real,
        data_quality: Real,
        volatility_stability: Real,
        signal_strength: Real,
        model_agreement: Real = 1.0,
    ) -> ConfidenceReport:
        return self.evaluate(
            ConfidenceInputs(
                regime_confidence=regime_confidence,
                strategy_confidence=strategy_confidence,
                strategy_consensus=strategy_consensus,
                historical_accuracy=historical_accuracy,
                recent_performance=recent_performance,
                risk_quality=risk_quality,
                data_quality=data_quality,
                volatility_stability=volatility_stability,
                signal_strength=signal_strength,
                model_agreement=model_agreement,
            )
        )

    def reset(self) -> None:
        self._last_report = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "weights": dict(self.weights),
            "reject_threshold": self.reject_threshold,
            "reduce_threshold": self.reduce_threshold,
            "increase_threshold": self.increase_threshold,
            "low_data_quality_threshold": (
                self.low_data_quality_threshold
            ),
            "low_consensus_threshold": (
                self.low_consensus_threshold
            ),
            "instability_threshold": self.instability_threshold,
            "max_penalty": self.max_penalty,
            "last_report": (
                self._last_report.to_dict()
                if self._last_report is not None
                else None
            ),
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reject_threshold={self.reject_threshold}, "
            f"reduce_threshold={self.reduce_threshold}, "
            f"increase_threshold={self.increase_threshold})"
        )
