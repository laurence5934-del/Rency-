from __future__ import annotations

from collections.abc import Iterable

from app.ai.ranking_config import RankingConfig
from app.ai.ranking_models import (
    RankingResult,
    RankingSummary,
)
from app.ai.recommendation_models import Recommendation
from app.watchlist.watchlist_models import WatchlistEntry


class RankingEngine:
    """
    Weighted multi-factor ranking engine for watchlist entries.
    """

    def __init__(
        self,
        config: RankingConfig | None = None,
    ) -> None:
        self.config = config or RankingConfig()

    def rank_entry(
        self,
        entry: WatchlistEntry,
    ) -> RankingResult:
        if not isinstance(entry, WatchlistEntry):
            raise TypeError(
                "entry must be a WatchlistEntry."
            )

        self._validate_factor_scores(entry)

        overall_score = self._calculate_overall_score(entry)
        confidence = self._calculate_confidence(entry)
        recommendation = self._recommend(overall_score)
        explanations = self._build_explanations(entry)

        return RankingResult(
            symbol=entry.symbol,
            overall_score=round(overall_score, 4),
            confidence=round(confidence, 4),
            recommendation=recommendation,
            trend_score=entry.trend_score,
            momentum_score=entry.momentum_score,
            volume_score=entry.volume_score,
            breakout_score=entry.breakout_score,
            risk_score=entry.risk_score,
            explanations=explanations,
        )

    def rank_entries(
        self,
        entries: Iterable[WatchlistEntry],
    ) -> RankingSummary:
        if isinstance(entries, (str, bytes)):
            raise TypeError(
                "entries must be an iterable of WatchlistEntry objects."
            )

        try:
            entry_list = list(entries)
        except TypeError as exc:
            raise TypeError(
                "entries must be an iterable of WatchlistEntry objects."
            ) from exc

        results = tuple(
            self.rank_entry(entry)
            for entry in entry_list
        )

        ordered_results = tuple(
            sorted(
                results,
                key=lambda result: (
                    -result.overall_score,
                    -result.confidence,
                    result.symbol,
                ),
            )
        )

        return RankingSummary(
            results=ordered_results,
        )

    def _calculate_overall_score(
        self,
        entry: WatchlistEntry,
    ) -> float:
        weights = self.config.weights

        return (
            entry.trend_score * weights.trend
            + entry.momentum_score * weights.momentum
            + entry.volume_score * weights.volume
            + entry.breakout_score * weights.breakout
            + entry.risk_score * weights.risk
        )

    def _calculate_confidence(
        self,
        entry: WatchlistEntry,
    ) -> float:
        scores = (
            entry.trend_score,
            entry.momentum_score,
            entry.volume_score,
            entry.breakout_score,
            entry.risk_score,
        )

        average = sum(scores) / len(scores)

        spread = max(scores) - min(scores)

        consistency_component = max(
            0.0,
            100.0 - spread,
        )

        raw_confidence = (
            average * 0.60
            + consistency_component * 0.40
        )

        return min(
            self.config.max_confidence,
            max(
                self.config.min_confidence,
                raw_confidence,
            ),
        )

    def _recommend(
        self,
        overall_score: float,
    ) -> Recommendation:
        thresholds = self.config.thresholds

        if overall_score >= thresholds.strong_buy:
            return Recommendation.STRONG_BUY

        if overall_score >= thresholds.buy:
            return Recommendation.BUY

        if overall_score >= thresholds.watch:
            return Recommendation.WATCH

        if overall_score >= thresholds.hold:
            return Recommendation.HOLD

        return Recommendation.SELL

    @staticmethod
    def _build_explanations(
        entry: WatchlistEntry,
    ) -> tuple[str, ...]:
        explanations: list[str] = []

        factor_messages = (
            (
                entry.trend_score,
                "Strong trend",
                "Weak trend",
            ),
            (
                entry.momentum_score,
                "Strong momentum",
                "Weak momentum",
            ),
            (
                entry.volume_score,
                "Strong volume participation",
                "Weak volume participation",
            ),
            (
                entry.breakout_score,
                "Strong breakout conditions",
                "Weak breakout conditions",
            ),
            (
                entry.risk_score,
                "Favorable risk profile",
                "Elevated risk profile",
            ),
        )

        for score, positive_message, negative_message in factor_messages:
            if score >= 70.0:
                explanations.append(positive_message)
            elif score <= 40.0:
                explanations.append(negative_message)

        if not explanations:
            explanations.append(
                "Balanced factor profile"
            )

        return tuple(explanations)

    @staticmethod
    def _validate_factor_scores(
        entry: WatchlistEntry,
    ) -> None:
        factor_scores = {
            "trend_score": entry.trend_score,
            "momentum_score": entry.momentum_score,
            "volume_score": entry.volume_score,
            "breakout_score": entry.breakout_score,
            "risk_score": entry.risk_score,
        }

        for name, value in factor_scores.items():
            if not isinstance(value, (int, float)):
                raise TypeError(
                    f"{name} must be numeric."
                )

            if not 0.0 <= value <= 100.0:
                raise ValueError(
                    f"{name} must be between 0 and 100."
                )