from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RankingWeights:
    """
    Configurable factor weights used by the AI ranking engine.

    All weights must be non-negative and must total 1.0.
    """

    trend: float = 0.30
    momentum: float = 0.25
    volume: float = 0.15
    breakout: float = 0.20
    risk: float = 0.10

    def __post_init__(self) -> None:
        values = (
            self.trend,
            self.momentum,
            self.volume,
            self.breakout,
            self.risk,
        )

        if any(value < 0.0 for value in values):
            raise ValueError(
                "Ranking weights cannot be negative."
            )

        total = sum(values)

        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                "Ranking weights must total 1.0."
            )


@dataclass(frozen=True, slots=True)
class RankingThresholds:
    """
    Score thresholds used to convert an overall score
    into a recommendation.
    """

    strong_buy: float = 85.0
    buy: float = 70.0
    watch: float = 55.0
    hold: float = 40.0

    def __post_init__(self) -> None:
        values = (
            self.strong_buy,
            self.buy,
            self.watch,
            self.hold,
        )

        if any(value < 0.0 or value > 100.0 for value in values):
            raise ValueError(
                "Ranking thresholds must be between 0 and 100."
            )

        if not (
            self.strong_buy
            > self.buy
            > self.watch
            > self.hold
        ):
            raise ValueError(
                "Thresholds must satisfy: "
                "strong_buy > buy > watch > hold."
            )


@dataclass(frozen=True, slots=True)
class RankingConfig:
    """
    Complete configuration for the AI ranking engine.
    """

    weights: RankingWeights = RankingWeights()
    thresholds: RankingThresholds = RankingThresholds()

    min_confidence: float = 0.0
    max_confidence: float = 100.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.min_confidence <= 100.0:
            raise ValueError(
                "min_confidence must be between 0 and 100."
            )

        if not 0.0 <= self.max_confidence <= 100.0:
            raise ValueError(
                "max_confidence must be between 0 and 100."
            )

        if self.min_confidence > self.max_confidence:
            raise ValueError(
                "min_confidence cannot exceed max_confidence."
            )