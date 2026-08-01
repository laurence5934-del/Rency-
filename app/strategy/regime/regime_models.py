from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")
_ONE = Decimal("1")


class RegimeDetectionStatus(str, Enum):
    """Lifecycle status for a market-regime detection run."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MarketRegime(str, Enum):
    """Supported market-regime classifications."""

    UNKNOWN = "UNKNOWN"
    STRONG_BULL = "STRONG_BULL"
    BULL = "BULL"
    SIDEWAYS = "SIDEWAYS"
    CORRECTION = "CORRECTION"
    BEAR = "BEAR"
    STRONG_BEAR = "STRONG_BEAR"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    RISK_OFF = "RISK_OFF"


class RegimeConfidence(str, Enum):
    """Confidence classification for a detected regime."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass(frozen=True, slots=True)
class MarketRegimeSignal:
    """Normalized market inputs used for regime detection."""

    signal_id: str
    trend_score: Decimal
    volatility_score: Decimal
    breadth_score: Decimal
    momentum_score: Decimal
    liquidity_score: Decimal
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_id = self.signal_id.strip()

        if not normalized_id:
            raise ValueError(
                "signal_id must not be empty"
            )

        for field_name in (
            "trend_score",
            "volatility_score",
            "breadth_score",
            "momentum_score",
            "liquidity_score",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

            if not _ZERO <= value <= _ONE:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        object.__setattr__(
            self,
            "signal_id",
            normalized_id,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )


@dataclass(frozen=True, slots=True)
class MarketRegimeReport:
    """Immutable output from the market-regime engine."""

    status: RegimeDetectionStatus
    regime: MarketRegime
    confidence: RegimeConfidence
    overall_score: Decimal
    signal: MarketRegimeSignal | None
    recommendation: str
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.status,
            RegimeDetectionStatus,
        ):
            raise TypeError(
                "status must be a RegimeDetectionStatus"
            )

        if not isinstance(self.regime, MarketRegime):
            raise TypeError(
                "regime must be a MarketRegime"
            )

        if not isinstance(
            self.confidence,
            RegimeConfidence,
        ):
            raise TypeError(
                "confidence must be a RegimeConfidence"
            )

        if not isinstance(self.overall_score, Decimal):
            raise TypeError(
                "overall_score must be a Decimal"
            )

        if not _ZERO <= self.overall_score <= _ONE:
            raise ValueError(
                "overall_score must be between 0 and 1"
            )

        if (
            self.signal is not None
            and not isinstance(
                self.signal,
                MarketRegimeSignal,
            )
        ):
            raise TypeError(
                "signal must be a MarketRegimeSignal or None"
            )

        normalized_recommendation = (
            self.recommendation.strip()
        )

        if not normalized_recommendation:
            raise ValueError(
                "recommendation must not be empty"
            )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if (
            self.status
            is RegimeDetectionStatus.FAILED
        ):
            if not normalized_error:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error:
            raise ValueError(
                "only failed reports may include an error"
            )

        object.__setattr__(
            self,
            "recommendation",
            normalized_recommendation,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )
        object.__setattr__(
            self,
            "error",
            normalized_error,
        )