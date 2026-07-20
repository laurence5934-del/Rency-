from __future__ import annotations

from collections.abc import Iterable

from app.ai.ranking_models import RankingResult
from app.ai.recommendation_models import RecommendationReport
from app.ai.recommendation_rules import RecommendationRules


class RecommendationEngine:
    """
    Generates complete AI recommendation reports
    from ranking results.
    """

    def generate(
        self,
        result: RankingResult,
    ) -> RecommendationReport:
        if not isinstance(result, RankingResult):
            raise TypeError(
                "result must be a RankingResult."
            )

        return RecommendationReport(
            symbol=result.symbol,
            recommendation=result.recommendation,
            confidence=result.confidence,
            overall_score=result.overall_score,
            strengths=RecommendationRules.strengths(result),
            weaknesses=RecommendationRules.weaknesses(result),
            risks=RecommendationRules.risks(result),
            suggested_actions=RecommendationRules.suggested_actions(result),
        )

    def generate_many(
        self,
        results: Iterable[RankingResult],
    ) -> tuple[RecommendationReport, ...]:
        if isinstance(results, (str, bytes)):
            raise TypeError(
                "results must be an iterable of RankingResult objects."
            )

        try:
            result_list = list(results)
        except TypeError as exc:
            raise TypeError(
                "results must be an iterable of RankingResult objects."
            ) from exc

        return tuple(
            self.generate(result)
            for result in result_list
        )