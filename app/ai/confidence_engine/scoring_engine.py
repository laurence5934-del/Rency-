from __future__ import annotations

from .models import ConfidenceFactor, ConfidenceInput


class ConfidenceScoringEngine:
    DEFAULT_WEIGHTS = {
        "consensus_score": 0.22,
        "agreement_ratio": 0.14,
        "contributor_reputation": 0.14,
        "validation_quality": 0.16,
        "data_completeness": 0.12,
        "freshness_score": 0.10,
        "stability_score": 0.12,
    }

    def calculate(
        self,
        source: ConfidenceInput,
    ) -> tuple[float, tuple[ConfidenceFactor, ...], dict[str, float]]:
        factors = tuple(
            ConfidenceFactor(
                name=name,
                score=float(getattr(source, name)),
                weight=weight,
                rationale=f"{name.replace('_', ' ').title()} contribution",
            )
            for name, weight in self.DEFAULT_WEIGHTS.items()
        )

        weighted_score = sum(factor.score * factor.weight for factor in factors)
        total_weight = sum(factor.weight for factor in factors)
        base_score = weighted_score / total_weight if total_weight else 0.0

        penalties = {
            "volatility_penalty": source.volatility_penalty,
            "uncertainty_penalty": source.uncertainty_penalty,
        }
        total_penalty = min(1.0, sum(penalties.values()))

        final_score = max(0.0, min(1.0, base_score * (1.0 - total_penalty)))
        return final_score, factors, penalties
