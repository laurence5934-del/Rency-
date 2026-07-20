from __future__ import annotations

from dataclasses import dataclass

from app.ai.ranking_config import (
    RankingConfig,
    RankingThresholds,
    RankingWeights,
)


@dataclass(frozen=True)
class RankingProfile:
    """
    Named ranking profile used to configure
    the AI Ranking Engine.
    """

    name: str
    description: str
    config: RankingConfig


class RankingProfiles:
    """
    Factory for built-in ranking profiles.
    """

    @staticmethod
    def growth() -> RankingProfile:
        return RankingProfile(
            name="Growth",
            description="Optimized for long-term capital appreciation.",
            config=RankingConfig(
                weights=RankingWeights(
                    trend=0.35,
                    momentum=0.30,
                    volume=0.10,
                    breakout=0.20,
                    risk=0.05,
                ),
                thresholds=RankingThresholds(
                    strong_buy=88,
                    buy=72,
                    watch=58,
                    hold=42,
                ),
            ),
        )

    @staticmethod
    def swing() -> RankingProfile:
        return RankingProfile(
            name="Swing",
            description="Optimized for short-term momentum trading.",
            config=RankingConfig(
                weights=RankingWeights(
                    trend=0.25,
                    momentum=0.35,
                    volume=0.20,
                    breakout=0.15,
                    risk=0.05,
                ),
                thresholds=RankingThresholds(
                    strong_buy=86,
                    buy=70,
                    watch=55,
                    hold=40,
                ),
            ),
        )

    @staticmethod
    def income() -> RankingProfile:
        return RankingProfile(
            name="Income",
            description="Optimized for stable dividend and income investing.",
            config=RankingConfig(
                weights=RankingWeights(
                    trend=0.20,
                    momentum=0.15,
                    volume=0.10,
                    breakout=0.10,
                    risk=0.45,
                ),
                thresholds=RankingThresholds(
                    strong_buy=85,
                    buy=68,
                    watch=52,
                    hold=38,
                ),
            ),
        )

    @staticmethod
    def conservative() -> RankingProfile:
        return RankingProfile(
            name="Conservative",
            description="Optimized for lower-risk investing.",
            config=RankingConfig(
                weights=RankingWeights(
                    trend=0.20,
                    momentum=0.20,
                    volume=0.10,
                    breakout=0.10,
                    risk=0.40,
                ),
                thresholds=RankingThresholds(
                    strong_buy=85,
                    buy=68,
                    watch=50,
                    hold=35,
                ),
            ),
        )

    @staticmethod
    def breakout() -> RankingProfile:
        return RankingProfile(
            name="Breakout",
            description="Optimized for technical breakout opportunities.",
            config=RankingConfig(
                weights=RankingWeights(
                    trend=0.25,
                    momentum=0.25,
                    volume=0.20,
                    breakout=0.25,
                    risk=0.05,
                ),
                thresholds=RankingThresholds(
                    strong_buy=90,
                    buy=75,
                    watch=60,
                    hold=45,
                ),
            ),
        )

    @classmethod
    def all(cls) -> tuple[RankingProfile, ...]:
        return (
            cls.growth(),
            cls.swing(),
            cls.income(),
            cls.conservative(),
            cls.breakout(),
        )

    @classmethod
    def names(cls) -> tuple[str, ...]:
        return tuple(
            profile.name
            for profile in cls.all()
        )