from __future__ import annotations

from app.ai.ranking_models import RankingResult
from app.ai.recommendation_models import Recommendation


class RecommendationRules:
    """
    Reusable rules for converting ranking results into
    strengths, weaknesses, risks, and suggested actions.
    """

    @staticmethod
    def strengths(
        result: RankingResult,
    ) -> tuple[str, ...]:
        RecommendationRules._validate_result(result)

        strengths: list[str] = []

        if result.trend_score >= 70:
            strengths.append("Strong price trend")

        if result.momentum_score >= 70:
            strengths.append("Strong market momentum")

        if result.volume_score >= 70:
            strengths.append("Healthy volume participation")

        if result.breakout_score >= 70:
            strengths.append("Favorable breakout conditions")

        if result.risk_score >= 70:
            strengths.append("Favorable risk profile")

        return tuple(strengths)

    @staticmethod
    def weaknesses(
        result: RankingResult,
    ) -> tuple[str, ...]:
        RecommendationRules._validate_result(result)

        weaknesses: list[str] = []

        if result.trend_score <= 40:
            weaknesses.append("Weak price trend")

        if result.momentum_score <= 40:
            weaknesses.append("Weak market momentum")

        if result.volume_score <= 40:
            weaknesses.append("Limited volume participation")

        if result.breakout_score <= 40:
            weaknesses.append("Breakout conditions are weak")

        return tuple(weaknesses)

    @staticmethod
    def risks(
        result: RankingResult,
    ) -> tuple[str, ...]:
        RecommendationRules._validate_result(result)

        risks: list[str] = []

        if result.risk_score <= 40:
            risks.append("Elevated risk profile")
        elif result.risk_score < 70:
            risks.append("Moderate risk profile")

        if result.confidence < 50:
            risks.append("Low recommendation confidence")

        if (
            result.trend_score >= 70
            and result.momentum_score <= 40
        ):
            risks.append(
                "Momentum does not confirm the current trend"
            )

        if (
            result.breakout_score >= 70
            and result.volume_score <= 40
        ):
            risks.append(
                "Breakout lacks strong volume confirmation"
            )

        return tuple(risks)

    @staticmethod
    def suggested_actions(
        result: RankingResult,
    ) -> tuple[str, ...]:
        RecommendationRules._validate_result(result)

        recommendation = result.recommendation

        if recommendation is Recommendation.STRONG_BUY:
            return (
                "Consider initiating a position",
                "Use disciplined position sizing",
                "Define a protective exit before entry",
            )

        if recommendation is Recommendation.BUY:
            return (
                "Consider initiating a partial position",
                "Add only if technical strength continues",
                "Monitor risk and breakout confirmation",
            )

        if recommendation is Recommendation.WATCH:
            return (
                "Keep the symbol on the active watchlist",
                "Wait for stronger technical confirmation",
                "Reassess after meaningful price or volume changes",
            )

        if recommendation is Recommendation.HOLD:
            return (
                "Avoid increasing exposure without improvement",
                "Monitor support levels and momentum",
                "Review the position if conditions weaken",
            )

        return (
            "Avoid initiating a new position",
            "Consider reducing exposure if already held",
            "Wait for the ranking factors to improve",
        )

    @staticmethod
    def _validate_result(
        result: RankingResult,
    ) -> None:
        if not isinstance(result, RankingResult):
            raise TypeError(
                "result must be a RankingResult."
            )
        